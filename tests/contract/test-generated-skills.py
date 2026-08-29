#!/usr/bin/env python3
"""Independent acceptance checks for the generated five-Skill distribution."""

from __future__ import annotations

import hashlib
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RENDERER = PROJECT / "scripts" / "render-skills.py"

PLATFORMS = {
    "grok-kaola-project-runner": {
        "display": "Grok Kaola Project Runner",
        "short": "Run projects through Grok CLI and Kaola Workflow",
        "prompt": "Use $grok-kaola-project-runner to start workflow-next immediately in the current Git repository.",
        "tokens": ("grok", "grok-kaola-project-runner"),
    },
    "claude-code-kaola-project-runner": {
        "display": "Claude Code Kaola Project Runner",
        "short": "Run Kaola Workflow projects through Claude Code",
        "prompt": "Use $claude-code-kaola-project-runner to start workflow-next immediately in the current Git repository.",
        "tokens": ("claude", "claude-code", "claude-code-kaola-project-runner"),
    },
    "opencode-kaola-project-runner": {
        "display": "OpenCode Kaola Project Runner",
        "short": "Run Kaola Workflow projects through OpenCode",
        "prompt": "Use $opencode-kaola-project-runner to start workflow-next immediately in the current Git repository.",
        "tokens": ("opencode", "opencode-kaola-project-runner"),
    },
    "kimi-cli-kaola-project-runner": {
        "display": "Kimi CLI Kaola Project Runner",
        "short": "Run Kaola Workflow projects through Kimi CLI",
        "prompt": "Use $kimi-cli-kaola-project-runner to start workflow-next immediately in the current Git repository.",
        "tokens": ("kimi", "kimi-cli", "kimi-cli-kaola-project-runner"),
    },
    "cursor-cli-kaola-project-runner": {
        "display": "Cursor CLI Kaola Project Runner",
        "short": "Run Kaola Workflow projects through Cursor CLI",
        "prompt": "Use $cursor-cli-kaola-project-runner to start workflow-next immediately in the current Git repository.",
        "tokens": ("cursor", "cursor-agent", "cursor-cli", "cursor-cli-kaola-project-runner"),
    },
}

REQUIRED = ("SKILL.md", "agents/openai.yaml")


class Assertions:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, name: str, condition: bool, detail: str) -> bool:
        if not condition:
            self.failures.append(f"{name} — {detail}")
            print(f"RED: {name} — {detail}", file=sys.stderr)
            return False
        return True

    def run(self, name: str, command: list[str], cwd: Path) -> subprocess.CompletedProcess[str] | None:
        try:
            result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
        except OSError as exc:
            self.check(name, False, str(exc))
            return None
        if result.returncode != 0:
            detail = f"exit {result.returncode}: {(result.stderr or result.stdout).strip()}"
            self.check(name, False, detail)
        return result


def frontmatter(skill: Path) -> tuple[str, str]:
    text = skill.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        raise ValueError("missing YAML frontmatter")
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            values[key.strip()] = value.strip().strip("'\"")
    return values.get("name", ""), values.get("description", "")


