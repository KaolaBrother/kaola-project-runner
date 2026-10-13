#!/usr/bin/env python3
"""Issue-scoped session names (Issue #313).

Importable parser and active-run lookup for Runner receipts and for the
later drift check (Issue #312). Advisory only: nothing here refuses a start,
renames a session, or writes a registry.

Two closed vocabularies:

* ``classification`` describes the name:
  ``ok`` | ``malformed`` | ``platform-token-mismatch`` | ``not-issue-named``.
* ``issue_name`` is the start/list advisory for an issue-named worker:
  ``ok`` | ``malformed`` | ``platform-token-mismatch`` | ``no-active-run``.
  Host, sideagent, and seat names are ``not-issue-named`` and carry no
  ``issue_name``. Their honest marker is ``name_role``
  (``host`` | ``sideagent`` | ``seat``). A worker's ``name_role`` is
  ``worker``.

``classification`` ``ok`` means the name is
``<platform>-<PROJECT>-i<ISSUE>-<purpose>`` and ``platform`` is the exact
platform id. The advisory ``ok`` also requires at least one active claim for
that issue. The consumer join is stricter: see ``JOIN_RULE``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Parse classes. Not the advisory field.
CLASSIFICATIONS = (
    "ok",
    "malformed",
    "platform-token-mismatch",
    "not-issue-named",
)
# Start/list advisory. Only issue-named workers carry this.
ISSUE_NAME_VALUES = (
    "ok",
    "malformed",
    "platform-token-mismatch",
    "no-active-run",
)
NAME_ROLES = ("worker", "host", "sideagent", "seat")
PARSED_KEYS = (
    "classification",
    "name_role",
    "platform_id",
    "name_token",
    "project",
    "issue",
    "purpose",
    "mismatch_kind",
)
MISMATCH_KINDS = ("short-alias", "other-platform", "other-token")

# Consumer join. The first sentence is the rule. The rest is how this
# repository decides each side of it. Archived runs are not claims.
JOIN_RULE = (
    "name parses AND the repo's active run claims that issue number => bound; "
    "else unbound. Parses means classification ok: the name is "
    "<platform>-<PROJECT>-i<ISSUE>-<purpose> and platform is the exact "
    "platform id derived from platforms/*.yaml session_prefix (the id, such "
    "as claude-code or cursor-cli, not a short alias such as claude or "
    "cursor). The repo's active run is exactly one non-archived "
    "kaola-workflow/<run>/workflow-state.md in that repo's main checkout "
    "whose status is active, whose issue_number equals that ISSUE, and whose "
    "claim_repository_id matches the Runner record repository identity. A "
    "short alias, another platform's prefix, a malformed name, a host, "
    "sideagent, or seat name, no active run, a repository mismatch, and two "
    "active runs for one issue are unbound."
)

# issue_name ok is existence of an active claim, not the consumer join.
# Two claims, or a claim_repository_id the consumer has not compared, can
# still be issue_name ok. The join above is what binds a progress bar.
ADVISORY_NOTE = (
    "issue_name ok means classification ok and at least one non-archived "
    "active workflow-state.md claim for that issue_number, with a "
    "claim_repository_id present. It does not require exactly one claim and "
    "it does not compare claim_repository_id to the Runner record. Those "
    "checks are the join rule. issue_name never blocks start."
)

# Same reserved names as scripts/kaola-kw-index.py. archive is not a run.
RESERVED_RUN_NAMES = {"archive", ".ledger", ".roadmap"}
_ISSUE_MARKER = re.compile(r"-i([1-9][0-9]*)-")
_PROJECT = re.compile(r"^[A-Za-z0-9]+$")
_PROJECT_ROLE = re.compile(r"^[A-Za-z0-9_.]+$")
_PURPOSE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_ROLE_NAME = re.compile(
    r"^(?P<token>.+)-(?P<project>[A-Za-z0-9_.]+)-"
    r"(?P<role>orchestrator|sideagent|sidekick|seat)-"
    r"(?P<purpose>[A-Za-z0-9][A-Za-z0-9_.-]*)$"
)
_ROLE_TO_NAME_ROLE = {
    "orchestrator": "host",
    "sideagent": "sideagent",
    "sidekick": "sideagent",
    "seat": "seat",
}
_CLAIM_LINE = re.compile(r"^([A-Za-z0-9_]+):\s*(.*?)\s*$")
_STATE_BYTES = 256 * 1024
_KAOLA_SUFFIX = "-kaola"


def default_platforms_dir() -> Path | None:
    """Checkout ``platforms/`` when this file sits in the repo or a skill copy.

    An installed skill that only has ``platform.yaml`` beside this file uses
    that directory. The walk is three fixed layouts, not an ancestor search.
    """
    here = Path(__file__).resolve().parent
    candidates = (
        here.parent / "platforms",
        here.parent.parent.parent / "platforms",
    )
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("*.yaml")):
            return candidate
    if (here / "platform.yaml").is_file():
        return here
    return None


def _manifest_strings(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return result
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        try:
            parsed = json.loads(value.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, str):
            result[key.strip()] = parsed
    return result


def platform_catalog(platforms_dir: Path | None = None) -> tuple[dict[str, str], ...]:
    """Exact platform ids from ``session_prefix``.

    Each manifest's name token is ``session_prefix`` with the ``-kaola``
    suffix removed. A file whose ``id`` disagrees with that token is omitted.
    """
    directory = platforms_dir if platforms_dir is not None else default_platforms_dir()
    if directory is None or not directory.is_dir():
        return ()
    rows: list[dict[str, str]] = []
    for path in sorted(directory.glob("*.yaml")):
        if not path.is_file() or path.is_symlink():
            continue
        fields = _manifest_strings(path)
        prefix = fields.get("session_prefix")
        ident = fields.get("id")
        if not prefix or not ident or not prefix.endswith(_KAOLA_SUFFIX):
            continue
        token = prefix[: -len(_KAOLA_SUFFIX)]
        if not token or token != ident:
            continue
        rows.append({"id": ident, "session_prefix": prefix, "name_token": token})
    return tuple(rows)


def platform_ids(platforms_dir: Path | None = None) -> tuple[str, ...]:
    return tuple(row["id"] for row in platform_catalog(platforms_dir))


def is_short_alias(token: str, platform_id: str) -> bool:
    """True when ``token`` is a leading piece of ``platform_id``.

    ``claude`` is a short alias of ``claude-code``. ``cursor`` is a short
    alias of ``cursor-cli``. The exact id is not a short alias of itself.
    """
    return bool(token) and token != platform_id and platform_id.startswith(token + "-")


def _blank(platform_id: str, **overrides: Any) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "classification": "malformed",
        "name_role": "worker",
        "platform_id": platform_id,
        "name_token": None,
        "project": None,
        "issue": None,
        "purpose": None,
        "mismatch_kind": None,
    }
    parsed.update(overrides)
    return parsed


def _mismatch_kind(token: str, platform_id: str, ids: tuple[str, ...]) -> str:
    if is_short_alias(token, platform_id):
        return "short-alias"
    if token in ids and token != platform_id:
        return "other-platform"
    for other in ids:
        if other != platform_id and is_short_alias(token, other):
            return "short-alias"
    return "other-token"


def parse_session_name(name: str, platform_id: str,
                       platforms_dir: Path | None = None) -> dict[str, Any]:
    """Classify ``name`` against the session's platform id.

    ``platform_id`` is the Runner platform of the session (the ``start``
    positional, or the list row's platform), not a token taken from the name.
    """
    ids = platform_ids(platforms_dir)
    if not isinstance(name, str) or not isinstance(platform_id, str) or not platform_id:
        return _blank(platform_id if isinstance(platform_id, str) else "")
    # An i<ISSUE> field is a worker shape, including a purpose that contains
    # the letters of a role. Role names are only names with no i<ISSUE> field.
    marker = _ISSUE_MARKER.search(name)
    if marker is not None:
        prefix = name[:marker.start()]
        purpose = name[marker.end():]
        token, separator, project = prefix.rpartition("-")
        if (separator and token and _PROJECT.fullmatch(project)
                and _PURPOSE.fullmatch(purpose)):
            issue = int(marker.group(1))
            if token == platform_id and (not ids or platform_id in ids):
                return _blank(
                    platform_id,
                    classification="ok",
                    name_role="worker",
                    name_token=token,
                    project=project,
                    issue=issue,
                    purpose=purpose,
                )
            return _blank(
                platform_id,
                classification="platform-token-mismatch",
                name_role="worker",
                name_token=token,
                project=project,
                issue=issue,
                purpose=purpose,
                mismatch_kind=_mismatch_kind(token, platform_id, ids),
            )
    role = _ROLE_NAME.fullmatch(name)
    if role is not None and _ISSUE_MARKER.search(name) is None:
        token = role.group("token")
        project = role.group("project")
        if _PROJECT_ROLE.fullmatch(project):
            return _blank(
                platform_id,
                classification="not-issue-named",
                name_role=_ROLE_TO_NAME_ROLE[role.group("role")],
                name_token=token,
                project=project,
                purpose=role.group("purpose"),
            )
    return _blank(platform_id)


def main_checkout(repo: str) -> Path:
    """Main checkout that holds ``kaola-workflow/``.

    Same resolution as ``scripts/kaola-kw-index.py`` ``_resolve_main_root``:
    ``git rev-parse --git-common-dir``. A worktree's run folders live in the
    main checkout. On any git failure the given path is used as-is.
    """
    root = Path(repo)
    try:
        out = subprocess.run(
            ["git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-common-dir"],
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


def _read_claim_fields(path: Path) -> dict[str, Any] | None:
    try:
        if not path.is_file() or path.is_symlink():
            return None
        if path.stat().st_size > _STATE_BYTES:
            return None
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    fields: dict[str, str] = {}
    for raw in text.splitlines():
        match = _CLAIM_LINE.match(raw.strip())
        if match is None:
            continue
        key, value = match.group(1), match.group(2)
        if key not in fields:
            fields[key] = value
    issue_raw = fields.get("issue_number")
    issue = int(issue_raw) if issue_raw and issue_raw.isascii() and issue_raw.isdecimal() else None
    claim_repo = fields.get("claim_repository_id") or None
    return {
        "status": fields.get("status"),
        "issue_number": issue,
        "claim_repository_id": claim_repo,
    }


def find_active_claims(repo: str, issue: int) -> dict[str, Any]:
    """Active claims for ``issue`` under the repo's main ``kaola-workflow/``.

    One directory level. ``archive``, dot names, ``.ledger``, and ``.roadmap``
    are not runs. A claim is read from the file: ``status`` active,
    ``issue_number`` equal to ``issue``, and a non-empty ``claim_repository_id``.
    The folder name is not a claim.
    """
    result: dict[str, Any] = {"repo": repo, "issue": issue, "count": 0, "claims": []}
    if (not isinstance(repo, str) or not repo or isinstance(issue, bool)
            or not isinstance(issue, int) or issue < 1):
        return result
    if not Path(repo).is_dir():
        return result
    main = main_checkout(repo)
    result["repo"] = str(main)
    kw = main / "kaola-workflow"
    if not kw.is_dir() or kw.is_symlink():
        return result
    try:
        children = sorted(
            child for child in kw.iterdir()
            if child.is_dir() and not child.is_symlink()
        )
    except OSError:
        return result
    claims: list[dict[str, Any]] = []
    for child in children:
        if child.name in RESERVED_RUN_NAMES or child.name.startswith("."):
            continue
        state = child / "workflow-state.md"
        fields = _read_claim_fields(state)
        if fields is None:
            continue
        if fields["status"] != "active" or fields["issue_number"] != issue:
            continue
        claim_repo = fields["claim_repository_id"]
        if not isinstance(claim_repo, str) or not claim_repo.strip():
            continue
        claims.append({
            "run": child.name,
            "status": "active",
            "issue_number": issue,
            "claim_repository_id": claim_repo,
            "archived": False,
            "path": f"kaola-workflow/{child.name}/workflow-state.md",
        })
    result["claims"] = claims
    result["count"] = len(claims)
    return result


def issue_name_for(parsed: dict[str, Any], active_claim_count: int) -> str | None:
    """The advisory value, or None when the session is not an issue-named worker."""
    if parsed.get("classification") == "not-issue-named" or parsed.get("name_role") != "worker":
        return None
    classification = parsed.get("classification")
    if classification == "malformed":
        return "malformed"
    if classification == "platform-token-mismatch":
        return "platform-token-mismatch"
    if classification == "ok":
        if isinstance(active_claim_count, int) and not isinstance(active_claim_count, bool):
            if active_claim_count >= 1:
                return "ok"
        return "no-active-run"
    return "malformed"


def join_bound(parsed: dict[str, Any], claims: list[dict[str, Any]],
               record_repository_id: str | None = None) -> bool:
    """The consumer join in ``JOIN_RULE``. ``claims`` are caller-supplied.

    A missing ``record_repository_id`` does not skip the identity check: the
    single matching claim's ``claim_repository_id`` is the identity, and the
    caller must pass the same string. An empty caller identity is unbound.
    """
    if parsed.get("classification") != "ok" or parsed.get("name_role") != "worker":
        return False
    issue = parsed.get("issue")
    if isinstance(issue, bool) or not isinstance(issue, int):
        return False
    if not isinstance(record_repository_id, str) or not record_repository_id.strip():
        return False
    matching: list[dict[str, Any]] = []
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("archived") is True:
            continue
        if claim.get("status") != "active" or claim.get("issue_number") != issue:
            continue
        claim_repo = claim.get("claim_repository_id")
        if not isinstance(claim_repo, str) or not claim_repo.strip():
            continue
        matching.append(claim)
    if len(matching) != 1:
        return False
    return matching[0].get("claim_repository_id") == record_repository_id


def advise(name: str, platform_id: str, repo: str | None = None,
           platforms_dir: Path | None = None) -> dict[str, Any]:
    """Parse ``name`` and, when it parses, look up the active claim.

    The lookup runs only for classification ``ok``. Other names do not need
    a workflow scan to receive their advisory.
    """
    parsed = parse_session_name(name, platform_id, platforms_dir)
    count = 0
    claims: list[dict[str, Any]] = []
    if (parsed["classification"] == "ok" and isinstance(parsed.get("issue"), int)
            and isinstance(repo, str) and repo):
        found = find_active_claims(repo, parsed["issue"])
        count = found["count"]
        claims = found["claims"]
    return {
        **parsed,
        "issue_name": issue_name_for(parsed, count),
        "active_claim_count": count,
        "claims": claims,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kaola-session-names.py")
    parser.add_argument("--session", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--repo")
    args = parser.parse_args(argv)
    print(json.dumps(
        advise(args.session, args.platform, args.repo),
        ensure_ascii=False, sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
