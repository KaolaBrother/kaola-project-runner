#!/usr/bin/env python3
"""Issue #65 round 2: look for native mid-turn steering entry points BEYOND the
four ACP method names, per platform, on the versions installed here.

For each CLI this extracts printable strings from every file that makes up the
installed runtime (compiled binaries embed their JS/Rust string tables) and
reports, separately:

  * steering vocabulary — steer / interject / inject / queue-while-running /
    follow-up-input style identifiers;
  * other protocol surfaces — an app-server, a local socket/HTTP/websocket
    control plane, an SDK/stream input mode, i.e. a channel other than ACP that
    could carry a mid-turn message;
  * the CLI's own advertised subcommands and flags.

It reads only installed program files. It starts no session, sends no prompt,
touches no configuration and reads no credential.
"""
import json, os, re, subprocess, sys
from pathlib import Path

STEER = re.compile(
    r"(?:steer\w*|interject\w*|midTurn|mid_turn|injectMessage|inject_message|"
    r"queueUserMessage|queuedMessage|pendingInput|followUpInput|followup_input|"
    r"interruptWith|appendMessage|pushUserMessage)", re.I)
SURFACE = re.compile(
    r"(?:app-server|appServer|--stdio|listen\(|websocket|ws://|/v1/sessions|"
    r"unix://|namedPipe|--input-format|stream-json|--sdk|jsonrpc|json-rpc|"
    r"session/(?:send|prompt|steer|steering|interrupt|input))", re.I)

TARGETS = {
    "claude-code": ["/opt/homebrew/lib/node_modules/@anthropic-ai/claude-code"],
    "codex": ["/opt/homebrew/lib/node_modules/@openai/codex"],
    "cursor-cli": ["/Users/ylminiserver/.local/share/cursor-agent/versions"],
    "devin": ["/Users/ylminiserver/.local/share/devin/cli/_versions"],
    "droid": ["/Users/ylminiserver/.local/bin/droid"],
    "grok": ["/opt/homebrew/lib/node_modules/@xai-official/grok"],
    "kimi-cli": ["/Users/ylminiserver/.kimi-code"],
    "opencode": ["/opt/homebrew/bin/opencode", "/opt/homebrew/lib/node_modules/opencode-ai"],
    "zcode": ["/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs"],
}
MAX_BYTES = 400 * 1024 * 1024


def files_for(roots):
    out = []
    for root in roots:
        path = Path(root)
        if path.is_file():
            out.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if not child.is_file() or child.is_symlink():
                    continue
                if any(part in ("node_modules", ".git") for part in child.parts[-4:]):
                    # keep a shallow node_modules sweep out of the scan
                    if "node_modules" in child.parts and child.suffix not in (".js", ".cjs", ".mjs"):
                        continue
                if child.suffix in (".map", ".md", ".png", ".jpg", ".wasm", ".node"):
                    continue
                out.append(child)
    return out


def strings_of(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_BYTES:
            return ""
    except OSError:
        return ""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    # printable runs of 4+ - the `strings(1)` behaviour, without the dependency
    return "\n".join(m.group().decode("latin-1")
                     for m in re.finditer(rb"[\x20-\x7e]{4,}", data))


def cli_help(binary: str) -> str:
    for args in (["--help"], ["help"]):
        try:
            proc = subprocess.run([binary, *args], capture_output=True, text=True, timeout=25)
            if proc.stdout.strip():
                return proc.stdout
        except Exception:                       # noqa: BLE001
            continue
    return ""


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    out_path = sys.argv[2] if len(sys.argv) > 2 else ""
    report = {}
    for platform, roots in TARGETS.items():
        if only and platform != only:
            continue
        hits_steer, hits_surface, scanned = {}, {}, []
        for path in files_for(roots):
            blob = strings_of(path)
            if not blob:
                continue
            scanned.append({"file": str(path), "bytes": path.stat().st_size})
            for m in STEER.finditer(blob):
                key = m.group()
                entry = hits_steer.setdefault(key, {"count": 0, "sample": ""})
                entry["count"] += 1
                if not entry["sample"]:
                    a = max(0, m.start() - 90)
                    entry["sample"] = blob[a:m.end() + 90].replace("\n", " ")
            for m in SURFACE.finditer(blob):
                key = m.group().lower()
                hits_surface[key] = hits_surface.get(key, 0) + 1
        report[platform] = {
            "roots": roots,
            "files_scanned": len(scanned),
            "bytes_scanned": sum(f["bytes"] for f in scanned),
            "steering_vocabulary": dict(sorted(hits_steer.items(),
                                               key=lambda kv: -kv[1]["count"])[:40]),
            "other_surfaces": dict(sorted(hits_surface.items(), key=lambda kv: -kv[1])),
        }
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text + "\n", encoding="utf-8")
    for platform, data in report.items():
        print(f"### {platform}: {data['files_scanned']} files, "
              f"{data['bytes_scanned'] // 1024} KiB")
        print("  steering vocab:", ", ".join(
            f"{k}({v['count']})" for k, v in list(data["steering_vocabulary"].items())[:12]) or "NONE")
        print("  surfaces:", ", ".join(f"{k}({v})" for k, v in
                                       list(data["other_surfaces"].items())[:14]) or "NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
