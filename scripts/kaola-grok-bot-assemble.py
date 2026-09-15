#!/usr/bin/env python3
"""Assemble a Grok Bot host plugin from generated Skill directories."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

NAMES = {
    "grok": "grok-kaola-project-runner",
    "claude-code": "claude-code-kaola-project-runner",
    "opencode": "opencode-kaola-project-runner",
    "kimi-cli": "kimi-cli-kaola-project-runner",
    "cursor-cli": "cursor-cli-kaola-project-runner",
    "devin": "devin-kaola-project-runner",
    "codex": "codex-kaola-project-runner",
}


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "usage: kaola-grok-bot-assemble.py ROOT DEST include_orchestrator [platform...]",
            file=sys.stderr,
        )
        return 2
    root = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    include_orchestrator = sys.argv[3] == "true"
    platforms = sys.argv[4:]
    plugin_src = root / "hosts" / "grok-bot" / ".cursor-plugin" / "plugin.json"
    if not plugin_src.is_file():
        print(
            "missing generated Grok Bot plugin manifest; run ./scripts/render-skills.py --write: "
            + str(plugin_src),
            file=sys.stderr,
        )
        return 1
    dest.mkdir(parents=True, exist_ok=True)
    (dest / ".generated-by-kaola-project-runner").write_text("grok-bot\n", encoding="utf-8")
    plugin_dir = dest / ".cursor-plugin"
    plugin_dir.mkdir(exist_ok=True)
    shutil.copy2(plugin_src, plugin_dir / "plugin.json")
    skills_out = dest / "skills"
    skills_out.mkdir(exist_ok=True)
    wanted = [NAMES[item] for item in platforms]
    if include_orchestrator:
        wanted.append("kaola-project-runner")
    if not wanted:
        print("Grok Bot host install selected no Skills", file=sys.stderr)
        return 1
    for name in wanted:
        source = root / "skills" / name
        if not (source / "SKILL.md").is_file() or not (
            source / ".generated-by-kaola-project-runner"
        ).is_file():
            print(
                "generated Skill is missing; run ./scripts/render-skills.py --write: " + str(source),
                file=sys.stderr,
            )
            return 1
        shutil.copytree(source, skills_out / name, symlinks=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
