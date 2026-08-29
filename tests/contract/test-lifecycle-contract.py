#!/usr/bin/env python3
"""Acceptance checks for the shared PR-handoff and terminal lifecycle contract.

The runner delegates Issue/PR mutation to Kaola-Workflow.  Consequently the
observable offline contract is the generated Skill guidance: every platform
must carry the same safety decisions, including the origin-watch-pr fallback
and the no-cleanup boundary for foreign or ambiguous claims.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
SKILL_IDS = (
    "grok-kaola-project-runner",
    "claude-code-kaola-project-runner",
    "opencode-kaola-project-runner",
    "kimi-cli-kaola-project-runner",
    "cursor-cli-kaola-project-runner",
)


REQUIRED_MARKERS = {
    "references/pr-claim-handoff.md": (
        "workflow:in-progress",
        "kw:claim project=",
        "UNCLAIMED_PR",
        "ORIGIN_PR_HANDOFF",
        "FOREIGN_CLAIM_CONFLICT",
        "watch-pr",
        "origin folder/state is absent",
        "`watch-pr` cannot perform cleanup",
        "originating run's exact local state is present",
        "never synthesize that state merely to make cleanup run",
        "MERGED_AWAITING_ORIGIN_WATCH_PR",
        "Do not create workflow state",
        "close Issues, clear labels",
        "repository is clean and aligned",
        "runner scheduler and detached intake counts are zero",
        "tmux/session shutdown follows the operating agreement",
        "HUMAN_DECISION_REQUIRED",
    ),
    "references/closing.md": (
        "Verify validation, sink, remote main/PR/Issue state",
        "Prefer the originating run's `watch-pr`",
        "when its state is absent or cleanup fails",
        "same {runtime} main conversation",
        "scheduler ID is absent",
        "matching scheduler count is zero",
        "no detached firing remains",
        "exact owned idle",
        "session shutdown",
        "delete the exact Codex supervision heartbeat",
        "incomplete state",
        "interrupted",
        "uncertain",
    ),
    "references/scheduling.md": (
        "foreground: true",
        "same main conversation",
        "zero detached General-loop schedulers",
        "zero detached project-intake subagents",
        "workflow:in-progress",
        "kw:claim project=",
        "HUMAN_DECISION_REQUIRED",
        "watch-pr",
        "clean review",
        "head advance requires re-review",
    ),
    "references/project-run.md": (
        "clean",
        "detached General loop",
        "detached subagent",
        "HUMAN_DECISION_REQUIRED",
        "actual sink, remote state, Issue state, archive, and cleanup",
    ),
    "references/task-modes.md": (
        "`watch-pr` cleanup when locally available",
        "claim:none",
        "origin state is absent or watch-pr cannot clean",
        "zero detached",
        "HUMAN_DECISION_REQUIRED",
        "same main orchestrator",
    ),
}


def main() -> int:
    failures: list[str] = []
    runtime_names = {
        "grok-kaola-project-runner": "Grok",
        "claude-code-kaola-project-runner": "Claude Code",
        "opencode-kaola-project-runner": "OpenCode",
        "kimi-cli-kaola-project-runner": "Kimi CLI",
        "cursor-cli-kaola-project-runner": "Cursor CLI",
    }
    for skill_id in SKILL_IDS:
        package = PROJECT / "skills" / skill_id
        for relative, markers in REQUIRED_MARKERS.items():
            path = package / relative
            if not path.is_file():
                failures.append(f"test_{skill_id}_{relative} — missing generated lifecycle reference")
                continue
            text = path.read_text(encoding="utf-8")
            searchable = " ".join(text.split())
            for marker in markers:
                marker = marker.replace("{runtime}", runtime_names[skill_id])
                if " ".join(marker.split()) not in searchable:
                    failures.append(
                        f"test_{skill_id}_{relative}_{marker[:30]} — missing lifecycle marker {marker!r}"
                    )

    if failures:
        for failure in failures:
            print(f"RED: {failure}", file=sys.stderr)
        print(f"lifecycle contract acceptance: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print("lifecycle contract acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
