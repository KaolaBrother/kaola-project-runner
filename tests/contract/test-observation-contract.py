#!/usr/bin/env python3
"""Independent Issue #6 observation, hash, fixture, and boundary oracles.

This file owns the acceptance meaning for the pure observation contract.  It
never imports or mocks the Runner's mutation code; adapter observations are
obtained by sourcing the real adapter and the public action checks live in
``test-guarded-actions.sh``.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
HELPER_PATH = PROJECT / "scripts" / "kaola-observation.py"
FIXTURE_ROOT = PROJECT / "tests" / "fixtures" / "observations" / "claude-code"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
CLAUDE_ADAPTER = PROJECT / "scripts" / "adapters" / "claude-code.sh"
OPENCODE_ADAPTER = PROJECT / "scripts" / "adapters" / "opencode.sh"
CURSOR_ADAPTER = PROJECT / "scripts" / "adapters" / "cursor-cli.sh"
CURSOR_X0_FRAME = (
    PROJECT
    / "tests"
    / "fixtures"
    / "observations"
    / "cursor-cli"
    / "ready-cursor-x0.frame.txt"
)

EXPECTED_FIXTURES = {
    "active-shell",
    "active-subagent",
    "spinner",
    "freeform-decision",
    "populated-draft",
    "completed-empty",
    "native-approval",
    "trust-screen",
}

OPAQUE_DIGESTS = {
    "snapshot": re.compile(r"^kpr-snapshot-v2:[0-9a-f]{64}$"),
    "pane": re.compile(r"^kpr-pane-v2:[0-9a-f]{64}$"),
    "decision": re.compile(r"^kpr-decision-v1:[0-9a-f]{64}$"),
    "receipt": re.compile(r"^kpr-answer-v2:[0-9a-f]{64}$"),
    "fingerprint": re.compile(r"^sha256:[0-9a-f]{64}$"),
}

GROK_GOLDEN_REVIEWED_SHA256 = {
    "SKILL.md": "ae74d354ef1059a60edbde8cb4a99dad09d2d25cc47e0fc637e2c9164cc70dbe",
    "agents/openai.yaml": "66699c5188eb10c53ab166572d530bbe77132c64d5b666c7258f68188bc64ddd",
    "references/closing.md": "2fda2a5726fa39abbbeb87ce7e80815e2d2870f001d7198e949e26f46a2b60c1",
    "references/codex-supervision.md": "b9c3ec5d4aa7081faccf7773d84b08b10bad828cc8e15f4221de9435be7cb2d4",
    "references/grok-tui.md": "818f9c7496d7d9a132112ceeb4d29c03d10d0c7a7765945026353d8e4033a6f8",
    "references/human-decisions.md": "f7abfdda3d3590fcefd10316cf3bc51a6ffcf79834ae7b23cf7c25f1ba621a2c",
    "references/kaola-lifecycle.md": "2c545d92737fee3bf3b3f1d147ac1e425999f698d0aa3e69a4afe210106dd9ea",
    "references/pr-claim-handoff.md": "d7b452943c5775aa2fc79db402ded3aab9a0cc332230b59f910ce334415c2377",
    "references/project-run.md": "742ec446152abd484fb4c7368da27183878d0f2075c63cec10a1327a8923187f",
    "references/scheduling.md": "6ea889913d7e8109767b61695b9d0030e393941861023a2a9955f093e2558e9e",
    "references/status-monitoring.md": "a113eee36c698c8c85d7e2e9a303837a8cc8dfd9c27a6e7e944789758776db20",
    "references/task-modes.md": "c9e8333d82a44edbdf8eb1d2bbb2f3f4f317b9ed34a02aea69fa2240aff3ca23",
}


def load_helper():
    if not HELPER_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("kaola_observation_issue6", HELPER_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HELPER = load_helper()


def read_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def run_platform_adapter_observer(adapter: Path, frame: str, pane_facts: dict) -> dict:
    """Call a real adapter hook, never a copy of its parser."""

    command = (
        "set -euo pipefail; "
        "source \"$1\"; "
        "type adapter_observe_frame >/dev/null; "
        "adapter_observe_frame \"$2\" \"$3\""
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            command,
            "issue6-adapter-observer",
            str(adapter),
            frame,
            json.dumps(pane_facts, ensure_ascii=False, separators=(",", ":")),
        ],
        cwd=PROJECT,
        text=True,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "PYTHON_BIN": sys.executable},
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{adapter.stem} adapter observer failed: "
            f"exit {result.returncode}; stderr={result.stderr.strip()!r}; stdout={result.stdout.strip()!r}"
        )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError(f"{adapter.stem} adapter observer emitted no JSON facts")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{adapter.stem} adapter observer did not emit JSON: {result.stdout!r}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"{adapter.stem} adapter observer emitted non-object facts: {payload!r}")
    return payload


def run_adapter_observer(frame: str, pane_facts: dict) -> dict:
    """Backward-compatible shorthand for the Claude fixture suite."""

    return run_platform_adapter_observer(CLAUDE_ADAPTER, frame, pane_facts)


def pane_facts() -> dict:
    return {
        "pane_id": "%7",
        "pane_dead": False,
        "pane_width": 120,
        "pane_height": 24,
        "cursor_x": 2,
        "cursor_y": 23,
        "cursor_flag": True,
        "alternate_on": True,
        "history_size": 106,
        "history_bytes": 1006,
        "pane_input_off": False,
        "relay_epoch": "1" * 32,
        "child_input_offset": 10,
        "child_output_offset": 20,
        "child_output_digest": "sha256:" + "8" * 64,
        "resize_revision": 0,
    }


def base_observation() -> dict:
    """Build a fully typed schema-v2 object with relay facts fixed."""

    assert HELPER is not None
    hard = {
        "present": True,
        "owned": True,
        "platform_match": True,
        "repo_match": True,
        "pane_count": 1,
        "pane_id": "%7",
        "pane_dead": False,
        "pane_input_off": False,
        "pane_width": 120,
        "pane_height": 24,
        "cursor_x": 2,
        "cursor_y": 23,
        "cursor_flag": True,
        "alternate_on": True,
        "history_size": 106,
        "history_bytes": 1006,
        "pane_path": "/workspace/fixture-repo",
        "pane_pid": 100,
        "pane_command": "python3",
        "pane_title": "Claude Code",
        "pane_process": "python3 kaola-pane-relay.py",
        "relay_process_match": True,
        "process_match": True,
        "tui_detected": True,
    }
    frame = "Completed work is ready to continue.\nshells: 0\nagents: 0\n❯\n"
    observation = {
        "schema_version": 2,
        "result": "observed",
        "platform": "claude-code",
        "runtime": "Claude Code",
        "session": "fixture-session",
        "repo": "/workspace/fixture-repo",
        "snapshot_id": "",
        "pane_revision": HELPER.make_pane_revision(pane_facts(), frame),
        "raw_current_frame": frame,
        "editor_state": "empty",
        "editor_fingerprint": "sha256:" + "1" * 64,
        "hard_evidence": hard,
        "relay": {
            "managed": True,
            "protocol_version": 1,
            "epoch": "1" * 32,
            "pid": 100,
            "start_fingerprint": "sha256:" + "1" * 64,
            "socket_path": "/tmp/relay-" + "2" * 32 + ".sock",
            "socket_owner_uid": 501,
            "socket_mode": "0600",
            "peer_pid_verified": True,
            "state": "running",
            "child_pid": 101,
            "child_pgid": 101,
            "child_start_fingerprint": "sha256:" + "3" * 64,
            "child_runtime_path": "/usr/local/bin/claude",
            "child_process": "claude --model opus",
            "child_process_state": "S",
            "child_process_match": True,
            "process_group_running": True,
            "lease_active": False,
            "child_input_offset": 10,
            "child_output_offset": 20,
            "child_output_digest": "sha256:" + "8" * 64,
            "resize_revision": 0,
            "bracketed_paste": True,
            "terminal_fence": "decrqm-nonce-v1",
        },
        "child_processes": [],
        "child_process_count": 0,
        "visible_shell_count": 0,
        "visible_agent_count": 0,
        "native_approval": {"state": "absent", "kind": None, "fingerprint": None},
        "structured_decision_marker": None,
        "later_output_barrier": None,
        "activity_hint": "idle",
        "runtime_session_id": "runtime-session",
        "git": {
            "branch": "main",
            "head": "fixture-head",
            "clean": True,
            "changed_count": 0,
            "upstream": "origin/main",
            "ahead": 0,
            "behind": 0,
        },
        "evidence_flags": [],
    }
    observation["snapshot_id"] = HELPER.make_snapshot_id(observation)
    return observation


class ObservationContractTests(unittest.TestCase):
    def assert_digest(self, kind: str, value: str) -> None:
        self.assertIsInstance(value, str)
        self.assertRegex(value, OPAQUE_DIGESTS[kind])

    def test_00_helper_is_importable_and_exposes_contract(self) -> None:
        if HELPER is None:
            self.skipTest("scripts/kaola-observation.py is not present")
        for name in (
            "parse_process_table",
            "descendants",
            "canonical_bytes",
            "make_pane_revision",
            "make_snapshot_id",
            "make_decision_marker",
            "make_answer_receipt",
        ):
            self.assertTrue(callable(getattr(HELPER, name, None)), f"missing helper function {name}")

    def test_01_manifest_has_exact_sanitized_fixture_set_and_hashes(self) -> None:
        manifest = read_manifest()
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["platform"], "claude-code")
        entries = manifest["fixtures"]
        self.assertEqual({entry["name"] for entry in entries}, EXPECTED_FIXTURES)
        self.assertEqual(len(entries), len(EXPECTED_FIXTURES))
        ansi = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|$))")
        uuid = re.compile(
            r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b"
        )
        for entry in entries:
            frame_path = FIXTURE_ROOT / entry["frame"]
            self.assertTrue(frame_path.is_file(), f"missing fixture {frame_path}")
            raw = frame_path.read_bytes()
            text = raw.decode("utf-8")
            self.assertEqual(raw[-1:], b"\n", f"fixture lacks one final LF: {frame_path}")
            self.assertNotIn(b"\r", raw, f"fixture contains CR bytes: {frame_path}")
            self.assertIsNone(ansi.search(text), f"fixture contains ANSI escapes: {frame_path}")
            self.assertNotRegex(text, r"/(?:Users|home)/")
            self.assertNotRegex(text, r"(?i)\b(?:https?|file|ssh)://")
            self.assertNotRegex(text, r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
            self.assertIsNone(uuid.search(text), f"fixture contains UUID material: {frame_path}")
            self.assertNotRegex(text, r"(?i)\b[0-9a-f]{40,}\b")
            digest = hashlib.sha256(raw).hexdigest()
            self.assertEqual(entry["sha256"], digest, f"manifest hash drift: {frame_path}")

    @unittest.skipUnless(HELPER_PATH.is_file(), "scripts/kaola-observation.py is not present")
    def test_02_claude_fixtures_emit_advisory_facts_without_making_them_authority(self) -> None:
        manifest = read_manifest()
        required = {
            "editor_state",
            "editor_fingerprint",
            "visible_shell_count",
            "visible_agent_count",
            "native_approval",
        }
        for entry in manifest["fixtures"]:
            with self.subTest(fixture=entry["name"]):
                frame = (FIXTURE_ROOT / entry["frame"]).read_text(encoding="utf-8")
                facts = run_adapter_observer(frame, entry["pane_facts"])
                self.assertTrue(required.issubset(facts), f"missing structural keys: {facts}")
                # These compatibility fields are evidence for the controlling
                # agent.  Their historical expected labels are deliberately
                # not an acceptance oracle for send/stop authority.
                self.assertIn(facts["editor_state"], {"empty", "nonempty", "unknown"})
                if facts["editor_fingerprint"] is not None:
                    self.assert_digest("fingerprint", facts["editor_fingerprint"])
                approval = facts["native_approval"]
                self.assertIsInstance(approval, dict)
                self.assertIn(approval["state"], {"absent", "present", "unknown"})
                if approval["fingerprint"] is not None:
                    self.assert_digest("fingerprint", approval["fingerprint"])

    @unittest.skipUnless(HELPER_PATH.is_file(), "scripts/kaola-observation.py is not present")
    def test_03_editor_and_decision_facts_are_not_activity_phrase_rules(self) -> None:
        manifest = read_manifest()
        by_name = {entry["name"]: entry for entry in manifest["fixtures"]}
        freeform = (FIXTURE_ROOT / by_name["freeform-decision"]["frame"]).read_text(encoding="utf-8")
        marker = HELPER.make_decision_marker(freeform)
        self.assertIsNone(marker, "free-form waiting prose fabricated a structured decision marker")

        exact = "\n".join(
            (
                "HUMAN_DECISION_REQUIRED",
                "Decision: choose fixture answer",
                "Evidence: sanitized fixture evidence",
                "Recommendation: choose chosen-answer",
                "Safe options: chosen-answer or decline",
                "Paused state: waiting for explicit answer",
            )
        ) + "\n"
        marker = HELPER.make_decision_marker(exact)
        self.assertIsInstance(marker, dict)
        self.assertEqual(set(marker), {"decision_id", "fingerprint", "current_frame"})
        self.assertTrue(marker["current_frame"])
        self.assert_digest("fingerprint", marker["fingerprint"])
        self.assert_digest("decision", marker["decision_id"])
        self.assertEqual(marker["decision_id"].split(":", 1)[1], marker["fingerprint"].split(":", 1)[1])
        partial = exact.replace("Safe options: chosen-answer or decline\n", "")
        self.assertIsNone(HELPER.make_decision_marker(partial))

    @unittest.skipUnless(HELPER_PATH.is_file(), "scripts/kaola-observation.py is not present")
    def test_04_canonical_bytes_and_pane_revisions_are_stable_and_opaque(self) -> None:
        first = HELPER.canonical_bytes({"b": 2, "a": "é"})
        second = HELPER.canonical_bytes({"a": "é", "b": 2})
        self.assertEqual(first, second)
        self.assertIn("é".encode("utf-8"), first, "canonical bytes escaped non-ASCII unexpectedly")

        frame = "one\ntwo\n"
        facts = pane_facts()
        revision = HELPER.make_pane_revision(facts, frame)
        self.assert_digest("pane", revision)
        self.assertEqual(revision, HELPER.make_pane_revision(dict(facts), frame))
        for field, value in (
            ("pane_id", "%8"),
            ("pane_dead", True),
            ("pane_width", 121),
            ("pane_height", 25),
            ("cursor_x", 3),
            ("cursor_y", 22),
            ("cursor_flag", False),
            ("alternate_on", False),
            ("history_size", 107),
            ("history_bytes", 1007),
            ("relay_epoch", "2" * 32),
            ("child_input_offset", 11),
            ("child_output_offset", 21),
            ("child_output_digest", "sha256:" + "9" * 64),
            ("resize_revision", 1),
        ):
            changed = dict(facts)
            changed[field] = value
            self.assertNotEqual(
                revision,
                HELPER.make_pane_revision(changed, frame),
                f"pane revision ignored transport fact {field}",
            )
        self.assertNotEqual(revision, HELPER.make_pane_revision(facts, frame + "output\n"))

    @unittest.skipUnless(HELPER_PATH.is_file(), "scripts/kaola-observation.py is not present")
    def test_05_snapshot_covers_all_mutation_premises(self) -> None:
        original = base_observation()
        self.assert_digest("snapshot", original["snapshot_id"])

        mutations = {
            "platform": lambda o: o.update(platform="grok"),
            "repo": lambda o: o.update(repo="/workspace/other-repo"),
            "session": lambda o: o.update(session="other-session"),
            "raw_current_frame": lambda o: o.update(raw_current_frame=o["raw_current_frame"] + "changed\n"),
            "hard_evidence": lambda o: o["hard_evidence"].update(pane_command="other-runtime"),
            "relay_epoch": lambda o: o["relay"].update(epoch="2" * 32),
            "relay_socket": lambda o: o["relay"].update(socket_path="/tmp/relay-other.sock"),
            "relay_peer": lambda o: o["relay"].update(peer_pid_verified=False),
            "child_input_offset": lambda o: o["relay"].update(child_input_offset=11),
            "resize_revision": lambda o: o["relay"].update(resize_revision=1),
            "child_identity": lambda o: o["relay"].update(child_pid=102, child_pgid=102),
            "child_runtime": lambda o: o["relay"].update(child_runtime_path="/usr/local/bin/other"),
            "child_processes": lambda o: o.update(
                child_processes=[{"pid": 202, "ppid": 101, "state": "S", "command": "sh"}],
                child_process_count=1,
            ),
            "child_process_count": lambda o: o.update(child_process_count=1),
            "native_approval": lambda o: o.update(
                native_approval={"state": "present", "kind": "tool", "fingerprint": "sha256:" + "2" * 64}
            ),
            "later_output_barrier": lambda o: o.update(
                later_output_barrier={
                    "receipt_id": "kpr-answer-v2:" + "2" * 64,
                    "prepared_pane_revision": original["pane_revision"],
                    "state": "pending",
                }
            ),
            "git": lambda o: o["git"].update(clean=False, changed_count=1),
        }
        for name, mutate in mutations.items():
            with self.subTest(field=name):
                changed = copy.deepcopy(original)
                mutate(changed)
                self.assertNotEqual(
                    original["snapshot_id"],
                    HELPER.make_snapshot_id(changed),
                    f"snapshot ignored mutation premise {name}",
                )

    @unittest.skipUnless(HELPER_PATH.is_file(), "scripts/kaola-observation.py is not present")
    def test_06_snapshot_ignores_advisory_and_reporting_facts(self) -> None:
        original = base_observation()
        for name, mutate in (
            ("activity_hint", lambda o: o.update(activity_hint="busy")),
            ("runtime_session_id", lambda o: o.update(runtime_session_id="another-runtime-session")),
            ("pane_revision", lambda o: o.update(pane_revision="kpr-pane-v2:" + "2" * 64)),
            ("pane_input_off", lambda o: o["hard_evidence"].update(pane_input_off=True)),
            ("history", lambda o: o["hard_evidence"].update(history_size=107, history_bytes=1007)),
            ("relay_state", lambda o: o["relay"].update(state="quiesced")),
            ("child_output_offset", lambda o: o["relay"].update(child_output_offset=21)),
            ("child_output_digest", lambda o: o["relay"].update(child_output_digest="sha256:" + "9" * 64)),
        ):
            with self.subTest(field=name):
                changed = copy.deepcopy(original)
                mutate(changed)
                self.assertEqual(
                    original["snapshot_id"],
                    HELPER.make_snapshot_id(changed),
                    f"advisory/reporting fact {name} became a mutation premise",
                )

    @unittest.skipUnless(HELPER_PATH.is_file(), "scripts/kaola-observation.py is not present")
    def test_07_process_table_and_descendant_evidence_is_deterministic(self) -> None:
        ps_text = """\
