#!/usr/bin/env python3
"""Hermetic ACP contract for the Issue #58 Droid worker platform.

Drives ``scripts/kaola-acp.py`` (the Runner ACP client, platform ``droid``)
against the fake droid agent ``tests/contract/fake-droid-acp-agent.py`` over
the real holder. No installed droid binary, login, account, or network is
used; a fixture ``droid --version`` responder keeps the shared model-policy
probe hermetic.

Asserts the live-probed droid 0.220.0 surface: config options are declared in
the session/new result (autonomy_level, model, reasoning_effort), start
applies ``model=auto`` through configId ``model`` and the bypass through
configId ``autonomy_level`` (never ``mode``), no effort is set unless
explicitly called, permission modes map onto autonomy_level values, the start
receipt carries the transport facts, and the resume path works.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
FAKE = PROJECT / "tests" / "contract" / "fake-droid-acp-agent.py"
SESSION_RE = "kaola-droid-acp"


class DroidAcpSessionFixture(unittest.TestCase):
    _tmp: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-droid-acp-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "fake-events.jsonl"
        cls.droid_shim = cls.root / "droid-fixture"
        cls.droid_shim.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ "${1:-}" == --version ]]; then printf "droid 0.220.0\\n"; exit 0; fi\n'
            "exit 0\n",
            encoding="utf-8",
        )
        cls.droid_shim.chmod(cls.droid_shim.stat().st_mode | stat.S_IXUSR)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"{SESSION_RE}-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self._started = False
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        if self._started:
            self.cli("stop", "--force", check=False, timeout=15)

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["DROID_ACP_LOG"] = str(self.mock_log)
        env["DROID_BIN"] = str(self.droid_shim)
        return env

    def mock_command(self, caps: str = "") -> str:
        parts = [sys.executable, str(FAKE)]
        if caps:
            parts += ["--caps", caps]
        return " ".join(parts)

    def cli(self, command: str, *args, check: bool = True, timeout: float = 30,
            caps: str = "", extra_env: dict[str, str] | None = None) -> dict:
        argv = [
            sys.executable, str(CLI), "droid", command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", self.mock_command(caps),
            *args,
        ]
        env = self.env()
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=timeout)
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kaola-acp droid {command} did not emit a JSON receipt\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        if check and "error" in receipt:
            self.fail(
                f"kaola-acp droid {command} returned error {receipt['error']}\n"
                f"receipt={json.dumps(receipt, sort_keys=True)}"
            )
        return receipt

    def start(self, *args, **kwargs) -> dict:
        receipt = self.cli("start", *args, **kwargs)
        self._started = True
        return receipt

    def read_fake_log(self) -> list[dict]:
        if not self.mock_log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.mock_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def config_events(self) -> list[tuple[str, str]]:
        events = []
        for event in self.read_fake_log():
            if event.get("event") != "set_config_option":
                continue
            events.append((str(event.get("configId")), str(event.get("value"))))
        return events

    def echoed_model_values(self) -> list[str]:
        """Every model ``currentValue`` the agent itself echoed.

        Issue #183: ACP 0.225.1 answers a set with an empty ``{}`` and never
        refreshes the ``session/new`` ``models`` snapshot, so the async
        ``config_option_update`` echo is the only read-back that shows what
        the session's model actually is.
        """
        values = []
        for event in self.read_fake_log():
            if event.get("event") != "config_option_update":
                continue
            for option in event.get("configOptions") or []:
                if option.get("id") == "model":
                    values.append(option.get("currentValue"))
        return values


class DroidAcpStartContractTests(DroidAcpSessionFixture):
    def test_default_start_applies_auto_model_and_autonomy_level(self) -> None:
        """Issue #117: the default preset is the first-class catalog id auto
        with no effort pin. The native currentValue is not auto, so model=auto
        is applied explicitly, never inherited."""
        receipt = self.start()
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        # model=auto through configId "model", bypass through autonomy_level,
        # never configId "mode" and no effort unless explicitly called.
        self.assertEqual(
            self.config_events(),
            [("model", "auto"), ("autonomy_level", "auto-high")],
        )
        application = receipt.get("config_application") or {}
        model = application.get("model") or {}
        self.assertTrue(model.get("applied"))
        self.assertEqual(model.get("config_id"), "model")
        self.assertEqual(model.get("value"), "auto")
        # The preset id is sent verbatim: nothing was mapped on the way out.
        self.assertIsNone(model.get("requested_id"))
        mode = application.get("mode") or {}
        self.assertTrue(mode.get("applied"))
        self.assertEqual(mode.get("config_id"), "autonomy_level")
        self.assertEqual(mode.get("value"), "auto-high")
        selection = receipt.get("model_selection") or {}
        self.assertEqual(selection.get("source"), "runner-default")
        self.assertEqual(selection.get("tier"), "default")
        self.assertEqual(selection.get("resolved_model"), "auto")
        self.assertFalse(selection.get("resolved_effort"))
        # Issue #183 (worker path): the session's model, read back from the
        # agent's OWN echo (the only read-back ACP 0.225.1 gives for a set;
        # the set result is an empty {} and the session/new models snapshot
        # is never refreshed), is the catalog Auto Model id "auto" - every
        # echo, including the one that follows the autonomy_level set.
        self.assertIn(("model", "auto"), self.config_events())
        self.assertEqual(self.echoed_model_values(), ["auto", "auto"])
        self.assertEqual((receipt.get("effective_selection") or {}).get("effective_model"), "auto")
        # Issue #185: the model verdict comes from that echo, not the
        # unreadable CLI catalog and not the frozen session/new
        # `models.currentModelId` snapshot.
        self.assertEqual(receipt.get("actual_runtime_model_id"), "auto")
        # The echoed session effort is reported as evidence; no effort was
        # pinned, so nothing is compared and the verdict is still true.
        self.assertEqual(receipt.get("actual_parameters"), {"effort": "high"})
        self.assertIs(receipt.get("model_verified"), True)
        self.assertIsNone(receipt.get("model_mismatch_reason"))
        actual = (receipt.get("model_evidence_provenance") or {}).get("actual") or {}
        self.assertEqual(actual.get("source"), "acp-config-echo")
        self.assertEqual(actual.get("model_id"), "auto")
        fast = receipt.get("fast") or {}
        self.assertEqual(fast.get("support"), "none")
        self.assertFalse(fast.get("applied"))

    def test_host_named_start_also_applies_auto_model(self) -> None:
        """Issue #183: a droid seat named as a Host takes the same preset path.

        The only session-name condition in the apply loop is the ZCode-only
        Host model pin, which changes nothing for droid, so a Host-class name
        must select the catalog Auto Model exactly like a worker name does.
        """
        self.session = "droid-KPR-orchestrator-x"
        receipt = self.start()
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        self.assertIn(("model", "auto"), self.config_events())
        self.assertEqual(self.echoed_model_values(), ["auto", "auto"])
        self.assertEqual((receipt.get("effective_selection") or {}).get("effective_model"), "auto")

    def test_auto_model_persists_across_prompts(self) -> None:
        """Issue #183: the Auto Model selection stays selected across turns.

        Probe-2 live evidence: one ``set_config_option model=auto`` followed by
        three prompts produced an ``auto`` model echo every time with zero
        reverts. ACP 0.225.1 cannot prove which model *served* a turn, so the
        observable claim under test is that the selection never reverts.
        """
        receipt = self.start()
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        for turn in range(3):
            send = self.cli("send", "--text", f"turn {turn}")
            self.assertEqual(send.get("outcome"), "turn_completed")
            self.assertEqual(send.get("stop_reason"), "end_turn")
        # Two echoes at start (model set, then autonomy_level set) + one per turn.
        self.assertEqual(self.echoed_model_values(), ["auto"] * 5)

    def test_start_receipt_carries_droid_transport_facts(self) -> None:
        receipt = self.start()
        transport = receipt.get("transport") or {}
        self.assertEqual(transport.get("selected"), "acp")
        self.assertEqual(transport.get("protocol_version"), 1)
        agent_info = transport.get("agent_info") or {}
        self.assertEqual(agent_info.get("name"), "@factory/cli")
        self.assertEqual(agent_info.get("title"), "Factory Droid")
        self.assertEqual(agent_info.get("version"), "0.220.0")
        capabilities = transport.get("capabilities") or {}
        self.assertTrue(capabilities.get("loadSession"))
        session_caps = capabilities.get("sessionCapabilities") or {}
        self.assertIn("resume", session_caps)
        self.assertIn("list", session_caps)
        self.assertEqual(receipt.get("acp_session_id"), "droid-session-1")
        self.assertEqual(receipt.get("schema_version"), 3)

    def test_preflight_reports_advertised_config_ids_and_auth(self) -> None:
        receipt = self.cli("preflight")
        ids = (receipt.get("transport") or {}).get("advertised_config_ids") or []
        self.assertEqual(ids, ["autonomy_level", "model", "reasoning_effort"])
        auth = (receipt.get("transport") or {}).get("auth_methods") or []
        self.assertEqual({entry.get("id") for entry in auth},
                         {"device-pairing", "factory-api-key"})
        options = (receipt.get("transport") or {}).get("advertised_config_options") or []
        self.assertEqual({option.get("id") for option in options},
                         {"autonomy_level", "model", "reasoning_effort"})

    def test_core_preset_effort_is_applied_exactly_once(self) -> None:
        """The core preset carries effort max: exactly that value, once.
        The default and upgrade presets carry none (Issue #125)."""
        self.start("--tier", "core")
        self.assertEqual(
            [value for config_id, value in self.config_events()
             if config_id == "reasoning_effort"],
            ["max"],
        )

    def test_explicit_model_gets_no_invented_effort(self) -> None:
        receipt = self.start("--model", "gpt-5.6-sol")
        selection = receipt.get("model_selection") or {}
        self.assertEqual(selection.get("source"), "user")
        events = self.config_events()
        self.assertIn(("model", "gpt-5.6-sol"), events)
        self.assertNotIn("reasoning_effort", [config_id for config_id, _ in events])
        # Issue #185: the explicit id is what the agent's echo confirms.
        self.assertEqual(receipt.get("actual_runtime_model_id"), "gpt-5.6-sol")
        self.assertIs(receipt.get("model_verified"), True)

    def test_a_model_the_agent_rejects_is_reported_false_not_a_gate(self) -> None:
        """Issue #185: a selection the agent never adopted is a mismatch, not a
        refusal. Droid's echoed model stays the session's real one; the start
        remains usable."""
        receipt = self.start("--model", "unavailable/droid")
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertNotEqual(receipt.get("result"), "refused")
        model = (receipt.get("config_application") or {}).get("model") or {}
        self.assertFalse(model.get("applied"))
        self.assertEqual(receipt.get("actual_runtime_model_id"), "gpt-5.6-sol")
        self.assertIs(receipt.get("model_verified"), False)
        self.assertEqual(receipt.get("model_mismatch_reason"), "actual-model-mismatch:gpt-5.6-sol")
        sent = self.cli("send", "--text", "usable")
        self.assertEqual(sent.get("outcome"), "turn_completed")

    def test_a_launch_argv_model_compares_the_echo_not_the_argv_value(self) -> None:
        """Issue #185 (B1): the verdict must read the agent's own echo, never
        the argv value the Runner itself supplied. The argv carries ``--model
        auto``, so no model option is sent and the agent keeps echoing its real
        session model ``gpt-5.6-sol``; a self-comparison would falsely verify."""
        receipt = self.start("--command", f"{self.mock_command()} --model auto")
        self.assertIsNone(receipt.get("error"), receipt)
        # The argv already selected the model: no model option was applied.
        self.assertEqual(
            [event for event in self.config_events() if event[0] != "autonomy_level"],
            [],
        )
        model = (receipt.get("config_application") or {}).get("model") or {}
        self.assertEqual(model.get("applied_via"), "argv")
        # Issue #140 keeps the display value as the argv model and the agent's
        # real echo as advertised_model; the verdict uses the echo.
        effective = receipt.get("effective_selection") or {}
        self.assertEqual(effective.get("effective_model_source"), "launch-argv")
        self.assertEqual(effective.get("effective_model"), "auto")
        self.assertEqual(effective.get("advertised_model"), "gpt-5.6-sol")
        self.assertEqual(receipt.get("actual_runtime_model_id"), "gpt-5.6-sol")
        self.assertIs(receipt.get("model_verified"), False)
        self.assertEqual(receipt.get("model_mismatch_reason"),
                         "actual-model-mismatch:gpt-5.6-sol")
        sent = self.cli("send", "--text", "usable")
        self.assertEqual(sent.get("outcome"), "turn_completed")

    def test_explicit_effort_is_set_only_when_called(self) -> None:
        self.start("--model", "gpt-5.6-sol", "--effort", "high")
        self.assertEqual(
            self.config_events(),
            [
                ("model", "gpt-5.6-sol"),
                ("reasoning_effort", "high"),
                ("autonomy_level", "auto-high"),
            ],
        )

    def test_effort_alone_pins_default_model_with_effort(self) -> None:
        """An explicit effort overrides the preset's, on the preset's model."""
        self.start("--effort", "medium")
        self.assertEqual(
            [event for event in self.config_events() if event[0] != "autonomy_level"],
            [("model", "auto"), ("reasoning_effort", "medium")],
        )

    def test_permission_mode_bypass_maps_to_auto_high_not_mode(self) -> None:
        self.start("--mode", "bypassPermissions")
        events = self.config_events()
        self.assertEqual([event for event in events if event[0] == "autonomy_level"],
                         [("autonomy_level", "auto-high")])
        self.assertNotIn("mode", [config_id for config_id, _ in events])

    def test_permission_mode_levels_map_to_autonomy_values(self) -> None:
        cases = {
            "low": "auto-low",
            "medium": "auto-medium",
            "high": "auto-high",
            "manual": "normal",
        }
        for mode, expected in cases.items():
            with self.subTest(mode=mode):
                self.cli("stop", "--force", check=False, timeout=15)
                self._started = False
                self.setUp()
                self.start("--mode", mode)
                self.assertEqual(
                    [event for event in self.config_events() if event[0] == "autonomy_level"],
                    [("autonomy_level", expected)],
                )

    def test_core_tier_applies_kimi_k3_max(self) -> None:
        """Issue #125: core (Kimi K3 Max) is the third tier, not the upgrade:
        kimi-k3 at reasoning_effort=max."""
        receipt = self.start("--tier", "core")
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        selection = receipt.get("model_selection") or {}
        self.assertEqual(selection.get("source"), "runner-core")
        self.assertEqual(selection.get("tier"), "core")
        self.assertEqual(selection.get("resolved_model"), "kimi-k3")
        self.assertEqual(selection.get("resolved_effort"), "max")
        self.assertEqual(
            self.config_events(),
            [("model", "kimi-k3"), ("reasoning_effort", "max"),
             ("autonomy_level", "auto-high")],
        )
        # Issue #185: the echoed effort is part of the verdict.
        self.assertEqual(receipt.get("actual_runtime_model_id"), "kimi-k3")
        self.assertEqual(receipt.get("actual_parameters"), {"effort": "max"})
        self.assertIs(receipt.get("model_verified"), True)

    def test_upgrade_tier_is_auto_like_default(self) -> None:
        """Issue #125: no stronger Droid tier is established, so upgrade
        resolves to the Auto default and never to kimi-k3."""
        receipt = self.start("--tier", "upgrade")
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        selection = receipt.get("model_selection") or {}
        self.assertEqual(selection.get("source"), "runner-upgrade")
        self.assertEqual(selection.get("resolved_model"), "auto")
        self.assertEqual(
            self.config_events(),
            [("model", "auto"), ("autonomy_level", "auto-high")],
        )

    def test_deleted_alternative_tier_is_refused(self) -> None:
        """Issue #117 deleted the alternative tier. The fake catalog still
        carries kimi-k2.7-code, so this refusal is tier-based, not a
        catalog-absence accident."""
        receipt = self.start("--tier", "alternative", check=False)
        self.assertEqual(receipt.get("result"), "refused")
        self.assertEqual(receipt.get("reason"), "tier-not-declared")
        self.assertEqual(receipt.get("available_tiers"), ["default", "upgrade", "core"])
        self.assertFalse(receipt.get("mutation_performed"))
        self.assertEqual(self.config_events(), [])

    def test_a_tier_droid_does_not_declare_is_refused(self) -> None:
        """Devin's word must not silently become Droid's `default`."""
        receipt = self.start("--tier", "fable", check=False)
        self.assertEqual(receipt.get("result"), "refused")
        self.assertEqual(receipt.get("reason"), "tier-not-declared")
        self.assertEqual(receipt.get("available_tiers"), ["default", "upgrade", "core"])
        self.assertFalse(receipt.get("mutation_performed"))
        self.assertEqual(self.config_events(), [])


class DroidAcpResumeTests(DroidAcpSessionFixture):
    def test_resume_path_works_and_keeps_bypass(self) -> None:
        # Resume is a single-start flow the holder drives through
        # session/resume; it never follows a live holder on the same session.
        resume_id = "858c4700-cb88-4c1a-a45c-a46c6af3e467"
        receipt = self.start("--resume", resume_id, caps="resume,list")
        self.assertIsNone(receipt.get("error"), f"resume start failed: {receipt}")
        self.assertEqual(receipt.get("acp_session_id"), resume_id)
        self.assertEqual(receipt.get("state"), "ready")
        selection = receipt.get("model_selection") or {}
        self.assertTrue(selection.get("preserved"))
        self.assertEqual(selection.get("source"), "resume-preserved")
        self.assertIsNone(selection.get("resolved_model"))
        # Issue #185: a preserved resume has no Runner target, so the echoed
        # model is reported but stays not-comparable/unknown.
        self.assertEqual(receipt.get("actual_runtime_model_id"), "gpt-5.6-sol")
        self.assertEqual(receipt.get("model_verified"), "unknown")
        self.assertEqual(receipt.get("model_mismatch_reason"),
                         "resume-preserved-actual-not-comparable")
        # No Runner model override on a preserved resume; bypass is still
        # asserted through autonomy_level.
        events = self.config_events()
        self.assertNotIn("model", [config_id for config_id, _ in events])
        self.assertEqual(
            [event for event in events if event[0] == "autonomy_level"],
            [("autonomy_level", "auto-high")],
        )
        self.assertIn("session_resume", [event.get("event") for event in self.read_fake_log()])
        send = self.cli("send", "--text", "resume ping", extra_env={"DROID_ACP_LOG": str(self.mock_log)})
        self.assertEqual(send.get("outcome"), "turn_completed")
        self.assertEqual(send.get("stop_reason"), "end_turn")
        self.assertIn("pong", send.get("final_text") or "")


if __name__ == "__main__":
    unittest.main()
