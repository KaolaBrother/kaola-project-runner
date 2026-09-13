#!/usr/bin/env python3
"""Host-neutral validator for the Agent Skills format used by this repository.

Checks each Skill directory against the portable SKILL.md contract: YAML
frontmatter with a spec-conformant ``name`` matching the directory and a
non-empty ``description``. No runtime-specific tooling or configuration is
required; optional host metadata such as ``agents/openai.yaml`` is ignored.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
    "allowed_tools",
}


def validate(skill_dir: Path) -> list[str]:
    findings: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir}: missing SKILL.md"]

    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        return [f"{skill_md}: missing YAML frontmatter delimited by --- lines"]

    fields: dict[str, str] = {}
    for number, raw in enumerate(match.group(1).splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            findings.append(f"{skill_md}: frontmatter line {number} is not key: value")
            continue
        key = key.strip()
        value = value.strip().strip("'\"")
        if key in fields:
            findings.append(f"{skill_md}: duplicate frontmatter field {key!r}")
        fields[key] = value

    unknown = sorted(set(fields) - ALLOWED_FIELDS)
    if unknown:
        findings.append(f"{skill_md}: unsupported frontmatter fields {unknown}")

    name = fields.get("name", "")
    if not name:
        findings.append(f"{skill_md}: frontmatter name is required")
    else:
        if len(name) > NAME_MAX or not NAME_PATTERN.fullmatch(name):
            findings.append(
                f"{skill_md}: name {name!r} must be <= {NAME_MAX} chars of"
                " lowercase letters, numbers, and single hyphens"
            )
        if name != skill_dir.name:
            findings.append(
                f"{skill_md}: name {name!r} must match directory {skill_dir.name!r}"
            )

    description = fields.get("description", "")
    if not description:
        findings.append(f"{skill_md}: frontmatter description is required")
    elif len(description) > DESCRIPTION_MAX:
        findings.append(
            f"{skill_md}: description exceeds {DESCRIPTION_MAX} chars"
        )
    return findings


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {Path(sys.argv[0]).name} SKILL_DIR [SKILL_DIR ...]", file=sys.stderr)
        return 2
    findings: list[str] = []
    for raw in sys.argv[1:]:
        skill_dir = Path(raw)
        if not skill_dir.is_dir():
            findings.append(f"{skill_dir}: not a directory")
            continue
        findings.extend(validate(skill_dir.resolve()))
    if findings:
        for finding in findings:
            print(f"RED: {finding}", file=sys.stderr)
        return 1
    print(f"validate-skill: PASS ({len(sys.argv) - 1} Skill(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
