#!/usr/bin/env python3
"""Kaola-Workflow read-only original-record index (issue #277, migration P4).

Implements the P4 contract ``docs/designs/modular-core-2026-10-07/p4-kw-readonly-index.md``:
given the root of a project that uses Kaola-Workflow, list the original KW records the
reader can see as ``{kind, path, sha256, schema_or_unknown}`` — a pointer table, by
reference only. Content, ownership, semantics and lifecycle stay with KW; nothing here
copies record content into KPR state.

The reader is strictly read-only: it opens files only for hashing/shape checks, writes
nothing anywhere (no cache, no temp file, no ledger or state edit), and makes no network
calls. The only subprocess is ``git rev-parse --git-common-dir`` to resolve the main
checkout root (the live mission ledger and run folders are main-resident per the KW
topology); on any git failure the given root is scanned as-is.

Record locations follow KW's ``KERNEL_ARTIFACT_REGISTRY``
(KW ``scripts/kaola-workflow-adaptive-schema.js:841-897`` at the revision this contract
was written against) plus the two ledger locations
(``kaola-workflow/.ledger/issue-<N>.jsonl`` live; ``kaola-workflow/archive/<project>/
mission-ledger.jsonl`` archived).

Each entry carries a typed status:

* ``present``     — regular readable file; ``sha256`` populated.
* ``absent``      — the named record path does not exist (normal mid-run for terminal
                    records); never guessed at.
* ``unsupported`` — the path exists but this reader cannot stand behind it
                    (``reason`` names the class: ``not-a-regular-file``, ``unreadable``,
                    ``unparseable-json``, ``shape-violation``,
                    ``ledger-shape-violation``, ``schema-version-unsupported``).

``schema_or_unknown`` reports the version KW declares inside the artifact
(``validation_vector/1``, ``outcome-log/1``); most KW records carry no version field —
their shape is contract-enforced — and report ``unknown``.

Usage::

    python3 scripts/kaola-kw-index.py --root <project-root> [--project <run-folder>] [--issue N]

Exit 0 whenever the scan completed (absent/unsupported are data, not failures); 2 on
usage errors or an unusable root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

INDEX_KIND = "kaola-kw-index/1"
KW_DIR = "kaola-workflow"
# Directories under kaola-workflow/ that are never run folders (KW's own rules skip
# `archive` and dot-prefixed names; `.ledger` and `.roadmap` are fixed non-run names).
RESERVED_RUN_NAMES = {"archive", ".ledger", ".roadmap"}

LEDGER_KEYS = ["n", "name", "details", "status"]
LEDGER_STATUSES = {"todo", "in-flight", "done", "failed", "blocked"}
LEDGER_NAME_RE = re.compile(r"^issue-([1-9][0-9]*)\.jsonl$")

# Schema versions this reader supports, reported as "<family>/<v>".
SUPPORTED_SCHEMAS = {
    "validation-vector": ("validation_vector", 1),
    "outcome-log": ("outcome-log", 1),
}

# Digest-field annotations from the P4 contract §4: which NAMED VIEW each KW-bound
# digest field belongs to. Metadata only — the field's value is never extracted.
DIGEST_FIELDS = {
    "chain-receipt": [{"field": "codeTreeHash", "view": "finalize-gate"}],
    "final-validation-record": [{"field": "validated_candidate_hash", "view": "finalize-gate"}],
    "validation-vector": [
        {"field": "candidate_digest", "view": "landable-record"},
        {"field": "runs[].pre_candidate_digest", "view": "landable-record"},
        {"field": "runs[].post_candidate_digest", "view": "landable-record"},
    ],
}

# Named run-folder records: (kind, path relative to the run folder, shape check).
# "json" = must parse as a JSON document; "jsonl-ledger" = the exact mission-ledger
# shape; "jsonl-outcome" = JSONL whose every line declares v==1; "file" = presence only.
RUN_RECORDS = [
    ("workflow-state", "workflow-state.md", "file"),
    ("finalization-summary", "finalization-summary.md", "file"),
    ("chain-receipt", ".cache/chain-receipt.json", "json"),
    ("final-validation-record", ".cache/final-validation.md", "file"),
    ("selection-record", ".cache/origin/selection-record.json", "json"),
    ("run-gaps", ".cache/run-gaps.json", "json"),
    ("sink-receipt", ".cache/sink-receipt.json", "json"),
    ("sink-fallback", ".cache/sink-fallback.json", "json"),
    ("outcome-log", ".cache/outcome-log.jsonl", "jsonl-outcome"),
    ("node-timings", ".cache/node-timings.jsonl", "file"),
]
VECTOR_GLOB_DIR = ".cache/validation-vectors"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(kind: str, rel: str, run: str | None, location: str) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "kind": kind,
        "path": rel,
        "status": "absent",
        "sha256": None,
        "schema_or_unknown": "unknown",
    }
    if run is not None:
        entry["run"] = run
    if location:
        entry["location"] = location
    if kind in DIGEST_FIELDS:
        entry["digest_fields"] = [dict(item) for item in DIGEST_FIELDS[kind]]
    return entry


def _check_ledger_shape(text: str) -> str | None:
    """Return a violation reason, or None when every line satisfies the KW shape rule."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for i, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return f"line {i}: not JSON"
        if not isinstance(obj, dict):
            return f"line {i}: not an object"
        if list(obj.keys()) != LEDGER_KEYS:
            return f"line {i}: keys must be exactly n,name,details,status"
        if obj["n"] != i:
            return f"line {i}: n must be {i}"
        if not isinstance(obj["name"], str) or not obj["name"].strip() or "\n" in obj["name"] or "\r" in obj["name"]:
            return f"line {i}: name must be one non-empty line"
        if not isinstance(obj["details"], str):
            return f"line {i}: details must be a string"
        if obj["status"] not in LEDGER_STATUSES:
            return f"line {i}: status must be one of {'|'.join(sorted(LEDGER_STATUSES))}"
    return None