def yaml_scalar(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*['\"]?(.*?)['\"]?\s*$", text)
    return match.group(1) if match else ""


def all_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def file_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in all_files(root):
        rel = path.relative_to(root).as_posix()
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def check_self_contained(assertions: Assertions, package: Path, package_id: str) -> None:
    assertions.check(
        f"test_skill_{package_id}_has_required_files",
        all((package / relative).is_file() for relative in REQUIRED),
        f"missing one of {REQUIRED} under {package}",
    )
    if not package.is_dir():
        return

    for path in package.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assertions.check(
            f"test_skill_{package_id}_has_no_parent_path_reference",
            "../" not in text and not re.search(r"(?:^|[\s(])\.\./", text),
            f"parent path reference in {path.relative_to(package)}",
        )
        if path.suffix.lower() in {".md", ".markdown"}:
            for target in re.findall(r"\]\(([^)]+)\)", text):
                target = target.split("#", 1)[0].strip()
                if not target or target.startswith(("/", "http:", "https:", "mailto:")):
                    continue
                resolved = (path.parent / target).resolve()
                inside = os.path.commonpath((str(package.resolve()), str(resolved))) == str(package.resolve())
                assertions.check(
                    f"test_skill_{package_id}_links_stay_inside_package",
                    inside and resolved.is_file(),
                    f"{path.relative_to(package)} links to {target}",
                )


def check_no_cross_platform_leakage(assertions: Assertions, package: Path, package_id: str) -> None:
    forbidden: dict[str, set[str]] = {}
    for other_id, details in PLATFORMS.items():
        if other_id == package_id:
            continue
        forbidden[other_id] = {token.lower() for token in details["tokens"]}

    text_parts: list[str] = []
    for path in package.rglob("*"):
        # The neutral control-plane copy intentionally contains the complete
        # platform enum and adapter dispatch table.  Those shared mechanics
        # are not platform prose and must not make every generated package
        # fail this isolation check.
        if path.is_file() and "scripts" not in path.relative_to(package).parts:
            try:
                text_parts.append(path.read_text(encoding="utf-8").lower())
            except UnicodeDecodeError:
                pass
    text = "\n".join(text_parts)
    # These mentions are part of the shared instruction-discovery, roadmap,
    # and frozen-contract vocabulary, not another runtime's adapter surface.
    # Keep the check focused on runtime leakage and allow only the exact
    # parity-gate wording called out by the contract.
    text = re.sub(r"\bclaude\.md\b", "", text)
    text = text.replace("roadmap cursor", "roadmap")
    text = text.replace("grok golden-contract parity target", "")
    for other_id, tokens in forbidden.items():
        for token in tokens:
            # A common word such as "cursor" is intentionally not exempted: a
            # generated package must not silently carry another adapter's facts.
            escaped = re.escape(token)
            leaked = re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text)
            assertions.check(
                f"test_skill_{package_id}_has_no_{other_id}_leakage",
                leaked is None,
                f"found platform token {token!r}",
            )


GROK_COMPATIBILITY_MARKERS = {
    "SKILL.md": (
        "## Full lifecycle",
        "## Four exposed capabilities",
        "Complete one Workflow project",
        "Recurring Workflow projects",
        "Complete one PR review and finalization",
        "Recurring PR review and finalization",
        "foreground: true",
        "HUMAN_DECISION_REQUIRED",
        "15-minute",
        "workflow-next",
        "kaola-workflow-finalize",
        "## Required handoff",
    ),
    "references/project-run.md": (
        "Work in this Grok main conversation as the owner of the project run.",
        "Repository: {repo}",
        "Selection context:",
        "Definition of done:",
        "Authority boundary:",
        "When an irreversible or value-laden decision requires the user, return HUMAN_DECISION_REQUIRED in",
        "Stop after this selected batch run; do not start a second unrelated batch in one-shot mode.",
    ),
    "references/task-modes.md": (
        "## 1. Complete one Workflow project",
        "## 2. Recurring Workflow projects",
        "## 3. Complete one PR review and finalization",
        "## 4. Recurring PR review and finalization",
        "15-minute current-thread heartbeat",
    ),
    "references/pr-claim-handoff.md": (
        "UNCLAIMED_PR",
        "ORIGIN_PR_HANDOFF",
        "FOREIGN_CLAIM_CONFLICT",
        "claim: none",
        "never synthesize that state merely to make cleanup run",
        "watch-pr",
        "zero matching `kw:claim` markers",
        "Never remove a foreign/mismatched claim",
    ),
    "references/codex-supervision.md": (
        "lightweight 15-minute",
        "supervise and report, not to become a second project owner",
        "HUMAN_DECISION_REQUIRED",
        "Do not inject",
    ),
    "references/scheduling.md": (
        "foreground: true",
        "same main conversation",
        "zero detached General-loop schedulers",
        "MAIN_THREAD_PR_INTAKE_V3_WORKFLOW_REVIEW_HANDOFF",
    ),
    "references/grok-tui.md": (
        "tmux environment metadata",
        "grok inspect --json",
        "The helper starts Grok with `--minimal`",
        "literal bytes",
        "idle",
    ),
    "references/closing.md": (
        "originating run's `watch-pr`",
        "zero matching claim residue",
        "Never clean foreign, mismatched, open unfinished, or ambiguous residue",
        "exact owned Grok session is idle",
        "delete the exact Codex supervision heartbeat",
    ),
}

