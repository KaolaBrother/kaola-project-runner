#!/usr/bin/env python3
"""Raw PTY child for Issue #9 communication-only acceptance.

The fixture deliberately changes only the visible semantic surface after a
payload has been prepared. Its editor buffer remains the exact bytes that the
relay received, so a Runner that treats the UI/editor parser as authority will
refuse a valid byte-attested submit while a communication-only Runner will
transfer the payload and let the controller read the resulting frame.
"""

from __future__ import annotations

import json
import os
import select
import sys
import termios
import tty
from pathlib import Path


PASTE_BEGIN = b"\x1b[200~"
PASTE_END = b"\x1b[201~"


def write_bytes(value: bytes) -> None:
    view = memoryview(value)
    while view:
        written = os.write(sys.stdout.fileno(), view)
        view = view[written:]


def write_frame(lines: list[str]) -> None:
    write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))


def write_title() -> None:
    write_bytes(b"\x1b]0;Claude Code\x07")


def normal_frame() -> list[str]:
    return [
        "Claude Code",
        "Issue #9 communication fixture",
        "No command is running",
        "shells: 0",
        "agents: 0",
        "❯",
    ]


def semantic_mismatch_frame(reason: str) -> list[str]:
    # This is intentionally a fully classified waiting/decision surface. The
    # visible prompt says "status-only-view", but the actual editor buffer is
    # never changed from the relay-prepared payload.
    return [
        "Claude Code",
        f"Issue #9 semantic advisory: {reason}",
        "Waiting for response",
        "HUMAN_DECISION_REQUIRED",
        "Decision: fixture surface changed",
        "Evidence: visible classification is advisory",
        "Recommendation: leave transport to the controller",
        "Safe options: continue or stop",
        "Paused state: waiting for explicit answer",
        "shells: 0",
        "agents: 0",
        "❯ status-only-view",
    ]


def append_submission(value: str) -> None:
    path = os.environ.get("FAKE_ISSUE9_SUBMIT_LOG")
    if path:
        with Path(path).open("a", encoding="utf-8") as stream:
            stream.write(f"submitted={value}\n")


def emit_cli_response(value: str) -> None:
    write_frame(
        [
            "Claude Code",
            "Issue #9 CLI response",
            json.dumps({"accepted": value}, ensure_ascii=False),
            "shells: 0",
            "agents: 0",
            "❯",
        ]
    )


def main() -> int:
    input_fd = sys.stdin.fileno()
    original = termios.tcgetattr(input_fd)
    tty.setraw(input_fd)
    write_title()
    # The relay must attest bracketed paste before accepting LF/TAB or a
    # multiline prompt. This fixture uses it for every ordinary payload.
    write_bytes(b"\x1b[?2004h")
    write_frame(normal_frame())

    editor = bytearray()
    pending = bytearray()
    in_paste = False
    change_path = os.environ.get("FAKE_ISSUE9_CHANGE_FILE")
    change_emitted = False

    try:
        while True:
            if not change_emitted and change_path and Path(change_path).exists():
                # Advance the visible frame and activity/decision classifiers
                # without changing the actual editor bytes.
                write_frame(semantic_mismatch_frame("external snapshot change"))
                change_emitted = True

            ready, _, _ = select.select([input_fd], [], [], 0.05)
            if not ready:
                continue
            data = os.read(input_fd, 4096)
            if not data:
                return 0
            pending.extend(data)

            while pending:
                if in_paste:
                    end = pending.find(PASTE_END)
                    if end < 0:
                        keep = min(len(pending), len(PASTE_END) - 1)
                        content_end = len(pending) - keep
                        if content_end:
                            editor.extend(pending[:content_end])
                            del pending[:content_end]
                        break
                    editor.extend(pending[:end])
                    del pending[: end + len(PASTE_END)]
                    in_paste = False
                    # Deliberately mismatch the visible editor fingerprint;
                    # the underlying editor byte buffer stays untouched.
                    write_frame(semantic_mismatch_frame("prepared bytes"))
                    continue

                if pending.startswith(PASTE_BEGIN):
                    del pending[: len(PASTE_BEGIN)]
                    in_paste = True
                    continue

                if PASTE_BEGIN.startswith(bytes(pending)):
                    break

                byte = pending.pop(0)
                if byte in (0x0A, 0x0D):
                    submitted = editor.decode("utf-8", errors="replace")
                    append_submission(submitted)
                    if submitted in {"/exit", "/quit"}:
                        return 0
                    editor.clear()
                    emit_cli_response(submitted)
                else:
                    editor.append(byte)
    finally:
        write_bytes(b"\x1b[?2004l")
        termios.tcsetattr(input_fd, termios.TCSADRAIN, original)


if __name__ == "__main__":
    raise SystemExit(main())
