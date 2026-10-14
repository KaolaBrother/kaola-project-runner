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
  Host, sideagent, seat, and general names are ``not-issue-named`` and
  carry no ``issue_name``. Their honest marker is ``name_role``
  (``host`` | ``sideagent`` | ``seat`` | ``general``). A worker's
  ``name_role`` is ``worker``.
* ``seat_issue_drift`` (Issue #312) is the live-seat advisory. Its
  ``advisories`` are ``dispatch-issue-mismatch`` and ``no-active-run``.
  ``None`` means the seat is not flagged. The function does not stop,
  rename, or refuse.

``classification`` ``ok`` means the name is
``<platform>-<CODE>-i<ISSUE>-<purpose>`` and ``platform`` is the exact
platform id. ``CODE`` starts with a letter and is letters and digits only.
The advisory ``ok`` requires exactly one in-progress non-bundle run for
that issue whose claim has the same git origin as the session repo.
``<platform>-<CODE>-general-<purpose>`` is not issue-named: ``name_role``
is ``general`` and there is no ``issue_name``. See ``JOIN_RULE``.
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
NAME_ROLES = ("worker", "host", "sideagent", "seat", "general")
# Live-seat drift. Not a start refusal and not a second name validator.
DRIFT_ADVISORIES = (
    "dispatch-issue-mismatch",
    "no-active-run",
)
SAFE_POINT_SUGGESTION = (
    "At the next safe point, exact-stop this seat and start a fresh "
    "standard-named session. Never retarget this live seat to another issue."
)
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
# repository decides each side of it. Archived runs and bundle runs are not
# the one active run.
JOIN_RULE = (
    "name parses AND the repo's active run claims that issue number => bound; "
    "else unbound. Parses means classification ok: the name is "
    "<platform>-<PROJECT>-i<ISSUE>-<purpose> and platform is the exact "
    "platform id derived from platforms/*.yaml session_prefix (the id, such "
    "as claude-code or cursor-cli, not a short alias such as claude or "
    "cursor). PROJECT starts with a letter and is letters and digits only. "
    "The repo's active run is exactly one non-archived non-bundle "
    "kaola-workflow/<run>/workflow-state.md in that repo's main checkout "
    "whose status is active, whose issue_number equals that ISSUE, and whose "
    "claim_repository_id has the same git origin as the session repo. A bundle "
    "is a run with a bundle_id, more than one issue_numbers value, or a "
    "bundle- folder name. Same origin is the same GitHub owner/repo, compared "
    "case-insensitively, or the same origin string when it is not a GitHub URL. "
    "A short alias, another platform's prefix, a malformed name, a host, "
    "sideagent, seat, or general name, no active run, a bundle run, a "
    "repository mismatch, and two active runs for one issue are unbound."
)

# issue_name ok is that same single non-bundle same-origin run. It still
# never blocks start. A different count or origin is no-active-run.
ADVISORY_NOTE = (
    "issue_name ok means classification ok and exactly one in-progress "
    "non-bundle run whose issue_number equals that issue, and whose "
    "claim_repository_id has the same git origin as the session repo. "
    "Zero runs, two or more runs, a bundle run, and a different origin "
    "are no-active-run. issue_name never blocks start."
)

# Same reserved names as scripts/kaola-kw-index.py. archive is not a run.
RESERVED_RUN_NAMES = {"archive", ".ledger", ".roadmap"}
_ISSUE_MARKER = re.compile(r"-i([1-9][0-9]*)-")
# CODE: a letter, then letters and digits. A leading digit is not a code.
_PROJECT = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
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
# GitHub origin forms. owner/repo, optional .git, case-insensitive later.
_GITHUB_ORIGINS = (
    re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", re.IGNORECASE),
    re.compile(r"^ssh://(?:[^@/]+@)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", re.IGNORECASE),
    re.compile(r"^git://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", re.IGNORECASE),
    re.compile(r"^git@github\.com:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", re.IGNORECASE),
)
_CLAIM_LINE = re.compile(r"^([A-Za-z0-9_]+):\s*(.*?)\s*$")
_STATE_BYTES = 256 * 1024
_KAOLA_SUFFIX = "-kaola"


def _split_general(name: str) -> tuple[str, str, str] | None:
    """``<platform>-<CODE>-general-<purpose>``, or None.

    The platform token may contain hyphens (``cursor-cli``). CODE does not.
    The first ``-general-`` is the delimiter, and the last hyphen before it
    separates the platform token from CODE.
    """
    if not isinstance(name, str):
        return None
    prefix, separator, purpose = name.partition("-general-")
    if not separator or not _PURPOSE.fullmatch(purpose):
        return None
    token, dash, project = prefix.rpartition("-")
    if not dash or not token or not _PROJECT.fullmatch(project):
        return None
    return token, project, purpose


def origin_key(value: str | None) -> str:
    """Comparable origin. GitHub URLs become ``owner/repo``; other strings stay."""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        return ""
    for pattern in _GITHUB_ORIGINS:
        match = pattern.fullmatch(text)
        if match:
            return f"{match.group(1)}/{match.group(2)}".lower()
    return text


def same_origin(claim_repository_id: str | None, session_origin: str | None) -> bool:
    """True when the claim and the session repo name the same git origin."""
    left = origin_key(claim_repository_id)
    right = origin_key(session_origin)
    return bool(left) and left == right


def session_origin(repo: str) -> str:
    """``git remote get-url origin`` for ``repo``, or empty when it cannot be read."""
    if not isinstance(repo, str) or not repo:
        return ""
    try:
        out = subprocess.run(
            ["git", "-C", repo, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if out.returncode != 0:
        return ""
    return out.stdout.strip()


def is_bundle_claim(claim: dict[str, Any]) -> bool:
    """A multi-issue run. It is not the one in-progress run for an issue."""
    if not isinstance(claim, dict):
        return False
    if claim.get("bundle") is True:
        return True
    bundle_id = claim.get("bundle_id")
    if isinstance(bundle_id, str) and bundle_id.strip():
        return True
    run = claim.get("run")
    if isinstance(run, str) and run.startswith("bundle-"):
        return True
    numbers = claim.get("issue_numbers")
    return isinstance(numbers, (list, tuple)) and len(numbers) > 1


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
    # A name with no issue. Host and sideagent names already returned above.
    # This form also draws no task progress: issue_name is omitted.
    general = _split_general(name)
    if general is not None and _ISSUE_MARKER.search(name) is None:
        token, project, purpose = general
        if token == platform_id and (not ids or platform_id in ids):
            return _blank(
                platform_id,
                classification="not-issue-named",
                name_role="general",
                name_token=token,
                project=project,
                purpose=purpose,
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
    numbers: list[int] = []
    for part in (fields.get("issue_numbers") or "").split(","):
        part = part.strip()
        if part.isascii() and part.isdecimal():
            number = int(part)
            if number >= 1:
                numbers.append(number)
    bundle_id = fields.get("bundle_id") or None
    if not isinstance(bundle_id, str) or not bundle_id.strip():
        bundle_id = None
    return {
        "status": fields.get("status"),
        "issue_number": issue,
        "claim_repository_id": claim_repo,
        "bundle_id": bundle_id,
        "issue_numbers": numbers,
    }


def find_active_claims(repo: str, issue: int) -> dict[str, Any]:
    """Active claims for ``issue`` under the repo's main ``kaola-workflow/``.

    One directory level. ``archive``, dot names, ``.ledger``, and ``.roadmap``
    are not runs. A claim is read from the file: ``status`` active,
    ``issue_number`` equal to ``issue``, and a non-empty ``claim_repository_id``.
    The folder name is not a claim. A bundle run is included with
    ``bundle`` true and is not part of ``count``. ``count`` does not compare
    origins; ``qualifying_claims`` does that.
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
        bundle = (
            child.name.startswith("bundle-")
            or bool(fields["bundle_id"])
            or len(fields["issue_numbers"]) > 1
        )
        claims.append({
            "run": child.name,
            "status": "active",
            "issue_number": issue,
            "claim_repository_id": claim_repo,
            "archived": False,
            "bundle": bundle,
            "bundle_id": fields["bundle_id"],
            "issue_numbers": fields["issue_numbers"],
            "path": f"kaola-workflow/{child.name}/workflow-state.md",
        })
    result["claims"] = claims
    result["count"] = sum(1 for claim in claims if not claim["bundle"])
    return result


def qualifying_claims(claims: list[dict[str, Any]] | None, issue: int,
                      session_origin_value: str | None) -> list[dict[str, Any]]:
    """In-progress, non-bundle claims for ``issue`` with the session's origin.

    Exactly one of these is ``issue_name`` ``ok``. Any other count is
    ``no-active-run``.
    """
    found: list[dict[str, Any]] = []
    if isinstance(issue, bool) or not isinstance(issue, int):
        return found
    for claim in claims or []:
        if not isinstance(claim, dict) or claim.get("archived") is True:
            continue
        if is_bundle_claim(claim):
            continue
        if claim.get("status") != "active" or claim.get("issue_number") != issue:
            continue
        claim_repo = claim.get("claim_repository_id")
        if not isinstance(claim_repo, str) or not claim_repo.strip():
            continue
        if not same_origin(claim_repo, session_origin_value):
            continue
        found.append(claim)
    return found


def issue_name_for(parsed: dict[str, Any], active_claim_count: int,
                   claims: list[dict[str, Any]] | None = None,
                   session_origin_value: str | None = None) -> str | None:
    """The advisory value, or None when the session is not an issue-named worker.

    When ``claims`` is given, the count is the qualifying same-origin
    non-bundle runs. Otherwise ``active_claim_count`` is that count already.
    """
    if parsed.get("classification") == "not-issue-named" or parsed.get("name_role") != "worker":
        return None
    classification = parsed.get("classification")
    if classification == "malformed":
        return "malformed"
    if classification == "platform-token-mismatch":
        return "platform-token-mismatch"
    if classification == "ok":
        if claims is not None:
            issue = parsed.get("issue")
            count = len(qualifying_claims(claims, issue, session_origin_value))
        elif isinstance(active_claim_count, int) and not isinstance(active_claim_count, bool):
            count = active_claim_count
        else:
            count = 0
        return "ok" if count == 1 else "no-active-run"
    return "malformed"


def join_bound(parsed: dict[str, Any], claims: list[dict[str, Any]],
               record_repository_id: str | None = None) -> bool:
    """The consumer join in ``JOIN_RULE``. ``claims`` are caller-supplied.

    A missing ``record_repository_id`` does not skip the identity check.
    The caller passes the session repo's origin. An empty origin is unbound.
    A bundle claim is not the active run. Identity is same git origin, not
    a raw string compare.
    """
    if parsed.get("classification") != "ok" or parsed.get("name_role") != "worker":
        return False
    issue = parsed.get("issue")
    if isinstance(issue, bool) or not isinstance(issue, int):
        return False
    return len(qualifying_claims(claims, issue, record_repository_id)) == 1


def _positive_issues(values: list[int] | tuple[int, ...] | None) -> list[int]:
    found: list[int] = []
    for value in values or []:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            continue
        if value not in found:
            found.append(value)
    found.sort()
    return found


def seat_issue_drift(name: str, platform_id: str,
                     dispatch_issues: list[int] | tuple[int, ...] | None = None,
                     *,
                     repo: str | None = None,
                     active_claim_count: int | None = None,
                     platforms_dir: Path | None = None) -> dict[str, Any] | None:
    """Advisory for one live seat, or None when nothing is flagged.

    The caller decides that the seat is live. ``dispatch_issues`` are the
    issues on its current execute items. A name issue that differs from any
    of them is ``dispatch-issue-mismatch``. ``no-active-run`` is the same
    fact as ``issue_name`` ``no-active-run``: classification ``ok`` and the
    qualifying run count is not exactly one. A passed ``active_claim_count``
    is that count. A short alias keeps its start advisory and is not also
    called ``no-active-run`` here. This function does not rename, stop, or
    refuse the seat.
    """
    parsed = parse_session_name(name, platform_id, platforms_dir)
    name_issue = parsed.get("issue")
    if isinstance(name_issue, bool) or not isinstance(name_issue, int):
        name_issue = None
    current = _positive_issues(dispatch_issues)
    advisories: list[str] = []
    if name_issue is not None and any(issue != name_issue for issue in current):
        advisories.append("dispatch-issue-mismatch")
    if parsed.get("classification") == "ok" and name_issue is not None:
        count = active_claim_count
        if count is None and isinstance(repo, str) and repo:
            found = find_active_claims(repo, name_issue)
            count = len(qualifying_claims(
                found["claims"], name_issue, session_origin(repo),
            ))
        if isinstance(count, int) and not isinstance(count, bool) and count != 1:
            advisories.append("no-active-run")
    if not advisories:
        return None
    body: dict[str, Any] = {
        "advisories": advisories,
        "name_issue": name_issue,
        "dispatch_issue": current[0] if len(current) == 1 else None,
        "suggestion": SAFE_POINT_SUGGESTION,
    }
    if len(current) > 1:
        body["dispatch_issues"] = current
    return body


def advise(name: str, platform_id: str, repo: str | None = None,
           platforms_dir: Path | None = None) -> dict[str, Any]:
    """Parse ``name`` and, when it parses, look up the active claim.

    The lookup runs only for classification ``ok``. Other names do not need
    a workflow scan to receive their advisory.
    """
    parsed = parse_session_name(name, platform_id, platforms_dir)
    count = 0
    claims: list[dict[str, Any]] = []
    origin = ""
    if (parsed["classification"] == "ok" and isinstance(parsed.get("issue"), int)
            and isinstance(repo, str) and repo):
        found = find_active_claims(repo, parsed["issue"])
        claims = found["claims"]
        origin = session_origin(repo)
        count = len(qualifying_claims(claims, parsed["issue"], origin))
    return {
        **parsed,
        "issue_name": issue_name_for(
            parsed, count, claims=claims, session_origin_value=origin,
        ),
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