# Reviewed immutable bytes for the frozen Grok prompt/protocol.  The root
# legacy carrier is intentionally absent in the Issue #1 distribution, so a
# root-vs-golden diff cannot detect an arbitrary future edit.  Updating one of
# these values is an explicit review event for the corresponding golden file;
# generated Grok files must continue to match the reviewed bytes below.
GROK_GOLDEN_REVIEWED_SHA256 = {
    "SKILL.md": "6589f47f7b34c3d697176b2d0abbc05dafd3676348f4b0479a0b925b5d188630",
    "agents/openai.yaml": "66699c5188eb10c53ab166572d530bbe77132c64d5b666c7258f68188bc64ddd",
    "references/closing.md": "ae6c47a21e851f745ea743928b7b20fdc1b08c23929466f05ee9c63c21a07601",
    "references/codex-supervision.md": "44c427a1503ef98fb345825962129c51058bd671d2cc806b047a968ea3baeabb",
    "references/grok-tui.md": "818f9c7496d7d9a132112ceeb4d29c03d10d0c7a7765945026353d8e4033a6f8",
    "references/human-decisions.md": "f7abfdda3d3590fcefd10316cf3bc51a6ffcf79834ae7b23cf7c25f1ba621a2c",
    "references/kaola-lifecycle.md": "2c545d92737fee3bf3b3f1d147ac1e425999f698d0aa3e69a4afe210106dd9ea",
    "references/pr-claim-handoff.md": "d7b452943c5775aa2fc79db402ded3aab9a0cc332230b59f910ce334415c2377",
    "references/project-run.md": "742ec446152abd484fb4c7368da27183878d0f2075c63cec10a1327a8923187f",
    "references/scheduling.md": "da7272156c5f0cca5f1ec223c9464caa338475493a37b296e1eba6fd5daa6867",
    "references/status-monitoring.md": "cd69e7de643f61c3455cfb7ce0b68dbd6131ef2952f3f74a498263815559fc05",
    "references/task-modes.md": "531dd0e0150f8abc05131addb53db92ea1d47c8dfab8084eec61fe81c2b191e1",
}


