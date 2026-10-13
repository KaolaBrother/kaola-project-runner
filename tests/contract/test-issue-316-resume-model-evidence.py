#!/usr/bin/env python3
"""Issue #316: a resume names an omitted tier, and status reads the actual model.

Resume with ``--tier`` applies that preset. Resume without ``--tier`` keeps the
saved selection and records ``tier_reason: resume-without-tier``. After a turn,
``status`` sets ``model_verified`` from a recorded session update, or from the
Claude session JSONL when that stream has none. A platform with neither stays
``actual-model-evidence-not-yet-read``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
CONTRACT = Path(__file__).resolve().parent
RESUME_ENV = {"MOCK_ACP_RESUME_ANY": "1"}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


def namespace(**overrides):
    values = {
        "platform": "codex",
        "manifest": {
            "default_model_name": "GPT-6.1 Sol",
            "default_model_id": "gpt-6.1-sol",
            "default_model_effort": "high",
            "named_tiers": "astra",
            "astra_model_name": "GPT-6 Astra",
            "astra_model_id": "gpt-6-astra",
            "astra_model_effort": "high",
        },
        "model": None,
        "effort": None,
        "tier": None,
        "resume": None,
        "use_continue": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def selection_evidence(**overrides) -> dict:
    selection = {
        "source": "runner-default",
        "tier": "default",
        "resolved_model": "opus",
        "resolved_effort": "high",
        "override_omitted": False,
        "preserved": False,
    }
    selection.update(overrides)
    return {
        "model_selection": selection,
        "model_verified": "unknown",
        "model_mismatch_reason": "actual-model-evidence-not-yet-read",
        "actual_runtime_model_id": None,
        "actual_parameters": None,
        "acp_session_id": "mock-session-1",
        "model_evidence_provenance": {"requested": {"source": selection["source"]}},
    }


def event_line(update: dict, cursor: int = 1) -> str:
    return json.dumps({
        "cursor": cursor, "ts": 1, "kind": "session_update", "update": update,
    }) + "\n"


class ResumeTierAndVerdict(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acp = load(SCRIPTS / "kaola-acp.py", "kaola_acp_issue_316")

    def test_preserve_records_a_null_tier_and_a_tier_still_applies(self) -> None:
        bare = self.acp.selection_basis(namespace(resume="saved-1"))
        self.assertEqual(bare["source"], "resume-preserved")
        self.assertIsNone(bare["tier"])
        self.assertEqual(bare["candidate"], "")
        tiered = self.acp.selection_basis(namespace(resume="saved-1", tier="astra"))
        self.assertEqual(tiered["source"], "runner-astra")
        self.assertEqual(tiered["tier"], "astra")
        self.assertEqual(tiered["candidate"], "gpt-6-astra")
        receipt: dict = {}
        self.acp.merge_policy_evidence(receipt, {
            "requested_model_source": "resume-preserved",
            "requested_tier": None,
            "requested_model_name": "native saved session selection",
            "resolved_runtime_model_id": "",
            "resolved_parameters": {},
        })
        selection = receipt["model_selection"]
        self.assertIsNone(selection["tier"])
        self.assertEqual(selection["tier_reason"], "resume-without-tier")
        self.assertIs(selection["override_omitted"], True)
        self.assertIs(selection["preserved"], False)

    def test_alias_is_not_the_transcript_id_and_a_preserved_resume_is_not_comparable(self) -> None:
        mismatch = self.acp.session_model_verdict(
            selection_evidence(), "claude-opus-5-5", {"effort": "high"})
        self.assertIs(mismatch["model_verified"], False)
        self.assertEqual(mismatch["model_mismatch_reason"], "actual-model-mismatch:claude-opus-5-5")
        self.assertEqual(mismatch["actual_parameters"], {"effort": "high"})
        matched = self.acp.session_model_verdict(
            selection_evidence(resolved_model="claude-opus-5-5"),
            "claude-opus-5-5", {"effort": "high"})
        self.assertIs(matched["model_verified"], True)
        self.assertIsNone(matched["model_mismatch_reason"])
        missing_effort = self.acp.session_model_verdict(
            selection_evidence(resolved_model="claude-opus-5-5"),
            "claude-opus-5-5", {})
        self.assertEqual(missing_effort["model_verified"], "unknown")
        self.assertEqual(missing_effort["model_mismatch_reason"], "actual-effort-evidence-unreadable")
        preserved = self.acp.session_model_verdict(
            selection_evidence(
                source="resume-preserved", tier=None, resolved_model=None,
                resolved_effort=None, override_omitted=True,
            ),
            "claude-opus-5-5", {"effort": "high"})
        self.assertEqual(preserved["model_verified"], "unknown")
        self.assertEqual(
            preserved["model_mismatch_reason"], "resume-preserved-actual-not-comparable")
        self.assertEqual(preserved["actual_runtime_model_id"], "claude-opus-5-5")

    def test_transcript_tail_skips_synthetic_and_rejects_a_path_id(self) -> None:
        acp = self.acp
        self.assertIsNone(acp.claude_transcript_path("/repo", "../etc/passwd"))
        self.assertIsNone(acp.claude_transcript_path("/repo", "a..b"))
        self.assertIsNone(acp.claude_transcript_path("/repo", "a/b"))
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = "/Users/example/project"
            slug = acp.claude_project_slug(repo)
            directory = root / "projects" / slug
            directory.mkdir(parents=True)
            path = directory / "sess-1.jsonl"
            path.write_text(
                "\n".join([
                    json.dumps({"type": "assistant", "message": {"model": "<synthetic>"}, "effort": "low"}),
                    json.dumps({
                        "type": "assistant",
                        "message": {"model": "claude-opus-5-5", "content": "SECRET-PROMPT-TEXT"},
                        "effort": "high",
                    }),
                    json.dumps({"type": "user", "message": {"content": "SECRET-PROMPT-TEXT"}}),
                ]) + "\n",
                encoding="utf-8",
            )
            loaded = acp.claude_transcript_model(path)
            self.assertEqual(loaded["id"], "claude-opus-5-5")
            self.assertEqual(loaded["parameters"], {"effort": "high"})
            self.assertNotIn("SECRET-PROMPT-TEXT", json.dumps(loaded))
            huge = root / "huge.jsonl"
            huge.write_bytes(b"x" * 50 + b"\nSECOND\n")
            self.assertEqual(acp._tail_text(huge, 10), "SECOND\n")
            only_synthetic = directory / "empty-model.jsonl"
            only_synthetic.write_text(
                json.dumps({"type": "assistant", "message": {"model": "<synthetic>"}}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(acp.claude_transcript_model(only_synthetic)["id"], "")

    def test_recorded_update_wins_and_a_missing_file_stays_unread(self) -> None:
        acp = self.acp
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            events = root / "events.jsonl"
            events.write_text(event_line({
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "SECRET-PROMPT-TEXT"},
                "_meta": {"runtime_model": {"id": "from-update", "effort": "high"}},
            }), encoding="utf-8")
            original = selection_evidence()
            snapshot = json.dumps(original, sort_keys=True)
            receipt = {"start_evidence": original, "acp_session_id": "mock-session-1"}
            acp.annotate_session_model_evidence(receipt, "claude-code", "/Users/example/project", root)
            self.assertEqual(json.dumps(original, sort_keys=True), snapshot)
            self.assertIs(receipt["model_verified"], False)
            self.assertEqual(receipt["actual_runtime_model_id"], "from-update")
            self.assertEqual(
                receipt["start_evidence"]["model_evidence_provenance"]["actual"]["source"],
                "acp-session-update",
            )
            self.assertNotIn("SECRET-PROMPT-TEXT", json.dumps(receipt))
            # No session model: a Droid echo stands, and a Claude miss stays unread.
            echo = selection_evidence(resolved_model="auto", resolved_effort=None)
            echo["model_verified"] = True
            echo["model_mismatch_reason"] = None
            echo["actual_runtime_model_id"] = "auto"
            echo["actual_parameters"] = {}
            echo["model_evidence_provenance"] = {
                "actual": {"source": "acp-config-echo", "model_id": "auto", "parameters": {}},
            }
            quiet = root / "quiet"
            quiet.mkdir()
            (quiet / "events.jsonl").write_text(event_line({
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "no model here"},
            }), encoding="utf-8")
            droid = {"start_evidence": echo}
            acp.annotate_session_model_evidence(droid, "droid", "/Users/example/project", quiet)
            self.assertIs(droid["start_evidence"]["model_verified"], True)
            self.assertNotIn("model_verified", droid)
            self.assertEqual(
                droid["start_evidence"]["model_evidence_provenance"]["actual"]["source"],
                "acp-config-echo",
            )
            unread = {"start_evidence": selection_evidence()}
            previous = os.environ.get("CLAUDE_CONFIG_DIR")
            os.environ["CLAUDE_CONFIG_DIR"] = str(root / "missing-claude")
            try:
                acp.annotate_session_model_evidence(
                    unread, "claude-code", "/Users/example/project", quiet)
            finally:
                if previous is None:
                    os.environ.pop("CLAUDE_CONFIG_DIR", None)
                else:
                    os.environ["CLAUDE_CONFIG_DIR"] = previous
            self.assertEqual(
                unread["start_evidence"]["model_mismatch_reason"],
                "actual-model-evidence-not-yet-read",
            )
            self.assertNotIn("model_verified", unread)

    def test_native_session_file_beats_the_acp_id_and_a_newer_event_wins(self) -> None:
        acp = self.acp
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "claude"
            repo = "/Users/example/project"
            native = "f96a6591-8262-40b5-a63f-599fedbb6991"
            slug = acp.claude_project_slug(repo)
            projects = config / "projects" / slug
            projects.mkdir(parents=True)
            (projects / f"{native}.jsonl").write_text(
                json.dumps({
                    "type": "assistant",
                    "message": {"model": "claude-opus-5-5"},
                    "effort": "high",
                }) + "\n",
                encoding="utf-8",
            )
            (projects / "mock-session-1.jsonl").write_text(
                json.dumps({
                    "type": "assistant",
                    "message": {"model": "decoy-model"},
                    "effort": "low",
                }) + "\n",
                encoding="utf-8",
            )
            (root / "events.jsonl").write_text(event_line({
                "sessionUpdate": "native_session_identity",
                "nativeSessionId": native,
            }), encoding="utf-8")
            previous = os.environ.get("CLAUDE_CONFIG_DIR")
            os.environ["CLAUDE_CONFIG_DIR"] = str(config)
            try:
                receipt = {"start_evidence": selection_evidence(), "acp_session_id": "mock-session-1"}
                acp.annotate_session_model_evidence(receipt, "claude-code", repo, root)
            finally:
                if previous is None:
                    os.environ.pop("CLAUDE_CONFIG_DIR", None)
                else:
                    os.environ["CLAUDE_CONFIG_DIR"] = previous
            self.assertEqual(receipt["actual_runtime_model_id"], "claude-opus-5-5")
            self.assertEqual(
                receipt["start_evidence"]["model_evidence_provenance"]["actual"]["source"],
                "claude-session-jsonl",
            )
            self.assertIs(receipt["model_verified"], False)
            rotated = root / "rotated"
            rotated.mkdir()
            (rotated / "events.jsonl.1").write_text(event_line({
                "sessionUpdate": "agent_message_chunk",
                "_meta": {"runtime_model": {"id": "older-model", "effort": "low"}},
            }, cursor=1), encoding="utf-8")
            (rotated / "events.jsonl").write_text(event_line({
                "sessionUpdate": "agent_message_chunk",
                "_meta": {"runtime_model": {"id": "newer-model", "effort": "high"}},
            }, cursor=2), encoding="utf-8")
            again = {"start_evidence": selection_evidence(resolved_model="newer-model")}
            acp.annotate_session_model_evidence(again, "grok", repo, rotated)
            self.assertEqual(again["actual_runtime_model_id"], "newer-model")
            self.assertIs(again["model_verified"], True)
            self.assertEqual(again["actual_parameters"], {"effort": "high"})

    def test_a_read_transcript_with_no_model_is_unreadable(self) -> None:
        acp = self.acp
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "claude"
            repo = "/Users/example/project"
            projects = config / "projects" / acp.claude_project_slug(repo)
            projects.mkdir(parents=True)
            (projects / "mock-session-1.jsonl").write_text(
                json.dumps({"type": "assistant", "message": {"model": "<synthetic>"}}) + "\n",
                encoding="utf-8",
            )
            previous = os.environ.get("CLAUDE_CONFIG_DIR")
            os.environ["CLAUDE_CONFIG_DIR"] = str(config)
            try:
                receipt = {"start_evidence": selection_evidence()}
                acp.annotate_session_model_evidence(receipt, "claude-code", repo, root)
            finally:
                if previous is None:
                    os.environ.pop("CLAUDE_CONFIG_DIR", None)
                else:
                    os.environ["CLAUDE_CONFIG_DIR"] = previous
            self.assertEqual(receipt["model_verified"], "unknown")
            self.assertEqual(receipt["model_mismatch_reason"], "actual-model-evidence-unreadable")
            self.assertIsNone(receipt["actual_runtime_model_id"])
            self.assertEqual(
                receipt["start_evidence"]["model_evidence_provenance"]["actual"]["source"],
                "claude-session-jsonl",
            )


_ACP = load(CONTRACT / "test-acp-contract.py", "acp_contract_i316")


class ResumeModelEvidenceLive(_ACP.AcpSessionFixture, unittest.TestCase):
    """Mock-agent sessions. ``CLAUDE_CONFIG_DIR`` is a temp dir, never ~/.claude."""

    cli = _ACP.Issue34ModelSelectionAcpTests.cli
    start = _ACP.Issue34ModelSelectionAcpTests.start
    config_events = _ACP.Issue34ModelSelectionAcpTests.config_events

    def setUp(self) -> None:
        super().setUp()
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def env(self) -> dict[str, str]:
        env = super().env()
        env["CODEX_BIN"] = str(self.root / "no-such-codex")
        env["CLAUDE_CONFIG_DIR"] = str(self.root / "claude-config")
        return env

    def saved_record(self, platform: str) -> dict:
        found = list((self.record_root / platform / self.session).glob("*/record.json"))
        self.assertEqual(len(found), 1, found)
        return json.loads(found[0].read_text(encoding="utf-8"))

    def write_transcript(self, repo: str, session_id: str, rows: list[dict]) -> None:
        slug = self.acp_module.claude_project_slug(repo)
        directory = self.root / "claude-config" / "projects" / slug
        directory.mkdir(parents=True, exist_ok=True)
        payload = "".join(json.dumps(row) + "\n" for row in rows)
        (directory / f"{session_id}.jsonl").write_text(payload, encoding="utf-8")

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.acp_module = load(SCRIPTS / "kaola-acp.py", "kaola_acp_issue_316_live")

    def test_resume_with_tier_applies_it_and_records_no_omission_reason(self) -> None:
        receipt = self.start(
            "codex", "--resume", "saved-codex-316", "--tier", "astra",
            caps="resume", extra_env=RESUME_ENV,
        )
        self.assertEqual(receipt["model_selection"]["source"], "runner-astra")
        self.assertEqual(receipt["model_selection"]["resolved_model"], "gpt-6-astra")
        self.assertNotIn("tier_reason", receipt["model_selection"])
        self.assertIs(receipt["model_selection"]["override_omitted"], False)
        self.assertIn(("model", "gpt-6-astra"), self.config_events())
        self.assertEqual(receipt["model_verified"], "unknown")
        self.assertEqual(receipt["model_mismatch_reason"], "actual-model-evidence-not-yet-read")
        status = self.cli("status", platform="codex")
        self.assertEqual(status["start_selection"]["tier"], "astra")
        self.assertNotIn("tier_reason", status["start_selection"])

    def test_resume_without_tier_records_the_reason_and_preserves_selection(self) -> None:
        receipt = self.start(
            "codex", "--resume", "saved-codex-316", caps="resume", extra_env=RESUME_ENV,
        )
        selection = receipt["model_selection"]
        self.assertEqual(selection["source"], "resume-preserved")
        self.assertIsNone(selection["tier"])
        self.assertEqual(selection["tier_reason"], "resume-without-tier")
        self.assertIs(selection["override_omitted"], True)
        self.assertIs(selection["preserved"], False)
        self.assertIsNone(selection["resolved_model"])
        sent = [config_id for config_id, _value in self.config_events()]
        self.assertNotIn("model", sent)
        self.assertNotIn("reasoning_effort", sent)
        status = self.cli("status", platform="codex")
        self.assertIsNone(status["start_selection"]["tier"])
        self.assertIsNone(status["start_selection"]["model"])
        self.assertIsNone(status["start_selection"]["effort"])
        self.assertEqual(status["start_selection"]["tier_reason"], "resume-without-tier")
        self.assertEqual(
            status["start_evidence"]["model_selection"]["tier_reason"], "resume-without-tier")
        self.assertNotIn("model_verified", status)

    def test_a_turn_with_a_recorded_runtime_model_verifies_it(self) -> None:
        receipt = self.start("codex", scenario="runtime_model")
        self.assertEqual(receipt["resolved_runtime_model_id"], "gpt-6.1-sol")
        self.assertEqual(receipt["model_verified"], "unknown")
        self.assertEqual(receipt["model_mismatch_reason"], "actual-model-evidence-not-yet-read")
        sent = self.cli("send", "--text", "ping", platform="codex", scenario="runtime_model")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        status = self.cli("status", platform="codex", scenario="runtime_model")
        self.assertIs(status["model_verified"], True)
        self.assertIsNone(status["model_mismatch_reason"])
        self.assertEqual(status["actual_runtime_model_id"], "gpt-6.1-sol")
        self.assertEqual(status["actual_parameters"], {"effort": "high"})
        evidence = status["start_evidence"]
        self.assertIs(evidence["model_verified"], True)
        self.assertEqual(evidence["actual_runtime_model_id"], "gpt-6.1-sol")
        self.assertEqual(
            evidence["model_evidence_provenance"]["actual"]["source"], "acp-session-update")
        observed = self.cli("observe", platform="codex", scenario="runtime_model")
        self.assertIs(observed["model_verified"], True)
        self.assertEqual(observed["actual_runtime_model_id"], "gpt-6.1-sol")
        # The holder file stays the start snapshot.
        self.assertEqual(
            self.saved_record("codex")["start_evidence"]["model_mismatch_reason"],
            "actual-model-evidence-not-yet-read",
        )

    def test_resume_without_tier_reports_the_actual_model_as_not_comparable(self) -> None:
        self.start(
            "codex", "--resume", "saved-codex-316", caps="resume",
            scenario="runtime_model", extra_env=RESUME_ENV,
        )
        sent = self.cli("send", "--text", "ping", platform="codex", scenario="runtime_model")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        status = self.cli("status", platform="codex", scenario="runtime_model")
        self.assertEqual(status["model_verified"], "unknown")
        self.assertEqual(status["model_mismatch_reason"], "resume-preserved-actual-not-comparable")
        self.assertEqual(status["actual_runtime_model_id"], "gpt-6.1-sol")
        self.assertEqual(status["actual_parameters"], {"effort": "high"})
        self.assertNotEqual(status["model_mismatch_reason"], "actual-model-evidence-not-yet-read")
        self.assertEqual(status["start_selection"]["tier_reason"], "resume-without-tier")

    def test_grok_without_session_evidence_stays_unknown(self) -> None:
        receipt = self.start("grok")
        self.assertEqual(receipt["model_verified"], "unknown")
        sent = self.cli("send", "--text", "ping", platform="grok")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        status = self.cli("status", platform="grok")
        self.assertNotIn("model_verified", status)
        evidence = status["start_evidence"]
        self.assertEqual(evidence["model_verified"], "unknown")
        self.assertEqual(evidence["model_mismatch_reason"], "actual-model-evidence-not-yet-read")
        self.assertIsNone(evidence["actual_runtime_model_id"])

    def test_claude_jsonl_is_read_when_the_update_stream_has_no_model(self) -> None:
        receipt = self.start("claude-code")
        self.assertEqual(receipt["model_selection"]["resolved_model"], "opus")
        self.assertEqual(receipt["model_verified"], "unknown")
        sent = self.cli("send", "--text", "ping", platform="claude-code")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        record = self.saved_record("claude-code")
        self.write_transcript(record["repo"], record["acp_session_id"], [
            {"type": "assistant", "message": {"model": "<synthetic>"}, "effort": "low",
             "content": "SECRET-PROMPT-TEXT"},
            {"type": "assistant", "message": {"model": "claude-opus-5-5",
                                              "content": "SECRET-PROMPT-TEXT"},
             "effort": "high"},
        ])
        status = self.cli("status", platform="claude-code")
        self.assertIs(status["model_verified"], False)
        self.assertEqual(status["model_mismatch_reason"], "actual-model-mismatch:claude-opus-5-5")
        self.assertEqual(status["actual_runtime_model_id"], "claude-opus-5-5")
        self.assertEqual(status["actual_parameters"], {"effort": "high"})
        self.assertEqual(
            status["start_evidence"]["model_evidence_provenance"]["actual"]["source"],
            "claude-session-jsonl",
        )
        self.assertNotIn("SECRET-PROMPT-TEXT", json.dumps(status))
        self.assertEqual(
            self.saved_record("claude-code")["start_evidence"]["model_mismatch_reason"],
            "actual-model-evidence-not-yet-read",
        )
        self.write_transcript(record["repo"], record["acp_session_id"], [
            {"type": "assistant", "message": {"model": "opus"}, "effort": "high"},
        ])
        matched = self.cli("status", platform="claude-code")
        self.assertIs(matched["model_verified"], True)
        self.assertIsNone(matched["model_mismatch_reason"])
        self.assertEqual(matched["actual_runtime_model_id"], "opus")

    def test_a_recorded_update_beats_the_claude_jsonl(self) -> None:
        receipt = self.start(
            "claude-code", scenario="runtime_model",
            extra_env={"MOCK_ACP_RUNTIME_MODEL": json.dumps({"id": "from-update", "effort": "high"})},
        )
        self.assertEqual(receipt["model_verified"], "unknown")
        sent = self.cli("send", "--text", "ping", platform="claude-code", scenario="runtime_model")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        record = self.saved_record("claude-code")
        self.write_transcript(record["repo"], record["acp_session_id"], [
            {"type": "assistant", "message": {"model": "claude-opus-5-5"}, "effort": "high"},
        ])
        status = self.cli("status", platform="claude-code", scenario="runtime_model")
        self.assertEqual(status["actual_runtime_model_id"], "from-update")
        self.assertEqual(
            status["start_evidence"]["model_evidence_provenance"]["actual"]["source"],
            "acp-session-update",
        )
        self.assertIs(status["model_verified"], False)

    def test_claude_resume_without_tier_reads_the_existing_transcript(self) -> None:
        native = "f96a6591-8262-40b5-a63f-599fedbb6991"
        receipt = self.start(
            "claude-code", "--resume", native, caps="resume", extra_env=RESUME_ENV,
        )
        self.assertEqual(receipt["model_selection"]["tier_reason"], "resume-without-tier")
        self.assertIsNone(receipt["model_selection"]["resolved_model"])
        self.assertEqual(receipt["model_verified"], "unknown")
        self.assertEqual(receipt["model_mismatch_reason"], "actual-model-evidence-not-yet-read")
        sent_ids = [config_id for config_id, _value in self.config_events()]
        self.assertNotIn("model", sent_ids)
        self.assertNotIn("effort", sent_ids)
        before = self.cli("status", platform="claude-code")
        self.assertEqual(
            before["start_evidence"]["model_mismatch_reason"],
            "actual-model-evidence-not-yet-read",
        )
        self.assertNotIn("model_verified", before)
        record = self.saved_record("claude-code")
        self.assertEqual(record["acp_session_id"], native)
        self.write_transcript(record["repo"], native, [
            {"type": "assistant", "message": {"model": "claude-opus-5-5"}, "effort": "high"},
        ])
        status = self.cli("status", platform="claude-code")
        self.assertEqual(status["model_verified"], "unknown")
        self.assertEqual(status["model_mismatch_reason"], "resume-preserved-actual-not-comparable")
        self.assertEqual(status["actual_runtime_model_id"], "claude-opus-5-5")
        self.assertEqual(status["actual_parameters"], {"effort": "high"})
        self.assertEqual(status["start_selection"]["tier_reason"], "resume-without-tier")
        self.assertIsNone(status["start_selection"]["tier"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
