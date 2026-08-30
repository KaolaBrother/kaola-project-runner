#!/usr/bin/env python3
"""Acceptance checks for the communication-only generated Skill contract.

Project Runner exposes an exact tmux transport to a controlling Agent. It does
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
)

EXPECTED_MARKDOWN = {
    "SKILL.md",
    "references/platform.md",
    "references/transport.md",
}

EXPECTED_ACTIVE_TEMPLATES = {
    "SKILL.md.tmpl",
    "agents/openai.yaml.tmpl",
    "references/platform.md.tmpl",
    "references/transport.md.tmpl",
}

SKILL_MARKERS = (
    "communication driver",
    "does not choose commands, Workflow modes, cadence, state, approvals, retries, or completion policy",
    "No invocation implicitly starts `workflow-next`",
    "creates a heartbeat",
    "runtime-tmux.sh start",
    "runtime-tmux.sh observe",
    "runtime-tmux.sh capture",
    "runtime-tmux.sh send",
    "runtime-tmux.sh key",
    "runtime-tmux.sh stop",
)

PLATFORM_MARKERS = (
    "The Agent decides",
    "does not block starting the CLI",
    "reported as evidence",
)

TRANSPORT_MARKERS = (
    "managed nested-PTY relay",
    "Transfer the agent's prompt",
    "Transfer an Agent-selected native key",
    "Read the response",
    "Stop and capability-specific actions",
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
            "Cursor CLI live experiments must explicitly open the native `/model` selector",
            "non-FAST Cursor Grok 4.6",
            "not a Runner gate",
        )
    ):
        failures.append(
            "test_cursor_live_experiment_policy — missing Agent-owned non-FAST Grok 4.6 protocol"
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
    templates = PROJECT / "templates"
    active_templates = {
        path.relative_to(templates).as_posix()
        for path in templates.rglob("*")
        if path.is_file() and "grok-golden" not in path.relative_to(templates).parts
    }
    if active_templates != EXPECTED_ACTIVE_TEMPLATES:
        failures.append(
            "test_active_template_inventory — expected "
            f"{sorted(EXPECTED_ACTIVE_TEMPLATES)}, got {sorted(active_templates)}"
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
            (package / "references/transport.md", TRANSPORT_MARKERS),
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
