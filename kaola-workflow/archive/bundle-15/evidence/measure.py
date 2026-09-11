#!/usr/bin/env python3
"""Part C measurement harness — same task over acp vs pty, N runs each.

Task: "Reply with exactly the string PONG and nothing else." (deterministic,
minimal agent work — isolates transport cost handed to the orchestrator).

Per run we record: UTF-8 bytes of every receipt/frame handed to the caller,
cl100k token count, Runner command invocations, observation reads
(orchestrator-look proxy), end-to-end wall time, recovery attempts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/tmp/kpr-tiktoken")
import tiktoken  # noqa: E402

ENC = tiktoken.get_encoding("cl100k_base")
WORKTREE = Path("/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-15")
ACP = WORKTREE / "scripts" / "kaola-acp.py"
PTY = WORKTREE / "scripts" / "kaola-tmux.sh"
TASK = "Reply with exactly the string PONG and nothing else."
RUNS = 5


def tok(text: str) -> int:
    return len(ENC.encode(text))


def run_cmd(argv: list[str], timeout: float = 180) -> tuple[str, float]:
    start = time.monotonic()
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return result.stdout, time.monotonic() - start


def acp_run(index: int) -> dict:
    session = f"kpr-meas-acp-{index}"
    repo = str(WORKTREE)
    out_bytes = 0
    tokens = 0
    invocations = 0
    observations = 0
    t0 = time.monotonic()

    out, _ = run_cmd([sys.executable, str(ACP), "grok", "start",
                      "--repo", repo, "--session", session])
    out_bytes += len(out.encode()); tokens += tok(out); invocations += 1

    out, _ = run_cmd([sys.executable, str(ACP), "grok", "send",
                      "--repo", repo, "--session", session,
                      "--text", TASK, "--timeout", "120"], timeout=150)
    out_bytes += len(out.encode()); tokens += tok(out); invocations += 1
    receipt = json.loads(out)
    ok = receipt.get("stop_reason") == "end_turn" and "PONG" in (receipt.get("final_text") or "")

    out, _ = run_cmd([sys.executable, str(ACP), "grok", "stop",
                      "--repo", repo, "--session", session], timeout=60)
    out_bytes += len(out.encode()); tokens += tok(out); invocations += 1

    return {"transport": "acp", "run": index, "bytes": out_bytes, "tokens": tokens,
            "invocations": invocations, "observations": observations,
            "wall_s": round(time.monotonic() - t0, 1), "task_ok": ok, "retries": 0}


def pty_run(index: int) -> dict:
    session = f"kpr-meas-pty-{index}"
    repo = str(WORKTREE)
    out_bytes = 0
    tokens = 0
    invocations = 0
    observations = 0
    retries = 0
    t0 = time.monotonic()

    def observe() -> tuple[str, dict]:
        nonlocal out_bytes, tokens, invocations, observations
        out, _ = run_cmd(["bash", str(PTY), "grok", "observe",
                          "--repo", repo, "--session", session], timeout=60)
        out_bytes += len(out.encode()); tokens += tok(out)
        invocations += 1; observations += 1
        try:
            return out, json.loads(out)
        except ValueError:
            return out, {}

    out, _ = run_cmd(["bash", str(PTY), "grok", "start",
                      "--repo", repo, "--session", session], timeout=120)
    out_bytes += len(out.encode()); tokens += tok(out); invocations += 1

    # orchestrator must observe to learn the TUI is ready before sending
    ready_deadline = time.monotonic() + 60
    while time.monotonic() < ready_deadline:
        _, obs = observe()
        frame = obs.get("raw_current_frame") or ""
        if "❯" in frame:
            break
        time.sleep(1.5)

    out, _ = run_cmd(["bash", str(PTY), "grok", "send",
                      "--repo", repo, "--session", session, "--text", TASK], timeout=60)
    out_bytes += len(out.encode()); tokens += tok(out); invocations += 1

    # orchestrator polls observe until the reply is on screen and agent idle
    done = False
    reply_deadline = time.monotonic() + 120
    while time.monotonic() < reply_deadline:
        _, obs = observe()
        frame = obs.get("raw_current_frame") or ""
        if "PONG" in frame and obs.get("activity_hint") == "idle":
            done = True
            break
        time.sleep(1.5)
    if not done:
        retries += 1

    out, _ = run_cmd(["bash", str(PTY), "grok", "stop",
                      "--repo", repo, "--session", session], timeout=60)
    out_bytes += len(out.encode()); tokens += tok(out); invocations += 1

    return {"transport": "pty", "run": index, "bytes": out_bytes, "tokens": tokens,
            "invocations": invocations, "observations": observations,
            "wall_s": round(time.monotonic() - t0, 1), "task_ok": done, "retries": retries}


def median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def main() -> int:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else RUNS
    results: list[dict] = []
    for i in range(runs):
        r = acp_run(i)
        results.append(r)
        print("acp", i, json.dumps(r), flush=True)
    for i in range(runs):
        r = pty_run(i)
        results.append(r)
        print("pty", i, json.dumps(r), flush=True)
    for transport in ("acp", "pty"):
        subset = [r for r in results if r["transport"] == transport]
        print(f"== {transport} medians over {len(subset)} runs ==")
        for key in ("bytes", "tokens", "invocations", "observations", "wall_s", "retries"):
            print(f"  {key}: {median([r[key] for r in subset])}")
        print(f"  task_ok: {sum(1 for r in subset if r['task_ok'])}/{len(subset)}")
    out_path = Path(__file__).with_name("part-c-raw.json")
    out_path.write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
