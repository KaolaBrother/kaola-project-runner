#!/usr/bin/env python3
"""Issue #275 (P1 slice 1) — characterization contracts for the decided CORE surfaces.

This slice moves NO code. These are *characterization* oracles: they pin the
CURRENT behaviour of the surfaces the later internal cut must preserve, so that
the cut can prove no behaviour change. Each case is named by the P1 decision it
will feed:

* identity/version facts  — canonical serialization, id normalization, the
  `worker_event_id` composition, the record-dir identity helper's revision
  guard, and the schema/receipt version strings;
* process facts (the DUAL) — the documented duplicate implementation
  `kaola-acp-holder.py` `process_alive`/`libproc_ps` (:76/:103 in the inventory
  source revision) versus `kaola-acp.py` `pid_alive`/`libproc_ps`
  (:1552/:1925), including the `PermissionError -> True` branch. A fixture with
  unreadable argv records what each variant does today. This suite does NOT
  pick or change a variant; it records the divergence as the P1 decision input;
* atomic state write — temp file + `os.replace`, and a failed write leaves the
  original file untouched.

The import-graph skeleton at the end records today's cross-file imports and
subprocess/file-load edges. It is a recording skeleton: it asserts only facts
that are true on current main, never the absence of an edge.

Run directly (`python3 tests/contract/test-issue-275-core-contracts.py`) or
through `scripts/validate.sh --suite test-issue-275-core-contracts.py`.
"""
from __future__ import annotations

import sys as _sys

_sys.dont_write_bytecode = True

import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"

HOLDER_PATH = SCRIPTS / "kaola-acp-holder.py"
ACP_PATH = SCRIPTS / "kaola-acp.py"
DISPATCH_PATH = SCRIPTS / "kaola-dispatch.py"
RECORD_PATH = SCRIPTS / "kaola-record-contract.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


holder = _load("i275_holder", HOLDER_PATH)
acp = _load("i275_acp", ACP_PATH)
dispatch = _load("i275_dispatch", DISPATCH_PATH)
record = _load("i275_record", RECORD_PATH)


# The named P1 decision input. The cut AFTER #278/#286/#287 merge picks ONE
# variant and fixtures it; this slice only records the divergence below.
P1_DUAL_DECISION_INPUT = (
    "P1 decision input — process facts are duplicated: "
    "kaola-acp-holder.py process_alive/libproc_ps (inventory :76/:103) versus "
    "kaola-acp.py pid_alive/libproc_ps (inventory :1552/:1925). Both return True "
    "on PermissionError, so an unreadable process frees nothing. They differ on a "
    "non-int pid: pid_alive returns False (total), process_alive raises TypeError. "
    "Do NOT pick a variant in this slice."
)


def fresh_dead_pid() -> int:
    """A pid that os.kill(pid, 0) proves is dead at call time."""
    for _ in range(5):
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        pid = proc.pid
        proc.wait()
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return pid
        except PermissionError:
            continue
    raise RuntimeError("could not obtain a proven-dead pid for the fixture")


class IdentityVersionFacts(unittest.TestCase):
    """The minimal-core identity surface and the version facts it carries."""

    def test_canonical_is_deterministic_and_key_order_independent(self):
        first = holder.canonical({"b": [1, 2], "a": "\u00e9"})
        second = holder.canonical({"a": "\u00e9", "b": [1, 2]})
        self.assertEqual(first, second)
        # compact separators, sorted keys, ensure_ascii=False (UTF-8 bytes)
        self.assertEqual(first, '{"a":"\u00e9","b":[1,2]}'.encode("utf-8"))

    def test_normalize_id_is_str(self):
        self.assertEqual(holder.normalize_id(None), "None")
        self.assertEqual(holder.normalize_id(7), "7")
        self.assertEqual(holder.normalize_id("x"), "x")

    def test_worker_event_id_composition(self):
        params = {"platform": "codex", "session": "s1",
                  "kind": "turn-end", "event_cursor": 5}
        self.assertEqual(holder.worker_event_id(params), "codex/s1/turn-end/5")
        self.assertEqual(holder.worker_event_id({}), "None/None/None/None")

    def test_accepted_revision_identity_guard(self):
        good = "a" * 40
        self.assertEqual(holder._hex_revision(good), good)
        self.assertIsNone(holder._hex_revision("A" * 40))
        self.assertIsNone(holder._hex_revision("a" * 39))

    def test_schema_version_constants(self):
        self.assertEqual(holder.HEARTBEAT_STATE_SCHEMA, "kaola-heartbeat-prompt/2")
        self.assertEqual(dispatch.STATE_SCHEMA, "kaola-heartbeat-prompt/2")
        self.assertEqual(dispatch.LEGACY_STATE_SCHEMA, "kaola-heartbeat-prompt/1")
        self.assertEqual(record.HOST_SCHEMA, "kaola-heartbeat-prompt/2")
        self.assertEqual(record.DELEGATOR_SCHEMA, "kaola-delegator-heartbeat/1")
        self.assertEqual(dispatch.STATE_FILE_MAX_BYTES, 1048576)

    def test_receipt_schema_version_is_3(self):
        receipt = acp.input_error_receipt("boom")
        self.assertEqual(receipt["schema_version"], 3)
        self.assertEqual(receipt["error"]["code"], "invalid-input")
        self.assertEqual(receipt["error"]["message"], "boom")

    def test_dispatch_index_version_literal_present(self):
        self.assertIn('"kaola-dispatch-index/1"',
                      DISPATCH_PATH.read_text(encoding="utf-8"))


