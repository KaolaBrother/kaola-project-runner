#!/usr/bin/env python3
"""Package the Grok Bot Private Skill payload as a deterministic zip archive.

Input is the generated ``hosts/grok-bot/kaola-project-runner`` tree. Before
anything is zipped, ``kaola-grok-bot-verify.py`` runs in its ``--repo`` form:
the payload is re-rendered from the shared templates and every file (root
``SKILL.md``, ``agents/openai.yaml``, ``references/``, every embedded worker
resource) must be byte-identical, with no extra files, no symlinks, and
executable bits only on ``.sh`` scripts. Any drift refuses the package, so a
hand-edited payload is never signed. Output is
``<output>/kaola-project-runner-grok-bot-skill.zip`` plus a ``.sha256`` sidecar.
Entries are sorted, timestamps fixed, and executable bits preserved, so the
same payload bytes always produce the same archive digest. The archive is a
private-skill hand-off for manual Grok Bot UAT; no official upload entry point
is claimed. Nothing outside ``<output>`` is written; no installed Skill
directory is touched.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import stat
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PAYLOAD = REPO / "hosts" / "grok-bot"
ROOT_SKILL = "kaola-project-runner"
ARCHIVE_NAME = f"{ROOT_SKILL}-grok-bot-skill.zip"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify", HERE / "kaola-grok-bot-verify.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def build(payload: Path, output_dir: Path) -> tuple[Path, str]:
    skill = payload / ROOT_SKILL
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / ARCHIVE_NAME
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill.rglob("*")):
            if not path.is_file():
                continue
            relative = f"{ROOT_SKILL}/{path.relative_to(skill).as_posix()}"
            info = zipfile.ZipInfo(relative, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            zf.writestr(info, path.read_bytes())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output_dir / (ARCHIVE_NAME + ".sha256")).write_text(f"{digest}  {ARCHIVE_NAME}\n", encoding="utf-8")
    return archive, digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, default=PAYLOAD)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--output", type=Path, default=REPO / "build" / "grok-bot")
    args = parser.parse_args()
    verifier = load_verifier()
    payload = args.payload.resolve()
    repo = args.repo.resolve()
    # Generated-state proof is mandatory here: the archive is signed, so it
    # must be exactly what the shared templates render, never hand-edited bytes.
    findings = verifier.validate(payload, repo)
    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        print(
            "kaola-grok-bot-package: refusing to package a payload that is invalid or "
            f"drifts from the generated state of {repo}",
            file=sys.stderr,
        )
        return 1
    archive, digest = build(payload, args.output.resolve())
    print(
        f"kaola-grok-bot-package: {archive}\nsha256: {digest}\n"
        f"verified: generated state of {repo} (render-skills.py templates)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
