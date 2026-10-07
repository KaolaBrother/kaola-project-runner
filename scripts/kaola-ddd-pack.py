#!/usr/bin/env python3
"""Read-only checker for context packs (kaola-ddd-check/1).

Proves form and references for pack schema kaola-ddd-pack/1. A clean run
proves form and references only, not meaning or contract satisfaction.

The flat `key: value` reader follows `parse_flat_yaml` in
`scripts/kaola-dispatch.py` (lines 145-161). Front matter is cut out first;
that function has no `---` fence handling. This script does not import it,
so the optional checker stays removable without touching dispatch.

Suite names are the `shell_suites` then `python_suites_all` entries that
`scripts/validate.sh --list` prints. The arrays are read as text. `validate.sh`
is not executed.

Checks not automated, from the phase-1 pilot in docs/ddd/README.md:

- Vocabulary terms present in referenced code: the pilot's presence check
  passed every term; the four real findings were differences of meaning.
- Files changed since baseline_commit outside the expected-change surface:
  the pilot had no code change after baseline_commit, so this check is unmeasured.
- Advisory path:line symbol drift: citations are prose aliases and line ranges,
  with no grammar that binds a symbol to those lines, so a simple scan cannot
  reliably detect the off-by-a-few-lines edits the pilot fixed by reading.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "kaola-ddd-check/1"
SUPPORTED_PACK = "kaola-ddd-pack/1"
NOTE = (
    "A clean run proves form and references only, not meaning or contract satisfaction."
)
USAGE = "usage: scripts/kaola-ddd-pack.py check [--repo ROOT] [PACK ...]"

REQUIRED_KEYS = (
    "pack_schema",
    "id",
    "status",
    "owner",
    "context_primary",
    "contexts_touched",
    "baseline_commit",
)
OPTIONAL_KEYS = ("related_issues", "supersedes")
STATUSES = {"draft", "current", "retired"}
REQUIRED_SECTIONS = (
    "Vocabulary",
    "Inputs and outputs",
    "Invariants",
    "Dependency contracts",
    "Acceptance",
    "Expected-change surface",
    "Evolution",
    "Evidence",
)
_AUTHORITY_PARTS = {
    "authorization",
    "grant",
    "grants",
    "seat",
    "seats",
    "writer",
    "writers",
    "permission",
    "permissions",
    "approval",
    "cap",
}
_CONTEXT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9][A-Za-z0-9_-]*$")
_COMMIT = re.compile(r"^[0-9a-fA-F]{7,40}$")
_ISSUES = re.compile(r"^\d+(?:\s*,\s*\d+)*$")
_ALIAS_DEF = re.compile(r"`([A-Za-z][A-Za-z0-9]*)` means `([^`]+)`")
_ALIAS_USE = re.compile(r"\b([A-Z][A-Z0-9]{0,3}):\d+")
_EXPLICIT_PATH = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:scripts|tests|docs|templates|platforms)/[A-Za-z0-9_.+/-]+)"
)
_HEADING = re.compile(r"(?m)^## (.+?)\s*$")
_SUITE = re.compile(r"suite:\s*(\S+)")
_EXIT = {"ok": 0, "absent": 0, "invalid": 1, "usage": 2, "unsupported": 3}


def parse_flat_yaml_text(text: str) -> tuple[dict[str, str], list[str]]:
    """Flat `key: value` lines, same rules as `parse_flat_yaml`."""
    data: dict[str, str] = {}
    duplicates: list[str] = []
    for raw in text.splitlines():
        if not raw or raw[0] in " \t#" or raw.lstrip().startswith("#"):
            continue
        key, sep, value = raw.partition(":")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = value[1:-1]
            value = parsed if isinstance(parsed, str) else value[1:-1]
        key = key.strip()
        if key in data:
            duplicates.append(key)
        data[key] = value
    return data, duplicates


def inventory_names(validate_text: str) -> list[str] | None:
    """Names `validate.sh --list` prints, or None when the arrays are unreadable."""
    names: list[str] = []
    for array in ("shell_suites", "python_suites_all"):
        match = re.search(array + r"=\((.*?)\n\)", validate_text, re.S)
        if match is None:
            return None
        names.extend(re.findall(r'"([^"]+)"', match.group(1)))
    return names


def is_authority_key(key: str) -> bool:
    norm = key.strip().lower().replace("-", "_")
    if not norm:
        return False
    if norm in _AUTHORITY_PARTS or norm == "approved_by" or "approved_by" in norm:
        return True
    if norm.endswith("_cap"):
        return True
    return any(part in _AUTHORITY_PARTS for part in norm.split("_") if part)


def split_front_matter(text: str) -> tuple[str | None, str, str | None]:
    """Return (front, body, error). error is 'missing' or 'unclosed'."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "missing"
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            front = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return front, body, None
    return None, text, "unclosed"


def _finding(check: str, severity: str, message: str) -> dict[str, str]:
    return {"check": check, "severity": severity, "message": message}


