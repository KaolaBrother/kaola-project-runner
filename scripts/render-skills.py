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
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ROOT / "platforms"
TEMPLATES = ROOT / "templates"
SKILLS = ROOT / "skills"
HOSTS = ROOT / "hosts"
VENDOR = ROOT / "vendor"
MARKER = ".generated-by-kaola-project-runner"
# The one vendored ACP bridge (Issue #50): shipped only inside this platform's worker Skill.
VENDORED_BRIDGE_PLATFORM = "claude-code"
VENDORED_BRIDGE = "claude-code-acp"
VENDORED_BRIDGE_FILES = ("dist/index.js", "dist/DERIVATION.json", "LICENSE", "UPSTREAM.md")
# Issue #51: Runner-owned ZCode ACP translator, shipped only inside the ZCode worker.
ZCODE_PLATFORM = "zcode"
ZCODE_ADAPTER = "kaola-zcode-acp.py"
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




def orchestrator_values(manifests: list[dict[str, str]]) -> dict[str, str]:
    return {
        "SKILL_NAME": ORCHESTRATOR_NAME,
        "DISPLAY_NAME": ORCHESTRATOR_DISPLAY,
        "LOCATOR": LOCATOR_COMMAND,
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


def expected_orchestrator_files(manifests: list[dict[str, str]]) -> dict[str, bytes]:
    orch = TEMPLATES / "orchestrator"
    skill_template = orch / "SKILL.md.tmpl"
    if not skill_template.is_file():
        raise ValueError(f"missing orchestrator template: {skill_template}")
    values = orchestrator_values(manifests)
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
    if manifest["id"] == VENDORED_BRIDGE_PLATFORM:
        # Issue #50: the Claude Code worker alone carries the vendored, pinned
        # claude-code-acp bridge as its ACP agent -- the committed single-file
        # bundle, its derivation record, and the upstream attribution. The
        # manifest's Skill-relative acp_command resolves to it inside the
        # installed Skill; no other worker, the orchestrator, or a host bundle
        # receives these bytes.
        for name in VENDORED_BRIDGE_FILES:
            source = VENDOR / VENDORED_BRIDGE / name
            if not source.is_file():
                raise ValueError(f"required vendored bridge file missing: {source}")
            result[f"scripts/vendor/{VENDORED_BRIDGE}/{name}"] = source.read_bytes()
    if manifest["id"] == ZCODE_PLATFORM:
        source = shared_root / ZCODE_ADAPTER
        if not source.is_file():
            raise ValueError(f"required ZCode ACP adapter missing: {source}")
        result[f"scripts/{ZCODE_ADAPTER}"] = source.read_bytes()
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
            if destination.suffix == ".sh" or destination.name in {"kaola-tmux.sh", ZCODE_ADAPTER}:
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
# template, the eight platform manifests, and their canonical references. A
# host adapter only re-packages that system for one host. Grok Bot receives
# exactly ONE thin account/cloud Skill -- the bridge -- rendered from
# templates/grok-bot/ alone: it names the repository, the accepted pinned
# revision, the device-local locator command, and the two canonical entry paths
# (ROOT/skills/kaola-project-runner and ROOT/skills/<platform>-kaola-project-
# runner). It copies NO canonical body, reference, worker text, transport, or
# path: every policy stays in the repository and is loaded on demand from a
# verified checkout on the bound execution target (progressive disclosure).
# Products: the bridge, its fingerprint manifest, and the one-write bootstrap
# guide. No platform manifest, no transport adapter, no runtime copy, no
# per-worker account Skills. --write owns every product; --check and
# kaola-grok-bot-verify.py reject any product that drifts from a fresh render.
# The adapter functions take no manifest: a platform-manifest edit leaves all
# three products byte-identical (Issue49BridgeInvariance proves it).
#
# Two-commit content/pin model. A commit cannot honestly pin itself, so the
# accepted revision file declares a stage:
#   stage "content" -- the content commit R (runtime, docs, tests). The bridge
#                      renders an explicit unpinned placeholder line and must
#                      not be saved to any account.
#   stage "pinned"  -- the pin commit P that follows R: commit = R plus exactly
#                      one of release (a vX.Y.Z tag at R) or label (honest
#                      pre-release text). The bridge saved from P names R; the
#                      UAT checkout is clean and detached at R.
# At the pinned stage --check/--write prove (pin_findings) that R exists here,
# is an ancestor of HEAD, is not a self-pin, carries every path the bridge
# tells the Agent to load or run, and that a named release tag points at R.
# --require-pinned is the final gate for P.
# ---------------------------------------------------------------------------
GROK_BOT_ADAPTER_INPUTS = (
    "templates/grok-bot",          # adapter-only prose: bridge, guide, accepted revision
)
STAGES = ("content", "pinned")
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ,;:#().+-]{2,79}$")
# A label is honest pre-release text: it may not look like a release tag or begin with "release".
LABEL_MASQUERADE = re.compile(r"(?i)(?:^\s*release\b|\bv\d+\.\d+\.\d+\b)")
CONTENT_STAGE_LINE = (
    "Accepted revision: none yet. This is the unpinned content-stage render; do not save it to any "
    "account. The pin commit that follows names the content commit."
)
GROK_BOT_TEMPLATES = TEMPLATES / "grok-bot"
BRIDGE_FILE = f"{ORCHESTRATOR_NAME}.md"
BRIDGE_MANIFEST = "bridge.json"
INSTALL_GUIDE = "INSTALL.md"
ACCEPTED_REVISION_FILE = "accepted-revision.json"
LOCATOR_COMMAND = "kaola-project-runner-locate"
REPO_SLUG = "KaolaBrother/kaola-project-runner"
EXPECTED_ORIGIN = f"github.com/{REPO_SLUG}"
REVISION = re.compile(r"^[0-9a-f]{40}$")
RELEASE = re.compile(r"^v\d+\.\d+\.\d+$")
BRIDGE_DESCRIPTION = (
    "Use when the controlling Agent should supervise explicitly authorized CLI workers "
    "through Project Runner on a bound execution target: locate that target's verified "
    "kaola-project-runner checkout, then load the main Skill and one selected platform "
    "worker from it."
)


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


def accepted_revision() -> dict[str, str | None]:
    path = GROK_BOT_TEMPLATES / ACCEPTED_REVISION_FILE
    if not path.is_file():
        raise ValueError(f"missing accepted revision file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    stage = str(data.get("stage") or "")
    if stage not in STAGES:
        raise ValueError(f"{path}: stage must be one of {list(STAGES)}, got {stage!r}")
    commit = str(data.get("commit") or "")
    release = str(data.get("release") or "")
    label = str(data.get("label") or "")
    if stage == "content":
        if commit or release or label:
            raise ValueError(f"{path}: the content stage carries no commit, release, or label")
        return {"stage": stage, "commit": None, "release": None, "label": None}
    if not REVISION.match(commit):
        raise ValueError(f"{path}: commit must be a 40-hex accepted revision, got {commit!r}")
    if bool(release) == bool(label):
        raise ValueError(f"{path}: the pinned stage names exactly one of release (vX.Y.Z tag) or label")
    if release and not RELEASE.match(release):
        raise ValueError(f"{path}: release must look like vX.Y.Z, got {release!r}")
    if label and not LABEL.match(label):
        raise ValueError(f"{path}: label must be 3-80 plain characters, got {label!r}")
    if label and LABEL_MASQUERADE.search(label):
        raise ValueError(f"{path}: label must not masquerade as a release (use release for a tag at R), got {label!r}")
    return {"stage": stage, "commit": commit, "release": release or None, "label": label or None}


def accepted_line(revision: dict[str, str | None]) -> str:
    if revision["stage"] == "content":
        return CONTENT_STAGE_LINE
    tag = f"release {revision['release']}" if revision["release"] else str(revision["label"])
    return f"Accepted revision: `{revision['commit']}` ({tag})."


def git_out(*args: str) -> str | None:
    """stdout of `git -C ROOT ...`, or None on any non-zero exit; never prompts."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), *args], capture_output=True, text=True, env=env,
            timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def required_pin_paths(manifests: list[dict[str, str]]) -> list[str]:
    """Every path the bridge tells the Agent to load or run from the pinned checkout."""
    paths = ["scripts/kaola-locate.py", f"skills/{ORCHESTRATOR_NAME}/SKILL.md"]
    for manifest in manifests:
        paths.append(f"skills/{manifest['skill_name']}/SKILL.md")
        paths.append(f"skills/{manifest['skill_name']}/scripts/runtime-tmux.sh")
    return paths


def pin_findings(revision: dict[str, str | None], manifests: list[dict[str, str]]) -> list[str]:
    """The pinned stage must name a real, reachable, complete, non-self content commit."""
    if revision["stage"] != "pinned":
        return []
    commit = str(revision["commit"])
    short = commit[:12]
    if git_out("rev-parse", "--is-inside-work-tree") != "true":
        return [f"pin: {short} cannot be verified: {ROOT} is not a Git checkout"]
    if git_out("cat-file", "-e", f"{commit}^{{commit}}") is None:
        return [f"pin: accepted commit {short} does not exist in this checkout"]
    findings: list[str] = []
    if git_out("merge-base", "--is-ancestor", commit, "HEAD") is None:
        findings.append(f"pin: accepted commit {short} is not an ancestor of HEAD")
    tree = set((git_out("ls-tree", "-r", "--name-only", commit) or "").splitlines())
    for path in required_pin_paths(manifests):
        if path not in tree:
            findings.append(f"pin: accepted commit {short} lacks {path}")
    pinned_file = git_out("show", f"{commit}:templates/grok-bot/{ACCEPTED_REVISION_FILE}")
    if pinned_file is None:
        findings.append(f"pin: accepted commit {short} lacks templates/grok-bot/{ACCEPTED_REVISION_FILE}")
    else:
        try:
            pinned_data = json.loads(pinned_file)
        except ValueError:
            pinned_data = None
        if not isinstance(pinned_data, dict):
            findings.append(f"pin: accepted commit {short} carries an unreadable {ACCEPTED_REVISION_FILE}")
        elif pinned_data.get("commit") == commit:
            findings.append(f"pin: accepted commit {short} pins itself (a commit cannot contain its own hash)")
        elif pinned_data.get("stage") != "content":
            # Only a content commit is an honest target: a pin commit names another commit.
            findings.append(f"pin: accepted commit {short} is not a content-stage commit (stage {pinned_data.get('stage')!r})")
    if revision["release"]:
        tag_commit = git_out("rev-parse", f"{revision['release']}^{{commit}}")
        if tag_commit != commit:
            findings.append(f"pin: release {revision['release']} is not a tag at {short}")
    findings.extend(pin_delta_findings(commit, revision))
    return findings


# The pin commit P may differ from its content commit R only by these four files.
PIN_DELTA_PATHS = frozenset({
    f"templates/{GROK_BOT_HOST}/{ACCEPTED_REVISION_FILE}",
    f"hosts/{GROK_BOT_HOST}/{BRIDGE_FILE}",
    f"hosts/{GROK_BOT_HOST}/{BRIDGE_MANIFEST}",
    f"hosts/{GROK_BOT_HOST}/{INSTALL_GUIDE}",
})


def pin_delta_findings(commit: str, revision: dict[str, str | None]) -> list[str]:
    """P differs from R only by the accepted revision and the three generated host products.

    The delta under test is the tracked working tree compared directly with R (``git diff
    <R>``), so the gate holds both before P is committed (HEAD = R with the four files
    modified) and after (a clean HEAD = P), and a change made and reverted in between does
    not count. A rebased or squashed pair, or a pair merged with an advanced ``main``,
    carries other paths and fails. The bridge must differ from R's bridge by exactly one
    line: the content-stage placeholder replaced by the accepted-revision line.
    """
    short = commit[:12]
    changed = git_out("diff", "--name-only", commit)
    if changed is None:
        return [f"pin: cannot compute the delta between {short} and this tree"]
    findings: list[str] = []
    delta = set(changed.splitlines())
    for path in sorted(delta - PIN_DELTA_PATHS):
        findings.append(
            f"pin: P may differ from {short} only by templates/{GROK_BOT_HOST}/{ACCEPTED_REVISION_FILE} "
            f"and the three generated hosts/{GROK_BOT_HOST}/ products; found {path}"
        )
    pinned_bridge = git_out("show", f"{commit}:hosts/{GROK_BOT_HOST}/{BRIDGE_FILE}")
    if pinned_bridge is None:
        return findings + [f"pin: accepted commit {short} lacks hosts/{GROK_BOT_HOST}/{BRIDGE_FILE}"]
    before = pinned_bridge.splitlines()
    after = bridge_document(bridge_values()).decode("utf-8").strip().splitlines()
    changed = [(a, b) for a, b in zip(before, after) if a != b]
    if len(before) != len(after) or len(changed) != 1 or changed[0] != (CONTENT_STAGE_LINE, accepted_line(revision)):
        findings.append(
            f"pin: the bridge must differ from {short} by exactly one line (the content-stage placeholder "
            f"replaced by the accepted-revision line); found {len(changed) if len(before) == len(after) else 'a different line count'}"
        )
    return findings


def bridge_values() -> dict[str, str]:
    revision = accepted_revision()
    return {
        "SKILL_NAME": ORCHESTRATOR_NAME,
        "DISPLAY_NAME": ORCHESTRATOR_DISPLAY,
        "DESCRIPTION": json.dumps(BRIDGE_DESCRIPTION),
        "REPO_SLUG": REPO_SLUG,
        "EXPECTED_ORIGIN": EXPECTED_ORIGIN,
        "LOCATOR": LOCATOR_COMMAND,
        "ACCEPTED_LINE": accepted_line(revision),
        "ACCEPTED_COMMIT": revision["commit"] or "<accepted commit>",
        "STAGE": str(revision["stage"]),
        "BRIDGE_FILE": BRIDGE_FILE,
        "MANIFEST": BRIDGE_MANIFEST,
    }


def bridge_document(values: dict[str, str]) -> bytes:
    template = GROK_BOT_TEMPLATES / "bridge.md.tmpl"
    if not template.is_file():
        raise ValueError(f"missing bridge template: {template}")
    return render_text(template.read_text(encoding="utf-8"), values, template).encode()


def bridge_manifest(bridge: bytes, revision: dict[str, str | None]) -> bytes:
    meta, body = split_frontmatter(bridge.decode("utf-8"))
    if meta.get("name") != ORCHESTRATOR_NAME:
        raise ValueError(f"{BRIDGE_FILE}: frontmatter name must be {ORCHESTRATOR_NAME!r}")
    payload = {
        "host": GROK_BOT_HOST,
        "adapter": "grok-bot-bridge",
        "repository": EXPECTED_ORIGIN,
        "stage": revision["stage"],
        "saveable": revision["stage"] == "pinned",
        "accepted_commit": revision["commit"],
        "release": revision["release"],
        "label": revision["label"],
        "locator": LOCATOR_COMMAND,
        "install_guide": INSTALL_GUIDE,
        "skill_count": 1,
        "skill": {
            "name": ORCHESTRATOR_NAME,
            "description": meta["description"],
            "source": BRIDGE_FILE,
            "bytes": len(bridge),
            "file_sha256": hash_bytes(bridge),
            "body_sha256": hash_bytes(body.encode("utf-8")),
        },
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def install_guide(values: dict[str, str]) -> bytes:
    template = GROK_BOT_TEMPLATES / (INSTALL_GUIDE + ".tmpl")
    if not template.is_file():
        raise ValueError(f"missing install guide template: {template}")
    return render_text(template.read_text(encoding="utf-8"), values, template).encode()


def expected_grok_bot_host_files() -> dict[str, bytes]:
    values = bridge_values()
    bridge = bridge_document(values)
    guide_values = dict(values, BRIDGE_BYTES=str(len(bridge)))
    return {
        MARKER: (GROK_BOT_HOST + "\n").encode(),
        BRIDGE_FILE: bridge,
        BRIDGE_MANIFEST: bridge_manifest(bridge, accepted_revision()),
        INSTALL_GUIDE: install_guide(guide_values),
    }


# ---------------------------------------------------------------------------
# Progressive-disclosure budgets (templates/budgets.json): every product is
# measured against its budget before it is written, so an over-budget Skill,
# reference, description, bridge, or guide never reaches disk.
# ---------------------------------------------------------------------------
BUDGETS_FILE = TEMPLATES / "budgets.json"


def budgets() -> dict[str, int]:
    if not BUDGETS_FILE.is_file():
        raise ValueError(f"missing budgets file: {BUDGETS_FILE}")
    data = json.loads(BUDGETS_FILE.read_text(encoding="utf-8"))
    result = {key: value for key, value in data.items() if not key.startswith("_")}
    for key, value in result.items():
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{BUDGETS_FILE}: {key} must be a positive integer")
    return result


def budget_findings(
    label: str, files: dict[str, bytes], skill_key: str, limits: dict[str, int]
) -> list[str]:
    findings: list[str] = []

    def over(surface: str, size: int, key: str) -> None:
        if size > limits[key]:
            findings.append(f"budget: {label}/{surface} is {size} B > {limits[key]} B ({key})")

    for name, data in files.items():
        if name == "SKILL.md":
            over(name, len(data), skill_key)
            meta, _ = split_frontmatter(data.decode("utf-8"))
            description = meta.get("description", "")
            if len(description) > limits["description_chars"]:
                findings.append(
                    f"budget: {label}/SKILL.md description is {len(description)} chars > "
                    f"{limits['description_chars']} chars (description_chars)"
                )
        elif name.startswith("references/") and name.endswith(".md"):
            over(name, len(data), "reference_bytes")
    return findings


def host_budget_findings(files: dict[str, bytes], limits: dict[str, int]) -> list[str]:
    findings: list[str] = []
    bridge = files[BRIDGE_FILE]
    if len(bridge) > limits["bridge_bytes"]:
        findings.append(
            f"budget: {GROK_BOT_HOST}/{BRIDGE_FILE} is {len(bridge)} B > {limits['bridge_bytes']} B (bridge_bytes)"
        )
    meta, _ = split_frontmatter(bridge.decode("utf-8"))
    if len(meta.get("description", "")) > limits["description_chars"]:
        findings.append(
            f"budget: {GROK_BOT_HOST}/{BRIDGE_FILE} description is {len(meta['description'])} chars > "
            f"{limits['description_chars']} chars (description_chars)"
        )
    guide = files[INSTALL_GUIDE]
    if len(guide) > limits["bridge_guide_bytes"]:
        findings.append(
            f"budget: {GROK_BOT_HOST}/{INSTALL_GUIDE} is {len(guide)} B > {limits['bridge_guide_bytes']} B (bridge_guide_bytes)"
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument(
        "--require-pinned", action="store_true",
        help="fail unless templates/grok-bot/accepted-revision.json is at the pinned stage "
             "and the pin is verified (the gate for the pin commit)",
    )
    args = parser.parse_args()

    manifests = [parse_manifest(path) for path in sorted(PLATFORMS.glob("*.yaml"))]
    expected_ids = [
        "claude-code", "codex", "cursor-cli", "devin", "grok", "kimi-cli", "opencode", "zcode",
    ]
    if [m["id"] for m in manifests] != expected_ids:
        raise ValueError(
            "platform inventory must be exactly claude-code,codex,cursor-cli,devin,grok,kimi-cli,opencode,zcode"
        )

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

    limits = budgets()
    revision = accepted_revision()
    worker_expected = {m["skill_name"]: expected_files(m) for m in manifests}
    orch_expected = expected_orchestrator_files(manifests)
    host_expected = expected_grok_bot_host_files()
    for name, expected in worker_expected.items():
        findings.extend(budget_findings(name, expected, "worker_skill_bytes", limits))
    findings.extend(budget_findings(ORCHESTRATOR_NAME, orch_expected, "main_skill_bytes", limits))
    findings.extend(host_budget_findings(host_expected, limits))
    findings.extend(pin_findings(revision, manifests))
    if args.require_pinned and revision["stage"] != "pinned":
        findings.append("pin: stage is content; --require-pinned demands a pinned, verified bridge")
    if findings:
        # An over-budget, unverifiable-pin, or unmanaged inventory is never written.
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1

    for manifest in manifests:
        target = SKILLS / manifest["skill_name"]
        expected = worker_expected[manifest["skill_name"]]
        if args.write:
            write_one(target, expected)
        else:
            findings.extend(check_one(target, expected))

    orch_target = SKILLS / ORCHESTRATOR_NAME
    if args.write:
        write_one(orch_target, orch_expected)
    else:
        findings.extend(check_one(orch_target, orch_expected))

    host_target = HOSTS / GROK_BOT_HOST
    if args.write:
        write_bundle(HOSTS, host_target, host_expected, "host")
    else:
        findings.extend(check_one(host_target, host_expected))

    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1
    stage = (
        f"pinned at {str(revision['commit'])[:12]}, pin verified" if revision["stage"] == "pinned"
        else "content stage, unpinned (not saveable)"
    )
    print(
        f"render-skills: {'WROTE' if args.write else 'PASS'} "
        f"({len(manifests)} workers + {ORCHESTRATOR_NAME} + {GROK_BOT_HOST} host: "
        f"1 bridge skill, {len(host_expected[BRIDGE_FILE])} B, {stage}; budgets OK)"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"render-skills: {exc}", file=sys.stderr)
        raise SystemExit(2)
