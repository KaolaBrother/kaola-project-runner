#!/usr/bin/env python3
"""Issue #84 - native `sess_*` resume must keep the session's Coding Plan model.

Hermetic, ACP only. Drives `scripts/kaola-zcode-acp.py` against
`fake-zcode-312-app-server.py` through the Issue #79 harness (same fixture
provider, same fixture credential, same env derivation, same cleanup), so this
file adds resume coverage without a parallel harness.

What the acceptance surface says a correct resume does, on a 3.12+ backend:

  * recover the persisted model from the shapes the real 3.12.3 app-server
    actually returns -- `session/read` with a message list whose model lives at
    `messages[i].info.model = {providerId, modelId}` and NO top-level
    `settings`, and the sibling `session/messages` with the same list in flat
    `info.modelId` / `info.providerId` keys;
  * when messages disagree, take the NEWEST one carrying model metadata,
    ordered by the timestamp the payload carries (`info.time.created`), not by
    array position;
  * fail closed with no substitution when that metadata is absent, malformed,
    or names a provider/model the enabled plan does not offer -- never a silent
    fall back to a default model and never a different account;
  * register the Coding Plan with the resumed backend's provider registry
    (`provider/updateAccountConfig`) BEFORE the resume-time `session/setModel`,
    because a resumed app-server starts with an empty registry;
  * send that `session/setModel` in the 3.12 shape -- no top-level
    `runtimeModel` key, which 3.12.3 rejects outright with a ZodError;
  * keep the plan credential out of every ACP byte and every log byte.

No installed ZCode, no login, no network and no real credential: the only
"secret" is the fixture value inside `tests/contract/fixtures/`.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
I79_PATH = PROJECT / "tests" / "contract" / "test-issue-79-zcode-312.py"


def _load_i79():
    spec = importlib.util.spec_from_file_location("kaola_i79_harness", I79_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The Issue #79 harness: Driver, TempCase, fixture constants. Imported as a
# module object on purpose, so unittest does not re-collect the #79 cases here.
I79 = _load_i79()

ACCOUNT_ID = I79.ACCOUNT_ID
CODING_PLAN_ID = I79.CODING_PLAN_ID
FIXTURE_SECRET = I79.FIXTURE_SECRET
PLAN_MODELS = ("GLM-5.3", "GLM-5.3-Flash")
REASONING_LEVELS = ("low", "high", "max")

# The native id an Agent hands back to `session/load` to resume.
NATIVE_ID = "sess_312_persisted"


class ResumeCase(I79.TempCase):
    """One native resume per test, on a 3.12+ backend."""

    def resume(self, scenario: str):
        """Handshake, then `session/load` the native id. Returns the driver and
        the ACP result for the load (which may carry an error)."""
        drv = self.driver(modern=True, scenario=scenario, expect_key=FIXTURE_SECRET)
        drv.request(1, "initialize", {"protocolVersion": 1, "clientCapabilities": {}})
        self.assertIsNotNone(drv.wait_result(1), "initialize returned nothing")
        drv.request(2, "session/load", {"sessionId": NATIVE_ID, "cwd": str(drv.cwd)})
        loaded = drv.wait_result(2)
        self.assertIsNotNone(loaded, "session/load returned nothing")
        return drv, loaded

    def resume_ok(self, scenario: str):
        drv, loaded = self.resume(scenario)
        self.assertNotIn(
            "error", loaded,
            "native resume failed: " + json.dumps(loaded.get("error") or {}))
        return drv, loaded

    def resume_set_model(self, drv) -> dict:
        """The `session/setModel` the backend saw for the resumed session."""
        sent = drv.record().get("resume_set_model")
        self.assertIsInstance(
            sent, dict,
            "the resumed session never reached session/setModel; the backend saw "
            + json.dumps(drv.record().get("calls") or []))
        return sent

    def assert_selected(self, drv, model_id: str) -> dict:
        sent = self.resume_set_model(drv)
        model = sent.get("model") or {}
        self.assertEqual(model.get("providerId"), ACCOUNT_ID)
        self.assertEqual(model.get("modelId"), model_id)
        # 3.12+ refuses an account selection with no explicit reasoning level.
        self.assertIn((model.get("options") or {}).get("reasoningLevel"),
                      REASONING_LEVELS)
        # A Runner turn never edits the user's workspace defaults.
        self.assertIs(sent.get("persistAsWorkspaceLastUsed"), False)
        return sent

    def assert_no_substitution(self, drv, loaded) -> None:
        """A refused resume must not quietly land on some other model."""
        self.assertIn(
            "error", loaded,
            "expected a fail-closed refusal, got " + json.dumps(loaded))
        message = (loaded.get("error") or {}).get("message") or ""
        self.assertNotIn(FIXTURE_SECRET, message)
        for attempt in drv.record().get("set_model_attempts") or []:
            model = (attempt.get("model") or {})
            self.assertNotIn(
                model.get("modelId"), PLAN_MODELS,
                "a plan model was substituted for unusable persisted metadata: "
                + json.dumps(attempt))


class TestPersistedModelRecovery(ResumeCase):
    def test_recovers_persisted_model_from_session_read_message_list(self):
        """Real 3.12.3 `session/read` has no top-level `settings`: the model is
        at `messages[i].info.model`."""
        drv, _ = self.resume_ok("resume_nested")
        self.assert_selected(drv, "GLM-5.3-Flash")

    def test_recovers_persisted_model_from_session_messages_flat_shape(self):
        """The sibling method returns the same list with flat
        `info.modelId` / `info.providerId` keys."""
        drv, _ = self.resume_ok("resume_flat")
        self.assert_selected(drv, "GLM-5.3-Flash")

    def test_newest_message_with_model_metadata_wins(self):
        """The fixture orders the transcript so array position is a wrong
        answer: the first and last model-bearing entries both say GLM-5.3, and
        only `info.time.created` identifies GLM-5.3-Flash as the newest."""
        drv, loaded = self.resume_ok("resume_ordered")
        self.assert_selected(drv, "GLM-5.3-Flash")
        options = {o["id"]: o for o in (loaded.get("result") or {}).get("configOptions", [])}
        self.assertTrue(
            str(options.get("model", {}).get("currentValue") or "")
            .endswith("\\GLM-5.3-Flash"),
            "the resumed session does not report the persisted model: "
            + json.dumps(options.get("model")))

    def test_resumed_session_completes_a_turn_on_the_persisted_model(self):
        """End to end: the recovered selection is real enough for the backend
        to run a turn on it."""
        drv, _ = self.resume_ok("resume_nested")
        res = drv.prompt(NATIVE_ID, rid=30, text="again")
        self.assertIsNotNone(res, "prompt after resume returned nothing")
        self.assertEqual((res.get("result") or {}).get("stopReason"), "end_turn",
                         json.dumps(res))
        self.assertTrue(drv.record().get("headers_answer_ok"),
                        f"headers rejected: {drv.record().get('headers_problem')}")


class TestResumeWireShape(ResumeCase):
    def test_resume_set_model_carries_no_runtime_model_key(self):
        """3.12.3 rejects a top-level `runtimeModel` on `session/setModel`
        with a ZodError; the resume path must use the same shape the working
        fresh-session path already uses."""
        drv, _ = self.resume_ok("resume_nested")
        sent = self.resume_set_model(drv)
        self.assertNotIn("runtimeModel", sent)
        self.assertEqual(sorted(sent.get("model") or {}),
                         ["modelId", "options", "providerId"])
        # The resume call itself is strict too.
        self.assertNotIn("runtimeModel", drv.record().get("resume_params") or {})

    def test_resume_registers_the_provider_before_selecting_the_model(self):
        """A resumed app-server starts with an empty provider registry, so the
        Coding Plan must be pushed before the resume-time selection or the
        backend refuses it."""
        drv, _ = self.resume_ok("resume_nested")
        calls = drv.record().get("calls") or []
        self.assertIn("provider/updateAccountConfig", calls,
                      "the resume path never registered the Coding Plan: "
                      + json.dumps(calls))
        self.assertIn("session/setModel", calls, json.dumps(calls))
        self.assertLess(calls.index("provider/updateAccountConfig"),
                        calls.index("session/setModel"),
                        "the provider was registered after the selection: "
                        + json.dumps(calls))
        # The registry the backend actually held when the resume arrived was
        # empty; only the push can have filled it.
        self.assertEqual(drv.record().get("catalog_at_resume"), {})
        self.assertIn(ACCOUNT_ID, drv.record().get("catalog") or {})


class TestFreshSessionPathUnchanged(ResumeCase):
    """The #84 transcript derivation is for resume. A freshly created session
    already knows its own selection from the `session/setModel` the backend
    accepted, and must not go looking for it in the transcript."""

    def fresh_turn(self, drv):
        msg = drv.new_session()
        self.assertIsNotNone(msg, "session/new returned nothing")
        self.assertNotIn("error", msg, f"session/new failed: {msg}")
        res = drv.prompt(msg["result"]["sessionId"])
        self.assertIsNotNone(res, "fresh prompt returned nothing")
        return res

    def test_fresh_session_does_not_read_the_transcript_for_its_model(self):
        drv = self.driver(modern=True, expect_key=FIXTURE_SECRET)
        res = self.fresh_turn(drv)
        self.assertEqual((res.get("result") or {}).get("stopReason"), "end_turn",
                         json.dumps(res))
        calls = drv.record().get("calls") or []
        self.assertNotIn(
            "session/messages", calls,
            "a fresh session went looking for its own model in the transcript: "
            + json.dumps(calls))

    def test_fresh_session_reports_the_account_qualified_model(self):
        """`select_account_model` records the provider it just had accepted, so
        the advertised option names the account the turn actually runs on."""
        drv = self.driver(modern=True, expect_key=FIXTURE_SECRET)
        self.fresh_turn(drv)
        sent = (drv.record().get("set_model_attempts") or [])
        self.assertTrue(sent, "the fresh session never selected a model")
        chosen = (sent[-1].get("model") or {})
        self.assertEqual(chosen.get("providerId"), ACCOUNT_ID)


class TestResumeFailureIsReported(ResumeCase):
    def test_unknown_session_reports_its_own_reason_not_a_schema_error(self):
        """A 3.12+ backend has no `runtimeModel` channel, so the resume path
        must not retry with that key after an ordinary failure: doing so
        replaces the real reason (the session is unknown or already deleted)
        with a ZodError about a key this build never accepts. Measured on real
        3.12.3, where the masked receipt read `Unrecognized key: "runtimeModel"`
        for a session that simply did not exist."""
        drv = self.driver(modern=True, scenario="resume_unknown",
                          expect_key=FIXTURE_SECRET)
        drv.request(1, "initialize", {"protocolVersion": 1, "clientCapabilities": {}})
        self.assertIsNotNone(drv.wait_result(1), "initialize returned nothing")
        drv.request(2, "session/load", {"sessionId": NATIVE_ID, "cwd": str(drv.cwd)})
        loaded = drv.wait_result(2)
        self.assertIsNotNone(loaded, "session/load returned nothing")
        self.assertIn("error", loaded, "an unknown session must fail")
        message = json.dumps(loaded.get("error") or {})
        self.assertNotIn("runtimeModel", message,
                         "the real resume failure was masked by the pre-3.12 "
                         "overlay retry: " + message)
        self.assertIn("not found", message,
                      "the receipt does not name the real reason: " + message)
        resumes = [c for c in (drv.record().get("calls") or [])
                   if c == "session/resume"]
        self.assertEqual(len(resumes), 1,
                         "a 3.12+ backend must not be retried with the overlay: "
                         + json.dumps(drv.record().get("calls") or []))


class TestResumeFailsClosed(ResumeCase):
    def test_absent_model_metadata_fails_closed(self):
        drv, loaded = self.resume("resume_no_metadata")
        self.assert_no_substitution(drv, loaded)

    def test_malformed_model_metadata_fails_closed(self):
        drv, loaded = self.resume("resume_malformed")
        self.assert_no_substitution(drv, loaded)

    def test_model_outside_the_plan_fails_closed(self):
        drv, loaded = self.resume("resume_foreign_model")
        self.assert_no_substitution(drv, loaded)

    def test_foreign_provider_does_not_switch_accounts(self):
        drv, loaded = self.resume("resume_foreign_provider")
        self.assert_no_substitution(drv, loaded)
        for attempt in drv.record().get("set_model_attempts") or []:
            self.assertNotEqual(
                (attempt.get("model") or {}).get("providerId"), ACCOUNT_ID,
                "the enabled account was substituted for a foreign one: "
                + json.dumps(attempt))

    def test_a_refused_resume_leaves_no_half_registered_session(self):
        """A later prompt must not silently create a fresh session under the
        native id the load refused."""
        drv, loaded = self.resume("resume_no_metadata")
        self.assert_no_substitution(drv, loaded)
        res = drv.prompt(NATIVE_ID, rid=31, text="again")
        self.assertIsNotNone(res, "prompt after a refused resume returned nothing")
        self.assertIn("error", res,
                      "a refused resume still served a turn: " + json.dumps(res))


class TestResumeSecrecy(ResumeCase):
    def test_credential_never_appears_in_acp_or_logs_on_resume(self):
        drv, _ = self.resume_ok("resume_nested")
        drv.prompt(NATIVE_ID, rid=32, text="again")
        self.assertNotIn(FIXTURE_SECRET, drv.stdout_text())
        self.assertNotIn(FIXTURE_SECRET, drv.stderr_text())
        self.assertNotIn(FIXTURE_SECRET, json.dumps(drv.record()))

    def test_credential_never_appears_when_resume_fails_closed(self):
        drv, loaded = self.resume("resume_foreign_provider")
        self.assertIn("error", loaded)
        self.assertNotIn(FIXTURE_SECRET, drv.stdout_text())
        self.assertNotIn(FIXTURE_SECRET, drv.stderr_text())


if __name__ == "__main__":
    unittest.main(verbosity=1)
