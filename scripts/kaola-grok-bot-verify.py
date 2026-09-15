#!/usr/bin/env python3
"""Offline verifier for the generated Grok Bot host plugin bundle.

Checks Cursor-plugin layout, Skill identities, generated markers, and optional
byte identity against ``skills/``. Does not contact Grok Bot and does not
claim live UI adoption.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ORCHESTRATOR = "kaola-project-runner"
WORKER_SKILLS = (
    "claude-code-kaola-project-runner",
    "codex-kaola-project-runner",
    "cursor-cli-kaola-project-runner",
    "devin-kaola-project-runner",
    "grok-kaola-project-runner",
    "kimi-cli-kaola-project-runner",
    "opencode-kaola-project-runner",
)
MARKER = ".generated-by-kaola-project-runner"
UNOFFICIAL = (
    "GrokBotService",
    "EnsureSandBox",
    "SAND_GATEWAY",
    "sand-host",
    "grokbot-sdk",
    "aiserver.v1",
    "/local-exec/",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_map(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def validate(bundle: Path, repo: Path | None) -> list[str]:
    findings: list[str] = []
    if not bundle.is_dir():
        return [f"{bundle}: missing plugin bundle directory"]

    marker = bundle / MARKER
    if not marker.is_file():
        findings.append(f"{bundle}: missing {MARKER}")
    elif marker.read_text(encoding="utf-8") != "grok-bot\n":
        findings.append(f"{bundle}: {MARKER} must contain grok-bot")

    plugin = bundle / ".cursor-plugin" / "plugin.json"
    if not plugin.is_file():
        findings.append(f"{bundle}: missing .cursor-plugin/plugin.json")
        return findings
    try:
        manifest = json.loads(plugin.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{plugin}: invalid JSON: {exc}"]
    if manifest.get("name") != ORCHESTRATOR:
        findings.append(f"{plugin}: name must be {ORCHESTRATOR!r}")
    if manifest.get("skills") != "./skills/":
        findings.append(f"{plugin}: skills must be ./skills/")

    skills_root = bundle / "skills"
    if not skills_root.is_dir():
        findings.append(f"{bundle}: missing skills/")
        return findings
    present = sorted(path.name for path in skills_root.iterdir() if path.is_dir())
    if not present:
        findings.append(f"{bundle}: plugin skills/ is empty")
    unknown = [name for name in present if name != ORCHESTRATOR and name not in WORKER_SKILLS]
    if unknown:
        findings.append(f"{bundle}: unexpected Skill directories {unknown}")
    if ORCHESTRATOR in present and set(WORKER_SKILLS).issubset(present):
        expected = sorted(WORKER_SKILLS + (ORCHESTRATOR,))
        if present != expected:
            findings.append(f"{bundle}: full bundle Skill set drifted: {present}")

    for name in present:
        skill = skills_root / name
        if not (skill / "SKILL.md").is_file():
            findings.append(f"{skill}: missing SKILL.md")
        skill_marker = skill / MARKER
        if not skill_marker.is_file():
            findings.append(f"{skill}: missing {MARKER}")
        elif repo is not None:
            canonical = repo / "skills" / name
            if not canonical.is_dir():
                findings.append(f"{skill}: no matching skills/{name} in repo")
                continue
            if file_map(canonical) != file_map(skill):
                findings.append(f"{skill}: bytes differ from skills/{name}")

    text = plugin.read_text(encoding="utf-8")
    for token in UNOFFICIAL:
        if token in text:
            findings.append(f"{plugin}: unofficial API token {token!r}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--repo", type=Path, default=None)
    args = parser.parse_args()
    findings = validate(args.bundle.resolve(), args.repo.resolve() if args.repo else None)
    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1
    print(f"kaola-grok-bot-verify: PASS {args.bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