def check_grok_compatibility(assertions: Assertions, root: Path) -> None:
    package = root / "skills" / "grok-kaola-project-runner"
    if not package.is_dir():
        return
    golden = root / "templates" / "grok-golden"
    assertions.check(
        "test_grok_compatibility_golden_contract_exists",
        golden.is_dir(),
        f"missing frozen Grok contract: {golden}",
    )
    if golden.is_dir():
        # The Grok package is not a paraphrase or a reduced adapter variant:
        # its canonical prose and prompt blocks must be byte-for-byte the
        # frozen golden contract.  Executable files are checked separately.
        expected_files = [
            Path("SKILL.md"),
            Path("agents/openai.yaml"),
            *sorted(path.relative_to(golden) for path in (golden / "references").glob("*.md")),
        ]
        expected_relatives = {relative.as_posix() for relative in expected_files}
        reviewed_relatives = set(GROK_GOLDEN_REVIEWED_SHA256)
        assertions.check(
            "test_grok_golden_reviewed_inventory_is_exact",
            expected_relatives == reviewed_relatives,
            f"reviewed SHA-256 inventory paths are {sorted(reviewed_relatives)!r}, expected {sorted(expected_relatives)!r}",
        )
        for relative in expected_files:
            expected = golden / relative
            actual = package / relative
            reviewed_hash = GROK_GOLDEN_REVIEWED_SHA256.get(relative.as_posix())
            golden_hash = hashlib.sha256(expected.read_bytes()).hexdigest() if expected.is_file() else ""
            assertions.check(
                f"test_grok_golden_reviewed_sha256_{relative.as_posix()}",
                expected.is_file() and reviewed_hash == golden_hash,
                f"golden bytes for {relative} no longer match the reviewed SHA-256 inventory",
            )
            assertions.check(
                f"test_grok_compatibility_exact_{relative.as_posix()}",
                actual.is_file() and expected.is_file() and actual.read_bytes() == expected.read_bytes()
                and hashlib.sha256(actual.read_bytes()).hexdigest() == reviewed_hash,
                f"generated Grok file is not byte-identical to {expected}",
            )

        # The frozen contract may add only the expressly authorized merged-PR
        # residue cleanup to the current root legacy Skill.  A deletion or
        # replacement would be semantic compression; additions are the sole
        # permitted delta, and the exact golden-byte check above constrains
        # those additions to the reviewed template.
        legacy_files = [Path("SKILL.md"), *sorted(Path("references").glob("*.md"))]
        inserted_text: list[str] = []
        legacy_changed = False
        for relative in legacy_files:
            legacy = root / relative
            frozen = golden / relative
            if not legacy.is_file() or not frozen.is_file():
                continue
            legacy_lines = legacy.read_text(encoding="utf-8").splitlines()
            frozen_lines = frozen.read_text(encoding="utf-8").splitlines()
            opcodes = difflib.SequenceMatcher(a=legacy_lines, b=frozen_lines).get_opcodes()
            for tag, _a1, _a2, b1, b2 in opcodes:
                if tag != "equal":
                    legacy_changed = True
                if tag == "delete":
                    assertions.check(
                        f"test_grok_compatibility_preserves_legacy_{relative.as_posix()}",
                        False,
                        f"frozen contract deletes or rewrites root legacy lines ({tag})",
                    )
                elif tag == "replace":
                    old_lines = legacy_lines[_a1:_a2]
                    new_lines = frozen_lines[b1:b2]
                    old_without_numbers = [re.sub(r"^\s*[0-9]+\.\s*", "", line) for line in old_lines]
                    new_without_numbers = [re.sub(r"^\s*[0-9]+\.\s*", "", line) for line in new_lines]
                    changed_for_residue = "\n".join(new_lines).lower()
                    renumber_only = old_without_numbers == new_without_numbers
                    authorized_delta = any(
                        marker in changed_for_residue
                        for marker in (
                            "watch-pr",
                            "workflow:in-progress",
                            "matching claim",
                            "residue",
                            "human_decision_required",
                        )
                    )
                    assertions.check(
                        f"test_grok_compatibility_preserves_legacy_{relative.as_posix()}",
                        renumber_only or authorized_delta,
                        "frozen contract rewrites root legacy lines outside the authorized residue delta",
                    )
                elif tag == "insert":
                    inserted_text.extend(
                        frozen_lines[b1:b2]
                    )
        residue_markers = (
            "watch-pr",
            "workflow:in-progress",
            "matching claim",
            "HUMAN_DECISION_REQUIRED",
        )
        assertions.check(
            "test_grok_compatibility_legacy_delta_is_authorized_residue_cleanup",
            not legacy_changed or any(any(marker in line for marker in residue_markers) for line in inserted_text),
            "frozen contract delta has no authorized merged-PR residue-cleanup marker",
        )
    for relative, markers in GROK_COMPATIBILITY_MARKERS.items():
        path = package / relative
        if not path.is_file():
            assertions.check(
                f"test_grok_compatibility_has_{relative}",
                False,
                f"missing canonical compatibility file {relative}",
            )
            continue
        text = path.read_text(encoding="utf-8")
        # Markdown prose wraps many of the canonical prompt lines.  Match the
        # semantic line while preserving the exact-byte comparison above.
        searchable = re.sub(r"\s+", " ", text)
        for marker in markers:
            assertions.check(
                f"test_grok_compatibility_{relative}_{marker[:32]}",
                re.sub(r"\s+", " ", marker) in searchable,
                f"generated Grok Skill lost canonical marker {marker!r}",
            )


