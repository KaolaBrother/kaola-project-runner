#!/usr/bin/env python3
"""Issue #400: placeholder cleanup reports one event per real state change.

A vrpai worktree had already been deleted, yet the holder re-emitted
``tool_cwd_placeholder_left`` for its placeholder every few seconds (about 150
of the newest 200 events) and never released the claim. The same loop also
reported the same non-empty placeholder on every cleanup.

These tests drive the holder's real ``_cwd_cleanup``, ``_cwd_error_set``,
``_cwd_placeholder_drop`` and ``_cwd_forget_placeholder_path`` against real
temporary directories. Only the two external probes are stubbed (the sibling
cwd guard and the git worktree registration), so the suite pins:

* a placeholder directory that is already gone is released silently: one
  record write, no event, no duty, and repeated cleanup is a no-op;
* the rmdir race (the directory disappears between the check and rmdir) takes
  the same silent path instead of reporting a phantom "left";
* a non-empty placeholder keeps its claim, records its duty once and emits
  exactly one ``tool_cwd_placeholder_left`` no matter how many cleanups run;
* emptying it lets the next cleanup remove it, emit
  ``tool_cwd_placeholder_removed``, release the claim and clear the duty;
* when the non-empty condition recurs, the new state reports once — not on
  every following cleanup.
"""

from __future__ import annotations

import errno
import importlib.machinery
import importlib.util
import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"


