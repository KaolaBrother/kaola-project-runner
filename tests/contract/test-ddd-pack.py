#!/usr/bin/env python3
"""Issue #282: optional read-only checker scripts/kaola-ddd-pack.py.

The suite exercises the checker. It is not a gate on pack meaning.
render-skills.py --check on this tree exits 1 because the protected Grok Bot
pin 3de9f61a is stale; that failure is pre-existing and is not this suite's
defect. The render assertion accepts that pin result and a future clean pass.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

PROJECT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT / "scripts" / "kaola-ddd-pack.py"
VALIDATE = PROJECT / "scripts" / "validate.sh"
README = PROJECT / "docs" / "ddd" / "README.md"
PILOT = PROJECT / "docs" / "ddd" / "packs" / "c4-state-retire.md"
NOTE = "A clean run proves form and references only, not meaning or contract satisfaction."
SECTIONS = (
    "Vocabulary",
    "Inputs and outputs",
    "Invariants",
    "Dependency contracts",
    "Acceptance",
    "Expected-change surface",
    "Evolution",
    "Evidence",
)


def load_checker():
    spec = importlib.util.spec_from_file_location("kaola_ddd_pack", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load kaola-ddd-pack.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECKER = load_checker()


def head_commit() -> str:
    return subprocess.check_output(
        ["git", "-C", str(PROJECT), "rev-parse", "HEAD"], text=True
    ).strip()


HEAD = head_commit()


def default_body() -> str:
    return "\n".join(
        [
            "## Vocabulary",
            "record means one current row.",
            "",
            "## Inputs and outputs",
            "`scripts/kaola-dispatch.py` is the state tool.",
            "",
            "## Invariants",
            "The file changes under one lock.",
            "",
            "## Dependency contracts",
            "- sample seam. suite: test-issue-271-dispatch-help.py",
            "",
            "## Acceptance",
            "A handled row leaves the file.",
            "",
            "## Expected-change surface",
            "`scripts/kaola-dispatch.py`",
            "",
            "## Evolution",
            "Refresh the pack when the tool moves.",
            "",
            "## Evidence",
            f"Checked at `{HEAD}`.",
            "",
        ]
    )


def front_matter(**overrides: str) -> dict[str, str]:
    data = {
        "pack_schema": "kaola-ddd-pack/1",
        "id": "sample",
        "status": "current",
        "owner": "host",
        "context_primary": "orchestration-state/C4-state",
        "contexts_touched": "none",
        "baseline_commit": HEAD,
    }
    data.update(overrides)
    return data


def render_pack(front: dict[str, str], body: str | None = None, drop: tuple[str, ...] = ()) -> str:
    lines = ["---"]
    for key, value in front.items():
        if key in drop:
            continue
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append(body if body is not None else default_body())
    return "\n".join(lines) + "\n"


def run_check(*packs: str, repo: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "check", "--repo", str(repo or PROJECT), *packs]
    return subprocess.run(cmd, capture_output=True, text=True)


def payload(proc: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(proc.stdout)


def error_checks(pack: dict) -> list[str]:
    return [item["check"] for item in pack["findings"] if item["severity"] == "error"]


class DddPackChecker(unittest.TestCase):
    def test_valid_pack_is_ok_and_states_the_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front_matter()), encoding="utf-8")
            proc = run_check(str(path))
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = payload(proc)
        self.assertEqual(data["schema"], "kaola-ddd-check/1")
        self.assertEqual(data["result"], "ok")
        self.assertEqual(data["note"], NOTE)
        self.assertEqual(data["counts"], {"ok": 1, "invalid": 0, "unsupported": 0})
        self.assertEqual(data["packs"][0]["status"], "ok")
        self.assertEqual(data["packs"][0]["id"], "sample")
        self.assertEqual(data["packs"][0]["findings"], [])

    def test_unmapped_primary_is_valid_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(
                render_pack(front_matter(context_primary="unmapped")),
                encoding="utf-8",
            )
            proc = run_check(str(path))
        self.assertEqual(payload(proc)["packs"][0]["status"], "ok", proc.stdout)

    def test_missing_context_primary_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(
                render_pack(front_matter(), drop=("context_primary",)),
                encoding="utf-8",
            )
            proc = run_check(str(path))
        self.assertEqual(proc.returncode, 1)
        pack = payload(proc)["packs"][0]
        self.assertEqual(pack["status"], "invalid")
        self.assertTrue(
            any("context_primary" in item["message"] for item in pack["findings"])
        )

    def test_missing_contexts_touched_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(
                render_pack(front_matter(), drop=("contexts_touched",)),
                encoding="utf-8",
            )
            proc = run_check(str(path))
        self.assertEqual(proc.returncode, 1)
        messages = " ".join(item["message"] for item in payload(proc)["packs"][0]["findings"])
        self.assertIn("contexts_touched", messages)

    def test_bad_contexts_touched_shape_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(
                render_pack(front_matter(contexts_touched="nope")),
                encoding="utf-8",
            )
            proc = run_check(str(path))
        self.assertEqual(payload(proc)["packs"][0]["status"], "invalid")
        self.assertIn("front-matter", error_checks(payload(proc)["packs"][0]))

    def test_missing_section_is_invalid(self) -> None:
        body = default_body().replace("## Evidence\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front_matter(), body=body), encoding="utf-8")
            proc = run_check(str(path))
        pack = payload(proc)["packs"][0]
        self.assertEqual(pack["status"], "invalid")
        self.assertIn("sections", error_checks(pack))
        self.assertTrue(any("Evidence" in item["message"] for item in pack["findings"]))

    def test_sections_out_of_order_are_invalid(self) -> None:
        body = default_body().replace(
            "## Evolution\nRefresh the pack when the tool moves.\n\n## Evidence\n",
            "## Evidence\nChecked.\n\n## Evolution\nRefresh the pack when the tool moves.\n",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front_matter(), body=body), encoding="utf-8")
            proc = run_check(str(path))
        messages = [item["message"] for item in payload(proc)["packs"][0]["findings"]]
        self.assertIn("sections out of order", messages)

    def test_suite_name_must_be_in_the_inventory(self) -> None:
        body = default_body().replace(
            "suite: test-issue-271-dispatch-help.py",
            "suite: test-not-in-inventory.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front_matter(), body=body), encoding="utf-8")
            proc = run_check(str(path))
        pack = payload(proc)["packs"][0]
        self.assertEqual(pack["status"], "invalid")
        self.assertTrue(any(item["check"] == "suite" for item in pack["findings"]))

    def test_suite_none_gap_is_not_an_inventory_lookup(self) -> None:
        body = default_body().replace(
            "suite: test-issue-271-dispatch-help.py",
            "suite: none (gap: G0 — example only)",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front_matter(), body=body), encoding="utf-8")
            proc = run_check(str(path))
        self.assertEqual(payload(proc)["packs"][0]["status"], "ok", proc.stdout)

    def test_suite_none_without_gap_is_invalid(self) -> None:
        body = default_body().replace(
            "suite: test-issue-271-dispatch-help.py",
            "suite: none",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front_matter(), body=body), encoding="utf-8")
            proc = run_check(str(path))
        self.assertEqual(payload(proc)["packs"][0]["status"], "invalid")
        self.assertIn("suite", error_checks(payload(proc)["packs"][0]))

    def test_cited_path_must_exist(self) -> None:
        body = default_body().replace(
            "scripts/kaola-dispatch.py",
            "scripts/no-such-ddd-pack-target.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front_matter(), body=body), encoding="utf-8")
            proc = run_check(str(path))
        pack = payload(proc)["packs"][0]
        self.assertEqual(pack["status"], "invalid")
        self.assertTrue(any("no-such-ddd-pack-target.py" in item["message"] for item in pack["findings"]))

    def test_undefined_alias_is_an_invalid_path(self) -> None:
        body = default_body() + "\nSee `ZZ:10`.\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front_matter(), body=body), encoding="utf-8")
            proc = run_check(str(path))
        self.assertTrue(
            any("undefined citation alias: ZZ" in item["message"] for item in payload(proc)["packs"][0]["findings"])
        )

    def test_baseline_commit_must_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(
                render_pack(
                    front_matter(baseline_commit="0000000000000000000000000000000000000000")
                ),
                encoding="utf-8",
            )
            proc = run_check(str(path))
        pack = payload(proc)["packs"][0]
        self.assertEqual(pack["status"], "invalid")
        self.assertIn("baseline", error_checks(pack))

    def test_forbidden_authority_keys_are_invalid(self) -> None:
        for key in ("grant", "seats", "writer_permission", "elite_cap", "approved_by"):
            with self.subTest(key=key):
                front = front_matter()
                front["id"] = "sample"
                front[key] = "no"
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "sample.md"
                    path.write_text(render_pack(front), encoding="utf-8")
                    proc = run_check(str(path))
                pack = payload(proc)["packs"][0]
                self.assertEqual(pack["status"], "invalid")
                self.assertTrue(
                    any(item["check"] == "authority" and key in item["message"] for item in pack["findings"])
                )

    def test_unknown_descriptive_key_is_advisory(self) -> None:
        front = front_matter()
        front["note"] = "a descriptive aside"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front), encoding="utf-8")
            proc = run_check(str(path))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        pack = payload(proc)["packs"][0]
        self.assertEqual(pack["status"], "ok")
        self.assertEqual(
            [item for item in pack["findings"] if item["severity"] == "advisory"],
            [{"check": "unknown-key", "severity": "advisory", "message": "unknown descriptive key: note"}],
        )

    def test_capacity_is_not_an_authority_key(self) -> None:
        front = front_matter()
        front["capacity"] = "descriptive"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(render_pack(front), encoding="utf-8")
            proc = run_check(str(path))
        pack = payload(proc)["packs"][0]
        self.assertEqual(pack["status"], "ok", proc.stdout)
        self.assertNotIn("authority", error_checks(pack))

    def test_pilot_pack_is_ok(self) -> None:
        before = subprocess.check_output(
            ["git", "-C", str(PROJECT), "status", "--porcelain"], text=True
        )
        proc = run_check(str(PILOT))
        after = subprocess.check_output(
            ["git", "-C", str(PROJECT), "status", "--porcelain"], text=True
        )
        self.assertEqual(before, after)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        data = payload(proc)
        self.assertEqual(data["result"], "ok")
        self.assertEqual(data["note"], NOTE)
        self.assertEqual(len(data["packs"]), 1)
        pack = data["packs"][0]
        self.assertEqual(pack["path"], "docs/ddd/packs/c4-state-retire.md")
        self.assertEqual(pack["id"], "c4-state-retire")
        self.assertEqual(pack["status"], "ok")
        self.assertEqual(pack["findings"], [])

    def test_discovery_includes_the_pilot_and_not_the_map(self) -> None:
        # The pilot must be ok. Other packs are reported and do not have to be
        # ok for this suite: a pack is not a gate on the inventory.
        proc = run_check()
        data = payload(proc)
        self.assertIn(data["result"], {"ok", "invalid", "unsupported"})
        paths = [pack["path"] for pack in data["packs"]]
        self.assertIn("docs/ddd/packs/c4-state-retire.md", paths)
        self.assertNotIn("docs/ddd/context-map.md", paths)
        pilot = next(pack for pack in data["packs"] if pack["path"].endswith("c4-state-retire.md"))
        self.assertEqual(pilot["status"], "ok")
        self.assertEqual(pilot["findings"], [])

    def test_absent_when_docs_ddd_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_check(repo=Path(tmp))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        data = payload(proc)
        self.assertEqual(data["result"], "absent")
        self.assertEqual(data["packs"], [])
        self.assertEqual(data["counts"], {"ok": 0, "invalid": 0, "unsupported": 0})
        self.assertEqual(data["note"], NOTE)

    def test_absent_when_pack_directory_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "ddd" / "packs").mkdir(parents=True)
            (root / "docs" / "ddd" / "README.md").write_text("stay", encoding="utf-8")
            proc = run_check(repo=root)
        self.assertEqual(payload(proc)["result"], "absent")
        self.assertEqual(proc.returncode, 0)

    def test_unsupported_does_not_fail_another_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            future = root / "future.md"
            future.write_text(
                "---\npack_schema: kaola-ddd-pack/9\nid: future\n---\n\nno sections\n",
                encoding="utf-8",
            )
            sample = root / "sample.md"
            sample.write_text(render_pack(front_matter()), encoding="utf-8")
            proc = run_check(str(future), str(sample))
        self.assertEqual(proc.returncode, 3, proc.stdout)
        data = payload(proc)
        self.assertEqual(data["result"], "unsupported")
        self.assertEqual(data["counts"], {"ok": 1, "invalid": 0, "unsupported": 1})
        by_id = {pack["id"]: pack for pack in data["packs"]}
        self.assertEqual(by_id["sample"]["status"], "ok")
        self.assertEqual(by_id["future"]["status"], "unsupported")
        self.assertEqual([item["check"] for item in by_id["future"]["findings"]], ["pack_schema"])
        self.assertNotIn("sections", error_checks(by_id["future"]))

    def test_invalid_and_unsupported_aggregate_to_invalid(self) -> None:
        body = default_body().replace("## Evidence\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            broken = root / "sample.md"
            broken.write_text(render_pack(front_matter(), body=body), encoding="utf-8")
            future = root / "future.md"
            future.write_text(
                "---\npack_schema: kaola-ddd-pack/2\nid: future\ngrant: host\n---\n",
                encoding="utf-8",
            )
            sample = root / "other.md"
            other_front = front_matter(id="other")
            sample.write_text(render_pack(other_front), encoding="utf-8")
            proc = run_check(str(broken), str(future), str(sample))
        self.assertEqual(proc.returncode, 1, proc.stdout)
        data = payload(proc)
        self.assertEqual(data["result"], "invalid")
        self.assertEqual(data["counts"], {"ok": 1, "invalid": 1, "unsupported": 1})
        by_id = {pack["id"]: pack for pack in data["packs"]}
        self.assertEqual(by_id["sample"]["status"], "invalid")
        self.assertEqual(by_id["future"]["status"], "unsupported")
        self.assertEqual(by_id["other"]["status"], "ok")
        self.assertEqual([item["check"] for item in by_id["future"]["findings"]], ["pack_schema"])

    def test_usage_on_a_bad_command_line(self) -> None:
        for args in (
            [],
            ["--help"],
            ["check", "--bogus"],
            ["check", "--repo"],
        ):
            with self.subTest(args=args):
                proc = subprocess.run(
                    [sys.executable, str(SCRIPT), *args],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(proc.returncode, 2, proc.stdout)
                data = payload(proc)
                self.assertEqual(data["result"], "usage")
                self.assertEqual(data["packs"], [])
                self.assertEqual(data["note"], NOTE)

    def test_missing_repo_is_usage(self) -> None:
        missing = PROJECT / "no-such-ddd-repo-282"
        proc = run_check(repo=missing)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(payload(proc)["result"], "usage")

    def test_checker_has_no_yaml_or_network_dependency(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("import yaml", text)
        self.assertNotIn("urllib", text)
        self.assertNotIn("requests", text)
        self.assertIn("parse_flat_yaml", text)

    def test_suite_is_in_exactly_one_lane_and_matches_list(self) -> None:
        text = VALIDATE.read_text(encoding="utf-8")
        found = {}
        for name in ("python_suites_all", "python_suites_a", "python_suites_b", "shell_suites"):
            match = re.search(name + r"=\((.*?)\n\)", text, re.S)
            self.assertIsNotNone(match, name)
            found[name] = re.findall(r'"([^"]+)"', match.group(1))
        self.assertIn("test-ddd-pack.py", found["python_suites_all"])
        lanes = [name for name in ("python_suites_a", "python_suites_b") if "test-ddd-pack.py" in found[name]]
        self.assertEqual(lanes, ["python_suites_b"])
        names = CHECKER.inventory_names(text)
        self.assertIsNotNone(names)
        self.assertEqual(names.count("test-ddd-pack.py"), 1)
        bash = shutil.which("bash") or "bash"
        version = subprocess.run([bash, "--version"], capture_output=True, text=True)
        match = re.search(r"version (\d+)", version.stdout)
        if not match or int(match.group(1)) < 4:
            self.skipTest("prerequisite missing: bash >= 4 is required to run validate.sh --list")
        listed = subprocess.run(
            [bash, str(VALIDATE), "--list"],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "NO_COLOR": "1"},
        )
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(listed.stdout.splitlines(), names)

    def test_readme_records_usage_uninstall_and_dropped_checks(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn("scripts/kaola-ddd-pack.py check", text)
        self.assertIn(NOTE, text)
        self.assertIn("docs/ddd/", text)
        self.assertIn("the pilot's presence check passed every term", text.lower())
        self.assertIn("this check is unmeasured", text)
        self.assertIn("no grammar that binds a symbol to those lines", text)
        self.assertIn("test-ddd-pack.py", text)
        self.assertIn("Deleting them is a separate action", text)

    def test_default_uninstall_keeps_docs_and_an_unrelated_suite(self) -> None:
        for rel in (
            "scripts/render-skills.py",
            "scripts/kaola-dispatch.py",
            "scripts/kaola-record-contract.py",
        ):
            self.assertNotIn("kaola-ddd-pack", (PROJECT / rel).read_text(encoding="utf-8"))
        orchestrator = PROJECT / "templates" / "orchestrator"
        for path in orchestrator.rglob("*"):
            if path.is_file():
                self.assertNotIn(
                    "kaola-ddd-pack",
                    path.read_text(encoding="utf-8", errors="replace"),
                    path,
                )
        original_docs = {
            path.relative_to(PROJECT / "docs" / "ddd").as_posix(): path.read_bytes()
            for path in (PROJECT / "docs" / "ddd").rglob("*")
            if path.is_file()
        }
        self.assertIn("packs/c4-state-retire.md", original_docs)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "tests" / "contract").mkdir(parents=True)
            shutil.copy(PROJECT / "scripts" / "kaola-dispatch.py", root / "scripts" / "kaola-dispatch.py")
            # execute --help imports the sibling record contract at load time,
            # and the contract loads the shared #278 path helper (#292).
            shutil.copy(
                PROJECT / "scripts" / "kaola-record-contract.py",
                root / "scripts" / "kaola-record-contract.py",
            )
            shutil.copy(
                PROJECT / "scripts" / "kaola-acp-paths.py",
                root / "scripts" / "kaola-acp-paths.py",
            )
            validate = VALIDATE.read_text(encoding="utf-8")
            removed = "\n".join(
                line for line in validate.splitlines() if line.strip() != '"test-ddd-pack.py"'
            ) + "\n"
            self.assertNotIn('"test-ddd-pack.py"', removed)
            self.assertIn('"test-issue-271-dispatch-help.py"', removed)
            (root / "scripts" / "validate.sh").write_text(removed, encoding="utf-8")
            shutil.copy(
                PROJECT / "tests" / "contract" / "test-issue-271-dispatch-help.py",
                root / "tests" / "contract" / "test-issue-271-dispatch-help.py",
            )
            shutil.copytree(PROJECT / "docs" / "ddd", root / "docs" / "ddd")
            self.assertFalse((root / "scripts" / "kaola-ddd-pack.py").exists())
            self.assertFalse((root / "tests" / "contract" / "test-ddd-pack.py").exists())
            copied_docs = {
                path.relative_to(root / "docs" / "ddd").as_posix(): path.read_bytes()
                for path in (root / "docs" / "ddd").rglob("*")
                if path.is_file()
            }
            self.assertEqual(copied_docs, original_docs)
            proc = subprocess.run(
                [sys.executable, str(root / "tests" / "contract" / "test-issue-271-dispatch-help.py")],
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertTrue((PROJECT / "docs" / "ddd" / "packs" / "c4-state-retire.md").is_file())
        self.assertTrue(SCRIPT.is_file())

    def test_render_check_does_not_depend_on_the_checker(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(PROJECT / "scripts" / "render-skills.py"), "--check"],
            cwd=PROJECT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc.returncode == 0:
            self.assertIn("PASS", proc.stdout)
            return
        lines = [line for line in proc.stderr.splitlines() if line.strip()]
        self.assertTrue(lines, proc.stdout + proc.stderr)
        for line in lines:
            self.assertTrue(line.startswith("pin:"), line)


if __name__ == "__main__":
    unittest.main(verbosity=2)
