#!/usr/bin/env python3
"""Issue #245: additive session_role on holder, list/status/view, and dispatch.

Expert is exercised with the manifest fixture and the mock ACP agent only.
No Expert preset is granted to dispatch.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
HOLDER = PROJECT / "scripts" / "kaola-acp-holder.py"
DISPATCH = PROJECT / "scripts" / "kaola-dispatch.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
PLATFORMS = PROJECT / "platforms"
ROLES = ("host", "sidekick", "expert", "elite", "worker")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def prompt_sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


class SessionRoleDerivation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acp = load_module("acp245_derive", CLI)

    def namespace(self, platform: str, session: str, **flags):
        return argparse.Namespace(
            platform=platform,
            session=session,
            manifest=flags.get("manifest") or self.acp.load_manifest(platform),
            model=flags.get("model"),
            effort=flags.get("effort"),
            tier=flags.get("tier"),
            resume=flags.get("resume"),
            use_continue=flags.get("use_continue", False),
            role=flags.get("role"),
        )

    def role(self, ns, prior=None, repo="/repo", acp_id=None):
        basis = self.acp.selection_basis(ns)
        return self.acp.session_role_value(ns, basis, prior, repo, acp_id)

    def test_five_roles_and_the_null_cases(self) -> None:
        self.assertEqual(self.acp.SESSION_ROLES, frozenset(ROLES))
        host = self.namespace("grok", "grok-KPR-orchestrator-main", role="sidekick")
        self.assertEqual(self.role(host), "host")
        self.assertTrue(self.acp.host_session("grok", host.session))

        sidekick = self.namespace("grok", "grok-i245-draft", role="sidekick")
        self.assertEqual(self.role(sidekick), "sidekick")

        expert = self.namespace("codex", "codex-i245-think", tier="astra")
        self.assertEqual(self.role(expert), "expert")
        elite = self.namespace("grok", "grok-i245-work")
        self.assertEqual(self.role(elite), "elite")
        worker = self.namespace("codex", "codex-i245-luna", tier="luna")
        self.assertEqual(self.role(worker), "worker")

        custom = self.namespace("codex", "elite-worker-expert", model="gpt-6-luna")
        self.assertIsNone(self.role(custom))
        spelled = self.namespace("grok", "worker-elite-expert-host", model="grok-4.7")
        self.assertIsNone(self.role(spelled))
        self.assertFalse(self.acp.host_session("grok", spelled.session))

        unknown = self.namespace(
            "grok", "grok-i245-odd",
            manifest={
                "id": "grok",
                "named_tiers": "odd",
                "odd_model_class": "Guru",
                "odd_model_name": "Odd",
                "odd_model_id": "odd-1",
                "default_model_class": "Elite",
            },
            tier="odd",
        )
        self.assertIsNone(self.role(unknown))

    def test_resume_inherits_only_the_same_native_session(self) -> None:
        ns = self.namespace("codex", "codex-i245-resume", resume="native-1")
        prior = {
            "platform": "codex",
            "repo": "/repo",
            "session": "codex-i245-resume",
            "acp_session_id": "native-1",
            "session_role": "expert",
            "holder_instance_id": "holder-prior",
            "start_evidence": {
                "acp_session_id": "native-1",
                "model_selection": {"source": "runner-astra"},
            },
        }
        self.assertEqual(self.role(ns, prior, "/repo", "native-1"), "expert")
        self.assertIsNone(self.role(ns, prior, "/repo", "native-other"))
        self.assertIsNone(self.role(ns, prior, "/repo", None))
        missing = dict(prior)
        missing["session_role"] = None
        self.assertIsNone(self.role(ns, missing, "/repo", "native-1"))
        custom = self.namespace(
            "codex", "codex-i245-resume", resume="native-1", model="gpt-6-luna",
        )
        self.assertIsNone(self.role(custom, prior, "/repo", "native-1"))


def live_table() -> dict[int, tuple[str, str]]:
    table = subprocess.run(
        ["ps", "-axo", "pid=,state=,command="], capture_output=True, text=True,
    )
    found: dict[int, tuple[str, str]] = {}
    for line in table.stdout.splitlines():
        fields = line.split(None, 2)
        if len(fields) == 3 and fields[0].isdigit():
            found[int(fields[0])] = (fields[1].upper(), fields[2])
    return found


class SessionRoleWire(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i245-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "mock.jsonl"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.started: list[tuple[str, str]] = []

    def tearDown(self) -> None:
        for platform, session in self.started:
            self.invoke(platform, "stop", "--force", session=session, check=False, timeout=20)
        self.started.clear()

    def env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items() if not key.startswith("KAOLA_")}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        env["CODEX_BIN"] = str(self.root / "no-such-codex")
        if extra:
            env.update(extra)
        return env

    def mock_command(self, caps: str = "") -> str:
        parts = [sys.executable, str(MOCK), "--scenario", "normal"]
        if caps:
            parts += ["--caps", caps]
        return " ".join(parts)

    def invoke(self, platform: str, command: str, *args: str, session: str,
               check: bool = True, timeout: float = 30,
               extra_env: dict[str, str] | None = None, caps: str = "") -> dict:
        argv = [
            sys.executable, str(CLI), platform, command,
            "--repo", str(self.repo), "--session", session,
            "--command", self.mock_command(caps), *args,
        ]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(extra_env), timeout=timeout,
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command} rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")
        if check and receipt.get("error"):
            self.fail(f"{command} error {receipt['error']}")
        if check and receipt.get("result") == "refused":
            self.fail(f"{command} refused {receipt.get('reason')}: {receipt.get('detail')}")
        return receipt

    def start(self, platform: str, session: str, *args: str, **kwargs) -> dict:
        if platform == "codex":
            kwargs.setdefault("caps", "resume")
        receipt = self.invoke(platform, "start", *args, session=session, **kwargs)
        self.started.append((platform, session))
        return receipt

    def rows(self, *args: str) -> list[dict]:
        result = subprocess.run(
            [sys.executable, str(CLI), "list", "--repo", str(self.repo), *args],
            capture_output=True, text=True, env=self.env(), timeout=30,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload.get("schema"), "kaola-acp-list/1")
        return payload["rows"]

    def row(self, session: str, *args: str) -> dict:
        found = [item for item in self.rows(*args) if item["session"] == session]
        self.assertEqual(len(found), 1, self.rows(*args))
        return found[0]

    def record(self, platform: str, session: str) -> dict:
        found = list((self.record_root / platform / session).glob("*/record.json"))
        self.assertEqual(len(found), 1, found)
        return json.loads(found[0].read_text(encoding="utf-8"))

    def test_holder_rejects_an_unknown_session_role(self) -> None:
        result = subprocess.run(
            [
                sys.executable, str(HOLDER),
                "--repo", str(self.repo), "--platform", "grok", "--session", "s",
                "--command", "true", "--session-role", "guru",
            ],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("invalid --session-role", result.stderr)
        refused = subprocess.run(
            [
                sys.executable, str(CLI), "grok", "start",
                "--repo", str(self.repo), "--session", "grok-i245-flag",
                "--role", "worker",
            ],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(refused.returncode, 2, refused.stderr)
        self.assertIn("invalid choice", refused.stderr)

    def test_preset_class_and_sidekick_persist_across_stop(self) -> None:
        cases = (
            ("grok", "grok-i245-elite", ("--tier", "default"), "elite"),
            ("grok", "grok-i245-side", ("--role", "sidekick"), "sidekick"),
            ("codex", "codex-i245-luna", ("--tier", "luna"), "worker"),
            ("codex", "codex-i245-astra", ("--tier", "astra"), "expert"),
            ("codex", "codex-i245-custom", ("--model", "gpt-6-luna"), None),
        )
        for platform, session, flags, expected in cases:
            with self.subTest(session=session):
                started = self.start(platform, session, *flags)
                self.assertEqual(started.get("session_role"), expected, started)
                self.assertIsNone(started.get("error"))
                for command in ("status", "observe", "view"):
                    receipt = self.invoke(platform, command, session=session)
                    self.assertEqual(receipt.get("session_role"), expected, (command, receipt))
                listed = self.row(session)
                self.assertIs(listed["host_class"], False)
                self.assertEqual(listed["session_role"], expected)
                saved = self.record(platform, session)
                self.assertEqual(saved.get("session_role"), expected)
                self.assertEqual((saved.get("start_selection") or {}).get("session_role"), expected)
                self.invoke(platform, "stop", "--force", session=session)
                self.started.remove((platform, session))
                stopped = self.invoke(platform, "status", session=session, check=False)
                self.assertEqual(stopped.get("session_role"), expected, stopped)

    def test_host_name_stays_host_even_with_sidekick_flag(self) -> None:
        session = "grok-KPR-orchestrator-main"
        started = self.start("grok", session, "--role", "sidekick")
        self.assertEqual(started.get("session_role"), "host", started)
        listed = self.row(session)
        self.assertIs(listed["host_class"], True)
        self.assertEqual(listed["session_role"], "host")
        self.assertEqual(self.invoke("grok", "view", session=session).get("session_role"), "host")

    def test_resume_keeps_or_drops_the_role_with_native_identity(self) -> None:
        session = "codex-i245-resume"
        first = self.start("codex", session, "--tier", "astra")
        native = first["acp_session_id"]
        self.assertEqual(first.get("session_role"), "expert")
        self.invoke("codex", "stop", "--force", session=session)
        self.started.remove(("codex", session))
        resumed = self.start(
            "codex", session, "--resume", native,
            extra_env={"MOCK_ACP_RESUME_ANY": "1"},
        )
        self.assertEqual(resumed.get("session_role"), "expert", resumed)
        self.assertEqual(self.record("codex", session).get("session_role"), "expert")
        self.invoke("codex", "stop", "--force", session=session)
        self.started.remove(("codex", session))
        overridden = self.start(
            "codex", session, "--resume", native, "--model", "gpt-6.1-sol",
            extra_env={"MOCK_ACP_RESUME_ANY": "1"},
        )
        self.assertIsNone(overridden.get("session_role"), overridden)
        self.invoke("codex", "stop", "--force", session=session)
        self.started.remove(("codex", session))
        other = self.start(
            "codex", session, "--resume", "native-started-elsewhere",
            extra_env={"MOCK_ACP_RESUME_ANY": "1"},
        )
        self.assertIsNone(other.get("session_role"), other)

    def test_legacy_list_rows_fall_back_without_relabeling(self) -> None:
        repo = os.path.realpath(str(self.repo))
        digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
        child = subprocess.Popen(["true"])
        child.wait()
        dead = child.pid

        def write(platform: str, session: str, **extra) -> None:
            path = self.record_root / platform / session / digest / "record.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "transport": "acp", "platform": platform, "session": session,
                "repo": repo, "holder_pid": dead, "state": "stopped",
                "agent_alive": False, "pending_permissions": [], "event_cursor": 0,
                "holder_instance_id": "b" * 32,
            }
            record.update(extra)
            path.write_text(json.dumps(record), encoding="utf-8")

        write("grok", "grok-KPR-orchestrator-legacy")
        write("grok", "grok-KPR-orchestrator-stale", session_role="worker")
        write("grok", "grok-i245-legacy")
        write("grok", "grok-i245-known", session_role="elite")
        write("grok", "grok-i245-junk", session_role="guru")
        rows = {item["session"]: item for item in self.rows("--include-dead")}
        self.assertEqual(rows["grok-KPR-orchestrator-legacy"]["session_role"], "host")
        self.assertIs(rows["grok-KPR-orchestrator-legacy"]["host_class"], True)
        self.assertEqual(rows["grok-KPR-orchestrator-stale"]["session_role"], "host")
        self.assertIsNone(rows["grok-i245-legacy"]["session_role"])
        self.assertEqual(rows["grok-i245-known"]["session_role"], "elite")
        self.assertIsNone(rows["grok-i245-junk"]["session_role"])
        self.assertIs(rows["grok-i245-known"]["host_class"], False)


FAKE_RUNNER = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    spec = json.loads(Path(os.environ["FAKE_SPEC"]).read_text())
    argv = sys.argv[1:]
    command = argv[0]
    session = argv[argv.index("--session") + 1]
    log = Path(os.environ["FAKE_LOG"])
    row = spec["sessions"][session]
    with log.open("a") as handle:
        handle.write(json.dumps({"command": command, "session": session, "argv": argv}) + "\\n")
    print(json.dumps(row[command]))
    """
)


