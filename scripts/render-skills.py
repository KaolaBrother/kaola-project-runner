#!/usr/bin/env python3
"""Render the self-contained portable Agent Skills from canonical templates."""

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
HOSTS = ROOT / "hosts"
MARKER = ".generated-by-kaola-project-runner"
ORCHESTRATOR_NAME = "kaola-project-runner"
ORCHESTRATOR_DISPLAY = "Project Runner"
GROK_BOT_HOST = "grok-bot"  # a host packaging adapter (see below), never a platform
TOKEN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
REQUIRED = {
    "id", "runtime_name", "skill_name", "display_name", "short_description",
    "default_prompt", "description", "session_prefix", "binary_name", "binary_env",
    "continue_syntax", "resume_syntax", "preflight_summary", "launch_summary",
    "recurring_execution", "recurring_summary", "quit_text", "default_model_name",
    "default_model_id", "default_model_parameters", "default_model_effort",
    "upgrade_model_name", "upgrade_model_id", "upgrade_model_parameters",
    "upgrade_model_effort", "fast_support", "fast_summary",
    "default_transport", "acp_command",
    "acp_client_capabilities", "acp_quirks", "acp_verified_versions", "acp_env_allowlist",
    "acp_login_requires_pty", "acp_model_config_id", "acp_effort_config_id",
    "acp_fast_config_id", "acp_model_map", "acp_wrapper_pin",
    "acp_init_meta", "acp_fast_values",
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
    if result["default_transport"] not in {"acp", "pty"}:
        raise ValueError(f"{path}: invalid default_transport")
    if not result["acp_command"]:
        raise ValueError(f"{path}: empty acp_command")
    return result


def variables(manifest: dict[str, str]) -> dict[str, str]:
    return {key.upper(): value for key, value in manifest.items()}


def render_text(template: str, values: dict[str, str], source: Path) -> str:
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


def render(template: str, manifest: dict[str, str], source: Path) -> str:
    return render_text(template, variables(manifest), source)


def supported_worker_summary(manifests: list[dict[str, str]]) -> str:
    rows = [
        "| Platform id | Skill directory | Display name | Default transport |",
        "|---|---|---|---|",
    ]
    for manifest in manifests:
        rows.append(
            f"| {manifest['id']} | `{manifest['skill_name']}` | "
            f"{manifest['display_name']} | {manifest['default_transport']} |"
        )
    return "\n".join(rows)




def orchestrator_values(
    manifests: list[dict[str, str]], host: str | None = None
) -> dict[str, str]:
    if host == GROK_BOT_HOST:
        host_workers = embedded_worker_routing(manifests)
    elif host == GROK_BOT_ACCOUNT:
        host_workers = private_skill_routing(manifests)
    elif host is None:
        host_workers = (
            "In a native skill-directory install the seven workers are sibling Skill "
            "directories next to this one; call each by its installed directory."
        )
    else:
        raise ValueError(f"unknown host {host!r}")
    return {
        "HOST_WORKERS": host_workers,
        "SKILL_NAME": ORCHESTRATOR_NAME,
        "DISPLAY_NAME": ORCHESTRATOR_DISPLAY,
        # JSON strings are YAML-compatible quoted scalars; colon-space in this
        # description is otherwise a ScannerError under yaml.safe_load.
        "DESCRIPTION": json.dumps(
            "Use when the controlling Agent should supervise explicitly authorized "
            "CLI workers through the seven platform Runner Skills: recover live "
            "authorization, dispatch and review work, accept deliveries before "
            "finalize, and stop idle sessions without dropping close-out duties."
        ),
        "SHORT_DESCRIPTION": (
            "Supervise authorized CLI workers through the seven platform Runner Skills"
        ),
        "DEFAULT_PROMPT": (
            f"Use ${ORCHESTRATOR_NAME} to recover authorization, supervise named "
            "CLI workers, review evidence, and finalize only after acceptance."
        ),
        "SUPPORTED_WORKERS": supported_worker_summary(manifests),
        "IDLE_BEFORE_STOP": (
            "At every heartbeat, match authorized idle workers to safe parallel work and "
            "dispatch every suitable match. Leave capacity idle rather than invent work or "
            "expand authorization"
        ),
        "ACCEPTANCE_BEFORE_FINALIZE": (
            "Mission-frontier done triggers review, not automatic finalize"
        ),
        "HEARTBEAT_DEFAULT": "30 minutes unless specified",
    }


def expected_orchestrator_files(
    manifests: list[dict[str, str]], host: str | None = None
) -> dict[str, bytes]:
    orch = TEMPLATES / "orchestrator"
    skill_template = orch / "SKILL.md.tmpl"
    if not skill_template.is_file():
        raise ValueError(f"missing orchestrator template: {skill_template}")
    values = orchestrator_values(manifests, host)
    result: dict[str, bytes] = {}
    result[MARKER] = (ORCHESTRATOR_NAME + "\n").encode()
    for source in sorted(orch.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(orch)
        if source.suffix == ".tmpl":
            dest = relative.with_suffix("").as_posix()
            result[dest] = render_text(
                source.read_text(encoding="utf-8"), values, source
            ).encode()
        elif source.name == "heartbeat-skeleton.txt" and relative.parts[0] == "references":
            skeleton = source.read_text(encoding="utf-8")
            intro = (
                "# Heartbeat skeleton\n\n"
                "Starting point for a project-specific heartbeat. Not a second copy "
                "of this Skill's policy. Render from current authorization and "
                "project instructions; replace the same heartbeat when those change. "
                "Do not hard-code host tool names.\n\n"
                "```text\n"
            )
            result["references/heartbeat-skeleton.md"] = (
                intro + skeleton.rstrip() + "\n```\n"
            ).encode()
        else:
            result[relative.as_posix()] = source.read_bytes()
    return result


def expected_files(manifest: dict[str, str]) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    result[MARKER] = (manifest["skill_name"] + "\n").encode()
    skill_template = TEMPLATES / "SKILL.md.tmpl"
    result["SKILL.md"] = render(
        skill_template.read_text(encoding="utf-8"), manifest, skill_template
    ).encode()
    metadata = TEMPLATES / "agents" / "openai.yaml.tmpl"
    result["agents/openai.yaml"] = render(
        metadata.read_text(encoding="utf-8"), manifest, metadata
    ).encode()
    platform_facts = TEMPLATES / "references" / "platform.md.tmpl"
    result["references/platform.md"] = render(
        platform_facts.read_text(encoding="utf-8"), manifest, platform_facts
    ).encode()

    transport = TEMPLATES / "references" / "transport.md.tmpl"
    result["references/transport.md"] = render(
        transport.read_text(encoding="utf-8"), manifest, transport
    ).encode()
    acp = TEMPLATES / "references" / "acp.md.tmpl"
    result["references/acp.md"] = render(
        acp.read_text(encoding="utf-8"), manifest, acp
    ).encode()

    core = ROOT / "scripts" / "kaola-tmux.sh"
    adapter = ROOT / "scripts" / "adapters" / f"{manifest['id']}.sh"
    shared_root = ROOT / "scripts"
    shared_sources = (
        (shared_root / "kaola-tmux.sh", "scripts/kaola-tmux.sh"),
        (shared_root / "kaola-acp.py", "scripts/kaola-acp.py"),
        (shared_root / "kaola-acp-holder.py", "scripts/kaola-acp-holder.py"),
        (PLATFORMS / f"{manifest['id']}.yaml", "scripts/platform.yaml"),
        (shared_root / "kaola-model-policy.py", "scripts/kaola-model-policy.py"),
        (shared_root / "kaola-observation.py", "scripts/kaola-observation.py"),
        (shared_root / "kaola-pane-relay.py", "scripts/kaola-pane-relay.py"),
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


def write_bundle(parent: Path, target: Path, expected: dict[str, bytes], kind: str) -> None:
    parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        marker = target / MARKER
        if not marker.is_file() or marker.read_bytes() != expected[MARKER]:
            raise ValueError(f"refusing to replace unmanaged {kind} directory: {target}")
    temp = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=parent))
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


def write_one(target: Path, expected: dict[str, bytes]) -> None:
    write_bundle(SKILLS, target, expected, "Skill")








# ---------------------------------------------------------------------------
# Host adapter: grok-bot (packaging adapter, not a CLI transport platform)
#
# One canonical Skill system exists: the orchestrator template, the worker
# template, the seven platform manifests, and their canonical references.
# A host adapter only re-packages that system for one host. This adapter's
# inputs are exactly GROK_BOT_ADAPTER_INPUTS; its outputs are the files of
# expected_grok_bot_host_files(). Host differences live only here: reference
# expansion, Local Computer path hints, the single-Markdown account form, the
# fingerprint manifest, and the install steps. Scheduling, safety, and
# transport semantics come from the canonical sources and are never authored
# in this section. This host has no platform manifest and no transport adapter.
# --write owns every product below; --check and kaola-grok-bot-verify.py
# reject any product that drifts from a fresh render.
# ---------------------------------------------------------------------------
GROK_BOT_ADAPTER_INPUTS = (
    "templates/orchestrator",      # canonical orchestrator Skill + references
    "templates/SKILL.md.tmpl",     # canonical worker contract
    "templates/agents",            # canonical Skill metadata
    "templates/references",        # canonical worker references
    "platforms",                   # the seven platform manifests
    "scripts",                     # shared runtime scripts and adapters
    "templates/grok-bot",          # adapter-only prose: the install guide
)
# Local Computer runtime copy: one directory, the orchestrator root plus the seven
# workers embedded as supporting resources (contract renamed so exactly one
# discoverable SKILL.md exists).
WORKER_CONTRACT = "WORKER.md"
EMBEDDED_WORKER_DROP = frozenset({MARKER, "agents/openai.yaml"})
# Account form: a Grok Bot private skill is one single Markdown (name, description,
# body), so the account receives eight standalone documents -- the orchestrator plus
# one per worker -- each derived from the canonical sources above. The fingerprint
# manifest lists them; the install guide is executed by Grok Bot itself (not a Skill).
GROK_BOT_ACCOUNT = "grok-bot-account"
PRIVATE_SKILLS_DIR = "private-skills"
PRIVATE_SKILLS_MANIFEST = "private-skills.json"
INSTALL_GUIDE = "INSTALL.md"
ACCOUNT_SECTION = "## Grok Bot account-private form"
BUNDLED_REFERENCE = "## Bundled reference: "
GROK_BOT_HOME = "${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}"
LOCAL_RUNTIME_COPY = f"{GROK_BOT_HOME}/skills/{ORCHESTRATOR_NAME}"
WORKER_REFERENCES = ("platform.md", "transport.md", "acp.md")
ORCHESTRATOR_REFERENCES = ("grok-bot-host.md", "heartbeat-skeleton.md")


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a single-Markdown Skill into its frontmatter map and body."""
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        raise ValueError("single-Markdown Skill must start with frontmatter")
    end = lines.index("---", 1)
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = json.loads(value)
        meta[key.strip()] = value
    return meta, "\n".join(lines[end + 1:])


def embedded_worker_routing(manifests: list[dict[str, str]]) -> str:
    rows = [
        "#### Embedded workers (Grok Bot Local Computer runtime copy)",
        "",
        "In this runtime copy the seven workers are supporting resources of this one Skill",
        "directory (one discoverable Skill, seven embedded workers), under",
        f"`workers/<platform id>/`; their contract file is `{WORKER_CONTRACT}`, not a",
        "discoverable `SKILL.md`. Load a worker contract on demand from this Skill's own",
        "directory; nothing else has to be discovered or enabled. A worker's `SKILL_DIR` is",
        "`<local execution copy of this Skill>/workers/<platform id>` and its Runner entry is",
        "`SKILL_DIR/scripts/runtime-tmux.sh`.",
        "",
        "| Platform id | Worker contract | Runner entry | Default transport |",
        "|---|---|---|---|",
    ]
    for manifest in manifests:
        rows.append(
            f"| {manifest['id']} | `workers/{manifest['id']}/{WORKER_CONTRACT}` | "
            f"`workers/{manifest['id']}/scripts/runtime-tmux.sh` | {manifest['default_transport']} |"
        )
    return "\n".join(rows)


def private_skill_routing(manifests: list[dict[str, str]]) -> str:
    rows = [
        "#### Worker Private Skills (Grok Bot account)",
        "",
        "On a Grok Bot account each of the seven workers is its own account-private Skill,",
        "saved from one single-Markdown document exactly like this one. Select a worker by",
        "the stable Skill name below and load that Skill (ask for it by name when it is not",
        "already loaded) for every transport operation: preflight, start, observe, send,",
        "capture, key, and stop. This Skill carries no transport contract, no scripts, and",
        "none of the worker text; each worker Skill states its own Local Computer script",
        "location.",
        "",
        "| Platform id | Worker Private Skill (stable name) | Display name | Default transport |",
        "|---|---|---|---|",
    ]
    for manifest in manifests:
        rows.append(
            f"| {manifest['id']} | `{manifest['skill_name']}` | "
            f"{manifest['display_name']} | {manifest['default_transport']} |"
        )
    return "\n".join(rows)


def embedded_worker_files(manifest: dict[str, str]) -> dict[str, bytes]:
    """One worker as a supporting resource: same bytes as its Skill, minus Skill identity."""
    result: dict[str, bytes] = {}
    for relative, data in expected_files(manifest).items():
        if relative in EMBEDDED_WORKER_DROP:
            continue
        if relative == "SKILL.md":
            relative = WORKER_CONTRACT
        result[relative] = data
    return result


def bundled_references(names: tuple[str, ...], files: dict[str, bytes]) -> str:
    """Append reference documents verbatim so a single-Markdown Skill needs no file tree."""
    parts: list[str] = []
    for name in names:
        text = files[f"references/{name}"].decode("utf-8")
        parts.append(f"\n{BUNDLED_REFERENCE}references/{name}\n\n{text.rstrip()}\n")
    return "".join(parts)


def worker_private_skill(manifest: dict[str, str]) -> bytes:
    """One worker as an account-private Skill: its canonical SKILL.md verbatim, then the
    Local Computer script location and its three references bundled verbatim."""
    files = expected_files(manifest)
    wid = manifest["id"]
    account = (
        f"\n{ACCOUNT_SECTION}\n\n"
        f"This document is the account-private Skill `{manifest['skill_name']}` for the Grok Bot\n"
        "host: one single Markdown (frontmatter `name` and `description` plus this body) saved on\n"
        "its own by the Bot's skill write. It depends on no other saved Skill and on no file tree\n"
        "in the account; the three reference documents linked above are bundled verbatim at the\n"
        "end of this document. The scripts run on **Local Computer** (never on the cloud Agent\n"
        "Computer) from the generated runtime copy installed on this machine by\n"
        "`./scripts/install-local.sh --runtime grok-bot`:\n\n"
        "```bash\n"
        f'SKILL_DIR="{LOCAL_RUNTIME_COPY}/workers/{wid}"\n'
        '"$SKILL_DIR/scripts/runtime-tmux.sh" preflight --repo "$REPO" --session "$SESSION"\n'
        "```\n\n"
        "`KAOLA_GROK_BOT_HOME` overrides the root `$HOME/.kaola/grok-bot`. In that copy this\n"
        f"contract is the file `workers/{wid}/{WORKER_CONTRACT}` and `$SKILL_DIR/references/` holds the\n"
        f"same three documents. The main Skill `{ORCHESTRATOR_NAME}` ({ORCHESTRATOR_DISPLAY}) selects\n"
        "this worker by its Skill name; this Skill stays transport-only and carries no\n"
        "orchestrator policy.\n"
    )
    text = files["SKILL.md"].decode("utf-8").rstrip() + "\n" + account
    return (text + bundled_references(WORKER_REFERENCES, files)).encode()


def orchestrator_private_skill(manifests: list[dict[str, str]]) -> bytes:
    """The orchestrator as an account-private Skill: the shared template rendered with the
    worker Private Skill routing table, then its two references bundled verbatim."""
    files = expected_orchestrator_files(manifests, GROK_BOT_ACCOUNT)
    account = (
        f"\n{ACCOUNT_SECTION}\n\n"
        f"This document is the account-private Skill `{ORCHESTRATOR_NAME}` ({ORCHESTRATOR_DISPLAY})\n"
        "for the Grok Bot host: one single Markdown (frontmatter `name` and `description` plus\n"
        "this body) saved on its own by the Bot's skill write. The seven workers are seven other\n"
        "account-private Skills with the stable names in the routing table above; this Skill\n"
        "carries no transport contract, no scripts, and none of their text. The two reference\n"
        "documents linked above are bundled verbatim at the end of this document. Grok Bot\n"
        f"installs and updates all eight from this repository by following `{INSTALL_GUIDE}` next\n"
        f"to the `{PRIVATE_SKILLS_DIR}/` documents.\n"
    )
    text = files["SKILL.md"].decode("utf-8").rstrip() + "\n" + account
    return (text + bundled_references(ORCHESTRATOR_REFERENCES, files)).encode()


def private_skill_documents(manifests: list[dict[str, str]]) -> dict[str, bytes]:
    """Exactly eight single-Markdown account-private Skills: 1 orchestrator + 7 workers."""
    result = {f"{ORCHESTRATOR_NAME}.md": orchestrator_private_skill(manifests)}
    for manifest in manifests:
        result[f"{manifest['skill_name']}.md"] = worker_private_skill(manifest)
    return result


def private_skill_manifest(manifests: list[dict[str, str]], documents: dict[str, bytes]) -> bytes:
    """Fingerprints of the eight account documents: name, description, body/file sha256."""
    roles = [(ORCHESTRATOR_NAME, "orchestrator", None)] + [
        (m["skill_name"], "worker", m["id"]) for m in manifests
    ]
    skills = []
    for name, role, platform_id in roles:
        data = documents[f"{name}.md"]
        meta, body = split_frontmatter(data.decode("utf-8"))
        if meta.get("name") != name:
            raise ValueError(f"{name}.md: frontmatter name must be {name!r}")
        skills.append({
            "name": name,
            "description": meta["description"],
            "role": role,
            "platform_id": platform_id,
            "source": f"{PRIVATE_SKILLS_DIR}/{name}.md",
            "file_sha256": hash_bytes(data),
            "body_sha256": hash_bytes(body.encode("utf-8")),
        })
    payload = {
        "host": GROK_BOT_HOST,
        "adapter": GROK_BOT_ACCOUNT,
        "install_guide": INSTALL_GUIDE,
        "skill_count": len(skills),
        "skills": skills,
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def install_guide(manifests: list[dict[str, str]]) -> bytes:
    template = TEMPLATES / "grok-bot" / (INSTALL_GUIDE + ".tmpl")
    if not template.is_file():
        raise ValueError(f"missing install guide template: {template}")
    rows = [
        "| # | Stable Skill name | Source file (read on Local Computer) | Role |",
        "|---|---|---|---|",
        f"| 1 | `{ORCHESTRATOR_NAME}` | `hosts/{GROK_BOT_HOST}/{PRIVATE_SKILLS_DIR}/{ORCHESTRATOR_NAME}.md` | main Skill ({ORCHESTRATOR_DISPLAY}) |",
    ]
    for number, manifest in enumerate(manifests, 2):
        rows.append(
            f"| {number} | `{manifest['skill_name']}` | "
            f"`hosts/{GROK_BOT_HOST}/{PRIVATE_SKILLS_DIR}/{manifest['skill_name']}.md` | "
            f"{manifest['runtime_name']} worker (transport-only) |"
        )
    names = [ORCHESTRATOR_NAME] + [m["skill_name"] for m in manifests]
    values = {
        "PRIVATE_SKILL_TABLE": "\n".join(rows),
        "PRIVATE_SKILL_NAMES": ", ".join(f"`{name}`" for name in names),
        "SKILL_COUNT": str(len(names)),
        "WORKER_COUNT": str(len(manifests)),
        "LOCAL_RUNTIME_COPY": LOCAL_RUNTIME_COPY,
        "FIRST_WORKER_ID": manifests[0]["id"],
        "FIRST_WORKER_SKILL": manifests[0]["skill_name"],
        "FIRST_WORKER_RUNTIME": manifests[0]["runtime_name"],
    }
    return render_text(template.read_text(encoding="utf-8"), values, template).encode()


def expected_grok_bot_host_files(manifests: list[dict[str, str]]) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    result[MARKER] = (GROK_BOT_HOST + "\n").encode()
    result[INSTALL_GUIDE] = install_guide(manifests)
    documents = private_skill_documents(manifests)
    for name, data in documents.items():
        result[f"{PRIVATE_SKILLS_DIR}/{name}"] = data
    result[PRIVATE_SKILLS_MANIFEST] = private_skill_manifest(manifests, documents)
    prefix = f"{ORCHESTRATOR_NAME}/"
    for relative, data in expected_orchestrator_files(manifests, GROK_BOT_HOST).items():
        result[prefix + relative] = data
    for manifest in manifests:
        worker_prefix = f"{prefix}workers/{manifest['id']}/"
        for relative, data in embedded_worker_files(manifest).items():
            result[worker_prefix + relative] = data
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifests = [parse_manifest(path) for path in sorted(PLATFORMS.glob("*.yaml"))]
    if [m["id"] for m in manifests] != ["claude-code", "codex", "cursor-cli", "devin", "grok", "kimi-cli", "opencode"]:
        raise ValueError("platform inventory must be exactly claude-code,codex,cursor-cli,devin,grok,kimi-cli,opencode")

    findings: list[str] = []
    expected_names = {m["skill_name"] for m in manifests} | {ORCHESTRATOR_NAME}
    if SKILLS.is_dir():
        for path in SKILLS.iterdir():
            if path.is_dir() and path.name not in expected_names:
                findings.append(f"unexpected Skill directory: {path.name}")
    if HOSTS.is_dir():
        for path in HOSTS.iterdir():
            if path.is_dir() and path.name != GROK_BOT_HOST:
                findings.append(f"unexpected host directory: {path.name}")

    for manifest in manifests:
        target = SKILLS / manifest["skill_name"]
        expected = expected_files(manifest)
        if args.write:
            write_one(target, expected)
        else:
            findings.extend(check_one(target, expected))

    orch_target = SKILLS / ORCHESTRATOR_NAME
    orch_expected = expected_orchestrator_files(manifests)
    if args.write:
        write_one(orch_target, orch_expected)
    else:
        findings.extend(check_one(orch_target, orch_expected))

    host_target = HOSTS / GROK_BOT_HOST
    host_expected = expected_grok_bot_host_files(manifests)
    if args.write:
        write_bundle(HOSTS, host_target, host_expected, "host")
    else:
        findings.extend(check_one(host_target, host_expected))

    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1
    print(
        f"render-skills: {'WROTE' if args.write else 'PASS'} "
        f"({len(manifests)} workers + {ORCHESTRATOR_NAME} + {GROK_BOT_HOST} host: "
        f"{len(manifests) + 1} private skills + runtime copy)"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"render-skills: {exc}", file=sys.stderr)
        raise SystemExit(2)
