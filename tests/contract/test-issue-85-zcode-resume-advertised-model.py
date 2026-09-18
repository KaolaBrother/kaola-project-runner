#!/usr/bin/env python3
"""Issue #85 - a failed-closed native `sess_*` resume must not advertise the
rejected model.

Hermetic, ACP only. Same Issue #79 harness and 3.12 fake as
`test-issue-84-zcode-native-resume.py` (same fixture provider, same fixture
credential, same env derivation, same cleanup), so this file adds only the
advertisement assertions.

Measured on `fef74d15afcdef3c3bd165abbc121ab3805141e1` (Issue #84 candidate,
merged at `8d7d00a`): when a native resume fails closed because the persisted
model is outside the enabled Coding Plan, `hydrate_settings()` has already
emitted `session/update` `{sessionUpdate: config_option_update}` whose model
`currentValue` names that rejected model before `reregister_provider()` raises
and the session is dropped. The client briefly sees an advertised option for a
model that was refused and never took effect.

Acceptance:

  * on every resume that fails closed, the ACP stream carries no
    `config_option_update` for the dropped session -- nothing is advertised
    for a session that never becomes usable, so no rejected model value can
    ever be named;
  * the fail-closed semantics are unchanged: the load reports an error, the
    backend sees no `session/setModel` at all, and no plan model is
    substituted (fresh 3.12+ path and pre-3.12 overlay path alike);
  * a resume that succeeds still advertises exactly one
    `config_option_update`, naming the established account-qualified model --
    the fix orders the emission after the selection is established, it does
    not delete it.

The legacy fake cannot persist a foreign model through the public resume
call (it stores the adapter's own plan overlay or the plan default), so the
pre-3.12 path is guarded at `read_fails`: a legacy resume that fails closed
emits no `config_option_update` and reaches no `session/setModel` either.
The ordering fix lives in the shared `_resume_backend_session`, so the same
assertion covers both protocol generations by construction.

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
FIXTURE_SECRET = I79.FIXTURE_SECRET
PLAN_MODELS = ("GLM-5.3", "GLM-5.3-Flash")

# The native id an Agent hands back to `session/load` to resume.
NATIVE_ID = "sess_312_persisted"


class ResumeCase(I79.TempCase):
    """One native resume per test; collects the updates the client saw."""

    def resume(self, scenario: str, modern: bool = True):
        drv = self.driver(modern=modern, scenario=scenario,
                          expect_key=FIXTURE_SECRET)
        drv.request(1, "initialize", {"protocolVersion": 1, "clientCapabilities": {}})
        self.assertIsNotNone(drv.wait_result(1), "initialize returned nothing")
        drv.request(2, "session/load", {"sessionId": NATIVE_ID, "cwd": str(drv.cwd)})
        loaded = drv.wait_result(2)
        self.assertIsNotNone(loaded, "session/load returned nothing")
        return drv, loaded

    def config_updates(self, drv, acp_id: str = NATIVE_ID) -> list[dict]:
        """Every `config_option_update` the client received for the session,
        in wire order."""
        updates = []
        for msg in drv.messages:
            if msg.get("method") != "session/update":
                continue
            params = msg.get("params") or {}
            if params.get("sessionId") != acp_id:
                continue
            update = params.get("update") or {}
            if update.get("sessionUpdate") == "config_option_update":
                updates.append(update)
        return updates

    def advertised_model_value(self, update: dict) -> str | None:
        for option in update.get("configOptions") or []:
            if option.get("id") == "model":
                return option.get("currentValue")
        return None

    def assert_fails_closed_silently(self, drv, loaded, rejected: str) -> None:
        """A resume that fails closed advertises nothing for the dropped
        session -- so no rejected model value can ever be named -- and the
        backend still sees no selection of any kind."""
        self.assertIn(
            "error", loaded,
            "expected a fail-closed refusal, got " + json.dumps(loaded))
        message = (loaded.get("error") or {}).get("message") or ""
        self.assertNotIn(FIXTURE_SECRET, message)
        updates = self.config_updates(drv)
        self.assertEqual(
            updates, [],
            "a dropped session still advertised config options "
            f"(rejected value {rejected!r} reached the client): "
            + json.dumps(updates))
        self.assertNotIn(
            rejected, json.dumps(updates),
            "the rejected model was advertised: " + json.dumps(updates))
        attempts = drv.record().get("set_model_attempts") or []
        self.assertEqual(
            attempts, [],
            "unusable persisted metadata still reached session/setModel: "
            + json.dumps(attempts))
        self.assertNotIn(
            "session/setModel", drv.record().get("calls") or [],
            "the backend saw a selection for a resume that fails closed: "
            + json.dumps(drv.record().get("calls") or []))


class TestFailedClosedResumeAdvertisesNothing(ResumeCase):
    def test_foreign_model_advertises_no_rejected_model(self):
        """The measured case: persisted `account:*\\GLM-9-not-in-plan` is
        refused, and must never be advertised first."""
        drv, loaded = self.resume("resume_foreign_model")
        self.assert_fails_closed_silently(
            drv, loaded, f"{ACCOUNT_ID}\\GLM-9-not-in-plan")

    def test_foreign_provider_advertises_no_rejected_model(self):
        """A persisted model on another account is refused and must not be
        advertised either."""
        drv, loaded = self.resume("resume_foreign_provider")
        self.assert_fails_closed_silently(
            drv, loaded, "account:someone-else\\GLM-5.3")

    def test_absent_model_metadata_advertises_nothing(self):
        """With nothing persisted there is no rejected model value, but the
        dropped session must still not emit a config advertisement."""
        drv, loaded = self.resume("resume_no_metadata")
        self.assert_fails_closed_silently(drv, loaded, "\\")

    def test_malformed_model_metadata_advertises_nothing(self):
        drv, loaded = self.resume("resume_malformed")
        self.assert_fails_closed_silently(drv, loaded, "\\")


class TestSuccessfulResumeStillAdvertises(ResumeCase):
    def test_established_selection_is_advertised_once(self):
        """The fix moves the emission behind the established selection; it
        does not remove it. A faithful resume still ends with exactly one
        `config_option_update` naming the model the backend accepted."""
        drv, loaded = self.resume("resume_nested")
        self.assertNotIn(
            "error", loaded,
            "native resume failed: " + json.dumps(loaded.get("error") or {}))
        updates = self.config_updates(drv)
        self.assertEqual(
            len(updates), 1,
            "the resumed session did not advertise its established "
            "selection exactly once: " + json.dumps(updates))
        value = self.advertised_model_value(updates[0])
        self.assertEqual(
            value, f"{ACCOUNT_ID}\\GLM-5.3-Flash",
            "the advertised model is not the established selection: "
            + json.dumps(updates[0]))


class TestLegacyPathFailsClosedSilently(ResumeCase):
    def test_legacy_resume_failure_advertises_nothing(self):
        """Pre-3.12 path (`read_fails`): the legacy fake cannot persist a
        foreign model, but a resume that still fails closed must emit no
        `config_option_update` and reach no `session/setModel`."""
        drv, loaded = self.resume("read_fails", modern=False)
        self.assert_fails_closed_silently(drv, loaded, "\\")


class TestNoSecretLeakOnAdvertisementPath(ResumeCase):
    def test_rejected_resume_never_leaks_the_credential(self):
        drv, loaded = self.resume("resume_foreign_model")
        self.assertIn("error", loaded)
        self.assertNotIn(FIXTURE_SECRET, drv.stdout_text())
        self.assertNotIn(FIXTURE_SECRET, drv.stderr_text())


if __name__ == "__main__":
    unittest.main(verbosity=1)
