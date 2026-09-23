#!/usr/bin/env python3
"""Independent acceptance checks for the generated Skill distribution.

Ten platform worker packages remain transport-only. Issue #41 adds one
control-plane package, ``kaola-project-runner``, which is generated through
the same byte inventory/write/check path and is not an eleventh platform.
"""

from __future__ import annotations

import hashlib
import json
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
        "short": "Communicate with Grok CLI through exact ACP",
        "prompt": "Use $grok-kaola-project-runner to start an exact Grok CLI ACP session, read its output, and send only the input I choose.",
        "tokens": ("grok", "grok-kaola-project-runner"),
    },
    "claude-code-kaola-project-runner": {
        "display": "Claude Code Kaola Project Runner",
        "short": "Communicate with Claude Code through exact ACP",
        "prompt": "Use $claude-code-kaola-project-runner to start an exact Claude Code ACP session, read its output, and send only the input I choose.",
        "tokens": ("claude", "claude-code", "claude-code-kaola-project-runner"),
    },
    "opencode-kaola-project-runner": {
        "display": "OpenCode Kaola Project Runner",
        "short": "Communicate with OpenCode through exact ACP",
        "prompt": "Use $opencode-kaola-project-runner to start an exact OpenCode ACP session, read its output, and send only the input I choose.",
        "tokens": ("opencode", "opencode-kaola-project-runner"),
    },
    "kimi-cli-kaola-project-runner": {
        "display": "Kimi CLI Kaola Project Runner",
        "short": "Communicate with Kimi CLI through exact ACP",
        "prompt": "Use $kimi-cli-kaola-project-runner to start an exact Kimi CLI ACP session, read its output, and send only the input I choose.",
        "tokens": ("kimi", "kimi-cli", "kimi-cli-kaola-project-runner"),
    },
    "cursor-cli-kaola-project-runner": {
        "display": "Cursor CLI Kaola Project Runner",
        "short": "Communicate with Cursor CLI through exact ACP",
        "prompt": "Use $cursor-cli-kaola-project-runner to start an exact Cursor CLI ACP session, read its output, and send only the input I choose.",
        "tokens": ("cursor", "cursor-agent", "cursor-cli", "cursor-cli-kaola-project-runner"),
    },
    "devin-kaola-project-runner": {
        "display": "Devin CLI Kaola Project Runner",
        "short": "Communicate with Devin CLI through exact ACP",
        "prompt": "Use $devin-kaola-project-runner to start an exact Devin CLI ACP session, read its output, and send only the input I choose.",
        "tokens": ("devin", "devin-kaola-project-runner"),
    },
    "codex-kaola-project-runner": {
        "display": "Codex CLI Kaola Project Runner",
        "short": "Communicate with Codex CLI through exact ACP",
        "prompt": "Use $codex-kaola-project-runner to start an exact Codex CLI ACP session, read its output, and send only the input I choose.",
        # "codex" alone is the controlling runtime name and legitimately
        # appears in every package's description, so only Codex-specific facts
        # are leakage tokens.
        "tokens": ("codex-kaola-project-runner", "gpt-6-sol", "gpt-6-astra", "codex-acp"),
    },
    "zcode-kaola-project-runner": {
        "display": "ZCode Kaola Project Runner",
        "short": "Communicate with ZCode through exact ACP",
        "prompt": "Use $zcode-kaola-project-runner to start an exact ZCode ACP session, read its output, and send only the input I choose.",
        "tokens": ("zcode", "zcode-kaola-project-runner"),
    },
    "droid-kaola-project-runner": {
        "display": "Droid Kaola Project Runner",
        "short": "Communicate with Droid through exact ACP",
        "prompt": "Use $droid-kaola-project-runner to start an exact Droid ACP session, read its output, and send only the input I choose.",
        "tokens": ("droid", "droid-kaola-project-runner"),
    },
    "dsh-kaola-project-runner": {
        "display": "dsh Kaola Project Runner",
        "short": "Communicate with dsh through exact ACP",
        "prompt": "Use $dsh-kaola-project-runner to start an exact dsh ACP session, read its output, and send only the input I choose.",
        "tokens": ("dsh", "dsh-kaola-project-runner"),
    },
}