def _display_path(repo: Path, pack: Path) -> str:
    try:
        return pack.resolve().relative_to(repo.resolve()).as_posix()
    except (OSError, ValueError):
        return str(pack)


def _commit_resolves(repo: Path, commit: str) -> bool:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", commit + "^{commit}"],
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode == 0


def _repo_file_exists(repo: Path, rel: str) -> bool:
    rel = rel.strip().rstrip(".,);:'\"")
    if not rel or rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
        return False
    root = repo.resolve()
    try:
        candidate = (root / rel).resolve()
        candidate.relative_to(root)
    except (OSError, ValueError):
        return False
    return candidate.is_file()


def _cited_paths(body: str) -> tuple[list[str], list[str]]:
    """Return (paths that must exist, undefined alias names)."""
    flat = re.sub(r"\s+", " ", body)
    aliases: dict[str, str] = {}
    for match in _ALIAS_DEF.finditer(flat):
        aliases[match.group(1)] = match.group(2).strip().rstrip(".,);")
    missing_alias: list[str] = []
    seen_alias: set[str] = set()
    for match in _ALIAS_USE.finditer(body):
        name = match.group(1)
        if name in aliases or name in seen_alias:
            continue
        seen_alias.add(name)
        missing_alias.append(name)
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        if path and path not in seen:
            seen.add(path)
            paths.append(path)

    for path in aliases.values():
        add(path)
    for match in _EXPLICIT_PATH.finditer(body):
        path = match.group(1).rstrip(".,);:'\"/")
        if "." not in Path(path).name:
            continue
        add(path)
    return paths, missing_alias


def _section_findings(body: str) -> list[dict[str, str]]:
    found = _HEADING.findall(body)
    if found == list(REQUIRED_SECTIONS):
        return []
    findings: list[dict[str, str]] = []
    required = list(REQUIRED_SECTIONS)
    for title in required:
        if title not in found:
            findings.append(_finding("sections", "error", f"missing section: {title}"))
    for title in found:
        if title not in required:
            findings.append(_finding("sections", "error", f"unexpected section: {title}"))
    present = [title for title in found if title in required]
    expected = [title for title in required if title in found]
    if present != expected:
        findings.append(_finding("sections", "error", "sections out of order"))
    return findings