101 1 S node /usr/local/bin/node --fixture
202 101 S sh /bin/sh -c fixture
303 202 Z zsh /bin/zsh
404 101 S python3 /usr/bin/python3 worker
"""
        rows = HELPER.parse_process_table(ps_text)
        self.assertEqual([row["pid"] for row in rows], [101, 202, 303, 404])
        for row in rows:
            self.assertEqual(set(row), {"pid", "ppid", "state", "command"})
            self.assertIsInstance(row["pid"], int)
            self.assertIsInstance(row["ppid"], int)
            self.assertNotIn("/", row["command"])
            self.assertNotIn(" ", row["command"])
        self.assertEqual([row["pid"] for row in HELPER.descendants(101, rows)], [202, 404])

    @unittest.skipUnless(HELPER_PATH.is_file(), "scripts/kaola-observation.py is not present")
    def test_08_answer_receipt_is_opaque_and_reproducible(self) -> None:
        fields = {
            "schema_version": 2,
            "action": "answer",
            "platform": "claude-code",
            "session": "fixture-session",
            "repo": "/workspace/fixture-repo",
            "decision_id": "kpr-decision-v1:" + "3" * 64,
            "replaced_editor_fingerprint": "sha256:" + "4" * 64,
            "answer_fingerprint": "sha256:" + "5" * 64,
            "based_on_snapshot": "kpr-snapshot-v2:" + "6" * 64,
            "relay_epoch": "7" * 32,
            "child_start_fingerprint": "sha256:" + "8" * 64,
            "prepared_pane_revision": "kpr-pane-v2:" + "9" * 64,
            "submitted_output_offset": 48221,
            "child_output_digest": "sha256:" + "a" * 64,
        }
        try:
            receipt = HELPER.make_answer_receipt(fields)
        except Exception as exc:  # noqa: BLE001 - turn a legacy helper crash into a RED oracle
            self.fail(f"schema-v2 answer receipt unavailable: {type(exc).__name__}: {exc}")
        if isinstance(receipt, dict):
            self.assertEqual(set(receipt), {"receipt_id"})
            receipt_id = receipt["receipt_id"]
        else:
            receipt_id = receipt
        self.assert_digest("receipt", receipt_id)
        receipt_input = {
            key: fields[key]
            for key in (
                "schema_version",
                "platform",
                "session",
                "repo",
                "decision_id",
                "replaced_editor_fingerprint",
                "answer_fingerprint",
                "based_on_snapshot",
                "relay_epoch",
                "child_start_fingerprint",
                "prepared_pane_revision",
                "submitted_output_offset",
                "child_output_digest",
            )
        }
        independently_expected = "kpr-answer-v2:" + hashlib.sha256(HELPER.canonical_bytes(receipt_input)).hexdigest()
        self.assertEqual(receipt_id, independently_expected)
        again = HELPER.make_answer_receipt(dict(fields))
        if isinstance(again, dict):
            self.assertEqual(again.get("receipt_id"), receipt_id)
        else:
            self.assertEqual(again, receipt_id)
        self.assertNotIn("draft-prefix", receipt_id)
        self.assertNotIn("chosen-answer", receipt_id)

        # Every identity/counter premise is part of the receipt. A receipt
        # that omits one of these fields could be replayed after the relay or
        # child changed while the answer was being prepared.
        for key, value in receipt_input.items():
            changed = dict(fields)
            if isinstance(value, int):
                changed[key] = value + 1
            elif key == "schema_version":
                changed[key] = 1
            elif key == "platform":
                changed[key] = "grok"
            elif key == "session":
                changed[key] = "other-session"
            elif key == "repo":
                changed[key] = "/workspace/other-repo"
            elif key == "decision_id":
                changed[key] = "kpr-decision-v1:" + "a" * 64
            elif key == "based_on_snapshot":
                changed[key] = "kpr-snapshot-v2:" + "a" * 64
            elif key == "prepared_pane_revision":
                changed[key] = "kpr-pane-v2:" + "a" * 64
            elif key == "relay_epoch":
                changed[key] = "a" * 32
            elif key.endswith("fingerprint"):
                changed[key] = "sha256:" + "a" * 64
            elif key == "child_output_digest":
                changed[key] = "sha256:" + "b" * 64
            else:
                self.fail(f"unhandled receipt mutation field {key}")
            candidate = HELPER.make_answer_receipt(changed)
            if isinstance(candidate, dict):
                candidate = candidate["receipt_id"]
            self.assertNotEqual(receipt_id, candidate, f"answer receipt ignored {key}")

    def test_09_generic_send_and_stop_do_not_use_semantic_advisories_as_authority(self) -> None:
        core = (PROJECT / "scripts" / "kaola-tmux.sh").read_text(encoding="utf-8")
        semantic_authority = re.compile(
            r"editor_state|editor_fingerprint|visible_shell_count|visible_agent_count|"
            r"structured_decision_marker|activity_hint|STATE_ACTIVITY|evidence_flags"
        )
        direct = re.search(r"(?ms)^open_transport_channel\(\).*?^\}\n", core)
        self.assertIsNotNone(direct, "missing open_transport_channel")
        assert direct is not None
        self.assertNotRegex(
            direct.group(0),
            semantic_authority,
            "direct transport turns advisory interpretation into mutation authority",
        )

        send = core.split("  send)", 1)[1].split("  stop)", 1)[0]
        self.assertNotIn("--require-empty-editor", send)
        self.assertNotIn("empty-editor-guard-required", send)
        self.assertNotIn("prepare_transaction", send)
        self.assertRegex(send, r"payload_fp.*==.*send_fp")

        stop = core.split("  stop)", 1)[1]
        self.assertRegex(
            stop,
            r"payload_fp.*==.*quit_fp",
            "ordinary stop lacks exact quit-payload transfer attestation",
        )

    def test_10_frozen_grok_golden_bytes_remain_unchanged(self) -> None:
        golden = PROJECT / "templates" / "grok-golden"
        actual_paths = {
            path.relative_to(golden).as_posix()
            for path in golden.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual_paths, set(GROK_GOLDEN_REVIEWED_SHA256))
        for relative, expected in GROK_GOLDEN_REVIEWED_SHA256.items():
            path = golden / relative
            self.assertTrue(path.is_file(), f"missing frozen Grok source {relative}")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected, relative)

    @unittest.skipUnless(HELPER_PATH.is_file(), "scripts/kaola-observation.py is not present")
    def test_11_schema_v2_contains_attested_relay_and_counter_facts(self) -> None:
        observation = base_observation()
        self.assertEqual(observation["schema_version"], 2)
        self.assertEqual(
            set(observation),
            {
                "schema_version",
                "result",
                "platform",
                "runtime",
                "session",
                "repo",
                "snapshot_id",
                "pane_revision",
                "raw_current_frame",
                "editor_state",
                "editor_fingerprint",
                "hard_evidence",
                "relay",
                "child_processes",
                "child_process_count",
                "visible_shell_count",
                "visible_agent_count",
                "native_approval",
                "structured_decision_marker",
                "later_output_barrier",
                "activity_hint",
                "runtime_session_id",
                "git",
                "evidence_flags",
            },
        )
        self.assertIn("relay_process_match", observation["hard_evidence"])
        self.assertEqual(
            set(observation["relay"]),
            {
                "managed",
                "protocol_version",
                "epoch",
                "pid",
                "start_fingerprint",
                "socket_path",
                "socket_owner_uid",
                "socket_mode",
                "peer_pid_verified",
                "state",
                "child_pid",
                "child_pgid",
                "child_start_fingerprint",
                "child_runtime_path",
                "child_process",
                "child_process_state",
                "child_process_match",
                "process_group_running",
                "lease_active",
                "child_input_offset",
                "child_output_offset",
                "child_output_digest",
                "resize_revision",
                "bracketed_paste",
                "terminal_fence",
            },
        )
        self.assertEqual(observation["relay"]["socket_mode"], "0600")
        self.assertRegex(observation["relay"]["epoch"], r"^[0-9a-f]{32}$")
        for key in ("start_fingerprint", "child_start_fingerprint", "child_output_digest"):
            self.assert_digest("fingerprint", observation["relay"][key])

    def test_12_kimi_workspace_trust_remains_explicit_native_approval_evidence(self) -> None:
        self.assertIsNotNone(HELPER)
        frame = (
            "Trust this folder?\n"
            "Enter select · Esc exit\n"
            "Project-level MCP servers are disabled until you explicitly choose Trust.\n"
            "Trust this folder\n"
            "❯ Don't trust\n"
        )
        facts = HELPER.kimi_frame_facts(frame, "waiting-human")
        self.assertEqual(facts["editor_state"], "unknown")
        self.assertEqual(facts["visible_shell_count"], 0)
        self.assertEqual(facts["visible_agent_count"], 0)
        self.assertEqual(facts["native_approval"]["state"], "present")
        self.assertEqual(facts["native_approval"]["kind"], "workspace-trust")

    def test_13_real_cursor_x0_frame_is_preserved_as_raw_evidence(self) -> None:
        self.assertTrue(CURSOR_X0_FRAME.is_file())
        frame = CURSOR_X0_FRAME.read_text(encoding="utf-8")
        self.assertEqual(len(frame.splitlines()), 13)
        self.assertIn("Cursor Agent", frame)
        self.assertIn("v2026.08.25-3e8eec8", frame)
        self.assertIn("→ Plan, search, build anything", frame)
        self.assertIn("Run Everything", frame)

        pane = pane_facts()
        pane.update(cursor_x=0, cursor_y=13, cursor_logical_y=12)
        facts = run_platform_adapter_observer(CURSOR_ADAPTER, frame, pane)
        # Legacy advisory labels may remain for compatibility. This fixture
        # intentionally asserts only the factual input surface; the public
        # Cursor send test proves that its labels have no mutation authority.
        self.assertTrue(
            {
                "editor_state",
                "editor_fingerprint",
                "visible_shell_count",
                "visible_agent_count",
                "native_approval",
                "activity_hint",
            }.issubset(facts)
        )


class MissingHelperRedTest(unittest.TestCase):
    """Keep baseline failure explicit when the P0 helper has not landed."""

    def test_00_issue6_helper_is_required(self) -> None:
        self.assertTrue(
            HELPER_PATH.is_file(),
            f"expected Issue #6 observation helper at {HELPER_PATH}; baseline has no structured observe implementation",
        )

    def test_01_non_claude_adapters_declare_answer_unsupported(self) -> None:
        for platform in ("grok", "opencode", "kimi-cli", "cursor-cli"):
            path = PROJECT / "scripts" / "adapters" / f"{platform}.sh"
            text = path.read_text(encoding="utf-8")
            self.assertTrue(
                re.search(r"(?m)^ADAPTER_ANSWER_MODE=['\"]?unsupported['\"]?$", text) is not None,
                f"{platform} must fail closed for answer in schema v2",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
