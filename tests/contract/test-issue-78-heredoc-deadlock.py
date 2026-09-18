#!/usr/bin/env python3
"""Issue #78: the shared entrypoint must never feed a command from a here-document.

Bash implements a here-document (and a here-string) whose body fits in its
compile-time ``HEREDOC_PIPESIZE`` - 4096 bytes - by creating a pipe and writing
the whole body into it from the forked child *before* ``exec``. That one process
holds both ends, so nothing is draining the pipe while it writes.

macOS does not guarantee the 65536-byte pipe the idle machine hands out. Once
system-wide pipe KVA is under pressure a fresh pipe carries only **512 bytes**;
measured on the development Mac by holding filled pipes open:

    held pipes    0 ->  65536      100 ->  65536
                 50 ->  65536      150 ->    512

Any here-document body above that floor therefore blocks in ``write()`` forever.
The stuck process has not ``exec``ed yet, so it wears this script's argv, owns no
children, and survives the SIGKILL a caller's timeout aims at its *parent* - which
is exactly the orphan shape Issue #78 reported: ``kaola-tmux.sh ... start``
processes alive for twenty minutes with an empty ``pgrep -P``, each ending on a
single SIGTERM.

Under load that deadlocked ``emit_json`` (an 883-byte body), which is the last
thing the canonical-root *refusal* path does. It is why two Issue #73 refusal
cases consumed the full 60 s ``run_cli`` budget while the accepting cases - which
run strictly more code but end at ``die``, a plain ``printf`` - passed in the same
run. Nothing about it was specific to the guard, to a transport, or to a target.

The repair is structural, so the guarantee is structural: this entrypoint carries
no here-document and no here-string at all. Python programs go in via ``-c`` and
``read`` is fed by a process substitution, whose writer is a separate process that
drains concurrently and so cannot deadlock against its own reader.

This rule covers the one shared entrypoint and its generated copies. Other shell
files in the repository still hold bodies in the dangerous range and are tracked
separately; they are deliberately out of this test's scope.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
ENTRYPOINT = PROJECT / "scripts" / "kaola-tmux.sh"

# Bash routes a body this size or smaller through a pipe instead of a temp file.
HEREDOC_PIPESIZE = 4096
# The smallest pipe macOS was measured handing out under pipe-KVA pressure.
DEGRADED_PIPE_CAPACITY = 512

# Every spelling bash accepts for a here-document tag: bare, single- or
# double-quoted (which may contain spaces), backslash-escaped, `<<-` dash form,
# and digit-leading tags. Plus the `cmd <<<word` here-string, which bash feeds
# through the same pipe and so deadlocks the same way.
HEREDOC_OPENER = re.compile(
    r"<<-?\s*(?:"
    r"'(?P<squote>[^']*)'"
    r'|"(?P<dquote>[^"]*)"'
    r"|\\(?P<escaped>\w+)"
    r"|(?P<bare>\w+)"
    r")"
)
HERESTRING = re.compile(r"<<<")
# `$((1 << n))` is an arithmetic left shift, not a redirection, and a `#` comment
# may quote a `<<` while describing this very rule.
NOT_A_REDIRECTION = ("$((", "#")


def shell_sources() -> list[Path]:
    """The entrypoint plus every generated per-platform copy of it."""
    found = [ENTRYPOINT]
    found.extend(sorted((PROJECT / "skills").glob("*/scripts/kaola-tmux.sh")))
    return found


def redirections(path: Path) -> list[tuple[int, str, int]]:
    """Every here-document/here-string in ``path`` as (line, tag, body bytes)."""
    lines = path.read_text(encoding="utf-8").split("\n")
    found: list[tuple[int, str, int]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if HERESTRING.search(line):
            found.append((index + 1, "<<<", 0))
        else:
            match = HEREDOC_OPENER.search(line)
            if match and not any(
                    token in line[:match.start()] for token in NOT_A_REDIRECTION):
                tag = (match.group("squote") or match.group("dquote")
                       or match.group("escaped") or match.group("bare"))
                cursor, size = index + 1, 0
                while cursor < len(lines) and lines[cursor].strip() != tag:
                    size += len(lines[cursor].encode("utf-8")) + 1
                    cursor += 1
                found.append((index + 1, tag, size))
                index = cursor
        index += 1
    return found


class TestEntrypointCannotSelfDeadlock(unittest.TestCase):

    def test_the_entrypoint_exists(self) -> None:
        self.assertTrue(ENTRYPOINT.is_file(), f"missing entrypoint at {ENTRYPOINT}")

    def test_no_here_document_anywhere_in_the_shared_entrypoint(self) -> None:
        """One rule, checked structurally: this file uses no heredoc, ever."""
        for path in shell_sources():
            with self.subTest(script=str(path.relative_to(PROJECT))):
                found = redirections(path)
                self.assertEqual(
                    found, [],
                    "a here-document in the shared entrypoint can deadlock against its "
                    "own pipe under load (Issue #78); pass Python programs with -c and "
                    "feed `read` from a process substitution instead. Found: "
                    + ", ".join(f"line {line} <<{tag} ({size} bytes)"
                                for line, tag, size in found))

    def test_every_generated_copy_is_covered(self) -> None:
        """The rule is worthless if it only guards the un-run source file."""
        copies = sorted((PROJECT / "skills").glob("*/scripts/kaola-tmux.sh"))
        self.assertEqual(len(copies), 9,
                         f"expected the nine generated platform copies, found {len(copies)}")
        source = ENTRYPOINT.read_bytes()
        for copy in copies:
            with self.subTest(copy=str(copy.relative_to(PROJECT))):
                self.assertEqual(copy.read_bytes(), source,
                                 "a generated copy drifted from scripts/kaola-tmux.sh; "
                                 "run ./scripts/render-skills.py --write")


if __name__ == "__main__":
    unittest.main(verbosity=2)
