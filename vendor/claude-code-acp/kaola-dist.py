#!/usr/bin/env python3
"""Committed-dist derivation for the vendored Claude Code ACP bridge.

``--write`` rebuilds ``dist/index.js`` from the vendored sources with the
locally installed dev toolchain (``npm ci`` must have run here) and records
``dist/DERIVATION.json``: sha256 of every build input, the toolchain versions,
and the sha256 of the output.

``--check`` needs no network and no ``node_modules``: it re-hashes every
recorded input and the committed output and fails when anything drifted, so a
source edit without a rebuild, or a hand-edited dist, cannot pass. When the
dev toolchain is present (or ``--rebuild`` is given) it also rebuilds into a
scratch directory and requires a byte-identical result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VENDOR = Path(__file__).resolve().parent
DERIVATION = VENDOR / "dist" / "DERIVATION.json"
OUTPUT = "dist/index.js"
INPUT_FILES = ("package.json", "package-lock.json", "tsconfig.json", "tsup.config.ts")
INPUT_DIRS = ("src", "bin")
TOOLCHAIN = ("tsup", "esbuild", "typescript", "@agentclientprotocol/sdk", "zod")
UPSTREAM_URL = "https://github.com/harukitosa/claude-code-acp"
UPSTREAM_COMMIT = "6c20f2802e390c80b0542247c6b9738e11efdc11"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_paths() -> list[str]:
    paths = [name for name in INPUT_FILES if (VENDOR / name).is_file()]
    for directory in INPUT_DIRS:
        root = VENDOR / directory
        paths.extend(
            str(path.relative_to(VENDOR))
            for path in sorted(root.rglob("*"))
            if path.is_file()
        )
    return paths


def hash_inputs() -> dict[str, str]:
    return {path: sha256(VENDOR / path) for path in input_paths()}


def package_version(name: str) -> str | None:
    manifest = VENDOR / "node_modules" / name / "package.json"
    if not manifest.is_file():
        return None
    return json.loads(manifest.read_text()).get("version")


def tsup_cli() -> Path | None:
    candidate = VENDOR / "node_modules" / "tsup" / "dist" / "cli-default.js"
    return candidate if candidate.is_file() else None


def node_binary() -> str:
    node = shutil.which("node")
    if not node:
        raise SystemExit("kaola-dist: node is required")
    return node


def build(out_dir: Path) -> None:
    cli = tsup_cli()
    if cli is None:
        raise SystemExit("kaola-dist: node_modules/tsup missing; run `npm ci` in the vendor dir first")
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    subprocess.run(
        [node_binary(), str(cli), "--out-dir", str(out_dir)],
        cwd=VENDOR, env=env, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    if not (out_dir / "index.js").is_file():
        raise SystemExit("kaola-dist: build produced no index.js")


def write() -> int:
    dist = VENDOR / "dist"
    dist.mkdir(exist_ok=True)
    build(dist)
    for stray in dist.iterdir():
        if stray.name not in ("index.js", "DERIVATION.json"):
            stray.unlink()
    node_version = subprocess.run(
        [node_binary(), "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    record = {
        "upstream": {"url": UPSTREAM_URL, "commit": UPSTREAM_COMMIT},
        "command": "node node_modules/tsup/dist/cli-default.js --out-dir dist",
        "toolchain": {"node": node_version, **{name: package_version(name) for name in TOOLCHAIN}},
        "inputs": hash_inputs(),
        "output": {OUTPUT: {"sha256": sha256(dist / "index.js"), "bytes": (dist / "index.js").stat().st_size}},
    }
    DERIVATION.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"kaola-dist: wrote {OUTPUT} ({record['output'][OUTPUT]['bytes']} bytes) and DERIVATION.json")
    return 0


def check(rebuild: bool) -> int:
    if not DERIVATION.is_file():
        print("kaola-dist: dist/DERIVATION.json missing", file=sys.stderr)
        return 1
    record = json.loads(DERIVATION.read_text())
    failures: list[str] = []
    current = hash_inputs()
    recorded = record.get("inputs", {})
    for path in sorted(set(current) | set(recorded)):
        if path not in recorded:
            failures.append(f"input not recorded: {path}")
        elif path not in current:
            failures.append(f"recorded input missing: {path}")
        elif current[path] != recorded[path]:
            failures.append(f"input drifted since the recorded build: {path}")
    output = VENDOR / OUTPUT
    expected = record.get("output", {}).get(OUTPUT, {}).get("sha256")
    if not output.is_file():
        failures.append(f"{OUTPUT} missing")
    elif sha256(output) != expected:
        failures.append(f"{OUTPUT} does not match the recorded sha256")
    for stray in sorted((VENDOR / "dist").iterdir()):
        if stray.name not in ("index.js", "DERIVATION.json"):
            failures.append(f"unexpected file in dist: {stray.name}")
    upstream = record.get("upstream", {})
    if upstream.get("commit") != UPSTREAM_COMMIT or upstream.get("url") != UPSTREAM_URL:
        failures.append("recorded upstream pin differs from kaola-dist.py")
    rebuilt = "skipped (no node_modules toolchain; hashes verified)"
    if rebuild or tsup_cli() is not None:
        with tempfile.TemporaryDirectory(prefix="kaola-dist-") as scratch:
            build(Path(scratch))
            if (Path(scratch) / "index.js").read_bytes() != output.read_bytes():
                failures.append("rebuild from source is not byte-identical to the committed dist")
                rebuilt = "differs"
            else:
                rebuilt = "byte-identical"
    for failure in failures:
        print(f"kaola-dist: FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print(f"kaola-dist: OK inputs={len(current)} output={expected[:12]} rebuild={rebuilt}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="rebuild dist and record the derivation")
    group.add_argument("--check", action="store_true", help="verify the committed dist against its derivation")
    parser.add_argument("--rebuild", action="store_true", help="with --check: require a rebuild comparison")
    args = parser.parse_args()
    return write() if args.write else check(args.rebuild)


if __name__ == "__main__":
    raise SystemExit(main())