def _suite_findings(body: str, inventory: set[str] | None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for match in _SUITE.finditer(body):
        name = match.group(1).rstrip(".,);")
        if name == "none":
            rest = body[match.end() :]
            if not re.match(r"\s*\(gap:", rest):
                findings.append(
                    _finding(
                        "suite",
                        "error",
                        "suite: none must use the form suite: none (gap: ...)",
                    )
                )
            continue
        if inventory is None:
            findings.append(
                _finding("suite", "error", "validate.sh inventory is unreadable")
            )
            continue
        if name not in inventory:
            findings.append(
                _finding(
                    "suite",
                    "error",
                    f"suite name is not in validate.sh --list: {name}",
                )
            )
    return findings


def _shape_findings(data: dict[str, str], duplicates: list[str], stem: str, repo: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for key in duplicates:
        findings.append(_finding("front-matter", "error", f"duplicate key: {key}"))
    for key in data:
        if is_authority_key(key):
            findings.append(
                _finding("authority", "error", f"forbidden authority key: {key}")
            )
        elif key not in REQUIRED_KEYS and key not in OPTIONAL_KEYS:
            findings.append(
                _finding("unknown-key", "advisory", f"unknown descriptive key: {key}")
            )
    for key in REQUIRED_KEYS:
        if key not in data:
            findings.append(_finding("front-matter", "error", f"missing required key: {key}"))
    if "id" in data and data["id"] != stem:
        findings.append(
            _finding("front-matter", "error", "id must match the pack file stem")
        )
    if "status" in data and data["status"] not in STATUSES:
        findings.append(
            _finding(
                "front-matter",
                "error",
                "status must be draft, current, or retired",
            )
        )
    if "owner" in data and not data["owner"].strip():
        findings.append(_finding("front-matter", "error", "owner must be non-empty"))
    primary = data.get("context_primary")
    if primary is not None and primary != "unmapped" and not _CONTEXT.match(primary):
        findings.append(
            _finding(
                "front-matter",
                "error",
                "context_primary must be unmapped or grouping/component",
            )
        )
    touched = data.get("contexts_touched")
    if touched is not None and not _touched_ok(touched):
        findings.append(
            _finding(
                "front-matter",
                "error",
                "contexts_touched must be none or a comma-separated grouping/component list",
            )
        )
    baseline = data.get("baseline_commit")
    if baseline is not None:
        if not _COMMIT.match(baseline):
            findings.append(
                _finding(
                    "baseline",
                    "error",
                    "baseline_commit must be a 7 to 40 hex commit",
                )
            )
        elif not _commit_resolves(repo, baseline):
            findings.append(
                _finding("baseline", "error", "baseline_commit does not resolve")
            )
    related = data.get("related_issues")
    if related is not None and not _ISSUES.match(related):
        findings.append(
            _finding(
                "front-matter",
                "error",
                "related_issues must be comma-separated issue numbers",
            )
        )
    supersedes = data.get("supersedes")
    if supersedes is not None and not supersedes.strip():
        findings.append(
            _finding("front-matter", "error", "supersedes must be non-empty when present")
        )
    return findings


def _touched_ok(value: str) -> bool:
    if value == "none":
        return True
    parts = [part.strip() for part in value.split(",")]
    return bool(parts) and all(_CONTEXT.match(part) for part in parts)


def evaluate_pack(repo: Path, pack: Path, inventory: set[str] | None) -> dict[str, object]:
    shown = _display_path(repo, pack)
    if not pack.is_file():
        return {
            "path": shown,
            "id": None,
            "status": "invalid",
            "findings": [_finding("front-matter", "error", "pack is not a file")],
        }
    try:
        text = pack.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "path": shown,
            "id": None,
            "status": "invalid",
            "findings": [_finding("front-matter", "error", f"pack is unreadable: {exc}")],
        }
    front, body, fence_error = split_front_matter(text)
    if fence_error is not None:
        message = "missing front matter" if fence_error == "missing" else "unclosed front matter"
        return {
            "path": shown,
            "id": None,
            "status": "invalid",
            "findings": [_finding("front-matter", "error", message)],
        }
    data, duplicates = parse_flat_yaml_text(front or "")
    pack_id = data.get("id")
    schema = data.get("pack_schema")
    if schema is not None and schema != SUPPORTED_PACK:
        return {
            "path": shown,
            "id": pack_id,
            "status": "unsupported",
            "findings": [
                _finding(
                    "pack_schema",
                    "error",
                    f"pack_schema {schema} is not supported; "
                    f"this checker supports {SUPPORTED_PACK}",
                )
            ],
        }
    findings = _shape_findings(data, duplicates, pack.stem, repo)
    findings.extend(_section_findings(body))
    findings.extend(_suite_findings(body, inventory))
    paths, undefined = _cited_paths(body)
    for name in undefined:
        findings.append(_finding("path", "error", f"undefined citation alias: {name}"))
    for rel in paths:
        if not _repo_file_exists(repo, rel):
            findings.append(_finding("path", "error", f"cited path does not exist: {rel}"))
    status = "invalid" if any(item["severity"] == "error" for item in findings) else "ok"
    return {"path": shown, "id": pack_id, "status": status, "findings": findings}


def discover_packs(repo: Path) -> list[Path] | None:
    root = repo / "docs" / "ddd"
    pack_dir = root / "packs"
    if not root.is_dir() or not pack_dir.is_dir():
        return None
    found = sorted(path for path in pack_dir.glob("*.md") if path.is_file())
    return found or None


def envelope(result: str, packs: list[dict[str, object]], message: str | None = None) -> dict[str, object]:
    counts = {"ok": 0, "invalid": 0, "unsupported": 0}
    for pack in packs:
        status = str(pack["status"])
        if status in counts:
            counts[status] += 1
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "result": result,
        "note": NOTE,
        "counts": counts,
        "packs": packs,
    }
    if message is not None:
        payload["message"] = message
    return payload


def parse_cli(argv: list[str]) -> tuple[Path | None, list[str]] | None:
    if not argv or argv[0] in {"-h", "--help"} or argv[0] != "check":
        return None
    repo: Path | None = None
    packs: list[str] = []
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg == "--repo":
            if index + 1 >= len(argv):
                return None
            repo = Path(argv[index + 1])
            index += 2
            continue
        if arg.startswith("-"):
            return None
        packs.append(arg)
        index += 1
    return repo, packs


def load_inventory(repo: Path) -> set[str] | None:
    path = repo / "scripts" / "validate.sh"
    try:
        names = inventory_names(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    if names is None:
        return None
    return set(names)


def run_check(repo: Path, pack_args: list[str]) -> dict[str, object]:
    if not repo.is_dir():
        return envelope("usage", [], USAGE)
    if pack_args:
        selected = [Path(arg) if Path(arg).is_absolute() else Path.cwd() / arg for arg in pack_args]
    else:
        discovered = discover_packs(repo)
        if discovered is None:
            return envelope("absent", [], "no docs/ddd packs")
        selected = discovered
    inventory = load_inventory(repo)
    packs = [evaluate_pack(repo, path, inventory) for path in selected]
    statuses = {str(pack["status"]) for pack in packs}
    if "invalid" in statuses:
        result = "invalid"
    elif "unsupported" in statuses:
        result = "unsupported"
    else:
        result = "ok"
    return envelope(result, packs)


def main(argv: list[str] | None = None) -> int:
    parsed = parse_cli(list(sys.argv[1:] if argv is None else argv))
    if parsed is None:
        report = envelope("usage", [], USAGE)
    else:
        repo_arg, pack_args = parsed
        repo = (repo_arg if repo_arg is not None else Path(__file__).resolve().parent.parent)
        report = run_check(repo, pack_args)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return _EXIT[str(report["result"])]


if __name__ == "__main__":
    sys.exit(main())
