#!/usr/bin/env python3
"""Issue #277 (P4) contract: the KW read-only original-record index.

Checked here, all against temp-dir fixtures (never the real KW repo, never a real
consumer checkout):

* ``scripts/kaola-kw-index.py`` lists original KW records as
  ``{kind, path, sha256, schema_or_unknown}`` with typed ``present`` / ``absent`` /
  ``unsupported`` results — including an ``unsupported`` schema-version case and a
  mission-ledger shape violation;
* the reader writes nothing anywhere: a full directory snapshot (path set, sizes,
  hashes) is byte-identical before and after a run;
* the two named digest views of the P4 contract CAN disagree: faithful test-only
  replicas of KW's ``computeCodeTreeHash`` (finalize-gate view,
  ``kaola-workflow-adaptive-schema.js:1124-1143`` at KW @16cab12d) and
  ``computeLandableTreeDigest`` (landable-record view,
  ``kaola-workflow-validation-runner.js:554-599``) over the same fixture tree return
  different values, and their covered path SETS diverge on a non-ASCII inert path
  (the gate view's quoted ``ls-tree`` token matches no inert-dir prefix).

Not checked: the cross-repo Python/JS same-schema validators (a later P4 sub-stage,
out of scope for this slice) and any wiring of the reader into skills/, templates/,
render, or Host dispatch (deliberately absent in this run).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
READER = PROJECT / "scripts" / "kaola-kw-index.py"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@test",
    "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@test",
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
}


def git(root: Path, *args: str, index: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ)
    env.update(GIT_ENV)
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    return subprocess.run(
        ["git", "-C", str(root), *args], env=env, capture_output=True, timeout=30)


def run_reader(root: Path, *extra: str) -> dict:
    result = subprocess.run(
        ["python3", str(READER), "--root", str(root), *extra],
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def make_run(root: Path, name: str) -> Path:
    run = root / "kaola-workflow" / name
    (run / ".cache" / "origin").mkdir(parents=True)
    (run / "workflow-state.md").write_text(
        f"# Kaola-Workflow State\n\n## Project\nname: {name}\nstatus: active\n\n"
        "## Sink\nissue_number: 7\nbranch: workflow/issue-7\n", encoding="utf-8")
    return run


def snapshot_tree(root: Path) -> dict[str, tuple[int, str]]:
    snap: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            snap[rel] = (-1, "symlink:" + os.readlink(path))
        elif path.is_file():
            snap[rel] = (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())
        else:
            snap[rel] = (-1, "dir")
    return snap


# ── Test-only replicas of the two KW digest views (P4 contract §4). These are
# demonstrations of the documented algorithms for the divergence fixture — NOT the
# later cross-repo validator, which is out of scope for this slice.

SELF_HOST_TEST_CONSUMED = [
    "README.md", "CHANGELOG.md", "docs/api.md",
    "docs/workflow-state-contract.md", "docs/agents-source.md",
]


def kw_is_invisible(rel: str, extra: list[str], self_host: bool) -> bool:
    """The band both views intend: consumed prose stays CODE; inert dirs drop."""
    consumed = set(SELF_HOST_TEST_CONSUMED if self_host else []) | set(extra)
    if rel in consumed:
        return False
    if rel in ("README.md", "CHANGELOG.md") or rel.startswith("docs/"):
        return True
    if rel.startswith("kaola-workflow/"):
        return True
    return False


def snapshot_worktree(root: Path, index: Path) -> str:
    git(root, "read-tree", "HEAD", index=index)  # zero-commit repos: skipped, empty base
    git(root, "add", "-A", index=index)
    return git(root, "write-tree", index=index).stdout.decode().strip()


def finalize_gate_view(root: Path, project: str | None = None, extra: list[str] | None = None,
                       self_host: bool = False) -> tuple[str, list[str]]:
    """Replica of computeCodeTreeHash (adaptive-schema.js:1124-1143).

    `ls-tree -r` text lines (C-quoted paths), `\\n` join, JS-string sort (UTF-16
    code-unit order, reproduced via utf-16-be byte order).
    """
    with tempfile.TemporaryDirectory() as tmp:
        tree = snapshot_worktree(root, Path(tmp) / "idx")
    listing = git(root, "ls-tree", "-r", tree).stdout.decode("utf-8", "surrogateescape")
    lines = [ln for ln in (s.rstrip("\r") for s in listing.split("\n")) if ln]
    kept = []
    for line in lines:
        tab = line.find("\t")
        rel = line[tab + 1:] if tab >= 0 else line
        if not kw_is_invisible(rel, extra or [], self_host):
            kept.append(line)
    kept.sort(key=lambda s: s.encode("utf-16-be", "surrogatepass"))  # JS string sort
    digest = hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()
    return digest, kept


def landable_record_view(root: Path, extra: list[str] | None = None,
                         self_host: bool = False) -> tuple[str, list[bytes]]:
    """Replica of computeLandableTreeDigest (validation-runner.js:554-599).

    `ls-tree -r -z` raw NUL records, per-record NUL suffix, Buffer.compare (byte) sort.
    """
    with tempfile.TemporaryDirectory() as tmp:
        index = Path(tmp) / "idx"
        has_head = git(root, "rev-parse", "--verify", "HEAD").returncode == 0
        git(root, "read-tree", "HEAD" if has_head else "--empty", index=index)
        git(root, "add", "-A", index=index)
        tree = git(root, "write-tree", index=index).stdout.decode().strip()
    out = git(root, "ls-tree", "-r", "-z", tree).stdout
    records = []
    for record in out.split(b"\x00"):
        if not record:
            continue
        tab = record.find(b"\t")
        rel = record[tab + 1:].decode("utf-8")
        if not kw_is_invisible(rel, extra or [], self_host):
            records.append(record)
    records.sort()  # Buffer.compare: byte order
    digest = hashlib.sha256()
    for record in records:
        digest.update(record)
        digest.update(b"\x00")
    return digest.hexdigest(), records


def covered_rel(kept_line: str) -> str:
    return kept_line.split("\t", 1)[1] if "\t" in kept_line else kept_line


class IndexPresentAbsent(unittest.TestCase):
    def test_present_absent_and_schema_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = make_run(root, "issue-7")
            (run / ".cache" / "chain-receipt.json").write_text(
                json.dumps({"headSha": "a" * 40, "codeTreeHash": "b" * 64, "chains": []}),
                encoding="utf-8")
            (run / ".cache" / "origin" / "selection-record.json").write_text(
                json.dumps({"selection_mode": "explicit-target"}), encoding="utf-8")
            vectors = run / ".cache" / "validation-vectors"
            vectors.mkdir()
            (vectors / "v.json").write_text(json.dumps(
                {"schema_version": 1, "kind": "validation_vector",
                 "candidate_digest": "c" * 64}), encoding="utf-8")
            ledger_dir = root / "kaola-workflow" / ".ledger"
            ledger_dir.mkdir()
            (ledger_dir / "issue-7.jsonl").write_text(
                '{"n":1,"name":"a","details":"","status":"done"}\n', encoding="utf-8")
            index = run_reader(root, "--project", "issue-7", "--issue", "7")

        by_path = {e["path"]: e for e in index["records"]}
        state = by_path["kaola-workflow/issue-7/workflow-state.md"]
        self.assertEqual(state["status"], "present")
        self.assertEqual(state["kind"], "workflow-state")
        self.assertRegex(state["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(state["schema_or_unknown"], "unknown")

        ledger = by_path["kaola-workflow/.ledger/issue-7.jsonl"]
        self.assertEqual((ledger["kind"], ledger["status"], ledger["location"]),
                         ("mission-ledger", "present", "ledger"))

        vector = by_path["kaola-workflow/issue-7/.cache/validation-vectors/v.json"]
        self.assertEqual(vector["status"], "present")
        self.assertEqual(vector["schema_or_unknown"], "validation_vector/1")
        views = {d["field"]: d["view"] for d in vector["digest_fields"]}
        self.assertEqual(views["candidate_digest"], "landable-record")

        receipt = by_path["kaola-workflow/issue-7/.cache/chain-receipt.json"]
        views = {d["field"]: d["view"] for d in receipt["digest_fields"]}
        self.assertEqual(views["codeTreeHash"], "finalize-gate")

        # Terminal and unwritten records are typed absent, never synthesized.
        for rel in ("kaola-workflow/issue-7/finalization-summary.md",
                    "kaola-workflow/issue-7/.cache/sink-receipt.json",
                    "kaola-workflow/.roadmap/_rules.md"):
            self.assertEqual(by_path[rel]["status"], "absent", rel)
            self.assertIsNone(by_path[rel]["sha256"])
        self.assertEqual(index["summary"]["unsupported"], 0)


class IndexUnsupported(unittest.TestCase):
    def test_unsupported_schema_and_shape_classes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = make_run(root, "issue-8")
            vectors = run / ".cache" / "validation-vectors"
            vectors.mkdir()
            (vectors / "newer.json").write_text(json.dumps(
                {"schema_version": 2, "kind": "validation_vector"}), encoding="utf-8")
            (vectors / "junk.json").write_text("not json {", encoding="utf-8")
            (run / ".cache" / "outcome-log.jsonl").write_text(
                '{"v":2,"ts":"t"}\n', encoding="utf-8")
            ledger_dir = root / "kaola-workflow" / ".ledger"
            ledger_dir.mkdir()
            (ledger_dir / "issue-8.jsonl").write_text(
                '{"n":1,"name":"a","details":"","status":"bogus"}\n', encoding="utf-8")
            index = run_reader(root, "--project", "issue-8", "--issue", "8")

        by_path = {e["path"]: e for e in index["records"]}
        newer = by_path["kaola-workflow/issue-8/.cache/validation-vectors/newer.json"]
        self.assertEqual(newer["status"], "unsupported")
        self.assertEqual(newer["reason"], "schema-version-unsupported")
        junk = by_path["kaola-workflow/issue-8/.cache/validation-vectors/junk.json"]
        self.assertEqual((junk["status"], junk["reason"]), ("unsupported", "unparseable-json"))
        log = by_path["kaola-workflow/issue-8/.cache/outcome-log.jsonl"]
        self.assertEqual((log["status"], log["reason"]),
                         ("unsupported", "schema-version-unsupported"))
        ledger = by_path["kaola-workflow/.ledger/issue-8.jsonl"]
        self.assertEqual((ledger["status"], ledger["reason"]),
                         ("unsupported", "ledger-shape-violation"))
        # An unsupported entry still reports the artifact's own hash — it indexes
        # what exists, it just refuses to stand behind its schema.
        self.assertRegex(ledger["sha256"], r"^[0-9a-f]{64}$")


class ReaderWritesNothing(unittest.TestCase):
    def test_directory_snapshot_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = make_run(root, "issue-9")
            (run / ".cache" / "chain-receipt.json").write_text("{}", encoding="utf-8")
            archive = root / "kaola-workflow" / "archive" / "issue-3"
            archive.mkdir(parents=True)
            (archive / "workflow-state.md").write_text("state", encoding="utf-8")
            (archive / "mission-ledger.jsonl").write_text(
                '{"n":1,"name":"a","details":"","status":"done"}\n', encoding="utf-8")
            before = snapshot_tree(root)
            index = run_reader(root)
            after = snapshot_tree(root)
        self.assertEqual(before, after)
        kinds = {e["kind"] for e in index["records"]}
        self.assertIn("mission-ledger-archive", kinds)


class DigestViewsDisagree(unittest.TestCase):
    def _repo(self, root: Path) -> None:
        git(root, "init", "-q")
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")
        (root / "docs").mkdir()
        (root / "docs" / "plain.md").write_text("inert\n", encoding="utf-8")
        (root / "kaola-workflow" / "issue-1").mkdir(parents=True)
        (root / "kaola-workflow" / "issue-1" / "workflow-state.md").write_text(
            "state\n", encoding="utf-8")
        (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
        (root / "ignored").mkdir()
        (root / "ignored" / "skip.bin").write_bytes(b"\x00\x01")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "fixture")

    def test_views_return_different_values_on_one_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            gate, gate_set = finalize_gate_view(root)
            record, record_set = landable_record_view(root)
        # Same covered set (all ASCII here) — the digests STILL differ, because the
        # two views hash different preimages ('\n'-joined lines vs NUL-suffixed
        # records). This is the documented T8e fact: same tree, different value.
        self.assertEqual([covered_rel(l) for l in gate_set],
                         [r.split(b"\t", 1)[1].decode() for r in record_set])
        self.assertNotEqual(gate, record)

    def test_non_ascii_inert_path_diverges_the_covered_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            (root / "docs" / "日本語.md").write_text("inert\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-qm", "non-ascii inert doc")
            _, gate_set = finalize_gate_view(root)
            _, record_set = landable_record_view(root)
        gate_paths = [covered_rel(l) for l in gate_set]
        record_paths = [r.split(b"\t", 1)[1].decode("utf-8") for r in record_set]
        # The record view sees raw -z bytes: docs/日本語.md matches the docs/ prefix
        # and drops out. The gate view sees a C-quoted token ("docs/\346...") that
        # matches no inert prefix — the same file stays IN its hash input.
        self.assertNotIn("docs/日本語.md", record_paths)
        self.assertTrue(
            any("docs/" in p and "日本語" not in p for p in gate_paths),
            f"gate view should keep the quoted inert path: {gate_paths}")
        self.assertNotIn("docs/日本語.md", gate_paths)


if __name__ == "__main__":
    unittest.main(verbosity=2)