class ProcessFactsDual(unittest.TestCase):
    """The DUAL process-facts implementation, recorded not resolved."""

    def test_dual_decision_input_is_named(self):
        for token in ("process_alive", "libproc_ps", "pid_alive",
                      "PermissionError"):
            self.assertIn(token, P1_DUAL_DECISION_INPUT)
        self.assertTrue(callable(holder.process_alive))
        self.assertTrue(callable(holder.libproc_ps))
        self.assertTrue(callable(acp.pid_alive))
        self.assertTrue(callable(acp.libproc_ps))

    def test_liveness_variants_agree_on_live_and_dead(self):
        live = os.getpid()
        dead = fresh_dead_pid()
        self.assertTrue(holder.process_alive(live))
        self.assertTrue(acp.pid_alive(live))
        self.assertFalse(holder.process_alive(dead))
        self.assertFalse(acp.pid_alive(dead))

    def test_permission_error_returns_true_in_both_variants(self):
        # The unreadable-process branch: neither variant may free a live seat.
        with mock.patch.object(os, "kill", side_effect=PermissionError("denied")):
            self.assertTrue(holder.process_alive(os.getpid()))
            self.assertTrue(acp.pid_alive(os.getpid()))

    def test_nonpositive_pid_false_in_both_variants(self):
        for pid in (0, -1):
            self.assertFalse(holder.process_alive(pid))
            self.assertFalse(acp.pid_alive(pid))

    def test_type_guard_divergence_is_recorded(self):
        # acp.py guards the type; the holder does not. Today's divergence:
        self.assertFalse(acp.pid_alive("not-a-pid"))
        self.assertFalse(acp.pid_alive(None))
        with self.assertRaises(TypeError):
            holder.process_alive("not-a-pid")
        with self.assertRaises(TypeError):
            holder.process_alive(None)

    def test_libproc_ps_off_darwin_is_none_in_both_variants(self):
        columns = ["pid", "ppid", "pgid", "state", "lstart"]
        with mock.patch.object(sys, "platform", "linux"):
            self.assertIsNone(holder.libproc_ps(columns))
            self.assertIsNone(acp.libproc_ps(columns))

    def test_unreadable_argv_frees_nothing(self):
        # Fixture: argv cannot be read (process_command returns None). Today the
        # acp.py variant returns None for a live pid (frees nothing) and False
        # only for a proven-dead pid; the holder has no argv anchor at all.
        live = os.getpid()
        dead = fresh_dead_pid()
        with mock.patch.object(acp, "process_command", return_value=None):
            self.assertIsNone(acp.holder_argv_paths(live))
            self.assertIsNone(acp.holder_argv_anchor(live, Path("/nonexistent")))
            self.assertIsNone(acp.holder_argv_paths(dead))
            self.assertFalse(acp.holder_argv_anchor(dead, Path("/nonexistent")))
        # recorded asymmetry of the DUAL: the argv anchor lives only in acp.py
        self.assertFalse(hasattr(holder, "holder_argv_anchor"))


