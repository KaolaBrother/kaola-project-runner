#!/usr/bin/env python3
"""Offline verifier for the generated Grok Bot host bundle ``hosts/grok-bot``.

Grok Bot is a bridge host: the account holds exactly **one** thin private Skill,
``kaola-project-runner`` (the bridge), and everything else -- the main Skill, the
seven platform workers, their references and scripts -- stays in the repository and
is loaded on demand from a verified checkout on the bound execution target. This
verifier proves that shape structurally:

* the bundle is exactly the marker, the bridge, ``bridge.json``, and ``INSTALL.md``;
* the bridge stays inside its byte budget (``templates/budgets.json``), names the
  repository, the expected origin, exactly one 40-hex accepted revision, the
  device-local locator command, and the two canonical entry paths
  (``ROOT/skills/kaola-project-runner`` and ``ROOT/skills/<platform>-kaola-project-runner``),
  binds the execution target before anything else, and names no individual worker;
* the bridge carries **no** canonical body, reference, transport, or orchestrator
  content, no fixed or default path, HOME convention, username, environment
  variable, symlink convention, runtime copy, and no credential handling pattern;
* the fingerprint manifest matches the bridge byte for byte;
* the guide is not a Skill, names the single source, and describes the one-write
  install plus the read-only Local Computer UAT (no cloud-to-Mac install).

With ``--repo`` it additionally proves **generated state** (every file byte-identical
to a fresh render from that checkout's ``scripts/render-skills.py``) and that no
sentence of any canonical ``skills/**/SKILL.md`` or reference appears in the bridge.
It does not contact Grok Bot and does not claim live adoption.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT_SKILL = "kaola-project-runner"
WORKER_IDS = ("claude-code", "codex", "cursor-cli", "devin", "grok", "kimi-cli", "opencode")
WORKER_SKILL_NAMES = tuple(f"{wid}-{ROOT_SKILL}" for wid in WORKER_IDS)
MARKER = ".generated-by-kaola-project-runner"
HOST_MARKER = "grok-bot\n"
BRIDGE_FILE = f"{ROOT_SKILL}.md"
BRIDGE_MANIFEST = "bridge.json"
INSTALL_GUIDE = "INSTALL.md"
LOCATOR_COMMAND = "kaola-project-runner-locate"
REPO_SLUG = "KaolaBrother/kaola-project-runner"
EXPECTED_ORIGIN = f"github.com/{REPO_SLUG}"
MAIN_ENTRY = f"ROOT/skills/{ROOT_SKILL}/SKILL.md"
WORKER_ENTRY = f"ROOT/skills/<platform>-{ROOT_SKILL}/SKILL.md"
REVISION = re.compile(r"\b[0-9a-f]{40}\b")
RENDERER = Path("scripts") / "render-skills.py"
BUDGETS = Path("templates") / "budgets.json"
DEFAULT_BUDGETS = {"bridge_bytes": 2560, "description_chars": 320, "bridge_guide_bytes": 8192}
# The bridge must not carry the workers' transport contract ...
TRANSPORT_MARKERS = (
    "## Transport facts", "## Communication loop", "mutation_status", "raw_current_frame",
    "--transport acp|pty", "SKILL_DIR=", "--tier default", "bracketed paste",
)
# ... nor the orchestrator's policy ...
ORCHESTRATOR_MARKERS = (
    "PROJECT_RUNNER_HEARTBEAT", "## Heartbeat", "## Main execution loop", "Allowed CLIs",
    "Needs attention", "Routine", "Mission-frontier", "Accept the delivery", "## Bundled reference",
)
# ... nor any fixed/default path, HOME convention, username, env var, symlink or runtime copy ...
PATH_PATTERNS = (
    r"\$HOME", r"~/", r"/Users/", r"/home/", r"/workspace", r"/Volumes/", r"/opt/", r"/tmp/",
    r"KAOLA_GROK_BOT_HOME", r"\bln -s\b", r"current ->", r"checkouts/", r"\.kaola/", r"\.local/bin",
    r"\bWORKER\.md\b", r"runtime copy", r"private-skills", r"\$\{?[A-Z_]{3,}\}?",
)
# ... nor any credential handling.
CREDENTIAL_PATTERNS = (
    r"GH_TOKEN", r"GITHUB_TOKEN", r"x-access-token", r"Authorization", r"--show-token",
    r"credential\.helper", r"GIT_ASKPASS", r"http\.extraheader", r"://[^/\s]+@", r"\btoken=",
)
UNOFFICIAL = ("GrokBotService", "EnsureSandBox", "SAND_GATEWAY", "sand-host", "grokbot-sdk", "aiserver.v1", "/local-exec/")
GUIDE_CLAUSES = (
    "exactly one", "same name", "local computer", "read-only", "never clones", "register",
    LOCATOR_COMMAND.lower(), "no_supported_path", "marketplace", "preflight", "--target local", "--target cloud",
)


def load_budgets(repo: Path | None) -> dict[str, int]:
    path = (repo or Path(__file__).resolve().parents[1]) / BUDGETS
    if not path.is_file():
        return dict(DEFAULT_BUDGETS)
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key: value for key, value in data.items() if not key.startswith("_")}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
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
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = json.loads(value)
        meta[key.strip()] = value
    return meta, "\n".join(lines[end + 1:])


def canonical_sentences(repo: Path) -> set[str]:
    """Every distinct line (>= 40 chars) of the canonical Skills and their references."""
    sentences: set[str] = set()
    for path in sorted((repo / "skills").rglob("*.md")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if len(line) >= 40 and not line.startswith(("|", "```", "#", "-", "name:", "description:")):
                sentences.add(line)
    return sentences


def bridge_findings(bundle: Path, repo: Path | None, budgets: dict[str, int]) -> list[str]:
    bridge = bundle / BRIDGE_FILE
    if not bridge.is_file():
        return [f"{bundle}: missing {BRIDGE_FILE}"]
    raw = bridge.read_bytes()
    text = raw.decode("utf-8")
    findings: list[str] = []
    if len(raw) > budgets["bridge_bytes"]:
        findings.append(f"{bridge}: {len(raw)} B exceeds bridge_bytes budget {budgets['bridge_bytes']} B")
    try:
        meta, body = parse_frontmatter(text)
    except ValueError as exc:
        return findings + [f"{bridge}: {exc}"]
    if meta.get("name") != ROOT_SKILL:
        findings.append(f"{bridge}: frontmatter name must be {ROOT_SKILL!r}, got {meta.get('name')!r}")
    description = meta.get("description", "")
    if not description:
        findings.append(f"{bridge}: frontmatter description must not be empty")
    elif len(description) > budgets["description_chars"]:
        findings.append(f"{bridge}: description is {len(description)} chars > {budgets['description_chars']}")
    if not body.strip():
        findings.append(f"{bridge}: body must not be empty")
    revisions = sorted(set(REVISION.findall(text)))
    if len(revisions) != 1:
        findings.append(f"{bridge}: must carry exactly one 40-hex accepted revision, found {revisions}")
    elif text.count(revisions[0]) != 1:
        findings.append(f"{bridge}: the accepted revision must appear on exactly one line")
    for needle in (REPO_SLUG, EXPECTED_ORIGIN, f"`{LOCATOR_COMMAND}`", f"`{MAIN_ENTRY}`", f"`{WORKER_ENTRY}`"):
        if needle not in text:
            findings.append(f"{bridge}: missing {needle!r}")
    lowered = re.sub(r"\s+", " ", body).lower()
    for clause in ("bind the execution target first", "local computer", "cloud", "never clone, install, update, or change anything on local computer",
                   "consumer project root", "same target", "never read script source", "never enter, print, or pass a token"):
        if clause not in lowered:
            findings.append(f"{bridge}: missing clause {clause!r}")
    if lowered.find("bind the execution target first") > lowered.find(f"`{LOCATOR_COMMAND}`".lower()):
        findings.append(f"{bridge}: the execution target must be bound before the locator is asked")
    if "only on the cloud target" not in lowered:
        findings.append(f"{bridge}: fetch/checkout must be limited to the cloud target")
    for name in WORKER_SKILL_NAMES:
        if name in text:
            findings.append(f"{bridge}: names worker {name}; only the selected `<platform>` placeholder belongs here")
    for marker in TRANSPORT_MARKERS:
        if marker in text:
            findings.append(f"{bridge}: carries worker transport content ({marker!r})")
    for marker in ORCHESTRATOR_MARKERS:
        if marker in text:
            findings.append(f"{bridge}: carries orchestrator/reference content ({marker!r})")
    for pattern in PATH_PATTERNS:
        if re.search(pattern, text):
            findings.append(f"{bridge}: prescribes a path/environment convention ({pattern!r})")
    for pattern in CREDENTIAL_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            findings.append(f"{bridge}: carries credential handling ({pattern!r})")
    if re.search(r"\]\((?:\./)?(?:references|workers|scripts|agents)/[^)]*\)", text):
        findings.append(f"{bridge}: links into a file tree the account does not hold")
    if repo is not None and (repo / "skills").is_dir():
        bridge_lines = {re.sub(r"\s+", " ", line).strip() for line in text.splitlines()}
        leaked = sorted(bridge_lines & canonical_sentences(repo))
        for line in leaked:
            findings.append(f"{bridge}: copies canonical Skill text: {line[:60]!r}")
    return findings


def manifest_findings(bundle: Path) -> list[str]:
    manifest = bundle / BRIDGE_MANIFEST
    if not manifest.is_file():
        return [f"{bundle}: missing {BRIDGE_MANIFEST}"]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{manifest}: invalid JSON: {exc}"]
    findings: list[str] = []
    if data.get("host") != "grok-bot" or data.get("install_guide") != INSTALL_GUIDE or data.get("skill_count") != 1:
        findings.append(f"{manifest}: host/install_guide/skill_count must be grok-bot/{INSTALL_GUIDE}/1")
    if data.get("locator") != LOCATOR_COMMAND or data.get("repository") != EXPECTED_ORIGIN:
        findings.append(f"{manifest}: locator/repository must be {LOCATOR_COMMAND}/{EXPECTED_ORIGIN}")
    commit = str(data.get("accepted_commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        findings.append(f"{manifest}: accepted_commit must be 40-hex")
    skill = data.get("skill") or {}
    bridge = bundle / BRIDGE_FILE
    if skill.get("name") != ROOT_SKILL or skill.get("source") != BRIDGE_FILE or not bridge.is_file():
        return findings + [f"{manifest}: skill.name/source must be {ROOT_SKILL}/{BRIDGE_FILE}"]
    raw = bridge.read_bytes()
    if skill.get("file_sha256") != hashlib.sha256(raw).hexdigest() or skill.get("bytes") != len(raw):
        findings.append(f"{manifest}: file_sha256/bytes do not match {BRIDGE_FILE}")
    try:
        meta, body = parse_frontmatter(raw.decode("utf-8"))
    except ValueError:
        return findings
    if skill.get("body_sha256") != hashlib.sha256(body.encode("utf-8")).hexdigest():
        findings.append(f"{manifest}: body_sha256 does not match the bridge body")
    if skill.get("description") != meta.get("description"):
        findings.append(f"{manifest}: description does not match the bridge frontmatter (resolved, without YAML quotes)")
    if commit and commit not in raw.decode("utf-8"):
        findings.append(f"{manifest}: accepted_commit is not the revision carried by the bridge")
    return findings


def guide_findings(bundle: Path, budgets: dict[str, int]) -> list[str]:
    guide = bundle / INSTALL_GUIDE
    if not guide.is_file():
        return [f"{bundle}: missing {INSTALL_GUIDE}"]
    raw = guide.read_bytes()
    text = raw.decode("utf-8")
    findings: list[str] = []
    if len(raw) > budgets["bridge_guide_bytes"]:
        findings.append(f"{guide}: {len(raw)} B exceeds bridge_guide_bytes budget {budgets['bridge_guide_bytes']} B")
    if text.startswith("---"):
        findings.append(f"{guide}: must not carry Skill frontmatter (it is not a second Skill)")
    sources = set(re.findall(r"hosts/grok-bot/([a-z0-9-]+)\.md", text))
    if sources != {ROOT_SKILL}:
        findings.append(f"{guide}: must name exactly the single source hosts/grok-bot/{BRIDGE_FILE}, got {sorted(sources)}")
    lowered = re.sub(r"\s+", " ", text).lower()
    for clause in GUIDE_CLAUSES:
        if clause not in lowered:
            findings.append(f"{guide}: missing clause {clause!r}")
    for pattern in CREDENTIAL_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            findings.append(f"{guide}: carries credential handling ({pattern!r})")
    for stale in ("KAOLA_GROK_BOT_HOME", "private-skills", "WORKER.md", "--runtime grok-bot", "kaola-grok-bot-package"):
        if stale in text:
            findings.append(f"{guide}: names a removed surface ({stale!r})")
    return findings


def generated_state_findings(bundle: Path, repo: Path) -> list[str]:
    renderer_path = repo / RENDERER
    if not renderer_path.is_file():
        return [f"{repo}: missing {RENDERER}; cannot prove generated state"]
    spec = importlib.util.spec_from_file_location("kaola_render_skills", renderer_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    try:
        spec.loader.exec_module(module)
        manifests = [module.parse_manifest(path) for path in sorted(module.PLATFORMS.glob("*.yaml"))]
        expected = {name: hashlib.sha256(data).hexdigest() for name, data in module.expected_grok_bot_host_files(manifests).items()}
    except (OSError, ValueError) as exc:
        return [f"{bundle}: cannot re-render from {repo}: {exc}"]
    actual = {p.relative_to(bundle).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(bundle.rglob("*")) if p.is_file()}
    findings: list[str] = []
    for name in sorted(expected.keys() | actual.keys()):
        if name not in actual:
            findings.append(f"{bundle}: missing generated file {name}")
        elif name not in expected:
            findings.append(f"{bundle}: unexpected file {name} (not produced by render-skills.py)")
        elif actual[name] != expected[name]:
            findings.append(f"{bundle}/{name}: differs from the shared generation source (hand-edited?)")
    return findings


def validate(bundle: Path, repo: Path | None) -> list[str]:
    if not bundle.is_dir():
        return [f"{bundle}: missing bundle directory"]
    budgets = load_budgets(repo)
    findings: list[str] = []
    marker = bundle / MARKER
    if not marker.is_file():
        findings.append(f"{bundle}: missing {MARKER}")
    elif marker.read_text(encoding="utf-8") != HOST_MARKER:
        findings.append(f"{bundle}: {MARKER} must contain grok-bot")
    entries = sorted(path.name for path in bundle.iterdir() if path.name != MARKER)
    expected_entries = sorted([BRIDGE_FILE, BRIDGE_MANIFEST, INSTALL_GUIDE])
    if entries != expected_entries:
        findings.append(f"{bundle}: bundle must contain exactly {expected_entries} (one bridge Skill, its manifest, the guide), got {entries}")
    for path in bundle.rglob("*"):
        if path.is_symlink():
            findings.append(f"{bundle}: symlink {path.name} is not part of a generated bundle")
        elif path.is_file() and path.stat().st_mode & 0o111:
            findings.append(f"{bundle}: {path.name} must not be executable")
    findings.extend(bridge_findings(bundle, repo, budgets))
    findings.extend(manifest_findings(bundle))
    findings.extend(guide_findings(bundle, budgets))
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            for token in UNOFFICIAL:
                if token in text:
                    findings.append(f"{path}: unofficial API token {token!r}")
    if repo is not None:
        findings.extend(generated_state_findings(bundle, repo))
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
    size = (args.bundle / BRIDGE_FILE).stat().st_size
    proof = "generated state" if args.repo else "shape only; pass --repo to prove generated state"
    print(f"kaola-grok-bot-verify: PASS {args.bundle} (1 bridge skill, {size} B, manifest, guide; no canonical content; {proof})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
