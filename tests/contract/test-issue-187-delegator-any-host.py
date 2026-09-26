#!/usr/bin/env python3
"""Issue #187: Kaola-Delegator selects any supported CLI Host.

Static half: the generated Delegator names no fixed Host platform; its
host-platforms.md row for every manifest carries that platform's own Runner,
exact ``host_skill_entry`` (codex ``$``, kimi-cli trailing space) and standard
Host name; native resume ids stay platform-specific; the Grok Bot bridge body
stays platform-neutral.

Behavioral half: the handoff's own commands, with ``$PLATFORM`` set to a
non-ZCode platform, driven through a copied generated Runner against the mock
ACP agent (no real CLI): start, verified ``host_class`` row, one-Host refusal
across platforms in both directions (codex/claude-code Host, then zcode or
kimi-cli), the handoff delivered with that platform's first line, exact stop,
and ``--resume`` of the attested ``session_meta`` id. Offline only: this is not
a live Host D3, not a Grok Bot account run, and not E1/E2 startup proof.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SKILLS = PROJECT / "skills"
DELEG = SKILLS / "kaola-delegator"
DELEG_T = PROJECT / "templates" / "kaola-delegator"
BRIDGE = PROJECT / "hosts" / "grok-bot" / "kaola-delegator.md"
PLATFORMS = PROJECT / "platforms"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
LOCATE = PROJECT / "scripts" / "kaola-locate.py"
BUDGETS = json.loads((PROJECT / "templates" / "budgets.json").read_text(encoding="utf-8"))
PYTHON = sys.executable


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def manifest_value(platform: str, key: str) -> str:
    text = (PLATFORMS / f"{platform}.yaml").read_text(encoding="utf-8")
    match = re.search(rf'(?m)^{key}: "(.*)"$', text)
    assert match, (platform, key)
    return json.loads(f'"{match.group(1)}"')


def handoff_block() -> str:
    handoff = (DELEG / "references" / "handoff.md").read_text(encoding="utf-8")
    return handoff.split("```text\n", 1)[1].split("```", 1)[0]


class GeneratedDelegator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (DELEG / "SKILL.md").read_text(encoding="utf-8")
        cls.handoff = (DELEG / "references" / "handoff.md").read_text(encoding="utf-8")
        cls.platforms = (DELEG / "references" / "host-platforms.md").read_text(encoding="utf-8")
        cls.ids = sorted(p.stem for p in PLATFORMS.glob("*.yaml"))

    def test_every_manifest_is_a_selectable_host_row(self) -> None:
        self.assertEqual(len(self.ids), 10)
        for platform in self.ids:
            with self.subTest(platform=platform):
                entry = manifest_value(platform, "host_skill_entry")
                self.assertTrue(entry, "every shipped platform has a measured entry")
                runtime = manifest_value(platform, "runtime_name")
                row = (f"| {platform} (`{runtime}`) | `{platform}-kaola-project-runner` | `{entry}` | "
                       f"`{platform}-<PROJECT_CODE>-orchestrator-<purpose>` |")
                self.assertIn(row, self.platforms)
                self.assertTrue((SKILLS / f"{platform}-kaola-project-runner" / "scripts"
                                 / "runtime-tmux.sh").is_file())

    def test_exact_codex_and_kimi_entries(self) -> None:
        self.assertIn("| codex (`Codex CLI`) | `codex-kaola-project-runner` | `$kaola-project-runner` |",
                      self.platforms)
        # The trailing space is part of the Kimi entry; the row keeps it.
        self.assertIn("| kimi-cli (`Kimi CLI`) | `kimi-cli-kaola-project-runner` | "
                      "`/skill:kaola-project-runner ` |", self.platforms)
        self.assertIn("single-quoted", self.platforms)

    def test_no_fixed_zcode_host(self) -> None:
        for name, text in (("SKILL", self.skill), ("handoff", self.handoff)):
            with self.subTest(surface=name):
                for locked in ("ZCode Host", "one ZCode", "$ZCODE", "--worker zcode",
                               "zcode-kaola-project-runner", "zcode-<PROJECT_CODE>"):
                    self.assertNotIn(locked, text)
        self.assertIn("Select any supported Host platform", flat(self.skill))
        self.assertIn("`<platform>-kaola-project-runner`", self.skill)
        self.assertIn("`<platform>-<PROJECT_CODE>-orchestrator-<purpose>`", self.skill)
        self.assertIn("One live Host per repo, whatever its platform", flat(self.skill))
        self.assertIn('RUNNER="<skills>/$PLATFORM-kaola-project-runner/scripts/runtime-tmux.sh"',
                      self.handoff)
        self.assertIn('HOST="$PLATFORM-<PROJECT_CODE>-orchestrator-main"', self.handoff)
        self.assertIn("`host-exists`: attach its `existing_host` (step 2)", flat(self.handoff))
        self.assertIn("Host platform unknown: run it from any installed Runner", flat(self.handoff))
        self.assertIn("startup_proof=quote one Skill-body-only sentence; no tool read", handoff_block())
        self.assertTrue(handoff_block().startswith(
            "<host_skill_entry>\nYou are the <runtime_name> Host for this run.\n"
            "platform=<PLATFORM> session=<HOST> repo=<PROJECT>\n"))

    def test_host_platform_is_not_worker_authorization(self) -> None:
        self.assertIn("the Host platform; authorized worker platforms", flat(self.skill))
        self.assertIn("apart from `authorized_platforms`", flat(self.platforms))
        self.assertIn("being the Host authorizes no worker seat", flat(self.platforms))
        block = handoff_block()
        self.assertIn("platform=<PLATFORM>", block)
        self.assertIn("authorized_platforms=<id:count, ...>", block)

    def test_native_resume_id_is_platform_specific(self) -> None:
        text = flat(self.platforms)
        self.assertIn("**zcode**: `sess_*`", text)
        self.assertIn("present only after the first prompt", text)
        self.assertIn("newest `native_session_identity` event (from turn one); a fresh seat's "
                      "`acp_session_id` is process-local and unresumable", text)
        self.assertIn("never synthesize one, never `--continue`", text)
        self.assertIn("No attested id: start a new Host", text)
        self.assertIn('--resume "$NATIVE_ID"', self.handoff)
        self.assertNotIn("sess_*` first", self.handoff)

    def test_startup_proof_is_platform_specific_and_codex_is_honest(self) -> None:
        text = flat(self.platforms)
        # The Delegator checks the handoff beat, so the rule must follow the
        # evidence matrix's D3 step-2 column, not its isolated-probe column.
        evidence = (PROJECT / "docs" / "host-entry-evidence.md").read_text(encoding="utf-8")
        beat: dict[str, str] = {}
        for line in evidence.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3 or cells[0] not in self.ids:
                continue
            probe_and_d3 = cells[2]
            # zcode's row is "E1 (#94)": the #94 entry is E1 at every beat.
            beat[cells[0]] = (probe_and_d3.split(";", 1)[1].split("/")[0].strip()
                              if ";" in probe_and_d3 else probe_and_d3)
        self.assertEqual(sorted(beat), self.ids, beat)
        self.assertIn("E1", beat["zcode"])
        self.assertTrue(beat["devin"].startswith("E2"), beat["devin"])
        for platform in self.ids:
            if platform != "zcode":
                with self.subTest(platform=platform):
                    self.assertIn("E2", beat[platform], "every non-zcode beat is E2-provable")
        self.assertIn("At the beat, zcode proves by E1; every other row by E2, devin included "
                      "(its E1 is the probe's `Invoked skill`, its beat is E2); an E1 there also counts",
                      text)
        self.assertIn("On zcode a missing tool_call means the install is wrong", text)
        self.assertNotIn("zcode, devin, opencode", text)
        self.assertNotIn("On an E1 row", text)
        self.assertIn("isolated 1.13.1 E2 probes answered `SKILL-NOT-LOADED`", text)
        self.assertIn("that owner acceptance, not E1/E2", text)
        # No unconditional tool_call rule for every Host.
        self.assertNotIn("a missing `Skill` tool_call means a bad install", flat(self.handoff))
        self.assertIn("E1 `Skill` tool_call or E2 quote", flat(self.handoff))

    def test_grok_bot_colocation_uses_the_selected_worker(self) -> None:
        text = flat(self.handoff)
        self.assertEqual(self.handoff.count('--worker "$PLATFORM" --session "$HOST"'), 2)
        self.assertIn("then a zcode launch with a missing or non-file `KAOLA_ZCODE_*` refuses", text)
        self.assertIn("Liveness is Runner `status`, not the locator's tmux `session.present`", text)
        platforms = flat(self.platforms)
        self.assertIn("`--intent start|resume` adds no launchability check for that CLI "
                      "(the `KAOLA_ZCODE_*` gate is zcode-only)", platforms)
        self.assertIn("that platform's worker script under ROOT, and the exact session name", platforms)

    def test_zcode_host_model_is_a_start_receipt_fact(self) -> None:
        text = flat(self.platforms)
        self.assertIn("pins GLM 5.3 at effort `max` (a Runner requirement, #108) and reports it in "
                      "that start receipt's `host_selection`", text)
        self.assertNotIn("manifest Host model", text)
        acp = (PROJECT / "scripts" / "kaola-acp.py").read_text(encoding="utf-8")
        self.assertIn('ZCODE_HOST_MODEL_ID = "GLM-5.3"', acp)
        self.assertIn('ZCODE_HOST_EFFORT = "max"', acp)
        self.assertIn('"host_selection"', acp)

    def test_bridge_stays_thin_and_platform_neutral(self) -> None:
        bridge = BRIDGE.read_text(encoding="utf-8")
        self.assertLessEqual(len(bridge.encode()), BUDGETS["bridge_bytes"])
        self.assertNotIn("zcode", bridge.lower())
        self.assertIn("ROOT/skills/kaola-delegator/SKILL.md", bridge)

    def test_budgets(self) -> None:
        self.assertLessEqual(len((DELEG / "SKILL.md").read_bytes()), BUDGETS["external_skill_bytes"])
        for ref in (DELEG / "references").glob("*.md"):
            with self.subTest(ref=ref.name):
                self.assertLessEqual(len(ref.read_bytes()), BUDGETS["reference_bytes"])
        self.assertTrue((DELEG_T / "references" / "host-platforms.md.tmpl").is_file())


class NonZCodeHostLifecycle(unittest.TestCase):
    """The handoff's commands with a non-ZCode $PLATFORM, over the mock agent."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.records = self.root / "records"
        self.records.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
        self.skills = self.root / "skills"   # the handoff's <skills>
        self.mock_log = self.root / "mock.jsonl"
        self.started: list[tuple[str, str]] = []

    def tearDown(self) -> None:
        for platform, session in self.started:
            self.runner(platform, "stop", "--force", session=session, check=False)
        self.tmp.cleanup()

    def env(self, **extra: str) -> dict[str, str]:
        base = {"HOME": str(self.home), "PATH": "/usr/bin:/bin", "TMPDIR": str(self.root),
                "KAOLA_ACP_RECORD_ROOT": str(self.records), "PYTHON_BIN": PYTHON,
                "PYTHONUNBUFFERED": "1", "LANG": "C", "MOCK_ACP_LOG": str(self.mock_log)}
        base.update(extra)
        return base

    def runner_path(self, platform: str) -> Path:
        tree = self.skills / f"{platform}-kaola-project-runner"
        if not tree.exists():
            shutil.copytree(SKILLS / f"{platform}-kaola-project-runner", tree)
        return tree / "scripts" / "runtime-tmux.sh"

    def runner(self, platform: str, command: str, *args: str, session: str,
               check: bool = True, **env: str) -> tuple[int, dict]:
        argv = [str(self.runner_path(platform)), command, "--repo", str(self.repo),
                "--session", session, *args]
        if command == "start":
            # The wrapper takes no --command; the mock agent comes in by env.
            env.setdefault("KAOLA_ACP_COMMAND",
                           f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close")
            self.started.append((platform, session))
        result = subprocess.run(argv, capture_output=True, text=True, env=self.env(**env), timeout=120)
        lines = (result.stdout or "").strip().splitlines()
        payload = json.loads(lines[-1]) if lines else {}
        if check and result.returncode != 0:
            self.fail(f"{platform} {command} exited {result.returncode}: {payload or result.stderr[-800:]}")
        return result.returncode, payload

    def rows(self) -> dict[str, dict]:
        cli = self.runner_path("codex").parent / "kaola-acp.py"
        result = subprocess.run([PYTHON, str(cli), "list", "--repo", str(self.repo), "--include-dead"],
                                capture_output=True, text=True, env=self.env(), timeout=60, check=True)
        return {row["session"]: row for row in json.loads(result.stdout)["rows"]}

    def prompts(self) -> list[str]:
        if not self.mock_log.is_file():
            return []
        events = [json.loads(line) for line in self.mock_log.read_text(encoding="utf-8").splitlines()]
        return [e["text"] for e in events if e.get("event") == "prompt"]

    def handoff_for(self, platform: str, host: str) -> str:
        block = handoff_block()
        return (block.replace("<host_skill_entry>", manifest_value(platform, "host_skill_entry"))
                .replace("<runtime_name>", manifest_value(platform, "runtime_name"))
                .replace("<PLATFORM>", platform).replace("<HOST>", host)
                .replace("<PROJECT>", str(self.repo)))

    def assert_gone(self, platform: str, host: str) -> None:
        _code, status = self.runner(platform, "status", session=host, check=False)
        state = status.get("state") or status.get("reason") or status.get("result")
        self.assertIn(state, ("stopped", "no-session"), status)
        if state == "stopped":
            self.assertIn("residual_pids", status)
            self.assertEqual(status["residual_pids"], [], status)

    def start_host(self, platform: str) -> tuple[str, dict]:
        host = f"{platform}-KPR-orchestrator-main"
        _code, before = self.runner(platform, "status", session=host, check=False)
        self.assertNotEqual(before.get("state"), "running", before)
        _code, started = self.runner(platform, "start", session=host)
        self.assertEqual(started.get("session"), host, started)
        self.assertTrue(started.get("holder_instance_id"), started)
        self.assertTrue(started.get("acp_session_id"), started)
        row = self.rows().get(host) or {}
        self.assertEqual(row.get("platform"), platform, row)
        self.assertIs(row.get("host_class"), True, row)
        self.assertEqual(row.get("identity"), "verified", row)
        return host, started

    def assert_second_host_refused(self, platform: str, host: str, started: dict, **env: str) -> None:
        second = f"{platform}-KPR-orchestrator-main"
        code, refused = self.runner(platform, "start", session=second, check=False, **env)
        self.assertEqual(code, 1, refused)
        self.assertEqual((refused.get("result"), refused.get("reason")), ("refused", "host-exists"), refused)
        existing = refused.get("existing_host") or {}
        self.assertEqual(existing.get("session"), host, refused)
        self.assertEqual(existing.get("holder_instance_id"), started["holder_instance_id"], refused)
        self.assertIs(refused.get("mutation_performed"), False, refused)
        self.assertFalse((self.records / platform / second).exists())

    def test_codex_host_handoff_exact_stop_and_attested_resume(self) -> None:
        host, started = self.start_host("codex")
        self.assert_second_host_refused("kimi-cli", host, started)
        self.assert_second_host_refused(
            "zcode", host, started,
            KAOLA_ZCODE_ENTRY=str(self.root / "absent-entry"), KAOLA_ZCODE_NODE="/bin/sh")

        # First handoff: codex's exact `$` entry is its own first line; argv
        # carries it verbatim (no shell expansion).
        text = self.handoff_for("codex", host)
        self.assertTrue(text.startswith("$kaola-project-runner\nYou are the Codex CLI Host for this run.\n"))
        self.runner("codex", "send", "--text", text, session=host)
        delivered = self.prompts()
        self.assertTrue(delivered and delivered[-1].split("\n", 1)[0] == "$kaola-project-runner",
                        delivered)
        self.assertIn(f"platform=codex session={host} repo={self.repo}", delivered[-1])

        # Exact stop: a different holder id is refused and leaves the Host up.
        code, mismatch = self.runner("codex", "stop", "--expected-holder-instance-id", "not-this-holder",
                                     session=host, check=False)
        self.assertEqual((mismatch.get("error") or {}).get("code"), "holder-instance-mismatch", mismatch)
        self.assertIs(mismatch.get("mutation_performed"), False, mismatch)
        self.assertIs(self.rows()[host].get("host_class"), True)
        self.runner("codex", "stop", "--expected-holder-instance-id", started["holder_instance_id"],
                    session=host)
        self.assert_gone("codex", host)

        # Resume with the id the receipt records (on a native ACP agent the
        # agent's own session/new sessionId); never --continue, never a
        # synthesized id. The mock accepts any id after a restart, so this leg
        # proves the Runner path, not the agent's persistence.
        native = started["acp_session_id"]
        self.assertRegex(native, r"^mock-session-\d+$")
        _code, resumed = self.runner("codex", "start", "--resume", native, session=host,
                                     MOCK_ACP_RESUME_ANY="1")
        self.assertEqual(resumed.get("acp_session_id"), native, resumed)
        self.assertNotEqual(resumed.get("holder_instance_id"), started["holder_instance_id"])
        self.runner("codex", "stop", "--expected-holder-instance-id", resumed["holder_instance_id"],
                    session=host)
        self.assert_gone("codex", host)

    def test_live_claude_host_blocks_a_zcode_host(self) -> None:
        host, started = self.start_host("claude-code")
        self.assert_second_host_refused(
            "zcode", host, started,
            KAOLA_ZCODE_ENTRY=str(self.root / "absent-entry"), KAOLA_ZCODE_NODE="/bin/sh")
        text = self.handoff_for("claude-code", host)
        self.assertTrue(text.startswith("/kaola-project-runner\nYou are the Claude Code Host"), text[:80])
        self.runner("claude-code", "stop", "--expected-holder-instance-id",
                    started["holder_instance_id"], session=host)
        self.assert_gone("claude-code", host)

    def test_kimi_entry_keeps_its_trailing_space_on_the_wire(self) -> None:
        host, started = self.start_host("kimi-cli")
        text = self.handoff_for("kimi-cli", host)
        self.runner("kimi-cli", "send", "--text", text, session=host)
        first = self.prompts()[-1].split("\n", 1)[0]
        self.assertEqual(first, "/skill:kaola-project-runner ")
        self.runner("kimi-cli", "stop", "--expected-holder-instance-id",
                    started["holder_instance_id"], session=host)
        self.assert_gone("kimi-cli", host)


class NonZCodeLocatorAttestation(unittest.TestCase):
    """The Grok Bot co-location command with a non-ZCode --worker."""

    def locate(self, repo: Path, worker: str, session: str, *extra: str) -> dict:
        env = {"HOME": str(repo.parent / "home"), "PATH": "/usr/bin:/bin", "LANG": "C"}
        result = subprocess.run([PYTHON, str(LOCATE), "receipt", "--target", "local",
                                 "--project", str(repo), "--worker", worker, "--session", session,
                                 *extra], capture_output=True, text=True, env=env, timeout=30)
        return json.loads((result.stdout or "").strip().splitlines()[-1])

    def test_selected_worker_is_attested_and_zcode_runtime_gate_is_zcode_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (Path(tmp) / "home").mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            host = "codex-KPR-orchestrator-main"
            codex = self.locate(repo, "codex", host, "--intent", "start")
            self.assertEqual((codex.get("worker") or {}).get("id"), "codex", codex)
            self.assertEqual((codex.get("worker") or {}).get("skill"),
                             "skills/codex-kaola-project-runner", codex)
            for reason in ("worker-unknown", "script-missing"):
                self.assertNotIn(reason, codex.get("reasons") or [], codex)
            self.assertEqual((codex.get("session") or {}).get("name"), host, codex)
            # tmux presence only; no ACP liveness claim for a non-zcode Host.
            self.assertNotIn("acp_holder_alive", codex.get("session") or {}, codex)
            self.assertIs((codex.get("zcode_runtime") or {}).get("required"), False, codex)
            for reason in ("zcode-runtime-unset", "zcode-runtime-invalid"):
                self.assertNotIn(reason, codex.get("reasons") or [], codex)
            zcode = self.locate(repo, "zcode", "zcode-KPR-orchestrator-main", "--intent", "start")
            self.assertIn("zcode-runtime-unset", zcode.get("reasons") or [], zcode)


if __name__ == "__main__":
    unittest.main(verbosity=2)