def install_fake(root: Path, platforms: list[str]) -> None:
    for platform in platforms:
        dest = root / f"{platform}-kaola-project-runner" / "scripts"
        dest.mkdir(parents=True, exist_ok=True)
        script = dest / "runtime-tmux.sh"
        script.write_text(FAKE_RUNNER, encoding="utf-8")
        script.chmod(0o755)


class SessionRoleDispatch(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "consumer"
        self.repo.mkdir()
        self.skills = self.root / "skills"
        self.log = self.root / "runner.log"
        self.env = os.environ.copy()
        self.env["FAKE_LOG"] = str(self.log)
        self.spec_path = self.root / "spec.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, payload: dict) -> Path:
        path = self.root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def dispatch(self, args: list[str]) -> dict:
        result = subprocess.run(
            [sys.executable, str(DISPATCH), *args],
            capture_output=True, text=True, env=self.env,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"stdout was not JSON ({exc}): {result.stdout}\n{result.stderr}")
        self.assertEqual(result.returncode, 0, payload)
        return payload

    def execute(self, plan: dict, auth: dict, live: dict | None = None,
                prior: dict | None = None) -> dict:
        plan_path = self.write("plan.json", plan)
        auth_path = self.write("auth.json", auth)
        args = [
            "execute", "--plan", str(plan_path), "--authorization", str(auth_path),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
            "--availability", str(self.write("avail.json", {
                "present": [item["preset"] for item in plan["items"]],
                "absent": [],
            })),
        ]
        if live is not None:
            args.extend(["--live", str(self.write("live.json", live))])
        if prior is not None:
            args.extend(["--prior-index", str(self.write("prior.json", prior))])
        return self.dispatch(args)

    def commands(self) -> list[dict]:
        if not self.log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_forged_roles_are_not_run_and_sidekick_reaches_argv(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        self.spec_path.write_text(json.dumps({"sessions": {
            "codex-KPR-i245-ok": {
                "status": {"error": {"code": "no-session"}},
                "start": {"repo": repo, "holder_instance_id": "holder-ok",
                          "config_application": {"model": {"applied": True, "value": "gpt-6-luna"}}},
                "send": {"outcome": "in_progress", "mutation_status": "in_progress",
                         "prompt_fingerprint": "fp-ok"},
            },
        }}), encoding="utf-8")
        self.env["FAKE_SPEC"] = str(self.spec_path)
        auth = {
            "grants": [{"id": "codex/luna", "state": "granted"}],
            "classes": {"Expert": "e", "Elite": "l", "Worker": "w"},
        }
        plan = {
            "scope": "research",
            "repo": repo,
            "items": [
                {"item_id": "expert", "preset": "codex/luna", "session": "codex-KPR-i245-ex",
                 "prompt": "a", "role": "expert"},
                {"item_id": "worker", "preset": "codex/luna", "session": "codex-KPR-i245-wk",
                 "prompt": "b", "role": "worker"},
                {"item_id": "cased", "preset": "codex/luna", "session": "codex-KPR-i245-cs",
                 "prompt": "c", "role": "Sidekick"},
                {"item_id": "ok", "preset": "codex/luna", "session": "codex-KPR-i245-ok",
                 "prompt": "d", "role": "sidekick"},
            ],
        }
        payload = self.execute(plan, auth, live={"rows": []})
        by_id = {item["item_id"]: item for item in payload["items"]}
        for item_id in ("expert", "worker", "cased"):
            self.assertEqual(by_id[item_id]["status"], "not-run", by_id[item_id])
            self.assertEqual(by_id[item_id]["reason"], "role-unproven")
            self.assertEqual(by_id[item_id]["role"], plan["items"][
                ["expert", "worker", "cased", "ok"].index(item_id)
            ]["role"])
        self.assertEqual(by_id["ok"]["status"], "in-flight")
        self.assertEqual(by_id["ok"]["role"], "sidekick")
        started = [row for row in self.commands() if row["command"] == "start"]
        self.assertEqual([row["session"] for row in started], ["codex-KPR-i245-ok"])
        self.assertEqual(started[0]["argv"][started[0]["argv"].index("--role") + 1], "sidekick")

    def test_sidekick_does_not_change_class_capacity(self) -> None:
        install_fake(self.skills, ["claude-code"])
        repo = str(self.repo)
        self.spec_path.write_text(json.dumps({"sessions": {
            "claude-code-KPR-i245-new": {
                "status": {"error": {"code": "no-session"}},
                "start": {"repo": repo, "holder_instance_id": "holder-new",
                          "config_application": {"model": {"applied": True, "value": "opus"}}},
                "send": {"outcome": "in_progress", "mutation_status": "in_progress",
                         "prompt_fingerprint": "fp-new"},
            },
        }}), encoding="utf-8")
        self.env["FAKE_SPEC"] = str(self.spec_path)
        auth = {
            "grants": [{"id": "claude-code/opus-xhigh", "state": "granted"}],
            "classes": {"Expert": "e", "Elite": "l", "Worker": "w"},
            "elite_cap": 1,
        }
        item = {
            "item_id": "opus", "preset": "claude-code/opus-xhigh",
            "session": "claude-code-KPR-i245-new", "prompt": "implement",
        }
        blocked = self.execute(
            {"scope": "research", "repo": repo, "items": [item]},
            auth,
            live={"rows": [{
                "preset": "claude-code/opus-xhigh", "platform": "claude-code",
                "repo": repo, "state": "ready", "session_role": "sidekick",
                "host_class": False,
            }]},
        )
        self.assertEqual(blocked["items"][0]["reason"], "seat-cap")
        self.log.write_text("", encoding="utf-8")
        admitted = self.execute(
            {"scope": "research", "repo": repo, "items": [item]},
            auth,
            live={"rows": [{
                "preset": "codex/luna", "platform": "codex", "repo": repo,
                "state": "ready", "session_role": "sidekick", "host_class": False,
            }]},
        )
        self.assertEqual(admitted["items"][0]["status"], "in-flight", admitted["items"][0])
        self.assertEqual(admitted["items"][0]["reason"], "admitted")

    def test_recovery_does_not_hot_change_role(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        prompt = "keep this draft"
        finger = prompt_sha(prompt)
        self.spec_path.write_text(json.dumps({"sessions": {
            "codex-KPR-i245-keep": {
                "status": {
                    "repo": repo, "holder_instance_id": "holder-keep",
                    "mutation_status": "in_progress", "prompt_fingerprint": finger,
                    "session_role": "worker",
                },
                "start": {"repo": repo, "holder_instance_id": "should-not"},
                "send": {"outcome": "in_progress", "mutation_status": "in_progress"},
            },
            "codex-KPR-i245-same": {
                "status": {
                    "repo": repo, "holder_instance_id": "holder-same",
                    "mutation_status": "in_progress", "prompt_fingerprint": finger,
                    "session_role": "sidekick",
                },
                "start": {"repo": repo, "holder_instance_id": "should-not"},
                "send": {"outcome": "in_progress", "mutation_status": "in_progress"},
            },
        }}), encoding="utf-8")
        self.env["FAKE_SPEC"] = str(self.spec_path)

        def prior_item(item_id: str, session: str, holder: str) -> dict:
            return {
                "item_id": item_id, "preset": "codex/luna", "session": session,
                "repo": repo, "status": "in-flight", "reason": "admitted",
                "prompt_sha256": finger, "prompt_fingerprint": finger,
                "holder_instance_id": holder, "role": "sidekick",
            }

        payload = self.execute(
            {
                "scope": "research", "repo": repo,
                "items": [
                    {"item_id": "keep", "preset": "codex/luna", "session": "codex-KPR-i245-keep",
                     "prompt": prompt, "role": "sidekick"},
                    {"item_id": "same", "preset": "codex/luna", "session": "codex-KPR-i245-same",
                     "prompt": prompt, "role": "sidekick"},
                ],
            },
            {
                "grants": [{"id": "codex/luna", "state": "granted"}],
                "classes": {"Expert": "e", "Elite": "l", "Worker": "w"},
            },
            live={"rows": []},
            prior={
                "items": [
                    prior_item("keep", "codex-KPR-i245-keep", "holder-keep"),
                    prior_item("same", "codex-KPR-i245-same", "holder-same"),
                ],
            },
        )
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["keep"]["status"], "in-flight")
        self.assertEqual(by_id["keep"]["reason"], "already-admitted")
        self.assertEqual(by_id["keep"]["role"], "sidekick")
        self.assertIn("worker", by_id["keep"]["evidence"]["role_note"])
        self.assertIn("not applied", by_id["keep"]["evidence"]["role_note"])
        self.assertEqual(by_id["same"]["reason"], "already-admitted")
        self.assertNotIn("role_note", by_id["same"]["evidence"])
        commands = self.commands()
        self.assertEqual({row["command"] for row in commands}, {"status"})
        self.assertFalse(any("--role" in row["argv"] for row in commands))


class SessionRoleAdapter(unittest.TestCase):
    """The real Runner adapter must forward --role into kaola-acp.py.

    Dispatch calls the generated runtime-tmux.sh. A fake Runner spec never
    reaches this parser, which is where Host QA saw ``unknown argument: --role``.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.record = self.root / "argv.txt"
        self.recorder = self.root / "python-record.sh"
        self.recorder.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" > \"$KAOLA_ACP_ARGV_RECORD\"\n"
            "printf '%s\\n' '{\"result\":\"ready\"}'\n",
            encoding="utf-8",
        )
        self.recorder.chmod(0o755)
        self.repo = self.root / "repo"
        self.repo.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def forwarded(self, runner: Path, args: list[str]) -> list[str]:
        env = {key: value for key, value in os.environ.items() if not key.startswith("KAOLA_")}
        env["PYTHON_BIN"] = str(self.recorder)
        env["KAOLA_ACP_ARGV_RECORD"] = str(self.record)
        if self.record.exists():
            self.record.unlink()
        result = subprocess.run(
            ["bash", str(runner), *args],
            capture_output=True, text=True, env=env, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("unknown argument", result.stderr)
        self.assertTrue(self.record.is_file(), result.stderr)
        return self.record.read_text(encoding="utf-8").splitlines()

    def test_start_forwards_role_sidekick_to_kaola_acp(self) -> None:
        start = [
            "start", "--repo", str(self.repo), "--session", "zcode-KPR-i245-fwd",
            "--role", "sidekick",
        ]
        source = self.forwarded(PROJECT / "scripts" / "kaola-tmux.sh", ["zcode", *start])
        self.assertTrue(source[0].endswith("kaola-acp.py"), source)
        self.assertEqual(source[1:3], ["zcode", "start"])
        self.assertEqual(source[source.index("--role") + 1], "sidekick")
        generated = PROJECT / "skills" / "zcode-kaola-project-runner" / "scripts" / "runtime-tmux.sh"
        wrapped = self.forwarded(generated, start)
        self.assertTrue(wrapped[0].endswith("kaola-acp.py"), wrapped)
        self.assertEqual(wrapped[1:3], ["zcode", "start"])
        self.assertEqual(wrapped[wrapped.index("--role") + 1], "sidekick")
        plain = self.forwarded(
            PROJECT / "scripts" / "kaola-tmux.sh",
            ["zcode", "start", "--repo", str(self.repo), "--session", "zcode-KPR-i245-fwd"],
        )
        self.assertNotIn("--role", plain)
        status = self.forwarded(
            PROJECT / "scripts" / "kaola-tmux.sh",
            ["zcode", "status", "--repo", str(self.repo), "--session", "zcode-KPR-i245-fwd",
             "--role", "sidekick"],
        )
        self.assertNotIn("--role", status)


if __name__ == "__main__":
    unittest.main(verbosity=2)
