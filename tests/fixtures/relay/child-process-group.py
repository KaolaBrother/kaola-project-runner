#!/usr/bin/env python3
"""Claude-shaped runtime with an inherited process-group descendant.

The relay PTY tests use this instead of a line-buffered fake so that child
input, grid-neutral output, resize, and group ownership are observable facts.
"""

from __future__ import annotations

import argparse
import os
import select
import signal
import subprocess
import sys
import termios
import tty
from pathlib import Path


def append(path: Path | None, line: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")
        stream.flush()


def frame(mode: str) -> str:
    if mode == "unknown":
        return "Claude Code\nKaola Workflow\nThinking...\n⠋\n"
    if mode == "populated":
        return (
            "Claude Code\nKaola Workflow\n"
            "HUMAN_DECISION_REQUIRED\n"
            "Decision: choose fixture answer\n"
            "Evidence: sanitized fixture evidence\n"
            "Recommendation: choose chosen-answer\n"
            "Safe options: chosen-answer or decline\n"
            "Paused state: waiting for explicit answer\n"
            "shells: 0\nagents: 0\n❯ draft-prefix\n"
        )
    if mode == "decision":
        return (
            "Claude Code\nKaola Workflow\n"
            "HUMAN_DECISION_REQUIRED\n"
            "Decision: choose fixture answer\n"
            "Evidence: sanitized fixture evidence\n"
            "Recommendation: choose chosen-answer\n"
            "Safe options: chosen-answer or decline\n"
            "Paused state: waiting for explicit answer\n"
            "shells: 0\nagents: 0\n❯\n"
        )
    return "Claude Code\nCompleted work is ready to continue.\nshells: 0\nagents: 0\n❯\n"


def process_state(pid: int) -> str:
    result = subprocess.run(
        ["ps", "-o", "state=", "-p", str(pid)],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "absent"


def main() -> int:
    if "--version" in sys.argv:
        print("Claude Code relay fixture 1.0.0")
        return 0
    if "--help" in sys.argv:
        print("--model <model> --effort <level> --permission-mode <mode>")
        return 0
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--state", required=False)
    parser.add_argument("--mode", default=os.environ.get("FAKE_CLAUDE_MODE", "empty"))
    parser.add_argument("--descendant-state")
    args, _unknown = parser.parse_known_args()
    state = Path(args.state or os.environ.get("FAKE_RELAY_FIXTURE_STATE", "")) if (args.state or os.environ.get("FAKE_RELAY_FIXTURE_STATE")) else None
    descendant_state = Path(args.descendant_state) if args.descendant_state else state
    grid_neutral = Path(os.environ["FAKE_GRID_NEUTRAL"]) if os.environ.get("FAKE_GRID_NEUTRAL") else None
    silent_input = Path(os.environ["FAKE_SILENT_INPUT"]) if os.environ.get("FAKE_SILENT_INPUT") else None
    escape_descendant = os.environ.get("FAKE_RELAY_ESCAPE_DESCENDANT") == "1"
    render_editor = os.environ.get("FAKE_RELAY_RENDER_EDITOR") == "1"

    descendant = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(3600)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=escape_descendant,
    )
    append(state, f"pid={os.getpid()}")
    append(state, f"pgid={os.getpgrp()}")
    append(state, f"descendant_pid={descendant.pid}")
    append(state, f"descendant_pgid={os.getpgid(descendant.pid)}")
    append(state, f"descendant_start_new_session={str(escape_descendant).lower()}")
    append(state, "ready")

    def stop(_signum: int, _frame: object) -> None:
        if not escape_descendant:
            try:
                descendant.terminate()
                descendant.wait(timeout=0.5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    descendant.kill()
                except OSError:
                    pass
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    signal.signal(signal.SIGINT, stop)
    sys.stdout.write(frame(args.mode))
    sys.stdout.flush()
    if grid_neutral is not None and grid_neutral.exists():
        os.write(sys.stdout.fileno(), b"\x1b[?25l")
        sys.stdout.flush()
        grid_neutral.unlink(missing_ok=True)

    input_fd = sys.stdin.fileno()
    old = termios.tcgetattr(input_fd)
    tty.setraw(input_fd)
    try:
        while True:
            if grid_neutral is not None and grid_neutral.exists():
                os.write(sys.stdout.fileno(), b"\x1b[?25l")
                sys.stdout.flush()
                grid_neutral.unlink(missing_ok=True)
            ready, _, _ = select.select([input_fd], [], [], 0.05)
            if not ready:
                continue
            data = os.read(input_fd, 4096)
            if not data:
                return 0
            append(descendant_state, f"input={data.hex()}")
            append(
                descendant_state,
                f"input_descendant_state={process_state(descendant.pid)};input={data.hex()}",
            )
            if render_editor and data not in (b"\r", b"\n"):
                editor = data.decode("utf-8", errors="replace")
                sys.stdout.write("\x1b[2J\x1b[H" + frame("empty").replace("❯\n", f"❯ {editor}\n"))
                sys.stdout.flush()
            if silent_input is not None and silent_input.exists():
                silent_input.unlink(missing_ok=True)
            if b"/exit" in data or b"/quit" in data:
                return 0
    finally:
        termios.tcsetattr(input_fd, termios.TCSADRAIN, old)
        if not escape_descendant:
            try:
                descendant.terminate()
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