def _classify(path: Path, kind: str, shape: str, entry: dict[str, Any]) -> dict[str, Any]:
    """Fill a record entry in place with the typed present/absent/unsupported verdict."""
    try:
        exists = path.exists() or path.is_symlink()
    except OSError:
        entry.update(status="unsupported", reason="unreadable")
        return entry
    if not exists:
        return entry  # absent: the named record path does not exist
    if path.is_symlink() or not path.is_file():
        entry.update(status="unsupported", reason="not-a-regular-file")
        return entry
    try:
        raw = path.read_bytes()
    except OSError:
        entry.update(status="unsupported", reason="unreadable")
        return entry

    entry["sha256"] = hashlib.sha256(raw).hexdigest()

    if shape == "file":
        entry["status"] = "present"
        return entry

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        entry.update(status="unsupported", reason="unparseable-json")
        return entry

    if shape == "json":
        try:
            json.loads(text)
        except json.JSONDecodeError:
            entry.update(status="unsupported", reason="unparseable-json")
            return entry
        entry["status"] = "present"
        return entry

    if shape == "jsonl-ledger":
        violation = _check_ledger_shape(text)
        if violation:
            entry.update(status="unsupported", reason="ledger-shape-violation", detail=violation)
            return entry
        entry["status"] = "present"
        return entry

    if shape == "jsonl-outcome":
        family, want = SUPPORTED_SCHEMAS["outcome-log"]
        for i, line in enumerate(text.split("\n"), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                entry.update(status="unsupported", reason="unparseable-json", detail=f"line {i}")
                return entry
            version = obj.get("v") if isinstance(obj, dict) else None
            if version != want:
                entry.update(status="unsupported", reason="schema-version-unsupported",
                             detail=f"line {i}: v={version!r} (supported: {want})")
                return entry
        entry.update(status="present", schema_or_unknown=f"{family}/{want}")
        return entry

    if shape == "vector":
        family, want = SUPPORTED_SCHEMAS["validation-vector"]
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            entry.update(status="unsupported", reason="unparseable-json")
            return entry
        if not isinstance(obj, dict) or obj.get("kind") != family:
            entry.update(status="unsupported", reason="shape-violation",
                         detail=f"kind field is {obj.get('kind')!r}, expected {family!r}"
                         if isinstance(obj, dict) else "not a JSON object")
            return entry
        version = obj.get("schema_version")
        if version != want:
            entry.update(status="unsupported", reason="schema-version-unsupported",
                         detail=f"schema_version={version!r} (supported: {want})")
            return entry
        entry.update(status="present", schema_or_unknown=f"{family}/{version}")
        return entry

    entry.update(status="unsupported", reason="shape-violation", detail=f"unknown shape {shape!r}")
    return entry


def _resolve_main_root(root: Path) -> Path:
    """The main checkout root: the live ledger and run folders are main-resident."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return root
    if out.returncode != 0 or not out.stdout.strip():
        return root
    common = Path(out.stdout.strip())
    main = common.parent if common.name == ".git" else common
    try:
        return main.resolve()
    except OSError:
        return root


def _iter_run_dirs(kw_root: Path) -> list[str]:
    """Run folder names under kaola-workflow/ that carry at least one visible sign."""
    names: list[str] = []
    try:
        children = sorted(p for p in kw_root.iterdir() if p.is_dir() and not p.is_symlink())
    except OSError:
        return names
    for child in children:
        name = child.name
        if name in RESERVED_RUN_NAMES or name.startswith("."):
            continue
        if (child / "workflow-state.md").is_file():
            names.append(name)
            continue
        # A folder with no state file still counts when it carries any named record.
        for _, rel, _ in RUN_RECORDS:
            if (child / rel).is_file():
                names.append(name)
                break
    return names


def _scan_run(root: Path, base: str, run: str, location: str) -> list[dict[str, Any]]:
    """Emit one entry per named record for one run folder (live or archive copy)."""
    entries: list[dict[str, Any]] = []
    run_dir = root / KW_DIR / base / run if base else root / KW_DIR / run
    rel_base = f"{KW_DIR}/{base}/{run}" if base else f"{KW_DIR}/{run}"
    for kind, rel, shape in RUN_RECORDS:
        entry = _entry(kind, f"{rel_base}/{rel}", run, location)
        _classify(run_dir / rel, kind, shape, entry)
        entries.append(entry)
    vector_dir = run_dir / VECTOR_GLOB_DIR
    vectors = []
    try:
        # Every name matching *.json is classified — a symlink or directory here is
        # `unsupported` evidence, never silently dropped.
        vectors = sorted(p for p in vector_dir.iterdir() if p.name.endswith(".json"))
    except OSError:
        vectors = []
    if not vectors:
        entry = _entry("validation-vector", f"{rel_base}/{VECTOR_GLOB_DIR}/*.json", run, location)
        entries.append(entry)  # absent: no vector recorded for this run
    for vector in vectors:
        rel = f"{rel_base}/{VECTOR_GLOB_DIR}/{vector.name}"
        entry = _entry("validation-vector", rel, run, location)
        _classify(vector, "validation-vector", "vector", entry)
        entries.append(entry)
    if location == "archive":
        ledger = run_dir / "mission-ledger.jsonl"
        entry = _entry("mission-ledger-archive", f"{rel_base}/mission-ledger.jsonl", run, location)
        _classify(ledger, "mission-ledger-archive", "jsonl-ledger", entry)
        entries.append(entry)
    return entries


def build_index(root: Path, project: str | None, issue: int | None) -> dict[str, Any]:
    root = root.resolve()
    main_root = _resolve_main_root(root)
    kw_root = main_root / KW_DIR
    records: list[dict[str, Any]] = []

    # Live mission ledgers: glob what exists; --issue adds the named one even when absent.
    ledger_dir = kw_root / ".ledger"
    seen_ledgers: set[str] = set()
    if ledger_dir.is_dir():
        for path in sorted(ledger_dir.glob("issue-*.jsonl")):
            seen_ledgers.add(path.name)
            rel = f"{KW_DIR}/.ledger/{path.name}"
            entry = _entry("mission-ledger", rel, None, "ledger")
            _classify(path, "mission-ledger", "jsonl-ledger", entry)
            records.append(entry)
    if issue is not None:
        name = f"issue-{issue}.jsonl"
        if name not in seen_ledgers:
            rel = f"{KW_DIR}/.ledger/{name}"
            entry = _entry("mission-ledger", rel, None, "ledger")
            _classify(ledger_dir / name, "mission-ledger", "jsonl-ledger", entry)
            records.append(entry)

    # Optional roadmap file.
    rules = kw_root / ".roadmap" / "_rules.md"
    entry = _entry("roadmap-rules", f"{KW_DIR}/.roadmap/_rules.md", None, "roadmap")
    _classify(rules, "roadmap-rules", "file", entry)
    records.append(entry)

    # Live run folders (+ a --project filter that also reports a missing folder's rows).
    live_runs = _iter_run_dirs(kw_root)
    if project is not None and project not in live_runs:
        live_runs.append(project)
        live_runs.sort()
    for run in live_runs:
        if project is not None and run != project:
            continue
        records.extend(_scan_run(main_root, "", run, "live"))

    # Archive run folders: same relative space, plus the archived ledger.
    archive_root = kw_root / "archive"
    archived: list[str] = []
    if archive_root.is_dir():
        try:
            archived = sorted(
                p.name for p in archive_root.iterdir()
                if p.is_dir() and not p.is_symlink() and not p.name.startswith(".")
            )
        except OSError:
            archived = []
    if project is not None:
        archived = [run for run in archived if run == project]
    for run in archived:
        records.extend(_scan_run(main_root, "archive", run, "archive"))

    records.sort(key=lambda e: e["path"])
    summary = {"present": 0, "absent": 0, "unsupported": 0}
    for entry in records:
        summary[entry["status"]] = summary.get(entry["status"], 0) + 1
    return {
        "index": INDEX_KIND,
        "scanned_root": str(root),
        "main_root": str(main_root),
        "filters": {"project": project, "issue": issue},
        "records": records,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List Kaola-Workflow original records as a read-only {kind, path, sha256, schema_or_unknown} index.")
    parser.add_argument("--root", required=True, help="the KW-using project root to scan")
    parser.add_argument("--project", default=None, help="restrict to one run folder name (e.g. issue-277)")
    parser.add_argument("--issue", type=int, default=None,
                        help="also report kaola-workflow/.ledger/issue-<N>.jsonl even when absent")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"kaola-kw-index: --root is not a directory: {args.root}", file=sys.stderr)
        return 2
    if args.project is not None and ("/" in args.project or "\\" in args.project
                                     or "\x00" in args.project or args.project in (".", "..")):
        print(f"kaola-kw-index: --project must be one path segment: {args.project!r}", file=sys.stderr)
        return 2
    if args.issue is not None and args.issue < 1:
        print("kaola-kw-index: --issue must be a positive integer", file=sys.stderr)
        return 2

    index = build_index(root, args.project, args.issue)
    json.dump(index, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