def load_holder():
    loader = importlib.machinery.SourceFileLoader("kaola_acp_holder_400", str(HOLDER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class _Guard:
    """The sibling guard's two calls used by cleanup, over real paths."""

    def within(self, root: str, path: str) -> bool:
        try:
            return (os.path.commonpath([os.path.realpath(root), os.path.realpath(path)])
                    == os.path.realpath(root))
        except ValueError:
            return False

    def same_path(self, left: str, right: str) -> bool:
        return os.path.realpath(left) == os.path.realpath(right)


class _RecordWrites:
    """A write_record stand-in that counts the cleanup's durable writes."""

    def __init__(self) -> None:
        self.count = 0

    def __call__(self, *args, **kwargs) -> None:
        self.count += 1


class PlaceholderLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_holder()

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i400-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.guard = _Guard()

    def placeholder_path(self) -> Path:
        return self.root / "wt" / "sdk" / "typescript"

    def holder(self, path: Path, *, last_known: str | None = "/elsewhere"):
        holder = self.module.Holder.__new__(self.module.Holder)
        holder.tool_cwd = {
            "last_known": last_known, "source": None, "observed_at": None,
            "exists": False, "placeholder": [str(path)], "notice": "none",
            "notice_paths": [], "notice_ts": None, "repairs": 0,
        }
        holder.tool_cwd_lock = threading.Lock()
        holder.tool_cwd_errors = []
        holder.tool_cwd_vanished_path = None
        holder.args = SimpleNamespace(repo=str(self.root))
        holder.events = []
        holder.record = _RecordWrites()
        holder.write_record = holder.record
        holder._cwd_guard = lambda: self.guard
        holder.registered_calls = []
        holder._cwd_registered_worktree = lambda candidate: (
            holder.registered_calls.append(candidate) or False)
        holder._cwd_route = lambda code, candidate=None: "test-route"
        return holder

    def left_events(self, holder) -> list[dict]:
        return [event for event in holder.events
                if event.get("kind") == "tool_cwd_placeholder_left"]

    def test_missing_placeholder_is_released_silently(self) -> None:
        """The reported case: the directory is already gone; no event/duty."""
        path = self.placeholder_path()
        holder = self.holder(path)
        self.assertFalse(os.path.isdir(path))

        for _ in range(5):
            holder._cwd_cleanup()

        self.assertEqual(holder.events, [])
        self.assertEqual(holder.tool_cwd["placeholder"], [])
        self.assertEqual(holder.tool_cwd_errors, [])
        # The resume-reconcile decision needs no git answer for a path that
        # does not exist, and the claim change is persisted exactly once.
        self.assertEqual(holder.registered_calls, [])
        self.assertEqual(holder.record.count, 1)

    def test_rmdir_race_is_released_silently(self) -> None:
        """rmdir may lose to another remover after the isdir pre-check."""
        path = self.placeholder_path()
        path.mkdir(parents=True)
        holder = self.holder(path)
        real_rmdir = os.rmdir

        def racing_rmdir(target):
            real_rmdir(target)
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), target)

        with mock.patch.object(self.module.os, "rmdir", side_effect=racing_rmdir):
            holder._cwd_cleanup()

        self.assertFalse(path.exists())
        self.assertEqual(holder.events, [])
        self.assertEqual(holder.tool_cwd["placeholder"], [])
        self.assertEqual(holder.tool_cwd_errors, [])
        self.assertEqual(holder.record.count, 1)

    def test_non_empty_placeholder_reports_once_until_it_is_emptied(self) -> None:
        path = self.placeholder_path()
        path.mkdir(parents=True)
        stray = path / "stray.txt"
        stray.write_text("kept\n", encoding="utf-8")
        holder = self.holder(path)

        holder._cwd_cleanup()
        writes_after_first = holder.record.count
        for _ in range(4):
            holder._cwd_cleanup()

        left = self.left_events(holder)
        self.assertEqual(len(left), 1, holder.events)
        self.assertEqual(left[0], {"kind": "tool_cwd_placeholder_left",
                                   "path": str(path), "reason": "not-empty"})
        self.assertEqual(
            [(item.get("code"), item.get("path")) for item in holder.tool_cwd_errors],
            [("cwd-placeholder-not-empty", str(path))])
        self.assertEqual(holder.tool_cwd["placeholder"], [str(path)])
        self.assertTrue(stray.is_file())
        self.assertEqual(holder.record.count, writes_after_first,
                         "a repeated unchanged cleanup rewrote the record")

        # The real condition clears: an empty placeholder is removed, and its
        # claim and duty go with it.
        stray.unlink()
        holder._cwd_cleanup()
        self.assertFalse(path.exists())
        self.assertEqual(holder.tool_cwd["placeholder"], [])
        self.assertEqual(holder.tool_cwd_errors, [])
        self.assertIn({"kind": "tool_cwd_placeholder_removed", "path": str(path)},
                      holder.events)

        # The condition recurs as a new state: one fresh report, then silence.
        path.mkdir()
        (path / "again.txt").write_text("again\n", encoding="utf-8")
        holder.tool_cwd["placeholder"] = [str(path)]
        writes_before_recur = holder.record.count
        holder._cwd_cleanup()
        for _ in range(4):
            holder._cwd_cleanup()

        left = self.left_events(holder)
        self.assertEqual(len(left), 2, holder.events)
        self.assertEqual(left[-1], {"kind": "tool_cwd_placeholder_left",
                                    "path": str(path), "reason": "not-empty"})
        self.assertEqual(len(holder.tool_cwd_errors), 1)
        self.assertEqual(holder.tool_cwd["placeholder"], [str(path)])
        self.assertEqual(holder.record.count, writes_before_recur + 2,
                         "the first report writes the duty and the event once")

    def test_vanished_reported_placeholder_drops_its_duty_without_a_new_event(self) -> None:
        """A reported non-empty placeholder that disappears is still silent."""
        path = self.placeholder_path()
        path.mkdir(parents=True)
        (path / "stray.txt").write_text("kept\n", encoding="utf-8")
        holder = self.holder(path)
        holder._cwd_cleanup()
        self.assertEqual(len(self.left_events(holder)), 1)
        self.assertEqual(len(holder.tool_cwd_errors), 1)

        # The worktree/placeholder is removed out of band after the report.
        (path / "stray.txt").unlink()
        path.rmdir()
        holder._cwd_cleanup()

        self.assertEqual(len(self.left_events(holder)), 1, holder.events)
        self.assertEqual(holder.tool_cwd["placeholder"], [])
        self.assertEqual(holder.tool_cwd_errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
