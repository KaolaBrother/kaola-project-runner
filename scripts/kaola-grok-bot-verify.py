#!/usr/bin/env python3
"""Offline verifier for the generated Grok Bot host bundle ``hosts/grok-bot``.

Proves the delivery shape for an individual Grok Bot plan. On the account a
private skill is one single Markdown (name, description, body), so the bundle
carries exactly **eight** standalone account-private Skill documents under
``private-skills/`` -- ``kaola-project-runner`` (Project Runner: authorization,
heartbeat, dispatch, acceptance, close-out; routes to workers by stable Skill
name, absorbs no transport, inlines no worker text) plus one
``<id>-kaola-project-runner`` per platform worker (begins with its canonical
contract, bundles its references verbatim, states its Local Computer script
location, absorbs no orchestrator policy) -- each with a unique frontmatter
name equal to its file stem, no ``../`` and no sibling-tree dependency; the
install guide ``INSTALL.md`` for Grok Bot itself (not a ninth Skill) that lists
exactly those eight sources; and the Local Computer runtime copy
``kaola-project-runner/``: exactly one discoverable root ``SKILL.md``, the seven
workers embedded under ``workers/<platform id>/`` as supporting resources
(contract file ``WORKER.md``), no sibling-Skill dependency, no plugin manifest,
no symlinks, executable bits only on ``.sh`` scripts, and no unofficial Sand API
identifiers in any text file.

With ``--repo`` it also proves **generated state**: the payload is re-rendered
from that checkout's shared templates (``scripts/render-skills.py``) and every
file in the payload -- the root ``SKILL.md``, ``agents/openai.yaml``,
``references/``, and every embedded worker resource -- must be byte-identical
to the fresh render, with no missing and no extra files. The shared generation
source is the truth; bytes on disk are never trusted on their own. Without
``--repo`` only the shape is proven.

It does not contact Grok Bot and does not claim live UI adoption.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import stat
import sys
from pathlib import Path

ROOT_SKILL = "kaola-project-runner"
WORKER_IDS = (
    "claude-code",
    "codex",
    "cursor-cli",
    "devin",
    "grok",
    "kimi-cli",
    "opencode",
)
WORKER_SKILL_NAMES = {wid: f"{wid}-kaola-project-runner" for wid in WORKER_IDS}
MARKER = ".generated-by-kaola-project-runner"
HOST_MARKER = "grok-bot\n"
WORKER_CONTRACT = "WORKER.md"
EMBEDDED_WORKER_DROP = frozenset({MARKER, "agents/openai.yaml"})
WORKER_REQUIRED = (
    WORKER_CONTRACT,
    "references/platform.md",
    "references/transport.md",
    "references/acp.md",
    "scripts/runtime-tmux.sh",
    "scripts/kaola-tmux.sh",
    "scripts/kaola-acp.py",
    "scripts/kaola-acp-holder.py",
    "scripts/platform.yaml",
)
PRIVATE_SKILLS_DIR = "private-skills"
PRIVATE_SKILLS_MANIFEST = "private-skills.json"
INSTALL_GUIDE = "INSTALL.md"
ACCOUNT_SKILL_NAMES = (ROOT_SKILL,) + tuple(WORKER_SKILL_NAMES[wid] for wid in WORKER_IDS)
LOCAL_RUNTIME_COPY = "${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}/skills/" + ROOT_SKILL
WORKER_OPERATIONS = ("preflight", "start", "observe", "send", "capture", "key", "stop")
# The main account Skill must not carry the workers' transport contract.
TRANSPORT_MARKERS = (
    "## Transport facts",
    "## Communication loop",
    'runtime-tmux.sh" send',
    'runtime-tmux.sh" observe',
    'runtime-tmux.sh" capture',
    'runtime-tmux.sh" key',
    "mutation_status",
    "raw_current_frame",
    "--transport acp|pty",
)
# A worker account Skill must not carry the orchestrator's policy.
ORCHESTRATOR_MARKERS = (
    "PROJECT_RUNNER_HEARTBEAT",
    "## Heartbeat",
    "## Main execution loop",
    "Allowed CLIs",
    "Needs attention",
    "Routine",
    "Mission-frontier",
    "Accept the delivery",
)
PLUGIN_MANIFESTS = (".cursor-plugin", ".grok-plugin", ".claude-plugin", "plugin.json")
UNOFFICIAL = (
    "GrokBotService",
    "EnsureSandBox",
    "SAND_GATEWAY",
    "sand-host",
    "grokbot-sdk",
    "aiserver.v1",
    "/local-exec/",
)
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".sh", ".py", ".txt"}
RENDERER = Path("scripts") / "render-skills.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_generated_map(repo: Path) -> dict[str, str]:
    """Re-render the payload from the checkout's shared templates (the truth)."""
    renderer_path = repo / RENDERER
    if not renderer_path.is_file():
        raise ValueError(f"{repo}: missing {RENDERER}; cannot prove generated state")
    spec = importlib.util.spec_from_file_location("kaola_render_skills", renderer_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    manifests = [module.parse_manifest(path) for path in sorted(module.PLATFORMS.glob("*.yaml"))]
    return {
        name: hashlib.sha256(data).hexdigest()
        for name, data in module.expected_grok_bot_host_files(manifests).items()
    }


def generated_state_findings(bundle: Path, repo: Path) -> list[str]:
    try:
        expected = expected_generated_map(repo)
    except (OSError, ValueError) as exc:
        return [f"{bundle}: cannot re-render from {repo}: {exc}"]
    actual = file_map(bundle)
    findings: list[str] = []
    for name in sorted(expected.keys() | actual.keys()):
        if name not in actual:
            findings.append(f"{bundle}: missing generated file {name}")
        elif name not in expected:
            findings.append(f"{bundle}: unexpected file {name} (not produced by render-skills.py)")
        elif actual[name] != expected[name]:
            findings.append(
                f"{bundle}/{name}: differs from the shared generation source "
                f"(expected={expected[name][:12]} actual={actual[name][:12]}; hand-edited?)"
            )
    return findings


def tree_integrity_findings(bundle: Path) -> list[str]:
    """Shape facts that need no repo: no symlinks, exec bits only on shell scripts."""
    findings: list[str] = []
    for path in sorted(bundle.rglob("*")):
        relative = path.relative_to(bundle).as_posix()
        if path.is_symlink():
            findings.append(f"{bundle}: symlink {relative} is not part of a generated payload")
            continue
        if not path.is_file():
            continue
        executable = bool(path.stat().st_mode & stat.S_IXUSR)
        if path.suffix == ".sh" and not executable:
            findings.append(f"{bundle}: {relative} must be executable")
        elif path.suffix != ".sh" and executable:
            findings.append(f"{bundle}: {relative} must not be executable")
    return findings


def file_map(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def expected_embedded_map(canonical: Path) -> dict[str, str]:
    """Map a generated worker Skill onto its embedded supporting-resource form."""
    result: dict[str, str] = {}
    for relative, digest in file_map(canonical).items():
        if relative in EMBEDDED_WORKER_DROP:
            continue
        if relative == "SKILL.md":
            relative = WORKER_CONTRACT
        result[relative] = digest
    return result


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split one single-Markdown Skill into its frontmatter map and body."""
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        raise ValueError("must start with a `---` frontmatter block")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("unterminated frontmatter") from exc
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator or not re.fullmatch(r"[a-z][a-z0-9_-]*", key.strip()):
            raise ValueError(f"invalid frontmatter line {line!r}")
        meta[key.strip()] = value.strip()
    return meta, "\n".join(lines[end + 1:])


def private_skill_findings(bundle: Path, repo: Path | None) -> list[str]:
    """Exactly eight standalone single-Markdown account Skills: 1 main + 7 workers."""
    findings: list[str] = []
    docs_dir = bundle / PRIVATE_SKILLS_DIR
    if not docs_dir.is_dir():
        return [f"{bundle}: missing {PRIVATE_SKILLS_DIR}/"]
    entries = sorted(docs_dir.iterdir())
    for entry in entries:
        if not entry.is_file() or entry.suffix != ".md":
            findings.append(f"{entry}: only single-Markdown Skill documents belong in {PRIVATE_SKILLS_DIR}/")
    docs = [entry for entry in entries if entry.is_file() and entry.suffix == ".md"]
    stems = sorted(doc.stem for doc in docs)
    if stems != sorted(ACCOUNT_SKILL_NAMES):
        findings.append(
            f"{docs_dir}: expected exactly {len(ACCOUNT_SKILL_NAMES)} account-private Skill documents "
            f"{sorted(ACCOUNT_SKILL_NAMES)}, got {stems}"
        )
    seen: dict[str, Path] = {}
    worker_by_name = {name: wid for wid, name in WORKER_SKILL_NAMES.items()}
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        try:
            meta, body = parse_frontmatter(text)
        except ValueError as exc:
            findings.append(f"{doc}: {exc}")
            continue
        name = meta.get("name", "")
        if name != doc.stem:
            findings.append(f"{doc}: frontmatter name must equal the file stem {doc.stem!r}, got {name!r}")
        if not meta.get("description"):
            findings.append(f"{doc}: frontmatter description must not be empty")
        if not body.strip():
            findings.append(f"{doc}: body must not be empty")
        if name in seen:
            findings.append(f"{doc}: duplicate Skill name {name!r} (also {seen[name].name})")
        seen[name] = doc
        # Standalone: no sibling Skill directory, no file-tree link, every reference bundled.
        if "../" in text:
            findings.append(f"{doc}: must not reach outside the document")
        for other in ACCOUNT_SKILL_NAMES:
            if re.search(rf"(?<![\w/-])(?:\.\./|skills/){re.escape(other)}\b", text):
                findings.append(f"{doc}: references sibling Skill directory {other}")
        for link in sorted(set(re.findall(r"\]\((references/[^)#]+)\)", text))):
            if f"## Bundled reference: {link}" not in text:
                findings.append(f"{doc}: links {link} without bundling it")
        if re.search(r"\]\((?:\./)?(?:workers|scripts|agents)/[^)]*\)", text):
            findings.append(f"{doc}: links into a file tree the account does not hold")
        if name == ROOT_SKILL:
            for worker_name in WORKER_SKILL_NAMES.values():
                if f"`{worker_name}`" not in text:
                    findings.append(f"{doc}: does not route to worker Skill {worker_name}")
            for marker in TRANSPORT_MARKERS:
                if marker in text:
                    findings.append(f"{doc}: main Skill absorbs worker transport ({marker!r})")
            if WORKER_CONTRACT in text:
                findings.append(f"{doc}: main Skill routes through a file tree ({WORKER_CONTRACT})")
        elif name in worker_by_name:
            wid = worker_by_name[name]
            for marker in ORCHESTRATOR_MARKERS:
                if marker in text:
                    findings.append(f"{doc}: worker Skill absorbs orchestrator policy ({marker!r})")
            if f'SKILL_DIR="{LOCAL_RUNTIME_COPY}/workers/{wid}"' not in text:
                findings.append(f"{doc}: missing Local Computer script location for {wid}")
            for operation in WORKER_OPERATIONS:
                if f'"$SKILL_DIR/scripts/runtime-tmux.sh" {operation} ' not in text:
                    findings.append(f"{doc}: worker Skill does not carry the {operation} operation")
            if repo is not None:
                canonical = repo / "skills" / name / "SKILL.md"
                if canonical.is_file() and not doc.read_bytes().startswith(canonical.read_bytes()):
                    findings.append(f"{doc}: does not begin with the canonical contract skills/{name}/SKILL.md")
    return findings


def manifest_findings(bundle: Path) -> list[str]:
    """The fingerprint manifest must describe exactly the eight documents on disk."""
    manifest = bundle / PRIVATE_SKILLS_MANIFEST
    if not manifest.is_file():
        return [f"{bundle}: missing {PRIVATE_SKILLS_MANIFEST}"]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{manifest}: invalid JSON: {exc}"]
    findings: list[str] = []
    if data.get("host") != "grok-bot" or data.get("install_guide") != INSTALL_GUIDE:
        findings.append(f"{manifest}: host/install_guide fields must name grok-bot and {INSTALL_GUIDE}")
    skills = data.get("skills")
    if not isinstance(skills, list) or data.get("skill_count") != len(skills):
        return findings + [f"{manifest}: skills list and skill_count disagree"]
    names = [entry.get("name") for entry in skills]
    if sorted(names) != sorted(ACCOUNT_SKILL_NAMES) or len(set(names)) != len(names):
        findings.append(f"{manifest}: must fingerprint exactly {sorted(ACCOUNT_SKILL_NAMES)}, got {sorted(names)}")
    for entry in skills:
        name = entry.get("name")
        source = bundle / str(entry.get("source", ""))
        if entry.get("source") != f"{PRIVATE_SKILLS_DIR}/{name}.md" or not source.is_file():
            findings.append(f"{manifest}: {name}: source must be {PRIVATE_SKILLS_DIR}/{name}.md and exist")
            continue
        raw = source.read_bytes()
        if entry.get("file_sha256") != hashlib.sha256(raw).hexdigest():
            findings.append(f"{manifest}: {name}: file_sha256 does not match {source.name}")
        try:
            meta, body = parse_frontmatter(raw.decode("utf-8"))
        except ValueError:
            continue
        if entry.get("body_sha256") != hashlib.sha256(body.encode("utf-8")).hexdigest():
            findings.append(f"{manifest}: {name}: body_sha256 does not match the document body")
        description = meta.get("description", "")
        if description.startswith('"') and description.endswith('"'):
            description = json.loads(description)
        if entry.get("description") != description:
            findings.append(f"{manifest}: {name}: description does not match the document frontmatter")
        expected_role = "orchestrator" if name == ROOT_SKILL else "worker"
        if entry.get("role") != expected_role:
            findings.append(f"{manifest}: {name}: role must be {expected_role}")
    return findings


def install_guide_findings(bundle: Path) -> list[str]:
    """The guide is for Grok Bot itself: repo-based, lists exactly the eight sources, not a Skill."""
    guide = bundle / INSTALL_GUIDE
    if not guide.is_file():
        return [f"{bundle}: missing {INSTALL_GUIDE}"]
    text = guide.read_text(encoding="utf-8")
    findings: list[str] = []
    if text.startswith("---"):
        findings.append(f"{guide}: must not carry Skill frontmatter (it is not a ninth Skill)")
    sources = set(re.findall(rf"hosts/grok-bot/{PRIVATE_SKILLS_DIR}/([a-z0-9-]+)\.md", text))
    if sources != set(ACCOUNT_SKILL_NAMES):
        findings.append(f"{guide}: must list exactly the {len(ACCOUNT_SKILL_NAMES)} source documents, got {sorted(sources)}")
    for name in ACCOUNT_SKILL_NAMES:
        if f"`{name}`" not in text:
            findings.append(f"{guide}: does not name Skill {name}")
    lowered = re.sub(r"\s+", " ", text).lower()
    for clause in ("idempotent", "same name", "public marketplace", "local computer", "failed rows only", PRIVATE_SKILLS_MANIFEST):
        if clause not in lowered:
            findings.append(f"{guide}: missing clause {clause!r}")
    return findings


def validate(bundle: Path, repo: Path | None) -> list[str]:
    findings: list[str] = []
    if not bundle.is_dir():
        return [f"{bundle}: missing payload directory"]

    marker = bundle / MARKER
    if not marker.is_file():
        findings.append(f"{bundle}: missing {MARKER}")
    elif marker.read_text(encoding="utf-8") != HOST_MARKER:
        findings.append(f"{bundle}: {MARKER} must contain grok-bot")

    entries = sorted(path.name for path in bundle.iterdir() if path.name != MARKER)
    if entries != sorted([INSTALL_GUIDE, ROOT_SKILL, PRIVATE_SKILLS_DIR, PRIVATE_SKILLS_MANIFEST]):
        findings.append(
            f"{bundle}: bundle must contain exactly {INSTALL_GUIDE!r}, {PRIVATE_SKILLS_MANIFEST!r}, "
            f"the runtime copy {ROOT_SKILL!r}, and {PRIVATE_SKILLS_DIR}/, got {entries}"
        )
        return findings
    skill = bundle / ROOT_SKILL
    findings.extend(tree_integrity_findings(bundle))
    findings.extend(private_skill_findings(bundle, repo))
    findings.extend(manifest_findings(bundle))
    findings.extend(install_guide_findings(bundle))

    # Exactly one discoverable Skill in the whole payload.
    discoverable = sorted(path.relative_to(bundle).as_posix() for path in bundle.rglob("SKILL.md"))
    if discoverable != [f"{ROOT_SKILL}/SKILL.md"]:
        findings.append(f"{bundle}: expected exactly one discoverable SKILL.md, got {discoverable}")
    for path in bundle.rglob("*"):
        if path.name in PLUGIN_MANIFESTS:
            findings.append(f"{path}: plugin manifest is not part of a Private Skill payload")

    skill_marker = skill / MARKER
    if not skill_marker.is_file():
        findings.append(f"{skill}: missing {MARKER}")
    elif skill_marker.read_text(encoding="utf-8") != ROOT_SKILL + "\n":
        findings.append(f"{skill}: {MARKER} must contain {ROOT_SKILL}")
    root_skill_md = skill / "SKILL.md"
    if not root_skill_md.is_file():
        findings.append(f"{skill}: missing SKILL.md")
        return findings
    root_text = root_skill_md.read_text(encoding="utf-8")
    if not re.search(rf"(?m)^name:\s*{re.escape(ROOT_SKILL)}\s*$", root_text):
        findings.append(f"{root_skill_md}: frontmatter name must be {ROOT_SKILL}")

    workers_root = skill / "workers"
    if not workers_root.is_dir():
        findings.append(f"{skill}: missing workers/")
        return findings
    present = sorted(path.name for path in workers_root.iterdir())
    if present != sorted(WORKER_IDS):
        findings.append(f"{workers_root}: expected exactly {sorted(WORKER_IDS)}, got {present}")

    for wid in WORKER_IDS:
        worker = workers_root / wid
        if not worker.is_dir():
            continue
        for relative in WORKER_REQUIRED:
            if not (worker / relative).is_file():
                findings.append(f"{worker}: missing {relative}")
        adapter = worker / "scripts" / "adapters" / f"{wid}.sh"
        if not adapter.is_file():
            findings.append(f"{worker}: missing scripts/adapters/{wid}.sh")
        for dropped in EMBEDDED_WORKER_DROP:
            if (worker / dropped).exists():
                findings.append(f"{worker}: embedded worker must not carry {dropped}")
        platform_yaml = worker / "scripts" / "platform.yaml"
        if platform_yaml.is_file():
            if f'id: "{wid}"' not in platform_yaml.read_text(encoding="utf-8"):
                findings.append(f"{platform_yaml}: platform id must be {wid}")
        contract = worker / WORKER_CONTRACT
        if contract.is_file():
            text = contract.read_text(encoding="utf-8")
            if "../" in text:
                findings.append(f"{contract}: must not reach outside its worker directory")
            if not re.search(rf"(?m)^name:\s*{re.escape(WORKER_SKILL_NAMES[wid])}\s*$", text):
                findings.append(f"{contract}: frontmatter name must be {WORKER_SKILL_NAMES[wid]}")
        if repo is not None:
            canonical = repo / "skills" / WORKER_SKILL_NAMES[wid]
            if not canonical.is_dir():
                findings.append(f"{worker}: no matching skills/{WORKER_SKILL_NAMES[wid]} in repo")
            elif expected_embedded_map(canonical) != file_map(worker):
                findings.append(f"{worker}: bytes differ from skills/{WORKER_SKILL_NAMES[wid]}")
        # Root routing must point at this embedded worker, not at a sibling Skill.
        if f"workers/{wid}/{WORKER_CONTRACT}" not in root_text:
            findings.append(f"{root_skill_md}: does not route to workers/{wid}/{WORKER_CONTRACT}")

    # No dependency on sibling Skill directories.
    for name in WORKER_SKILL_NAMES.values():
        if re.search(rf"(?<![\w/-])(?:\.\./|skills/){re.escape(name)}\b", root_text):
            findings.append(f"{root_skill_md}: references sibling Skill directory {name}")
    if "../" in root_text:
        findings.append(f"{root_skill_md}: must not reach outside the Skill directory")

    if repo is not None:
        canonical_refs = repo / "skills" / ROOT_SKILL / "references"
        if canonical_refs.is_dir() and file_map(canonical_refs) != file_map(skill / "references"):
            findings.append(f"{skill}/references: bytes differ from skills/{ROOT_SKILL}/references")
        # Whole-payload generated state: root SKILL.md, agents/, references/,
        # every embedded resource, no extras. The templates are the truth.
        findings.extend(generated_state_findings(bundle, repo))

    for path in sorted(bundle.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            for token in UNOFFICIAL:
                if token in text:
                    findings.append(f"{path}: unofficial API token {token!r}")
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
    proof = "generated state" if args.repo else "shape only; pass --repo to prove generated state"
    print(
        f"kaola-grok-bot-verify: PASS {args.bundle} "
        f"({len(ACCOUNT_SKILL_NAMES)} private skill docs + manifest + install guide; runtime copy: "
        f"1 root skill, {len(WORKER_IDS)} embedded workers; {proof})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
