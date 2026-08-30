#!/usr/bin/env python3
"""Drive a pane-native DECRQM query and record the exact PTY reply."""

from __future__ import annotations

import argparse
import os
import select
import sys
import termios
import tty
from pathlib import Path


def append(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(value + "\n")
        stream.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--go", required=True)
    parser.add_argument("--reply-log", required=True)
    parser.add_argument("--child-query", action="store_true")
    args = parser.parse_args()
    state = Path(args.state)
    go = Path(args.go)
    reply_log = Path(args.reply_log)

    sys.stdout.write("Fence fixture\nStable grid\n❯\n")
    sys.stdout.flush()
    append(state, "ready")
    while not go.exists():
        select.select([], [], [], 0.01)

    nonce = 424242 if args.child_query else 4242
    query = f"\x1b[{nonce}$p".encode("ascii")

    input_fd = sys.stdin.fileno()
    old = termios.tcgetattr(input_fd)
    tty.setraw(input_fd)
    received = bytearray()
    try:
        deadline = 5.0
        while len(received) < 64 and deadline > 0:
            # The first query can race tmux pane startup on a busy host. A
            # repeated identical query keeps this native probe deterministic;
            # it still accepts only the exact nonce response below.
            os.write(sys.stdout.fileno(), query)
            sys.stdout.flush()
            ready, _, _ = select.select([input_fd], [], [], 0.05)
            deadline -= 0.05
            if not ready:
                continue
            block = os.read(input_fd, 64)
            if not block:
                break
            received.extend(block)
            if b"$ y" in received or received.endswith(b"$y"):
                break
    finally:
        termios.tcsetattr(input_fd, termios.TCSADRAIN, old)
    append(reply_log, received.hex())
    append(state, "reply-received")
    while True:
        select.select([], [], [], 0.1)


if __name__ == "__main__":
    raise SystemExit(main())
