#!/usr/bin/env python3
"""A tiny raw-mode Claude-shaped TUI used by the Issue #6 public API test.

It deliberately implements the reviewed whole-editor Ctrl-U binding and
bracketed-paste event sequence.  A line-oriented stdin fixture would not
prove that answer replaces an existing editor draft.
"""

from __future__ import annotations

import os
import select
import signal
import sys
import termios
import tty
from pathlib import Path


PASTE_BEGIN = b"\x1b[200~"
PASTE_END = b"\x1b[201~"


def write_frame(lines: list[str]) -> None:
    sys.stdout.write("\r\n".join(lines))
    sys.stdout.flush()


def replace_frame(lines: list[str]) -> None:
    sys.stdout.write("\x1b[2J\x1b[H" + "\r\n".join(lines))
    sys.stdout.flush()


def editor_rows(editor: str) -> list[str]:
    lines = editor.split("\n")
    first = f"❯ {lines[0]}" if lines[0] else "❯"
    return [first, *(f"  {line}" for line in lines[1:])]


def decision_frame(editor: str = "draft-prefix") -> list[str]:
    return [
        "Claude Code",
        "Kaola Workflow",
        "HUMAN_DECISION_REQUIRED",
        "Decision: choose fixture answer",
        "Evidence: sanitized fixture evidence",
        "Recommendation: choose chosen-answer",
        "Safe options: chosen-answer or decline",
        "Paused state: waiting for explicit answer",
        "shells: 0",
        "agents: 0",
        *editor_rows(editor),
    ]


def completed_frame(editor: str = "") -> list[str]:
    return [
        "Completed work is ready to continue.",
        "shells: 0",
        "agents: 0",
        *editor_rows(editor),
    ]


def native_approval_frame() -> list[str]:
    return [
        "Claude Code",
        "Kaola Workflow",
        "This command requires approval",
        "Tool approval",
        "Do you want to proceed?",
        "❯ 1. Allow",
        "  2. Deny",
    ]


def changed_editor_frame(editor: bytearray) -> list[str]:
    return [
        "Claude Code",
        "Kaola Workflow",
        "Surface changed while input was being prepared.",
        "shells: 0",
        "agents: 0",
        *editor_rows(editor.decode("utf-8", errors="replace")),
    ]


def write_log(line: str) -> None:
    target = os.environ.get("FAKE_CLAUDE_SUBMIT_LOG")
    if target:
        with Path(target).open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


def emit_later_output() -> None:
    replace_frame([f"Later output line {index:02d}" for index in range(1, 30)] + completed_frame())


def emit_editor_change() -> None:
    replace_frame([f"Editor change line {index:02d}" for index in range(1, 30)] + decision_frame("changed-draft"))


def redraw_decision_editor(editor: bytearray) -> None:
    write_frame(decision_frame(editor.decode("utf-8", errors="replace")))