class AtomicStateWrite(unittest.TestCase):
    """Atomic state access: temp file + replace, failure leaves the original."""

    def test_write_replaces_and_leaves_no_temp(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "state.json"
            target.write_text('{"old": true}', encoding="utf-8")
            dispatch.atomic_write(target, '{"new": true}')
            self.assertEqual(target.read_text(encoding="utf-8"), '{"new": true}')
            self.assertFalse((Path(td) / "state.json.tmp").exists())

    def test_write_creates_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "a" / "b" / "state.json"
            dispatch.atomic_write(target, '{"x": 1}')
            self.assertTrue(target.is_file())
            self.assertFalse((Path(td) / "a" / "b" / "state.json.tmp").exists())

    def test_replace_failure_leaves_original(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "state.json"
            target.write_text("ORIGINAL", encoding="utf-8")
            with mock.patch.object(os, "replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    dispatch.atomic_write(target, "REPLACEMENT")
            self.assertEqual(target.read_text(encoding="utf-8"), "ORIGINAL")
            self.assertFalse((Path(td) / "state.json.tmp").exists())

    def test_temp_write_failure_leaves_original(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "state.json"
            target.write_text("ORIGINAL", encoding="utf-8")
            with mock.patch.object(Path, "write_text", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    dispatch.atomic_write(target, "REPLACEMENT")
            self.assertEqual(target.read_text(encoding="utf-8"), "ORIGINAL")
            self.assertFalse((Path(td) / "state.json.tmp").exists())

    def test_read_state_file_roundtrip_missing_and_bad(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            self.assertEqual(dispatch.read_state_file(path), (None, None))
            path.write_text('{"schema": "kaola-heartbeat-prompt/2", "state": {}}',
                            encoding="utf-8")
            doc, raw = dispatch.read_state_file(path)
            self.assertEqual(doc["schema"], "kaola-heartbeat-prompt/2")
            self.assertEqual(raw, path.read_bytes())
            path.write_text("[1, 2]", encoding="utf-8")
            with self.assertRaises(ValueError):
                dispatch.read_state_file(path)


def _module_graph(path: Path) -> dict[str, list[str]]:
    """Record one file's imports, subprocess calls and module loads."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    subprocess_calls: set[str] = set()
    file_loads: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            value = node.func.value
            if isinstance(value, ast.Name) and value.id == "subprocess":
                subprocess_calls.add(attr)
            if attr in ("spec_from_file_location", "module_from_spec", "exec_module"):
                file_loads.add(attr)
    return {"imports": sorted(imports),
            "subprocess_calls": sorted(subprocess_calls),
            "file_loads": sorted(file_loads)}


class ImportGraphSkeleton(unittest.TestCase):
    """Record today's cross-file imports/subprocess loads (P1 file-level graph).

    Skeleton by design: it records the snapshot and asserts only facts true on
    current main. It never asserts the ABSENCE of an edge, so the later cut can
    tighten it without a false failure here.
    """

    def test_records_cross_file_imports_and_subprocess_loads(self):
        targets = {
            "kaola-acp-holder.py": HOLDER_PATH,
            "kaola-acp.py": ACP_PATH,
            "kaola-dispatch.py": DISPATCH_PATH,
            "kaola-record-contract.py": RECORD_PATH,
        }
        graph = {name: _module_graph(path) for name, path in targets.items()}
        dynamic_loads = {
            "kaola-acp-holder.py": {
                "QUOTA_MODULE": holder.QUOTA_MODULE,
                "RECORD_MODULE": holder.RECORD_MODULE,
                "COMPACT_MODULE": holder.COMPACT_MODULE,
            },
        }
        record_json = json.dumps(
            {"imports": graph, "dynamic_file_loads": dynamic_loads},
            indent=2, sort_keys=True)
        print("\n[issue-275 import-graph recording]\n" + record_json)

        # Structural facts only (all true today):
        self.assertEqual(set(graph), {
            "kaola-acp-holder.py", "kaola-acp.py",
            "kaola-dispatch.py", "kaola-record-contract.py"})
        for name, entry in graph.items():
            self.assertTrue(entry["imports"], name)

        # Known code-dependency facts from the design's acyclic graph:
        self.assertIn("spec_from_file_location",
                      graph["kaola-acp-holder.py"]["file_loads"])
        self.assertIn("run", graph["kaola-dispatch.py"]["subprocess_calls"])
        for name in ("kaola-acp-holder.py", "kaola-acp.py",
                     "kaola-dispatch.py"):
            self.assertIn("subprocess", graph[name]["imports"])

        # C1 -> C2-data / C1 -> C6 / C1 -> C4 sibling file-loads:
        self.assertEqual(holder.QUOTA_MODULE, "kaola-quota.py")
        self.assertEqual(holder.RECORD_MODULE, "kaola-record-contract.py")
        self.assertEqual(holder.COMPACT_MODULE, "kaola-compact-recovery.py")


if __name__ == "__main__":
    unittest.main(verbosity=2)