REQUIRED = ("SKILL.md", "agents/openai.yaml")
ORCHESTRATOR_ID = "kaola-project-runner"
ORCHESTRATOR_DISPLAY = "Project Runner"
EXTERNAL_ID = "kaola-delegator"
EXTERNAL_DISPLAY = "Kaola-Delegator"
ORCHESTRATOR_MARKER = ".generated-by-kaola-project-runner"
WORKER_TRANSPORT_FILES = (
    "scripts/runtime-tmux.sh",
    "scripts/kaola-tmux.sh",
    "scripts/platform.yaml",
    "scripts/adapters",
)


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


def shell_examples(markdown: str) -> list[str]:
    """Return normalized commands from bash/sh fenced examples."""
    examples: list[str] = []
    for match in re.finditer(r"```(?:bash|sh)\n(.*?)\n```", markdown, flags=re.DOTALL):
        command = re.sub(r"\\\n\s*", " ", match.group(1))
        examples.extend(line.strip() for line in command.splitlines() if line.strip())
    return examples


def is_shell_command_example(command: str) -> bool:
    """Reject diff artifacts and other standalone tokens in routed examples."""
    return re.search(r"(?:^|\s)\+(?:\s|$)", command) is None


def file_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in all_files(root):
        rel = path.relative_to(root).as_posix()
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def check_self_contained(
    assertions: Assertions,
    package: Path,
    package_id: str,
    required: tuple[str, ...] = REQUIRED,
) -> None:
    assertions.check(
        f"test_skill_{package_id}_has_required_files",
        all((package / relative).is_file() for relative in required),
        f"missing one of {required} under {package}",
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
    if package_id == "cursor-cli-kaola-project-runner":
        # Cursor's user-selected Runner presets are intentionally Cursor Grok /
        # Claude Opus models. Remove only those exact declared model facts
        # before checking for accidental adapter/protocol leakage.
        text = text.replace("grok 4.7 extra high", "cursor-default-model")
        text = text.replace("grok-4.7-xhigh", "cursor-default-model-id")
        text = text.replace("claude opus 5.5 high", "cursor-upgrade-model")
        text = text.replace("claude-opus-5-5-high", "cursor-upgrade-model-id")
        # Cursor's ACP option values are the adapter's own bracketed model
        # descriptors; they are declared manifest facts, not Grok adapter
        # leakage. Remove only the exact advertised value strings.
        text = text.replace("grok-4.7[effort=high,fast=true]", "cursor-acp-model-value")
        text = text.replace("claude-fable-5-1[thinking=true,context=300k,effort=high]", "cursor-acp-model-value")
    if package_id == "devin-kaola-project-runner":
        # Devin's declared upgrade and fable preset IDs are Fusion combos that
        # literally name the Claude sidecar (Issue #144); the quirks also name
        # the retired pure fable ID. Remove only those exact declared facts.
        text = text.replace("fusion-claude-opus-5-5-high-sidekick-swe-2-medium", "devin-upgrade-model-id")
        text = text.replace("fusion-claude-fable-5-1-high-sidekick-swe-2-medium", "devin-fable-model-id")
        text = text.replace("claude-fable-5-1-high", "devin-retired-fable-model-id")
    if package_id == "droid-kaola-project-runner":
        # Issue #111/#117: Droid's catalog carries first-class Kimi-family
        # models, and its Runner core preset selects kimi-k3 (Issue #125). That is a
        # Factory catalog fact, not Kimi CLI adapter leakage -- remove only the
        # exact declared preset strings, so a real kimi-cli fact would still fail.
        text = text.replace("kimi k3 max", "droid-core-model")
        text = text.replace("kimi-k3", "droid-core-model-id")
    if package_id == "dsh-kaola-project-runner":
        # Issue #111: dsh's model catalog is grouped by provider route, and one
        # of its routes is literally named `opencode-go`. The default preset
        # selects it, so the route name and the Runner-side display name built
        # from it are declared facts, not OpenCode adapter leakage.
        text = text.replace("opencode-go", "dsh-route-id")
        text = text.replace("opencode go", "dsh-route-name")
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


# Reviewed immutable bytes for the current Grok prompt/protocol.  The root
# legacy carrier is intentionally absent in the Issue #1 distribution, so a
# root-vs-golden diff cannot detect an arbitrary future edit.  Updating one of
# these values is an explicit review event for the corresponding golden file;
# generated Grok files must continue to match the reviewed bytes below.
GROK_GOLDEN_REVIEWED_SHA256 = {
    "SKILL.md": "ae74d354ef1059a60edbde8cb4a99dad09d2d25cc47e0fc637e2c9164cc70dbe",
    "agents/openai.yaml": "66699c5188eb10c53ab166572d530bbe77132c64d5b666c7258f68188bc64ddd",
    "references/closing.md": "2fda2a5726fa39abbbeb87ce7e80815e2d2870f001d7198e949e26f46a2b60c1",
    "references/codex-supervision.md": "b9c3ec5d4aa7081faccf7773d84b08b10bad828cc8e15f4221de9435be7cb2d4",
    "references/grok-tui.md": "818f9c7496d7d9a132112ceeb4d29c03d10d0c7a7765945026353d8e4033a6f8",
    "references/human-decisions.md": "f7abfdda3d3590fcefd10316cf3bc51a6ffcf79834ae7b23cf7c25f1ba621a2c",
    "references/kaola-lifecycle.md": "2c545d92737fee3bf3b3f1d147ac1e425999f698d0aa3e69a4afe210106dd9ea",
    "references/pr-claim-handoff.md": "d7b452943c5775aa2fc79db402ded3aab9a0cc332230b59f910ce334415c2377",
    "references/project-run.md": "742ec446152abd484fb4c7368da27183878d0f2075c63cec10a1327a8923187f",
    "references/scheduling.md": "6ea889913d7e8109767b61695b9d0030e393941861023a2a9955f093e2558e9e",
    "references/status-monitoring.md": "a113eee36c698c8c85d7e2e9a303837a8cc8dfd9c27a6e7e944789758776db20",
    "references/task-modes.md": "c9e8333d82a44edbdf8eb1d2bbb2f3f4f317b9ed34a02aea69fa2240aff3ca23",
}


def check_grok_compatibility(assertions: Assertions, root: Path) -> None:
    package = root / "skills" / "grok-kaola-project-runner"
    golden = root / "templates" / "grok-golden"
    reviewed_relatives = set(GROK_GOLDEN_REVIEWED_SHA256)
    actual_golden = {
        path.relative_to(golden).as_posix()
        for path in golden.rglob("*")
        if path.is_file()
    } if golden.is_dir() else set()
    assertions.check(
        "test_grok_golden_reviewed_inventory_is_exact",
        actual_golden == reviewed_relatives,
        f"golden inventory drifted: actual={sorted(actual_golden)!r}",
    )
    for relative, reviewed_hash in GROK_GOLDEN_REVIEWED_SHA256.items():
        path = golden / relative
        current_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        assertions.check(
            f"test_grok_golden_reviewed_sha256_{relative}",
            current_hash == reviewed_hash,
            f"frozen historical Grok bytes changed at {relative}",
        )
    active = package / "SKILL.md"
    active_text = active.read_text(encoding="utf-8") if active.is_file() else ""
    active_normalized = re.sub(r"\s+", " ", active_text)
    assertions.check(
        "test_grok_active_skill_is_transport_only",
        all(
            marker in active_normalized
            for marker in (
                "communication driver",
                "does not choose commands",
                '"$SKILL_DIR/scripts/runtime-tmux.sh" send',
                "`key --key escape` (or `cancel`) cancels the running turn",
                '"$SKILL_DIR/scripts/runtime-tmux.sh" capture',
                "No invocation implicitly starts `workflow-next`",
            )
        ),
        "active Grok Skill must expose communication tools without Workflow orchestration authority",
    )
    generated_references = {
        path.name for path in (package / "references").glob("*.md")
    }
    assertions.check(
        "test_grok_active_package_has_only_communication_references",
        generated_references == {"acp.md", "platform.md", "steering.md"},
        f"active package carries orchestration references: {sorted(generated_references)!r}",
    )


def check_evidence_first_transport_guidance(
    assertions: Assertions, package: Path, package_id: str
) -> None:
    """Pin the generated Skills to the agent-owned interaction loop.

    Issue #130 retired PTY: the tmux `references/transport.md` overlay (raw
    frame, relay, snapshot and retained-editor evidence) is gone, and the
    Skill's own `## Transport` section plus `references/acp.md` carry the ACP
    facts. The Agent-directed send/stop/key examples stay pinned below.
    """
    transport = package / "references" / "transport.md"
    assertions.check(
        f"test_{package_id}_no_retired_pty_transport_overlay",
        not transport.exists(),
        f"retired PTY transport overlay is still generated: {transport}",
    )
    skill_text = (package / "SKILL.md").read_text(encoding="utf-8") if (package / "SKILL.md").is_file() else ""
    skill_normalized = re.sub(r"\s+", " ", skill_text).lower()
    assertions.check(
        f"test_{package_id}_skill_teaches_agent_decides_then_sends_without_fallback",
        "the controlling agent chooses what to send" in skill_normalized
        and "runner never auto-falls back or resends" in skill_normalized
        and "transport-pty-retired" in skill_normalized,
        "Skill must leave the send decision to the Agent, never auto-fall back, and name the PTY refusal",
    )

    if package_id == "grok-kaola-project-runner":
        # Grok's reviewed prompt/protocol files remain byte-frozen.  Issue #6
        # may add a transport overlay, but must not silently fold it into the
        # golden tree and re-baseline the live-proven Grok contract.
        golden_transport = package.parents[1] / "templates" / "grok-golden" / "references" / "transport.md"
        assertions.check(
            "test_grok_transport_overlay_stays_outside_frozen_golden_contract",
            not golden_transport.exists(),
            f"transport overlay was added to frozen Grok golden bytes: {golden_transport}",
        )
    platform = package / "references" / "platform.md"
    assertions.check(
        f"test_{package_id}_platform_routes_mutations_through_acp",
        platform.is_file() and "[acp.md](acp.md)" in platform.read_text(encoding="utf-8"),
        "generated platform guidance does not route mutations through acp.md",
    )
    if not platform.is_file():
        return

    skill_examples = shell_examples((package / "SKILL.md").read_text(encoding="utf-8"))
    routed_sends = [command for command in skill_examples if " send " in f" {command} "]
    routed_stops = [command for command in skill_examples if " stop " in f" {command} "]
    routed_keys = [command for command in skill_examples if " key " in f" {command} "]
    assertions.check(
        f"test_{package_id}_routed_send_examples_are_evidence_first",
        bool(routed_sends)
        and all(
            is_shell_command_example(command)
            and "--if-snapshot" not in command
            and "--require-empty-editor" not in command
            for command in routed_sends
        ),
        f"routed send example(s) bypass fresh evidence or retain semantic editor authority: {routed_sends!r}",
    )
    assertions.check(
        f"test_{package_id}_routed_stop_examples_are_agent_directed",
        bool(routed_stops)
        and all(is_shell_command_example(command) and "--if-snapshot" not in command for command in routed_stops),
        f"routed stop example(s) still present snapshot correlation as authority: {routed_stops!r}",
    )
    # Issue #130: the PTY native-key examples are gone; the only key is the
    # Agent-selected ACP cancel, and any key example must still name --key.
    assertions.check(
        f"test_{package_id}_routed_key_examples_are_agent_selected",
        all("--key" in command for command in routed_keys)
        and "`key --key escape` (or `cancel`) cancels the running turn" in re.sub(r"\s+", " ", skill_text),
        f"active Skill does not expose the explicit Agent-selected cancel key: {routed_keys!r}",
    )


def check_orchestrator_package(assertions: Assertions, root: Path) -> None:
    package = root / "skills" / ORCHESTRATOR_ID
    assertions.check(
        "test_orchestrator_package_exists",
        package.is_dir(),
        f"missing generated control-plane Skill directory: {package}",
    )
    if not package.is_dir():
        return

    marker = package / ORCHESTRATOR_MARKER
    assertions.check(
        "test_orchestrator_generated_marker",
        marker.is_file() and marker.read_bytes() == f"{ORCHESTRATOR_ID}\n".encode(),
        f"marker must be {ORCHESTRATOR_MARKER} containing {ORCHESTRATOR_ID!r}",
    )
    skill = package / "SKILL.md"
    if not skill.is_file():
        assertions.check("test_orchestrator_skill_md", False, f"missing {skill}")
        return
    try:
        skill_name, description = frontmatter(skill)
    except (OSError, ValueError) as exc:
        assertions.check("test_orchestrator_frontmatter", False, str(exc))
        return
    assertions.check(
        "test_orchestrator_frontmatter_name",
        skill_name == ORCHESTRATOR_ID,
        f"YAML name is {skill_name!r}, expected {ORCHESTRATOR_ID!r}",
    )
    assertions.check(
        "test_orchestrator_frontmatter_description",
        bool(description),
        "description is empty",
    )
    heading = skill.read_text(encoding="utf-8")
    metadata_path = package / "agents" / "openai.yaml"
    display = yaml_scalar(metadata_path.read_text(encoding="utf-8"), "display_name") if metadata_path.is_file() else ""
    assertions.check(
        "test_orchestrator_display_name_project_runner",
        display == ORCHESTRATOR_DISPLAY or re.search(r"(?m)^# Project Runner\s*$", heading) is not None,
        f"display name must be {ORCHESTRATOR_DISPLAY!r} (heading or agents/openai.yaml)",
    )
    relative_files = {path.relative_to(package).as_posix() for path in all_files(package)}
    for forbidden in WORKER_TRANSPORT_FILES:
        leaked = [name for name in relative_files if name == forbidden or name.startswith(forbidden + "/")]
        assertions.check(
            f"test_orchestrator_has_no_{forbidden.replace('/', '_')}",
            not leaked,
            f"control-plane Skill must not ship transport/adapter bytes: {leaked!r}",
        )
    check_self_contained(assertions, package, ORCHESTRATOR_ID, required=("SKILL.md",))
    normalized_heading = re.sub(r"\s+", " ", heading)
    assertions.check(
        "test_orchestrator_consumer_boundary_is_read_only",
        all(
            marker in normalized_heading
            for marker in (
                "For consumer-project work, the Project Runner checkout, templates, generated files, and installed Skill payload are read-only.",
                "Store project-specific authorization, heartbeat, and run facts in the consuming project.",
                "Do not edit this repository, its templates, generated files, or an installed Skill payload unless a human explicitly assigned Project Runner development.",
            )
        ),
        "main Skill must tell consumer-project agents the checkout/templates/generated/installed payload are read-only and to store facts in the consuming project",
    )
    assertions.check(
        "test_orchestrator_records_authorization_in_consuming_project",
        "Record the human's CLI, model/effort, count, and capability restrictions in the consuming project's run records, not in this Skill."
        in normalized_heading,
        "authorization facts must be stored in the consuming project, not in this Skill",
    )


def check_external_package(assertions: Assertions, root: Path) -> None:
    package = root / "skills" / EXTERNAL_ID
    assertions.check(
        "test_external_package_exists",
        package.is_dir(),
        f"missing generated external Skill directory: {package}",
    )
    if not package.is_dir():
        return
    marker = package / ORCHESTRATOR_MARKER
    assertions.check(
        "test_external_generated_marker",
        marker.is_file() and marker.read_bytes() == f"{EXTERNAL_ID}\n".encode(),
        f"marker must contain {EXTERNAL_ID!r}",
    )
    skill = package / "SKILL.md"
    if not skill.is_file():
        assertions.check("test_external_skill_md", False, f"missing {skill}")
        return
    try:
        skill_name, description = frontmatter(skill)
    except (OSError, ValueError) as exc:
        assertions.check("test_external_frontmatter", False, str(exc))
        return
    assertions.check("test_external_frontmatter_name", skill_name == EXTERNAL_ID, f"YAML name is {skill_name!r}")
    assertions.check("test_external_frontmatter_description", bool(description), "description is empty")
    heading = skill.read_text(encoding="utf-8")
    metadata_path = package / "agents" / "openai.yaml"
    display = yaml_scalar(metadata_path.read_text(encoding="utf-8"), "display_name") if metadata_path.is_file() else ""
    assertions.check(
        "test_external_display_name_zcode_orchestrator",
        display == EXTERNAL_DISPLAY or re.search(r"(?m)^# Kaola-Delegator\s*$", heading) is not None,
        f"display name must be {EXTERNAL_DISPLAY!r}",
    )
    relative_files = {path.relative_to(package).as_posix() for path in all_files(package)}
    for forbidden in WORKER_TRANSPORT_FILES:
        leaked = [name for name in relative_files if name == forbidden or name.startswith(forbidden + "/")]
        assertions.check(
            f"test_external_has_no_{forbidden.replace('/', '_')}",
            not leaked,
            f"external Skill must not ship transport/adapter bytes: {leaked!r}",
        )
    check_self_contained(assertions, package, EXTERNAL_ID, required=("SKILL.md",))
    normalized = re.sub(r"\s+", " ", heading)
    assertions.check(
        "test_external_does_not_copy_the_runner_engine",
        "Do not copy that engine" in normalized
        and "Do not dispatch workers" in normalized
        and "KAOLA_ACP_HEARTBEAT_HOST" not in heading,
        "external Skill must stay a thin handoff and not leak per-worker heartbeat binding",
    )
    assertions.check(
        "test_external_names_the_inner_runner",
        "kaola-project-runner" in normalized and "zcode-kaola-project-runner" in normalized,
        "external Skill must name Project Runner and the ZCode worker used to start the Host",
    )


def check_issue_132_one_host(assertions: Assertions, root: Path) -> None:
    """Issue #132 T10/T11: one Host per repo and the reach-out repo sweep are
    stated where each reader looks, and no surface introduces a registry,
    lock file, or pointer file, or reads PPID as an orphan test."""
    def text(*parts: str) -> str:
        path = root.joinpath(*parts)
        return re.sub(r"\s+", " ", path.read_text(encoding="utf-8")) if path.is_file() else ""

    delegator = text("skills", EXTERNAL_ID, "SKILL.md")
    handoff_raw = (root / "skills" / EXTERNAL_ID / "references" / "handoff.md")
    handoff_raw = handoff_raw.read_text(encoding="utf-8") if handoff_raw.is_file() else ""
    handoff = re.sub(r"\s+", " ", handoff_raw)
    main = text("skills", ORCHESTRATOR_ID, "SKILL.md")
    startup = text("skills", ORCHESTRATOR_ID, "references", "host-startup.md")
    dispatch = text("skills", ORCHESTRATOR_ID, "references", "zcode-host-dispatch.md")
    pins = {
        "delegator": (delegator, ("One live Host per repo", "`host-exists` means attach its `existing_host`",
                                  "never rename and retry", "is exact-stopped, proven gone (`residual_pids: []`)",
                                  "`sweep=` line")),
        "handoff": (handoff, ("list --repo \"$PROJECT\" --include-dead", "`identity: verified`",
                              "never a second `start`", "(`stopped` with `residual_pids: []`, or `no-session`)",
                              "first exact-stopped by its own platform's Runner",
                              "`unreachable` twice", "report a `mismatch`", "each with the `sweep=` line",
                              "a PID alone is never liveness")),
        "main": (main, ("one Host per root (`host-exists`)", "the repo sweep first in every beat")),
        "host-startup": (startup, ("## Repo sweep: first step of every beat a Delegator opens",
                                   "`host-exists`", "a PID alone is never liveness",
                                   "`HUMAN_DECISION_REQUIRED`", "Only orphans stop",
                                   "in-flight work is never guessed dead", "`swept: stopped=",
                                   "--include-dead", "`pid_reused: true` never signalled that reused PID",
                                   "`--force` only for `dead` or when that fails",
                                   "`unreachable` on a second `list`",
                                   "attach it if verified, else sweep it")),
        "zcode-host-dispatch": (dispatch, ("identity-verified", "a PID alone is not a seat",
                                           "`holder_pid` is a fourth fact")),
    }
    for surface, (body, phrases) in pins.items():
        for phrase in phrases:
            assertions.check(f"test_issue_132_{surface}_states_one_host_and_sweep",
                             phrase in body, f"{surface} lost {phrase!r}")
    assertions.check("test_issue_132_handoff_text_carries_sweep_line",
                     re.search(r"(?m)^sweep=.*list --repo.*stop orphans only.*keep in-flight", handoff_raw)
                     is not None, "the handoff text block has no sweep= line")
    # Control-plane surfaces; a worker's platform.md may name a platform's own
    # registry (ZCode's desktop provider registry) as a measured fact.
    surfaces = [*root.glob(f"skills/{ORCHESTRATOR_ID}/**/*.md"),
                *root.glob(f"skills/{EXTERNAL_ID}/**/*.md"), *root.glob("hosts/grok-bot/*.md")]
    negation = re.compile(r"\b(no|not|never|do not|absent|without)\b", re.IGNORECASE)
    for path in surfaces:
        body = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        for sentence in re.split(r"(?<=[.;:])\s", body):
            if re.search(r"registry|lock file|pointer file", sentence, re.IGNORECASE):
                assertions.check("test_issue_132_no_registry_lock_or_pointer_mechanism",
                                 negation.search(sentence) is not None,
                                 f"{path.relative_to(root)} names a new mechanism: {sentence[:160]!r}")
        assertions.check("test_issue_132_ppid_is_no_orphan_criterion", "PPID" not in body,
                         f"{path.relative_to(root)} mentions PPID")


def check_generated_tree(assertions: Assertions, root: Path, require_check: bool = True) -> None:
    generated = root / "skills"
    actual_ids = {
        path.name for path in generated.iterdir() if path.is_dir()
    } if generated.is_dir() else set()
    expected_ids = set(PLATFORMS) | {ORCHESTRATOR_ID, EXTERNAL_ID}
    assertions.check(
        "test_generated_skill_inventory_is_ten_workers_orchestrator_and_external",
        actual_ids == expected_ids,
        f"generated Skill directories are {sorted(actual_ids)!r}, expected {sorted(expected_ids)!r}",
    )
    check_orchestrator_package(assertions, root)
    check_external_package(assertions, root)
    check_issue_132_one_host(assertions, root)
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
        check_evidence_first_transport_guidance(assertions, package, package_id)

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
        # The copy has no .git, so a pinned Grok Bot bridge could not be verified there;
        # determinism is measured at the content stage.
        (copy / "templates" / "grok-bot" / "accepted-revision.json").write_text('{"stage": "content"}\n', encoding="utf-8")
        first = assertions.run("test_renderer_write_first_run", [sys.executable, "scripts/render-skills.py", "--write"], copy)
        if first is None or first.returncode != 0:
            return
        first_hashes = file_hashes(copy / "skills")
        assertions.check(
            "test_renderer_write_includes_orchestrator_inventory",
            any(path == f"{ORCHESTRATOR_ID}/SKILL.md" or path.startswith(f"{ORCHESTRATOR_ID}/") for path in first_hashes),
            "first --write did not emit skills/kaola-project-runner through the generated inventory",
        )
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
        orchestrator_skill = copy / "skills" / ORCHESTRATOR_ID / "SKILL.md"
        if orchestrator_skill.is_file():
            candidate.write_text(candidate.read_text(encoding="utf-8").replace("\nDRIFT\n", ""), encoding="utf-8")
            orchestrator_skill.write_text(
                orchestrator_skill.read_text(encoding="utf-8") + "\nDRIFT\n", encoding="utf-8"
            )
            orch_drift = subprocess.run(
                [sys.executable, "scripts/render-skills.py", "--check"], cwd=copy, text=True, capture_output=True
            )
            assertions.check(
                "test_render_skills_check_rejects_orchestrator_drift",
                orch_drift.returncode != 0,
                "--check accepted a modified generated orchestrator Skill",
            )


def check_install_verify(assertions: Assertions, root: Path) -> None:
    """Issue #107: an installed Skills tree is verified against this render
    byte-for-byte, prose included. A stale ``SKILL.md`` — the main Skill or a
    worker Skill — is reported by name with a typed receipt and exit 1 instead
    of needing the manual step-3 ``diff -rq``. The comparison is read-only."""
    renderer = root / "scripts" / "render-skills.py"
    if not renderer.is_file():
        assertions.check("test_install_verify_renderer_exists", False, f"missing {renderer}")
        return
    with tempfile.TemporaryDirectory(prefix="kaola-install-verify-") as temporary:
        installed = Path(temporary) / "skills"
        shutil.copytree(root / "skills", installed)
        aligned = subprocess.run(
            [sys.executable, str(renderer), "--verify-install", str(installed)],
            cwd=root, text=True, capture_output=True,
        )
        ok = assertions.check(
            "test_install_verify_aligned",
            aligned.returncode == 0,
            f"aligned install reported skew (exit {aligned.returncode}): "
            f"{(aligned.stderr or '')[-400:]}",
        )
        if not ok:
            return
        receipt = json.loads((aligned.stdout or "").strip().splitlines()[-1])
        assertions.check(
            "test_install_verify_aligned_receipt",
            receipt.get("result") == "aligned" and receipt.get("reason") is None
            and receipt.get("skew_count") == 0 and receipt.get("mutation_performed") is False,
            f"aligned receipt is wrong: {receipt}",
        )

        stale_main = installed / ORCHESTRATOR_ID / "SKILL.md"
        worker_id = next(iter(PLATFORMS))
        stale_worker = installed / worker_id / "SKILL.md"
        main_original, worker_original = stale_main.read_bytes(), stale_worker.read_bytes()
        main_stale_bytes = main_original + b"\n# an older prose build\n"
        worker_stale_bytes = worker_original + b"\n# an older prose build\n"
        stale_main.write_bytes(main_stale_bytes)
        stale_worker.write_bytes(worker_stale_bytes)
        skewed = subprocess.run(
            [sys.executable, str(renderer), "--verify-install", str(installed)],
            cwd=root, text=True, capture_output=True,
        )
        assertions.check(
            "test_install_verify_rejects_prose_skew",
            skewed.returncode == 1,
            f"prose skew was not refused (exit {skewed.returncode})",
        )
        receipt = json.loads((skewed.stdout or "").strip().splitlines()[-1])
        assertions.check(
            "test_install_verify_prose_skew_receipt",
            receipt.get("result") == "refused" and receipt.get("reason") == "skill-install-skew"
            and receipt.get("mutation_performed") is False,
            f"prose-skew receipt is wrong: {receipt}",
        )
        entries = {(entry["skill"], entry["path"]): entry for entry in receipt.get("skew", [])}
        main_entry = entries.get((ORCHESTRATOR_ID, "SKILL.md"))
        worker_entry = entries.get((worker_id, "SKILL.md"))
        assertions.check(
            "test_install_verify_names_stale_main_skill",
            main_entry is not None and main_entry.get("state") == "stale"
            and main_entry.get("expected") and main_entry.get("actual") != main_entry.get("expected"),
            f"stale main SKILL.md not named with both digests: {main_entry}",
        )
        assertions.check(
            "test_install_verify_names_stale_worker_skill",
            worker_entry is not None and worker_entry.get("state") == "stale",
            f"stale worker SKILL.md not named: {worker_entry}",
        )
        assertions.check(
            "test_install_verify_is_read_only",
            stale_main.read_bytes() == main_stale_bytes
            and stale_worker.read_bytes() == worker_stale_bytes,
            "install verification modified the installed bytes",
        )


def main() -> int:
    assertions = Assertions()
    check_deterministic_renderer(assertions)
    if RENDERER.is_file():
        # The repository itself is the published tree. This catches a committed
        # package that was generated correctly in a temporary copy but is stale
        # in the checkout being tested.
        check_generated_tree(assertions, PROJECT, require_check=True)
        check_install_verify(assertions, PROJECT)
    if assertions.failures:
        print(f"generated Skill acceptance: {len(assertions.failures)} failure(s)", file=sys.stderr)
        return 1
    print("generated Skill acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