def main() -> int:
    if sys.argv[1:] == ["inspect", "--json"]:
        print(
            '{"grokVersion":"fixture","projectRoot":"fixture",'
            '"skills":[{"name":"workflow-next"},'
            '{"name":"kaola-workflow-finalize"}]}'
        )
        return 0
    if "--version" in sys.argv:
        print("Claude Code fixture 1.0.0")
        return 0
    if "--help" in sys.argv:
        print("--model <model>\n--effort <level>\n--permission-mode <mode>")
        return 0

    initial_mode = os.environ.get("FAKE_CLAUDE_MODE", "decision")
    input_fd = sys.stdin.fileno()
    original = termios.tcgetattr(input_fd)
    tty.setraw(input_fd)
    terminal_title = os.environ.get("FAKE_CLAUDE_TITLE", "")
    if terminal_title:
        os.write(sys.stdout.fileno(), f"\x1b]0;{terminal_title}\x07".encode("utf-8"))
    # Claude enables bracketed paste on its raw terminal before accepting
    # editor input. The relay uses this exact terminal-mode evidence to
    # decide whether to add paste delimiters around a literal payload. The
    # negative acceptance fixture can explicitly omit this negotiation.
    bracketed_paste_enabled = os.environ.get("FAKE_CLAUDE_BRACKETED_PASTE", "1") != "0"
    if bracketed_paste_enabled:
        os.write(sys.stdout.fileno(), b"\x1b[?2004h")
    if initial_mode == "unknown":
        write_frame(["Claude Code", "Kaola Workflow", "Thinking...", "⠋"])
    elif initial_mode == "empty":
        write_frame(completed_frame())
    else:
        write_frame(decision_frame())
    pending = bytearray()
    editor = bytearray(b"draft-prefix") if initial_mode == "decision" else bytearray()
    in_paste = False
    answered = False
    released = False
    changed = False
    release_path = os.environ.get("FAKE_CLAUDE_RELEASE")
    change_path = os.environ.get("FAKE_CLAUDE_EDITOR_CHANGE")
    grid_neutral_path = os.environ.get("FAKE_CLAUDE_GRID_NEUTRAL")
    grid_neutral_emitted = False
    redraw_on_continue = os.environ.get("FAKE_CLAUDE_REDRAW_ON_CONT") == "1"
    prepare_drift = os.environ.get("FAKE_CLAUDE_PREPARE_DRIFT", "")
    exit_on_submit = os.environ.get("FAKE_CLAUDE_EXIT_ON_SUBMIT") == "1"
    prepare_drift_emitted = False
    continue_redraw_requested = False

    def request_continue_redraw(_signum: int, _frame: object) -> None:
        nonlocal continue_redraw_requested
        continue_redraw_requested = True

    if redraw_on_continue:
        signal.signal(signal.SIGCONT, request_continue_redraw)

    try:
        while True:
            if continue_redraw_requested:
                if released:
                    replace_frame(completed_frame())
                elif initial_mode == "decision":
                    replace_frame(decision_frame(editor.decode("utf-8", errors="replace")))
                else:
                    replace_frame(completed_frame())
                continue_redraw_requested = False
            if answered and not released and release_path and Path(release_path).exists():
                emit_later_output()
                released = True
            if answered and not grid_neutral_emitted and grid_neutral_path and Path(grid_neutral_path).exists():
                # Resetting an already-default rendition changes child output
                # bytes without changing the grid, cursor, or editor facts.
                os.write(sys.stdout.fileno(), b"\x1b[0m")
                sys.stdout.flush()
                grid_neutral_emitted = True
            if not changed and change_path and Path(change_path).exists():
                emit_editor_change()
                changed = True

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
                        # Keep a possible split suffix of the closing marker
                        # out of the editor while waiting for the next PTY
                        # read. All preceding bytes are paste content.
                        keep = min(len(pending), len(PASTE_END) - 1)
                        content_end = len(pending) - keep
                        if content_end:
                            editor.extend(pending[:content_end])
                            del pending[:content_end]
                        break
                    editor.extend(pending[:end])
                    del pending[: end + len(PASTE_END)]
                    in_paste = False
                    if prepare_drift and not prepare_drift_emitted:
                        if prepare_drift == "native-approval":
                            replace_frame(native_approval_frame())
                        elif prepare_drift == "editor-change":
                            editor.extend(b"-foreign-draft")
                            replace_frame(changed_editor_frame(editor))
                        elif prepare_drift == "editor-hard-line":
                            editor.extend(b"\nforeign-hard-line")
                            replace_frame(changed_editor_frame(editor))
                        else:
                            raise RuntimeError(f"unknown FAKE_CLAUDE_PREPARE_DRIFT: {prepare_drift}")
                        prepare_drift_emitted = True
                    elif initial_mode == "decision" and not answered:
                        redraw_decision_editor(editor)
                    elif not answered:
                        replace_frame(completed_frame(editor.decode("utf-8", errors="replace")))
                    elif released:
                        replace_frame(completed_frame(editor.decode("utf-8", errors="replace")))
                    continue

                if pending.startswith(PASTE_BEGIN):
                    del pending[: len(PASTE_BEGIN)]
                    in_paste = True
                    continue

                # A PTY read may end in the prefix of a paste opener. Wait for
                # the remaining bytes instead of turning a partial CSI into
                # lost editor input.
                if PASTE_BEGIN.startswith(bytes(pending)):
                    break

                byte = pending.pop(0)
                if byte == 0x15:  # Ctrl-U: the reviewed whole-editor clear key.
                    editor.clear()
                elif byte in (0x0A, 0x0D):
                    submitted = editor.decode("utf-8", errors="replace")
                    write_log(f"submitted={submitted}")
                    if exit_on_submit:
                        return 0
                    if submitted == "chosen-answer" and not answered:
                        answered = True
                        editor.clear()
                    elif submitted == "follow-up" and released:
                        editor.clear()
                        replace_frame([f"Follow-up output line {index:02d}" for index in range(1, 30)] + completed_frame())
                    else:
                        editor.clear()
                else:
                    # When bracketed paste is not negotiated, the relay sends
                    # the payload as ordinary literal bytes. They still form
                    # the editor buffer and must not be silently discarded.
                    editor.append(byte)
    finally:
        if bracketed_paste_enabled:
            os.write(sys.stdout.fileno(), b"\x1b[?2004l")
        termios.tcsetattr(input_fd, termios.TCSADRAIN, original)


if __name__ == "__main__":
    raise SystemExit(main())