def check_generated_tree(assertions: Assertions, root: Path, require_check: bool = True) -> None:
    generated = root / "skills"
    actual_ids = {
        path.name for path in generated.iterdir() if path.is_dir()
    } if generated.is_dir() else set()
    assertions.check(
        "test_generated_skill_inventory_is_exactly_five",
        actual_ids == set(PLATFORMS),
        f"generated Skill directories are {sorted(actual_ids)!r}, expected {sorted(PLATFORMS)!r}",
    )
    for package_id, details in PLATFORMS.items():
        package = generated / package_id
        check_self_contained(assertions, package, package_id)
        if not package.is_dir():
            continue
        try:
            skill_name, description = frontmatter(package / "SKILL.md")
        except (OSError, ValueError) as exc:
            assertions.check(f"test_skill_{package_id}_frontmatter", False, str(exc))
            continue
        assertions.check(
            f"test_skill_{package_id}_frontmatter_name",
            skill_name == package_id,
            f"name is {skill_name!r}, expected {package_id!r}",
        )
        assertions.check(
            f"test_skill_{package_id}_frontmatter_description",
            bool(description),
            "description is empty",
        )
        metadata_path = package / "agents" / "openai.yaml"
        if not metadata_path.is_file():
            assertions.check(
                f"test_skill_{package_id}_ui_metadata_exists",
                False,
                f"missing UI metadata: {metadata_path}",
            )
            continue
        metadata = metadata_path.read_text(encoding="utf-8")
        display = yaml_scalar(metadata, "display_name")
        short_description = yaml_scalar(metadata, "short_description")
        default_prompt = yaml_scalar(metadata, "default_prompt")
        assertions.check(
            f"test_skill_{package_id}_ui_display_name",
            display == details["display"],
            f"display_name is {display!r}",
        )
        assertions.check(
            f"test_skill_{package_id}_ui_short_description",
            short_description == details["short"],
            f"short_description is {short_description!r}, expected {details['short']!r}",
        )
        assertions.check(
            f"test_skill_{package_id}_ui_default_prompt",
            default_prompt == details["prompt"],
            f"default_prompt is {default_prompt!r}, expected {details['prompt']!r}",
        )
        check_no_cross_platform_leakage(assertions, package, package_id)

    check_grok_compatibility(assertions, root)

    if require_check:
        result = assertions.run(
            "test_render_skills_check_is_clean",
            [sys.executable, str(root / "scripts" / "render-skills.py"), "--check"],
            root,
        )
        if result is not None and result.returncode == 0:
            assertions.check("test_render_skills_check_is_clean", True, "")


def check_deterministic_renderer(assertions: Assertions) -> None:
    if not RENDERER.is_file():
        assertions.check("test_renderer_exists", False, f"missing {RENDERER}")
        return

    ignored = shutil.ignore_patterns(".git", ".kw", "__pycache__", "node_modules")
    with tempfile.TemporaryDirectory(prefix="kaola-render-issue-1-") as temporary:
        copy = Path(temporary) / "repo"
        shutil.copytree(PROJECT, copy, ignore=ignored)
        first = assertions.run("test_renderer_write_first_run", [sys.executable, "scripts/render-skills.py", "--write"], copy)
        if first is None or first.returncode != 0:
            return
        first_hashes = file_hashes(copy / "skills")
        second = assertions.run("test_renderer_write_second_run", [sys.executable, "scripts/render-skills.py", "--write"], copy)
        if second is None or second.returncode != 0:
            return
        second_hashes = file_hashes(copy / "skills")
        assertions.check(
            "test_renderer_is_deterministic",
            first_hashes == second_hashes,
            "second --write changed generated bytes",
        )
        check_generated_tree(assertions, copy, require_check=False)

        candidate = copy / "skills" / next(iter(PLATFORMS)) / "SKILL.md"
        candidate.write_text(candidate.read_text(encoding="utf-8") + "\nDRIFT\n", encoding="utf-8")
        drift = subprocess.run([sys.executable, "scripts/render-skills.py", "--check"], cwd=copy, text=True, capture_output=True)
        assertions.check(
            "test_render_skills_check_rejects_drift",
            drift.returncode != 0,
            "--check accepted a modified generated Skill",
        )


def main() -> int:
    assertions = Assertions()
    check_deterministic_renderer(assertions)
    if RENDERER.is_file():
        # The repository itself is the published tree. This catches a committed
        # package that was generated correctly in a temporary copy but is stale
        # in the checkout being tested.
        check_generated_tree(assertions, PROJECT, require_check=True)
    if assertions.failures:
        print(f"generated Skill acceptance: {len(assertions.failures)} failure(s)", file=sys.stderr)
        return 1
    print("generated Skill acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
