#!/usr/bin/env python3
"""Issue #351: dsh/default and dsh/commandcode share one profile text.

Fail-on-main at 77489f00: the platform file, the profile catalog, the README
preset rows and the rendered dsh platform copy still carry the previous
sentence, so the byte-identity check and the 3D/frontend wording fail.
OpenCode keeps its own preset.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
PROFILE = (
    "Fast, low-cost worker for self-contained tasks with clear goals, "
    "boundaries, acceptance criteria; strong at 3D and frontend; one-pass "
    "complete features; iterative validation, self-repair. Review each "
    "output; split long chain."
)
OLD = (
    "Fast implementation worker for tasks with clear goals and boundaries; "
    "emphasizes autonomous progress, iterative validation, and self-repair."
)
SKIP_DIRS = {".git", ".kw", "kaola-workflow", "__pycache__", "node_modules"}


def yaml_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r'^([a-z0-9_]+):\s*(".*")\s*$', line)
        if match:
            values[match.group(1)] = json.loads(match.group(2))
    return values


def row_profile(text: str, tier: str) -> str:
    needle = f"| dsh | `{tier}` |"
    for line in text.splitlines():
        if needle in line:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            return cells[-1]
    raise AssertionError(f"missing dsh {tier} row")


def leftover_old_sentence() -> list[str]:
    found: list[str] = []
    this = Path(__file__).resolve()
    for path in PROJECT.rglob("*"):
        if not path.is_file() or path.resolve() == this:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if "docs/evidence" in path.as_posix():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if OLD in text:
            found.append(str(path.relative_to(PROJECT)))
    return found


class DshProfileText(unittest.TestCase):
    def test_both_tiers_match_on_four_surfaces(self) -> None:
        platform = yaml_values(PROJECT / "platforms" / "dsh.yaml")
        rendered = yaml_values(
            PROJECT / "skills" / "dsh-kaola-project-runner" / "scripts" / "platform.yaml")
        catalog = (PROJECT / "skills" / "kaola-project-runner" / "references"
                   / "profile-catalog.md").read_text(encoding="utf-8")
        readme = (PROJECT / "README.md").read_text(encoding="utf-8")
        samples = [
            platform["default_model_profile"],
            platform["commandcode_model_profile"],
            rendered["default_model_profile"],
            rendered["commandcode_model_profile"],
            row_profile(catalog, "default"),
            row_profile(catalog, "commandcode"),
            row_profile(readme, "default"),
            row_profile(readme, "commandcode"),
        ]
        self.assertEqual(samples, [PROFILE] * len(samples))
        self.assertLessEqual(len(PROFILE), 225)
        self.assertIn("3D", PROFILE)
        self.assertIn("frontend", PROFILE)
        catalog_bytes = (PROJECT / "skills" / "kaola-project-runner" / "references"
                         / "profile-catalog.md").stat().st_size
        self.assertLessEqual(catalog_bytes, 8130)
        self.assertEqual(leftover_old_sentence(), [])

    def test_opencode_profile_is_a_different_preset(self) -> None:
        opencode = yaml_values(PROJECT / "platforms" / "opencode.yaml")
        self.assertNotEqual(opencode["default_model_profile"], PROFILE)
        self.assertIn(
            "tends to investigate deeper root causes and reduce unrelated changes.",
            opencode["default_model_profile"],
        )


if __name__ == "__main__":
    unittest.main()
