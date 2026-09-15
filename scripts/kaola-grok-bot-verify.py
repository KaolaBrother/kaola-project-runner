#!/usr/bin/env python3
"""Offline verifier for the generated Grok Bot Private Skill payload.

Proves the delivery shape for an individual Grok Bot plan: exactly one
discoverable root ``SKILL.md`` (Project Runner), the seven platform workers
embedded under ``workers/<platform id>/`` as supporting resources (contract
file ``WORKER.md``), no sibling-Skill dependency, no plugin manifest, no
unofficial Sand API identifiers anywhere in the payload, and (with ``--repo``)
byte identity with the generated ``skills/`` trees. It does not contact Grok
Bot and does not claim live UI adoption.
"""

from __future__ import annotations

import argparse
import hashlib
import re
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    if entries != [ROOT_SKILL]:
        findings.append(
            f"{bundle}: payload must contain exactly one Skill directory {ROOT_SKILL!r}, got {entries}"
        )
        return findings
    skill = bundle / ROOT_SKILL

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
    print(f"kaola-grok-bot-verify: PASS {args.bundle} (1 root skill, {len(WORKER_IDS)} embedded workers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
