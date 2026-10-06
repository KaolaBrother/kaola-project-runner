#!/usr/bin/env python3
"""Issue #254: OpenCode applies opencode-go/deepseek-v4.1-flash after it is advertised.

Measured on OpenCode 2.0.22: session/new lists only opencode/*, and an immediate
session/set_config_option of opencode-go/deepseek-v4.1-flash returns JSON-RPC
-32602 model not found. A later config_option_update advertises that id, and
the same set then applies it. Start waits for the advertisement. It does not
substitute another model.

dsh's --version catalog probe is a separate reporting gap: catalog-missing
from that probe is not evidence the model is absent.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
CLI = SCRIPTS / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
TARGET = "opencode-go/deepseek-v4.1-flash"
INITIAL_CURRENT = "opencode/fledge-alpha-free"


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def model_option(current: str, values: list[str]) -> dict[str, Any]:
    return {
        "id": "model",
        "name": "Model",
        "category": "model",
        "type": "select",
        "currentValue": current,
        "options": [{"name": value, "value": value} for value in values],
    }


class OpenCodeModelAdvertisement(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i254-")
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.record_root = self.root / "records"
        self.mock_log = self.root / "mock-events.jsonl"
        stub = self.root / "opencode"
        stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        self.stub = stub
        self.session = f"opencode-i254-{self._testMethodName}"[:79]
        self._started = False

    def tearDown(self) -> None:
        if self._started:
            self.cli("stop", "--force", check=False, timeout=15)
        self._tmp.cleanup()

    def env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items() if not key.startswith("KAOLA_") or (key == "KAOLA_LAUNCH_BACKEND" and value == "direct")}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        env["OPENCODE_BIN"] = str(self.stub)
        if extra:
            env.update(extra)
        return env

    def cli(self, command: str, *args: str, check: bool = True,
            timeout: float = 30, extra_env: dict[str, str] | None = None) -> dict[str, Any]:
        argv = [
            sys.executable, str(CLI), "opencode", command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", f"{sys.executable} {MOCK}",
            *args,
        ]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(extra_env), timeout=timeout,
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kaola-acp {command} did not emit JSON\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        if check and receipt.get("error"):
            self.fail(f"kaola-acp {command} error {receipt['error']}")
        if check and receipt.get("result") == "refused":
            self.fail(f"kaola-acp {command} refused: {receipt.get('reason')}: {receipt.get('detail')}")
        return receipt

    def log(self) -> list[dict[str, Any]]:
        if not self.mock_log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.mock_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_start_sets_the_model_only_after_it_is_advertised(self) -> None:
        initial = [model_option(INITIAL_CURRENT, [INITIAL_CURRENT])]
        ready = [model_option(INITIAL_CURRENT, [INITIAL_CURRENT, TARGET])]
        fixture = {
            "new": initial,
            "defer_model": {
                "value": TARGET,
                "delay_ms": 400,
                "provider_id": "opencode-go",
                "ready": ready,
            },
        }
        receipt = self.cli(
            "start", timeout=30,
            extra_env={"MOCK_ACP_CONFIG": json.dumps(fixture)},
        )
        self._started = True
        model = (receipt.get("config_application") or {}).get("model") or {}
        self.assertTrue(model.get("applied"), model)
        self.assertEqual(model.get("value"), TARGET)
        self.assertEqual(
            (receipt.get("effective_selection") or {}).get("effective_model"),
            TARGET,
        )
        events = self.log()
        advertised = next(i for i, event in enumerate(events) if event.get("event") == "model_advertised")
        model_sets = [
            i for i, event in enumerate(events)
            if event.get("event") == "set_config_option"
            and (event.get("params") or {}).get("configId") == "model"
        ]
        self.assertTrue(model_sets, events)
        self.assertGreater(model_sets[0], advertised)
        self.assertEqual(
            (events[model_sets[-1]].get("params") or {}).get("value"),
            TARGET,
        )

    def test_a_model_that_is_never_advertised_is_not_replaced(self) -> None:
        initial = [model_option(INITIAL_CURRENT, [INITIAL_CURRENT])]
        fixture = {
            "new": initial,
            "defer_model": {
                "value": TARGET,
                "delay_ms": 60000,
                "provider_id": "opencode-go",
                "ready": [model_option(INITIAL_CURRENT, [INITIAL_CURRENT, TARGET])],
            },
        }
        receipt = self.cli(
            "start", timeout=30,
            extra_env={"MOCK_ACP_CONFIG": json.dumps(fixture)},
        )
        self._started = True
        model = (receipt.get("config_application") or {}).get("model") or {}
        self.assertFalse(model.get("applied"), model)
        self.assertEqual(model.get("value"), TARGET)
        self.assertEqual(model.get("error", {}).get("code"), "config-option-failed")
        detail = (model.get("error") or {}).get("detail") or {}
        self.assertEqual(detail.get("code"), -32602)
        self.assertIn(TARGET, str(detail.get("message")))
        self.assertEqual(
            (receipt.get("effective_selection") or {}).get("effective_model"),
            INITIAL_CURRENT,
        )
        self.assertNotEqual(receipt.get("result"), "refused")


class DshCatalogProbeGap(unittest.TestCase):
    def test_validate_sh_runs_this_suite(self) -> None:
        text = (PROJECT / "scripts" / "validate.sh").read_text(encoding="utf-8")
        self.assertEqual(text.count("test-issue-254-opencode-model.py"), 2)
    def test_version_probe_keeps_the_candidate_and_records_the_gap(self) -> None:
        policy = load("kaola-model-policy")
        with tempfile.TemporaryDirectory(prefix="kaola-i254-dsh-") as raw:
            root = Path(raw)
            stub = root / "dsh"
            stub.write_text(
                "#!/bin/sh\nprintf '%s\\n' 'dsh 0.2.0-rc.2' 'opencode/fledge-alpha-free'\n",
                encoding="utf-8",
            )
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            repo = root / "repo"
            repo.mkdir()
            args = argparse.Namespace(
                platform="dsh",
                runtime_bin=str(stub),
                repo=str(repo),
                source="runner-default",
                requested_name="DeepSeek V4.1 Flash",
                candidate_id=TARGET,
                effort="",
                fast="false",
                tier="default",
                fast_mechanism="none",
                fast_suffixes="-fast,-priority",
            )
            resolved = policy.resolve(args)
        provenance = resolved["model_evidence_provenance"]
        self.assertEqual(resolved["resolved_runtime_model_id"], TARGET)
        self.assertEqual(
            provenance["resolution"]["state"],
            "catalog-missing-declared-candidate",
        )
        self.assertFalse(provenance["catalog_probe"]["candidate_present"])
        self.assertEqual(
            provenance["catalog_probe"]["reporting_gap"],
            "version-probe-does-not-list-acp-models",
        )
        self.assertEqual(provenance["catalog_probe"]["probes"][0]["command"][1:], ["--version"])

    def test_opencode_catalog_probe_is_not_labeled_with_the_dsh_gap(self) -> None:
        policy = load("kaola-model-policy")
        with tempfile.TemporaryDirectory(prefix="kaola-i254-oc-probe-") as raw:
            root = Path(raw)
            stub = root / "opencode"
            stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            repo = root / "repo"
            repo.mkdir()
            args = argparse.Namespace(
                platform="opencode",
                runtime_bin=str(stub),
                repo=str(repo),
                source="runner-default",
                requested_name="DeepSeek V4.1 Flash",
                candidate_id=TARGET,
                effort="",
                fast="false",
                tier="default",
                fast_mechanism="none",
                fast_suffixes="-fast,-priority",
            )
            resolved = policy.resolve(args)
        probe = resolved["model_evidence_provenance"]["catalog_probe"]
        self.assertNotIn("reporting_gap", probe)


if __name__ == "__main__":
    unittest.main()
