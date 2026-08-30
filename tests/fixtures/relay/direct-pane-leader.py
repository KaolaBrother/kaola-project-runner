#!/usr/bin/env python3
"""Small direct pane leader used only for the Issue #6 legacy/STOP oracle."""

from __future__ import annotations

import argparse
import os
import select
import signal
import sys
from pathlib import Path


def append(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")
        stream.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--input-log")
    parser.add_argument("--claude", action="store_true")
    args = parser.parse_args()
    state = Path(args.state)
    input_log = Path(args.input_log) if args.input_log else None

    append(state, f"pid={os.getpid()}")
    append(state, f"pgid={os.getpgrp()}")
    append(state, "ready")

    def resumed(_signum: int, _frame: object) -> None:
        append(state, "SIGCONT")

    def stopped(_signum: int, _frame: object) -> None:
        append(state, "TERM")
        raise SystemExit(0)

    signal.signal(signal.SIGCONT, resumed)
    signal.signal(signal.SIGTERM, stopped)
    signal.signal(signal.SIGHUP, stopped)
    if args.claude:
        sys.stdout.write(
            "Claude Code\n"
            "Kaola Workflow\n"
            "Completed work is ready to continue.\n"
            "shells: 0\n"
            "agents: 0\n"
            "❯\n"
        )
        sys.stdout.flush()

    input_fd = sys.stdin.fileno()
    while True:
        ready, _, _ = select.select([input_fd], [], [], 0.1)
        if not ready:
            continue
        data = os.read(input_fd, 4096)
        if not data:
            return 0
        if input_log is not None:
            append(input_log, data.hex())


if __name__ == "__main__":
    raise SystemExit(main())
