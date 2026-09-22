#!/usr/bin/env python3
"""Acceptance checks for the communication-only generated Skill contract.

Project Runner exposes an exact owned ACP session to a controlling Agent. It does
not own Workflow commands, scheduling, task modes, lifecycle state, or semantic
classification. Generated packages must keep that boundary identical across
all supported CLIs.
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
    "devin-kaola-project-runner",
    "codex-kaola-project-runner",
    "zcode-kaola-project-runner",
    "droid-kaola-project-runner",
    "dsh-kaola-project-runner",
)

EXPECTED_MARKDOWN = {
    "SKILL.md",
    "references/acp.md",
    "references/platform.md",
    "references/steering.md",
}

EXPECTED_ACTIVE_TEMPLATES = {
    "SKILL.md.tmpl",
    "agents/openai.yaml.tmpl",
    "references/acp.md.tmpl",
    "references/platform.md.tmpl",
    "references/steering.md.tmpl",
}

# Issue #130 retired PTY; its tmux transport overlay must not come back.
RETIRED_TEMPLATES = {"references/transport.md.tmpl"}

SKILL_MARKERS = (
    "communication driver",
    "does not choose commands, Workflow modes, cadence, state, approvals, retries, or completion policy",
    "No invocation implicitly starts `workflow-next`",
    "creates a heartbeat",
    '"$SKILL_DIR/scripts/runtime-tmux.sh" start',
    '"$SKILL_DIR/scripts/runtime-tmux.sh" observe',
    '"$SKILL_DIR/scripts/runtime-tmux.sh" capture',
    '"$SKILL_DIR/scripts/runtime-tmux.sh" send',
    "`key --key escape` (or `cancel`) cancels the running turn",
    '"$SKILL_DIR/scripts/runtime-tmux.sh" stop',
)

PLATFORM_MARKERS = (
    "The Agent decides",
    "does not block starting the CLI",
    "reported as evidence",
)

PROHIBITED_POLICY = (
    "starts workflow-next immediately",
    "Complete one Workflow project",
    "Recurring Workflow projects",
    "Recurring PR review and finalization",
    "Every started or resumed project run gets one",
    "15-minute heartbeat",
    "MERGED_AWAITING_ORIGIN_WATCH_PR",
    "UNCLAIMED_PR",
    "FOREIGN_CLAIM_CONFLICT",
    "HUMAN_DECISION_REQUIRED",
)


def normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def main() -> int:
    failures: list[str] = []
    agents_text = normalized(PROJECT / "AGENTS.md")
    cursor_evidence = normalized(
        PROJECT / "docs" / "live-smoke-evidence-first-2026-08-30.md"
    )
    if not all(
        marker in agents_text
        for marker in (
            "Live Cursor experiments use `grok-4.7-xhigh` with Fast disabled",
            "never use `/model` as a read-only probe",
        )
    ):
        failures.append(
            "test_cursor_live_experiment_policy — missing argv-selected non-FAST Cursor model protocol"
        )
    if not all(
        marker in cursor_evidence
        for marker in (
            "Cursor Grok 4.6 Extra High, FAST off",
            "KPR_CURSOR_GROK46_NO_FAST_OK",
            "status returned `absent`",
        )
    ):
        failures.append(
            "test_cursor_live_experiment_evidence — missing model, reply, or exact-session shutdown proof"
        )
    # Worker templates remain required. Extra files (the Issue #41 orchestrator
    # template tree) are allowed; grok-golden is excluded from this inventory.
    templates = PROJECT / "templates"
    active_templates = {
        path.relative_to(templates).as_posix()
        for path in templates.rglob("*")
        if path.is_file() and "grok-golden" not in path.relative_to(templates).parts
    }
    missing_worker_templates = EXPECTED_ACTIVE_TEMPLATES - active_templates
    if missing_worker_templates:
        failures.append(
            "test_active_template_inventory — missing worker templates "
            f"{sorted(missing_worker_templates)}"
        )
    revived = RETIRED_TEMPLATES & active_templates
    if revived:
        failures.append(
            f"test_active_template_inventory — retired PTY templates present {sorted(revived)}"
        )
    for skill_id in SKILL_IDS:
        package = PROJECT / "skills" / skill_id
        markdown = {
            path.relative_to(package).as_posix() for path in package.rglob("*.md")
        }
        if markdown != EXPECTED_MARKDOWN:
            failures.append(
                f"test_{skill_id}_markdown_inventory — expected {sorted(EXPECTED_MARKDOWN)}, got {sorted(markdown)}"
            )

        checks = (
            (package / "SKILL.md", SKILL_MARKERS),
            (package / "references/platform.md", PLATFORM_MARKERS),
        )
        for path, markers in checks:
            if not path.is_file():
                failures.append(f"test_{skill_id}_{path.name} — missing generated reference")
                continue
            text = normalized(path)
            for marker in markers:
                if " ".join(marker.split()) not in text:
                    failures.append(
                        f"test_{skill_id}_{path.name}_{marker[:32]} — missing communication marker {marker!r}"
                    )

        for path in package.rglob("*.md"):
            text = normalized(path)
            for marker in PROHIBITED_POLICY:
                if " ".join(marker.split()) in text:
                    failures.append(
                        f"test_{skill_id}_{path.relative_to(package)}_{marker[:32]} — active package retained orchestration policy {marker!r}"
                    )

    if failures:
        for failure in failures:
            print(f"RED: {failure}", file=sys.stderr)
        print(f"communication lifecycle acceptance: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print("communication lifecycle acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
