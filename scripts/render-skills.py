#!/usr/bin/env python3
"""Render the five self-contained Codex Skills from canonical templates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ROOT / "platforms"
TEMPLATES = ROOT / "templates"
SKILLS = ROOT / "skills"
MARKER = ".generated-by-kaola-project-runner"
TOKEN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
REQUIRED = {
    "id", "runtime_name", "skill_name", "display_name", "short_description",
    "default_prompt", "description", "session_prefix", "binary_name", "binary_env",
    "continue_syntax", "resume_syntax", "preflight_summary", "launch_summary",
    "recurring_execution", "recurring_summary", "quit_text",
}


def parse_manifest(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path}:{number}: expected key: value")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ValueError(f"{path}:{number}: invalid key {key!r}")
        if key in result:
            raise ValueError(f"{path}:{number}: duplicate key {key!r}")
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: values must be JSON strings") from exc
        if not isinstance(parsed, str):
            raise ValueError(f"{path}:{number}: values must be strings")
        result[key] = parsed
    missing = REQUIRED - result.keys()
    extra = result.keys() - REQUIRED
    if missing or extra:
        raise ValueError(f"{path}: missing={sorted(missing)} extra={sorted(extra)}")
    if path.stem != result["id"]:
        raise ValueError(f"{path}: filename must match id {result['id']!r}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", result["skill_name"]):
        raise ValueError(f"{path}: invalid skill name {result['skill_name']!r}")
    if result["recurring_execution"] not in {"supported", "unsupported"}:
        raise ValueError(f"{path}: invalid recurring_execution")
    return result


def variables(manifest: dict[str, str]) -> dict[str, str]:
    return {key.upper(): value for key, value in manifest.items()}


def render(template: str, manifest: dict[str, str], source: Path) -> str:
    values = variables(manifest)

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise ValueError(f"{source}: unknown template token {key}")
        return values[key]

    output = TOKEN.sub(replace, template)
    leftovers = TOKEN.findall(output)
    if leftovers:
        raise ValueError(f"{source}: unresolved tokens {leftovers}")
    return output


def align_grok_contract(text: str, manifest: dict[str, str]) -> str:
    """Mechanically align a newer runtime to the frozen, live-proven Grok contract."""
    replacements = (
        (
            "Treat current `grok inspect\n   --json` output",
            "Treat the live adapter preflight result",
        ),
        (
            "The helper starts Grok with `--minimal` so terminal evidence remains capturable.",
            f"{manifest['launch_summary']} Preserve terminal evidence so it remains capturable.",
        ),
        (
            "`pane_current_command` may be `node` for the Grok launcher.",
            "`pane_current_command` may name a launcher or runtime process.",
        ),
        (
            "This only sends `/quit` to an owned idle Grok session.",
            f"This only sends `{manifest['quit_text']}` to an owned idle {manifest['runtime_name']} session.",
        ),
        ("$grok-kaola-project-runner", f"${manifest['skill_name']}"),
        ("grok-kaola-project-runner", manifest["skill_name"]),
        ("Grok Kaola Project Runner", manifest["display_name"]),
        ("scripts/grok-tmux.sh", "scripts/runtime-tmux.sh"),
        ("references/grok-tui.md", "references/platform.md"),
        ("grok-kaola-", f"{manifest['session_prefix']}-"),
        ("$GROK_SESSION_ID", "$RUNTIME_SESSION_ID"),
        ("GROK_START_TIMEOUT", "KAOLA_START_TIMEOUT"),
        ("GROK_BIN", manifest["binary_env"]),
        ("`grok inspect --json`", "the live adapter preflight result"),
        ("grok inspect --json", "the live adapter preflight result"),
        ("`grok plugin list`", "a runtime-native catalog listing"),
        ("`grok`", f"`{manifest['binary_name']}`"),
        ("Grok CLI", manifest["runtime_name"]),
        ("Grok", manifest["runtime_name"]),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def apply_guarded_transport_overlay(text: str, script: str) -> str:
    """Update only generated mutation examples; keep frozen Grok source bytes intact."""
    route = (
        "Mutation commands use the schema-v2 snapshot and editor guards in "
        "[transport.md](transport.md).\n\n"
    )
    observe_heading = "## Observe\n\n"
    if route not in text:
        if text.count(observe_heading) != 1:
            raise ValueError("platform guidance lost the unique Observe heading")
        text = text.replace(observe_heading, route + observe_heading, 1)
    replacements = (
        (
            f'{script} send --repo "$REPO" --session "$SESSION" --text "$PROMPT"',
            f'{script} send --repo "$REPO" --session "$SESSION" \\\n  --if-snapshot "$SNAPSHOT_ID" --require-empty-editor --text "$PROMPT"',
        ),
        (
            f'{script} send --repo "$REPO" --session "$SESSION" < prompt.txt',
            f'{script} send --repo "$REPO" --session "$SESSION" \\\n  --if-snapshot "$SNAPSHOT_ID" --require-empty-editor < prompt.txt',
        ),
        (
            f'{script} stop --repo "$REPO" --session "$SESSION"',
            f'{script} stop --repo "$REPO" --session "$SESSION" \\\n  --if-snapshot "$SNAPSHOT_ID"',
        ),
    )
    for old, new in replacements:
        if text.count(old) != 1:
            raise ValueError(f"platform guidance lost guarded overlay anchor: {old}")
        text = text.replace(old, new, 1)
    return text


def expected_files(manifest: dict[str, str]) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    result[MARKER] = (manifest["skill_name"] + "\n").encode()
    if manifest["id"] == "grok":
        # Grok is the live-proven golden contract. Its runtime-native procedures remain the
        # reference implementation; cross-platform orchestration changes must update these
        # reviewed bytes explicitly rather than being injected only into generated variants.
        contract = TEMPLATES / "grok-golden"
        result["SKILL.md"] = (contract / "SKILL.md").read_bytes()
        result["agents/openai.yaml"] = (contract / "agents" / "openai.yaml").read_bytes()
        for source in sorted((contract / "references").glob("*.md")):
            if source.name == "grok-tui.md":
                overlaid = apply_guarded_transport_overlay(
                    source.read_text(encoding="utf-8"), "scripts/grok-tmux.sh"
                )
                result[f"references/{source.name}"] = overlaid.encode()
            else:
                result[f"references/{source.name}"] = source.read_bytes()
    else:
        contract = TEMPLATES / "grok-golden"
        skill = align_grok_contract((contract / "SKILL.md").read_text(encoding="utf-8"), manifest)
        if manifest["id"] == "claude-code":
            skill = skill.replace(
                "  [references/task-modes.md](references/task-modes.md),\n"
                "  [references/project-run.md](references/project-run.md), and\n"
                "  [references/kaola-lifecycle.md](references/kaola-lifecycle.md).\n",
                "  [references/task-modes.md](references/task-modes.md),\n"
                "  [references/project-run.md](references/project-run.md),\n"
                "  [references/kaola-lifecycle.md](references/kaola-lifecycle.md), and\n"
                "  [references/launch.md](references/launch.md).\n",
                1,
            )
            skill = skill.replace(
                "3. Start a new Claude Code conversation or resume the intended one.",
                "3. Start a new Claude Code conversation or resume the intended one through the "
                "measured configuration and verification sequence in "
                "[references/launch.md](references/launch.md).",
                1,
            )
        result["SKILL.md"] = skill.encode()

        metadata = TEMPLATES / "agents" / "openai.yaml.tmpl"
        result["agents/openai.yaml"] = render(
            metadata.read_text(encoding="utf-8"), manifest, metadata
        ).encode()

        for source in sorted((contract / "references").glob("*.md")):
            target_name = "platform.md" if source.name == "grok-tui.md" else source.name
            if manifest["id"] == "claude-code" and source.name == "scheduling.md":
                claude_schedule = TEMPLATES / "claude-code" / "references" / "scheduling.md"
                aligned = claude_schedule.read_text(encoding="utf-8")
            elif source.name == "scheduling.md":
                schedule = TEMPLATES / "references" / "scheduling.md.tmpl"
                aligned = render(schedule.read_text(encoding="utf-8"), manifest, schedule)
            else:
                aligned = align_grok_contract(source.read_text(encoding="utf-8"), manifest)
            if source.name == "grok-tui.md":
                facts = TEMPLATES / "references" / "platform.md.tmpl"
                aligned = render(facts.read_text(encoding="utf-8"), manifest, facts) + "\n---\n\n" + aligned
                if manifest["id"] == "claude-code":
                    aligned = aligned.replace(
                        "- `idle`: input may be sent if every ownership and identity field is also true.\n",
                        "- `idle`: input may be sent if every ownership and identity field is also true.\n"
                        "- `waiting-human`: a trust, native approval, or Workflow human-decision "
                        "surface is visible; do not inject.\n",
                        1,
                    )
                    aligned = aligned.replace(
                        "The helper uses the exact cwd, its tmux\n"
                        "ownership marker, and the pane title together instead of assuming the executable name is `claude`.\n",
                        "The helper uses exact cwd, tmux ownership, resolved process identity, and stable "
                        "Claude CLI surfaces. Claude may replace the pane title with its active task; that "
                        "does not invalidate an otherwise exact TUI.\n",
                        1,
                    )
                aligned = apply_guarded_transport_overlay(aligned, "scripts/runtime-tmux.sh")
            result[f"references/{target_name}"] = aligned.encode()

        if manifest["id"] == "claude-code":
            launch = TEMPLATES / "claude-code" / "references" / "launch.md"
            result["references/launch.md"] = launch.read_bytes()

    transport = TEMPLATES / "references" / "transport.md.tmpl"
    result["references/transport.md"] = render(
        transport.read_text(encoding="utf-8"), manifest, transport
    ).encode()

    core = ROOT / "scripts" / "kaola-tmux.sh"
    adapter = ROOT / "scripts" / "adapters" / f"{manifest['id']}.sh"
    shared_sources = (
        (core, "scripts/kaola-tmux.sh"),
        (ROOT / "scripts" / "kaola-observation.py", "scripts/kaola-observation.py"),
        (ROOT / "scripts" / "kaola-pane-relay.py", "scripts/kaola-pane-relay.py"),
        (ROOT / "scripts" / "kaola-relay-client.py", "scripts/kaola-relay-client.py"),
        (ROOT / "scripts" / "kaola-relay-protocol.py", "scripts/kaola-relay-protocol.py"),
        (adapter, f"scripts/adapters/{adapter.name}"),
    )
    for source, target in shared_sources:
        if not source.is_file():
            raise ValueError(f"required runtime source missing: {source}")
        result[target] = source.read_bytes()
    wrapper = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "script_dir=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd -P)\"\n"
        + ("export KAOLA_CLAUDE_PROFILE_REQUIRED=true\n" if manifest["id"] == "claude-code" else "")
        + f"exec \"$script_dir/kaola-tmux.sh\" {manifest['id']} \"$@\"\n"
    )
    result["scripts/runtime-tmux.sh"] = wrapper.encode()
    if manifest["id"] == "grok":
        result["scripts/grok-tmux.sh"] = wrapper.encode()
    return result


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory(root: Path) -> dict[str, bytes]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def check_one(target: Path, expected: dict[str, bytes]) -> list[str]:
    actual = inventory(target)
    findings: list[str] = []
    for name in sorted(expected.keys() | actual.keys()):
        if name not in actual:
            findings.append(f"{target.name}: missing {name}")
        elif name not in expected:
            findings.append(f"{target.name}: unexpected {name}")
        elif actual[name] != expected[name]:
            findings.append(
                f"{target.name}: stale {name} "
                f"expected={hash_bytes(expected[name])[:12]} actual={hash_bytes(actual[name])[:12]}"
            )
    return findings


def write_one(target: Path, expected: dict[str, bytes]) -> None:
    SKILLS.mkdir(parents=True, exist_ok=True)
    if target.exists():
        marker = target / MARKER
        if not marker.is_file() or marker.read_bytes() != expected[MARKER]:
            raise ValueError(f"refusing to replace unmanaged Skill directory: {target}")
    temp = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=SKILLS))
    try:
        for name, data in expected.items():
            destination = temp / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            if destination.suffix == ".sh" or destination.name == "kaola-tmux.sh":
                destination.chmod(0o755)
        if target.exists():
            shutil.rmtree(target)
        os.replace(temp, target)
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifests = [parse_manifest(path) for path in sorted(PLATFORMS.glob("*.yaml"))]
    if [m["id"] for m in manifests] != ["claude-code", "cursor-cli", "grok", "kimi-cli", "opencode"]:
        raise ValueError("platform inventory must be exactly claude-code,cursor-cli,grok,kimi-cli,opencode")

    findings: list[str] = []
    expected_names = {m["skill_name"] for m in manifests}
    if SKILLS.is_dir():
        for path in SKILLS.iterdir():
            if path.is_dir() and path.name not in expected_names:
                findings.append(f"unexpected Skill directory: {path.name}")

    for manifest in manifests:
        target = SKILLS / manifest["skill_name"]
        expected = expected_files(manifest)
        if args.write:
            write_one(target, expected)
        else:
            findings.extend(check_one(target, expected))

    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1
    print(f"render-skills: {'WROTE' if args.write else 'PASS'} ({len(manifests)} Skills)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"render-skills: {exc}", file=sys.stderr)
        raise SystemExit(2)
