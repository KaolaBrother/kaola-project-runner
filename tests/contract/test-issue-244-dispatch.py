#!/usr/bin/env python3
"""Issue #244: capability projection and one dispatch/collect entry.

Behavioral checks drive the CLI with fake Runner receipts. They do not import
the entry's helpers or score model capability. The omitted-row order check
calls merge_index_rows. A sequential CLI sees the same bytes at read and at
lock, so it cannot show this order. That check starts no Runner.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
RECORD = REPO / "scripts" / "kaola-record-contract.py"
PLATFORMS = REPO / "platforms"
ORCHESTRATOR = REPO / "skills" / "kaola-project-runner"
DELEGATOR = REPO / "skills" / "kaola-delegator"

FAKE_RUNNER = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys, time
    from pathlib import Path
    spec = json.loads(Path(os.environ["FAKE_SPEC"]).read_text())
    argv = sys.argv[1:]
    command = argv[0]
    session = argv[argv.index("--session") + 1]
    log = Path(os.environ["FAKE_LOG"])
    row = spec["sessions"][session]
    import fcntl
    with log.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(json.dumps({"command": command, "session": session, "argv": argv, "t": time.time()}) + "\\n")
        handle.flush()
        fcntl.flock(handle, fcntl.LOCK_UN)
    if command == "status":
        gate = row.get("wait_for")
        if isinstance(gate, str) and gate:
            deadline = time.time() + 30
            while not Path(gate).exists():
                if time.time() >= deadline:
                    break
                time.sleep(0.02)
        calls = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
        if sum(c["command"] == "status" and c["session"] == session for c in calls) >= 2:
            if row.get("second_status_hang"):
                time.sleep(row.get("hang_for") or 2)
                raise SystemExit(0)
            if "status_second" in row:
                print(json.dumps(row["status_second"]))
                raise SystemExit(0)
    time.sleep(row.get("sleep") or 0)
    if command in row.get("hang", []):
        time.sleep(row.get("hang_for") or 2)
        raise SystemExit(0)
    if command in row.get("garbage", []):
        print("not-json")
        raise SystemExit(0)
    if command in row.get("fail", []):
        print(json.dumps({"result": "refused", "error": {"code": "boom"}}))
        raise SystemExit(1)
    print(json.dumps(row[command]))
    """
)


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout was not JSON ({exc}): {proc.stdout}\\n{proc.stderr}") from exc
    return proc.returncode, payload


def write_json(directory: Path, name: str, payload: dict) -> Path:
    path = directory / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def install_fake(root: Path, platforms: list[str]) -> None:
    for platform in platforms:
        dest = root / f"{platform}-kaola-project-runner" / "scripts"
        dest.mkdir(parents=True, exist_ok=True)
        script = dest / "runtime-tmux.sh"
        script.write_text(FAKE_RUNNER, encoding="utf-8")
        script.chmod(0o755)


def commands(log: Path) -> list[dict]:
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def absent(repo: str) -> dict:
    return {"error": {"code": "no-session"}}


def started(repo: str, model, effort=None, advertised=None, holder: str = "holder-1",
           mapped: bool = False, requested_id: str | None = None,
           unapplied: bool = False, nest: bool = False) -> dict:
    """A realistic start receipt.

    Applied evidence is ``config_application``. ``resolved_*`` is deliberately
    a different value so a test fails if the entry treats it as applied.
    Send receipts omit the holder; the start receipt carries it.
    """
    application: dict = {}
    if model is not None or unapplied:
        slot = {"applied": not unapplied, "value": model}
        if mapped:
            slot["mapped"] = True
            slot["requested_id"] = requested_id
        application["model"] = slot
    if effort is not None:
        application["effort"] = {"applied": True, "value": effort}
    advertised_block = {
        "effective_model": advertised if advertised is not None else model,
        "effective_effort": effort,
    }
    receipt = {
        "holder_instance_id": holder,
        "repo": repo,
        "model_selection": {"resolved_model": "resolved-not-applied", "resolved_effort": "resolved-not-applied"},
        "resolved_parameters": {"effort": "resolved-not-applied"},
    }
    if nest:
        receipt["start_evidence"] = {
            "config_application": application,
            "effective_selection": advertised_block,
        }
    else:
        if application:
            receipt["config_application"] = application
        receipt["effective_selection"] = advertised_block
    return receipt


def plan_item(name: str, preset: str = "codex/luna") -> dict:
    return {"item_id": name, "preset": preset, "session": f"codex-KPR-i255-{name}", "prompt": name}


def sent(fingerprint: str = "fp-1", cursor: int = 7) -> dict:
    return {
        "outcome": "in_progress",
        "prompt_fingerprint": fingerprint,
        "dispatch_event_cursor": cursor,
        "mutation_status": "in_progress",
    }


class DispatchEntry(unittest.TestCase):
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

    def authorization(self, grants=None, **extra) -> Path:
        body = {"grants": grants or [], "classes": {"Expert": "e", "Elite": "l", "Worker": "w"}}
        body.update(extra)
        return write_json(self.root, "auth.json", body)

    def availability(self, present=None, absent_ids=None) -> Path:
        return write_json(self.root, "avail.json", {"present": present or [], "absent": absent_ids or []})

    def plan(self, items, scope="research", **extra) -> Path:
        body = {"scope": scope, "repo": str(self.repo), "items": items}
        body.update(extra)
        return write_json(self.root, "plan.json", body)

    def use_spec(self, sessions: dict) -> None:
        self.spec_path.write_text(json.dumps({"sessions": sessions}), encoding="utf-8")
        self.env["FAKE_SPEC"] = str(self.spec_path)

    def project(self, auth: Path, avail: Path | None = None) -> dict:
        args = ["project", "--authorization", str(auth), "--platforms", str(PLATFORMS)]
        if avail:
            args.extend(["--availability", str(avail)])
        code, payload = run(args, self.env)
        self.assertEqual(code, 0, payload)
        return payload

    def execute(self, plan: Path, auth: Path, avail: Path | None = None, **flags) -> dict:
        args = [
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
        ]
        if avail:
            args.extend(["--availability", str(avail)])
        live = flags.pop("live", None)
        if live != "omit":
            if live is None:
                live = write_json(self.root, "live-empty.json", {"rows": []})
            args.extend(["--live", str(live)])
        for key, value in flags.items():
            args.extend([f"--{key.replace('_', '-')}", str(value)])
        code, payload = run(args, self.env)
        self.assertEqual(code, 0, payload)
        return payload

    def execute_dry_run(self, plan: Path, auth: Path, avail: Path | None = None,
                        live: Path | None = None) -> dict:
        args = [
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills), "--dry-run",
        ]
        if avail:
            args.extend(["--availability", str(avail)])
        if live:
            args.extend(["--live", str(live)])
        code, payload = run(args, self.env)
        self.assertEqual(code, 0, payload)
        return payload

    def collect(self, index: Path) -> dict:
        code, payload = run(
            ["collect", "--index", str(index), "--skills-root", str(self.skills)],
            self.env,
        )
        self.assertEqual(code, 0, payload)
        return payload

    def test_summary_uses_present_grants_and_hides_ungranted_expert(self) -> None:
        auth = self.authorization([
            {"id": "codex/default", "state": "granted", "count": 1},
        ], exclusions=["codex/luna"])
        avail = self.availability(["codex/default", "zcode/default", "codex/astra"])
        payload = self.project(auth, avail)
        summary = payload["capability_summary"]
        self.assertNotIn("classes", summary)
        self.assertNotIn("computer_interaction", summary)
        self.assertIn("codex/default", summary["presets"])
        self.assertIn("zcode/default", summary["presets"])
        self.assertNotIn("visual:", summary["text"])
        self.assertNotIn("computer-use:", summary["text"])
        self.assertNotIn("exploring directions", summary["text"])
        self.assertNotIn("Design, goal definition", summary["text"])
        self.assertNotIn("Expert not granted", summary["text"])
        ids = {item["id"] for item in payload["candidates"]}
        self.assertIn("codex/default", ids)
        self.assertIn("zcode/default", ids)
        self.assertNotIn("codex/astra", ids)
        self.assertNotIn("codex/luna", ids)
        luna = [row for row in payload["withheld"] if row["id"] == "codex/luna"]
        self.assertEqual(luna, [{"id": "codex/luna", "reason": "excluded"}])
        codex = next(item for item in payload["candidates"] if item["id"] == "codex/default")
        self.assertEqual(codex["class"], "Elite")
        self.assertTrue(codex["selection"]["model_id"])
        self.assertTrue(codex["selection"]["effort"])
        self.assertIn("computer-use capability", codex["profile"])
        self.assertNotIn("computer-use", summary["text"])
        zcode = next(item for item in payload["candidates"] if item["id"] == "zcode/default")
        self.assertEqual(zcode["availability"], "present")
        self.assertTrue(zcode["pool"])

    def test_unknown_availability_is_projected_and_not_advertised(self) -> None:
        auth = self.authorization()
        payload = self.project(auth, self.availability([]))
        zcode = next(item for item in payload["candidates"] if item["id"] == "zcode/default")
        self.assertEqual(zcode["availability"], "unknown")
        self.assertIn("availability unknown:", payload["capability_summary"]["text"])
        self.assertIn("zcode/default", payload["capability_summary"]["text"])
        self.assertNotIn("Autonomous engineering", payload["capability_summary"]["text"])
        self.assertNotIn("computer_interaction", payload["capability_summary"])

    def test_exact_tier_and_override_are_not_substituted(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        self.use_spec({
            "codex-KPR-i244-tier": {
                "status": absent(repo),
                "start": started(repo, "gpt-6-luna", "high"),
                "send": sent("fp-tier"),
            }
        })
        auth = self.authorization([
            {"id": "codex/luna", "special_requirements": {"task_scope": "visual QA"}},
        ])
        plan = self.plan([{
            "item_id": "tier",
            "preset": "codex/luna",
            "session": "codex-KPR-i244-tier",
            "prompt": "read only",
            "overrides": {"effort": "high"},
        }])
        payload = self.execute(plan, auth, self.availability(["codex/luna"]))
        item = payload["items"][0]
        self.assertEqual(item["status"], "in-flight")
        self.assertEqual(item["reason"], "admitted")
        self.assertEqual(item["acceptance"], "pending")
        self.assertEqual(item["selection"]["requested"]["tier"], "luna")
        self.assertEqual(item["selection"]["requested"]["effort"], "high")
        self.assertEqual(item["selection"]["requested"]["model_id"], "gpt-6-luna")
        start = next(row for row in commands(self.log) if row["command"] == "start")
        self.assertEqual(start["argv"][start["argv"].index("--tier") + 1], "luna")
        self.assertEqual(start["argv"][start["argv"].index("--effort") + 1], "high")
        self.assertNotIn("--model", start["argv"])

    def test_sideagent_role_reaches_start_argv(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        self.use_spec({
            "codex-KPR-i245-role": {
                "status": absent(repo),
                "start": started(repo, "gpt-6-luna", "max"),
                "send": sent("fp-role"),
            }
        })
        auth = self.authorization([{"id": "codex/luna", "state": "granted"}])
        plan = self.plan([{
            "item_id": "sideagent",
            "preset": "codex/luna",
            "session": "codex-KPR-i245-role",
            "prompt": "draft only",
            "role": "sideagent",
        }])
        payload = self.execute(plan, auth, self.availability(["codex/luna"]))
        item = payload["items"][0]
        self.assertEqual(item["status"], "in-flight")
        self.assertEqual(item["reason"], "admitted")
        self.assertEqual(item["role"], "sideagent")
        start = next(row for row in commands(self.log) if row["command"] == "start")
        self.assertEqual(start["argv"][start["argv"].index("--role") + 1], "sideagent")
        self.assertNotIn("--model", start["argv"])

    def test_provider_qualified_model_matches_and_a_different_id_does_not(self) -> None:
        install_fake(self.skills, ["zcode", "codex", "opencode"])
        repo = str(self.repo)
        self.use_spec({
            "zcode-KPR-i244-qual": {
                "status": absent(repo),
                "start": started(repo, "builtin:bigmodel-coding-plan\\GLM-5.3", "max"),
                "send": sent("fp-qual"),
            },
            "codex-KPR-i244-miss": {
                "status": absent(repo),
                "start": started(repo, "gpt-6-sol", "max", advertised="gpt-6-luna"),
                "send": sent("fp-should-not"),
            },
            "opencode-KPR-i244-route": {
                "status": absent(repo),
                "start": started(repo, "deepseek-official/deepseek-v4.1-flash"),
                "send": sent("fp-route"),
            },
        })
        auth = self.authorization()
        plan = self.plan([
            {"item_id": "qualified", "preset": "zcode/default", "session": "zcode-KPR-i244-qual", "prompt": "a"},
            {"item_id": "mismatch", "preset": "codex/luna", "session": "codex-KPR-i244-miss", "prompt": "b"},
            {"item_id": "route", "preset": "opencode/default", "session": "opencode-KPR-i244-route", "prompt": "c"},
        ])
        payload = self.execute(plan, auth, self.availability(["zcode/default", "codex/luna", "opencode/default"]))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["qualified"]["selection"]["fields"]["model_id"]["applied"], "match")
        self.assertEqual(by_id["qualified"]["status"], "in-flight")
        self.assertEqual(by_id["qualified"]["reason"], "admitted")
        self.assertEqual(by_id["mismatch"]["selection"]["fields"]["model_id"]["applied"], "mismatch")
        self.assertEqual(by_id["mismatch"]["status"], "failed")
        self.assertEqual(by_id["mismatch"]["reason"], "selection-mismatch")
        self.assertEqual(by_id["route"]["selection"]["fields"]["model_id"]["applied"], "mismatch")
        self.assertEqual(by_id["route"]["status"], "failed")
        sent_sessions = {row["session"] for row in commands(self.log) if row["command"] == "send"}
        self.assertIn("zcode-KPR-i244-qual", sent_sessions)
        self.assertNotIn("codex-KPR-i244-miss", sent_sessions)
        self.assertNotIn("opencode-KPR-i244-route", sent_sessions)

    def test_unknown_selection_is_not_a_mismatch_and_does_not_block_send(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        self.use_spec({
            "codex-KPR-i244-unk": {
                "status": absent(repo),
                "start": started(repo, None, None, None),
                "send": sent("fp-unk", 11),
            }
        })
        auth = self.authorization()
        plan = self.plan([{
            "item_id": "unknown",
            "preset": "codex/luna",
            "session": "codex-KPR-i244-unk",
            "prompt": "look",
        }])
        payload = self.execute(plan, auth, self.availability(["codex/luna"]))
        item = payload["items"][0]
        self.assertEqual(item["selection"]["comparison"], "unknown")
        self.assertEqual(item["selection"]["fields"]["model_id"]["applied"], "unknown")
        self.assertEqual(item["selection"]["fields"]["model_id"]["advertised"], "unknown")
        self.assertEqual(item["status"], "in-flight")
        self.assertEqual(item["reason"], "admitted")
        self.assertEqual(item["prompt_fingerprint"], "fp-unk")
        self.assertEqual(item["dispatch_event_cursor"], 11)
        self.assertNotIn("role", item)
        self.assertTrue(str(item["prompt_sha256"]).startswith("sha256:"))
        self.assertEqual(item["holder_instance_id"], "holder-1")
        self.assertIsNone(item["evidence"]["send"]["holder_instance_id"])
        self.assertEqual(item["evidence"]["send"]["prompt_fingerprint"], "fp-unk")
        send = next(row for row in commands(self.log) if row["command"] == "send")
        self.assertEqual(
            send["argv"][send["argv"].index("--expected-holder-instance-id") + 1],
            "holder-1",
        )

    def test_advertised_difference_stays_visible_without_blocking_send(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        self.use_spec({
            "codex-KPR-i244-adv": {
                "status": absent(repo),
                "start": started(repo, "gpt-6-luna", "max", advertised="something-else"),
                "send": sent("fp-adv"),
            }
        })
        auth = self.authorization()
        plan = self.plan([{
            "item_id": "advertised",
            "preset": "codex/luna",
            "session": "codex-KPR-i244-adv",
            "prompt": "look",
        }])
        payload = self.execute(plan, auth, self.availability(["codex/luna"]))
        item = payload["items"][0]
        self.assertEqual(item["selection"]["fields"]["model_id"]["applied"], "match")
        self.assertEqual(item["selection"]["fields"]["model_id"]["advertised"], "unknown")
        self.assertEqual(item["selection"]["advertised"]["model_id"], "something-else")
        self.assertEqual(item["selection"]["comparison"], "match")
        self.assertEqual(item["status"], "in-flight")
        self.assertEqual(item["reason"], "admitted")

    def test_partial_results_stay_visible(self) -> None:
        install_fake(self.skills, ["zcode", "codex"])
        repo = str(self.repo)
        self.use_spec({
            "zcode-KPR-i244-ok": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max"),
                "send": sent("fp-ok"),
            },
            "codex-KPR-i244-bad": {
                "status": absent(repo),
                "start": started(repo, "gpt-6-luna", "max"),
                "fail": ["start"],
                "send": sent("fp-no"),
            },
        })
        auth = self.authorization([{"id": "cursor-cli/opus", "state": "revoked"}])
        plan = self.plan([
            {"item_id": "ok", "preset": "zcode/default", "session": "zcode-KPR-i244-ok", "prompt": "a"},
            {"item_id": "bad", "preset": "codex/luna", "session": "codex-KPR-i244-bad", "prompt": "b"},
            {"item_id": "revoked", "preset": "cursor-cli/opus", "session": "cursor-cli-KPR-i244-no", "prompt": "c"},
        ])
        payload = self.execute(plan, auth, self.availability(["zcode/default", "codex/luna", "cursor-cli/opus"]))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["ok"]["status"], "in-flight")
        self.assertEqual(by_id["bad"]["status"], "failed")
        self.assertEqual(by_id["revoked"]["status"], "not-run")
        self.assertEqual(by_id["revoked"]["reason"], "revoked")
        self.assertEqual(payload["coverage"]["in-flight"], ["ok"])
        self.assertEqual(payload["coverage"]["returned"], [])
        self.assertEqual(payload["coverage"]["failed"], ["bad"])
        self.assertEqual(payload["coverage"]["not-run"], ["revoked"])
        self.assertTrue(payload["correlation_only"])
        self.assertNotIn("missions", payload)
        self.assertNotIn("cursor-cli-KPR-i244-no", {row["session"] for row in commands(self.log)})

    def test_recovery_does_not_replay_an_ambiguous_or_completed_send(self) -> None:
        install_fake(self.skills, ["zcode"])
        repo = str(self.repo)
        self.use_spec({
            "zcode-KPR-i244-done": {
                "status": {
                    "holder_instance_id": "holder-9",
                    "repo": repo,
                    "mutation_status": "completed",
                    "last_prompt": {"fingerprint": "fp-done"},
                    "prompt_fingerprint": "fp-done",
                    "dispatch_event_cursor": 4,
                },
            },
            "zcode-KPR-i244-bound": {
                "status": {
                    "holder_instance_id": "holder-9",
                    "repo": repo,
                    "mutation_status": "completed",
                    "last_prompt": {"fingerprint": "fp-done"},
                    "prompt_fingerprint": "fp-done",
                    "dispatch_event_cursor": 4,
                },
            },
            "zcode-KPR-i244-diff": {
                "status": {
                    "holder_instance_id": "holder-9",
                    "repo": repo,
                    "mutation_status": "completed",
                    "last_prompt": {"fingerprint": "fp-other"},
                },
            },
            "zcode-KPR-i244-named": {
                "status": {
                    "holder_instance_id": "holder-2",
                    "repo": repo,
                    "mutation_status": "in_progress",
                    "last_prompt": {"fingerprint": "fp-live"},
                },
            },
            "zcode-KPR-i244-holder": {
                "status": {
                    "holder_instance_id": "other-holder",
                    "repo": repo,
                    "mutation_status": "not_started",
                },
            },
            "zcode-KPR-i244-replay": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max", holder="holder-new"),
                "send": sent("fp-replay"),
            },
        })
        auth = self.authorization()
        prompt_sha = hashlib.sha256(b"a").hexdigest()
        prior = write_json(self.root, "prior.json", {"items": [
            {"item_id": "done", "prompt_fingerprint": "fp-done"},
            {
                "item_id": "bound",
                "repo": repo,
                "session": "zcode-KPR-i244-bound",
                "preset": "zcode/default",
                "holder_instance_id": "holder-9",
                "prompt_sha256": prompt_sha,
                "prompt_fingerprint": "fp-done",
                "status": "in-flight",
            },
            {
                "item_id": "diff",
                "repo": repo,
                "session": "zcode-KPR-i244-diff",
                "preset": "zcode/default",
                "holder_instance_id": "holder-9",
                "prompt_sha256": hashlib.sha256(b"b").hexdigest(),
                "prompt_fingerprint": "fp-done",
                "status": "in-flight",
            },
            {
                "item_id": "replay",
                "repo": repo,
                "session": "zcode-KPR-i244-replay",
                "preset": "zcode/default",
                "holder_instance_id": "holder-old",
                "prompt_sha256": "sha256:" + hashlib.sha256(b"replay").hexdigest(),
                "prompt_fingerprint": "fp-replay",
                "status": "unknown",
                "reason": "send-timeout",
                "dispatch_event_cursor": 3,
                "evidence": {"send": {"marker": "maybe-sent"}},
            },
        ]})
        plan = self.plan([
            {"item_id": "done", "preset": "zcode/default", "session": "zcode-KPR-i244-done", "prompt": "a"},
            {"item_id": "bound", "preset": "zcode/default", "session": "zcode-KPR-i244-bound", "prompt": "a"},
            {"item_id": "diff", "preset": "zcode/default", "session": "zcode-KPR-i244-diff", "prompt": "b"},
            {"item_id": "named", "preset": "zcode/default", "session": "zcode-KPR-i244-named", "prompt": "c"},
            {
                "item_id": "holder",
                "preset": "zcode/default",
                "session": "zcode-KPR-i244-holder",
                "prompt": "d",
                "expected_holder_instance_id": "holder-9",
            },
            {"item_id": "replay", "preset": "zcode/default", "session": "zcode-KPR-i244-replay", "prompt": "replay"},
        ])
        payload = self.execute(
            plan, auth, self.availability(["zcode/default"]), prior_index=prior,
        )
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["done"]["status"], "unknown")
        self.assertEqual(by_id["done"]["reason"], "assignment-unbound")
        self.assertEqual(by_id["bound"]["status"], "in-flight")
        self.assertEqual(by_id["bound"]["reason"], "already-admitted")
        self.assertNotEqual(by_id["bound"]["reason"], "already-dispatched")
        self.assertEqual(by_id["diff"]["status"], "unknown")
        self.assertEqual(by_id["diff"]["reason"], "fingerprint-differs")
        self.assertEqual(by_id["named"]["status"], "unknown")
        self.assertEqual(by_id["named"]["reason"], "existing-session-ambiguous")
        self.assertEqual(by_id["holder"]["status"], "unknown")
        self.assertEqual(by_id["holder"]["reason"], "holder-mismatch")
        self.assertEqual(by_id["replay"]["status"], "unknown")
        self.assertEqual(by_id["replay"]["reason"], "reconciliation-needed")
        self.assertEqual(by_id["replay"]["holder_instance_id"], "holder-old")
        self.assertEqual(by_id["replay"]["dispatch_event_cursor"], 3)
        self.assertEqual(by_id["replay"]["evidence"]["send"]["marker"], "maybe-sent")
        replay_cmds = [row["command"] for row in commands(self.log) if row["session"] == "zcode-KPR-i244-replay"]
        self.assertEqual(replay_cmds, ["status"])
        self.assertNotIn("send", {row["command"] for row in commands(self.log)})
        self.assertNotIn("start", replay_cmds)

    def test_shared_seat_blocks_the_pair_and_an_independent_item_runs(self) -> None:
        install_fake(self.skills, ["droid", "zcode"])
        repo = str(self.repo)
        self.use_spec({
            "droid-KPR-i244-a": {"status": absent(repo), "start": started(repo, "auto"), "send": sent()},
            "droid-KPR-i244-b": {"status": absent(repo), "start": started(repo, "claude-opus-5-5", "high"), "send": sent()},
            "zcode-KPR-i244-free": {"status": absent(repo), "start": started(repo, "GLM-5.3", "max"), "send": sent("fp-free")},
        })
        auth = self.authorization([
            {"id": "droid/default", "state": "granted", "shared_seat": "droid", "count": 1},
            {"id": "droid/opus", "state": "granted", "shared_seat": "droid", "count": 1},
        ])
        plan = self.plan([
            {"item_id": "a", "preset": "droid/default", "session": "droid-KPR-i244-a", "prompt": "a"},
            {"item_id": "b", "preset": "droid/opus", "session": "droid-KPR-i244-b", "prompt": "b"},
            {"item_id": "free", "preset": "zcode/default", "session": "zcode-KPR-i244-free", "prompt": "c"},
        ])
        payload = self.execute(plan, auth, self.availability(["droid/default", "droid/opus", "zcode/default"]))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["a"]["reason"], "resource-conflict")
        self.assertEqual(by_id["b"]["reason"], "resource-conflict")
        self.assertIn("b", by_id["a"]["conflicts_with"])
        self.assertEqual(by_id["free"]["status"], "in-flight")
        sessions = {row["session"] for row in commands(self.log)}
        self.assertNotIn("droid-KPR-i244-a", sessions)
        self.assertNotIn("droid-KPR-i244-b", sessions)
        self.assertIn("zcode-KPR-i244-free", sessions)

    def test_shared_droid_pool_admits_two_items_and_refuses_a_third(self) -> None:
        presets = ["droid/default", "droid/opus", "droid/core"]
        auth = self.authorization([
            {"id": preset, "state": "granted", "shared_seat": "droid", "count": 2}
            for preset in presets
        ], elite_cap=4)
        plan = self.plan([
            {"item_id": preset, "preset": preset,
             "session": f"droid-KPR-i261-{preset.split('/')[-1]}", "prompt": preset}
            for preset in presets
        ])
        available = self.availability(presets)
        live = write_json(self.root, "live-empty.json", {"rows": []})

        payload = self.execute_dry_run(plan, auth, available, live)

        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(payload["effective_cap"], 4, payload)
        self.assertEqual(by_id["droid/default"]["reason"], "dry-run", payload)
        self.assertEqual(by_id["droid/opus"]["reason"], "dry-run", payload)
        self.assertEqual(by_id["droid/core"]["reason"], "shared-occupied", payload)
        self.assertFalse(self.log.exists(), "dry-run must not call a Runner")

    def test_one_live_droid_uses_one_slot_of_the_shared_pool(self) -> None:
        repo = str(self.repo)
        presets = ["droid/default", "droid/opus", "droid/core"]
        auth = self.authorization([
            {"id": preset, "state": "granted", "shared_seat": "droid", "count": 2}
            for preset in presets
        ], elite_cap=4)
        plan = self.plan([
            {"item_id": "default", "preset": "droid/default",
             "session": "droid-KPR-i261-live-combined-default", "prompt": "default"},
            {"item_id": "core", "preset": "droid/core",
             "session": "droid-KPR-i261-live-combined-core", "prompt": "core"},
        ])
        available = self.availability(presets)
        live = write_json(self.root, "live-droid.json", {"rows": [{
            "platform": "droid", "preset": "droid/opus", "shared_seat": "droid",
            "session": "droid-KPR-i261-live-opus", "repo": repo, "state": "ready",
            "holder_instance_id": "holder-live", "identity": "verified",
        }]})

        payload = self.execute_dry_run(plan, auth, available, live)

        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(payload["effective_cap"], 4, payload)
        self.assertEqual(by_id["default"]["reason"], "dry-run", payload)
        self.assertEqual(by_id["core"]["reason"], "shared-occupied", payload)
        self.assertFalse(self.log.exists(), "dry-run must not call a Runner")

    def test_write_overlap_is_a_conflict_and_pool_ignores_the_seat_cap(self) -> None:
        install_fake(self.skills, ["codex", "cursor-cli", "zcode"])
        repo = str(self.repo)
        self.use_spec({
            "codex-KPR-i244-cap1": {
                "status": absent(repo),
                "start": started(repo, "gpt-6.1-sol", "high"),
                "send": sent("fp-cap"),
            },
            "cursor-cli-KPR-i244-cap2": {
                "status": absent(repo),
                "start": started(repo, "grok-4.7-xhigh"),
                "send": sent("fp-cap2"),
            },
            "zcode-KPR-i244-pool": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max"),
                "send": sent("fp-pool"),
            },
            "zcode-KPR-i244-w1": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max"),
                "send": sent("fp-w1"),
            },
            "opencode-KPR-i244-w2": {
                "status": absent(repo),
                "start": started(repo, "x"),
                "send": sent("fp-w2"),
            },
        })
        install_fake(self.skills, ["codex", "cursor-cli", "zcode", "opencode"])
        auth = self.authorization([
            {"id": "codex/default", "state": "granted"},
            {"id": "cursor-cli/default", "state": "granted"},
        ])
        plan = self.plan([
            {
                "item_id": "elite-1", "preset": "codex/default", "session": "codex-KPR-i244-cap1",
                "prompt": "a", "resources": {"writes": ["same.md"]},
            },
            {
                "item_id": "elite-2", "preset": "cursor-cli/default", "session": "cursor-cli-KPR-i244-cap2",
                "prompt": "b", "resources": {"writes": ["same.md"]},
            },
            {"item_id": "pool", "preset": "zcode/default", "session": "zcode-KPR-i244-pool", "prompt": "c"},
        ], seat_cap=1)
        payload = self.execute(plan, auth, self.availability(["codex/default", "cursor-cli/default", "zcode/default"]))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["elite-1"]["reason"], "resource-conflict")
        self.assertEqual(by_id["elite-2"]["reason"], "resource-conflict")
        self.assertEqual(by_id["pool"]["status"], "in-flight")

        cap_plan = self.plan([
            {"item_id": "elite-1", "preset": "codex/default", "session": "codex-KPR-i244-cap1", "prompt": "a"},
            {"item_id": "elite-2", "preset": "cursor-cli/default", "session": "cursor-cli-KPR-i244-cap2", "prompt": "b"},
            {"item_id": "pool", "preset": "zcode/default", "session": "zcode-KPR-i244-pool", "prompt": "c"},
        ], seat_cap=1)
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(cap_plan, auth, self.availability(["codex/default", "cursor-cli/default", "zcode/default"]))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["elite-1"]["status"], "in-flight")
        self.assertEqual(by_id["elite-2"]["status"], "not-run")
        self.assertEqual(by_id["elite-2"]["reason"], "seat-cap")
        self.assertEqual(by_id["pool"]["status"], "in-flight")

    def test_single_item_and_bounded_parallel_admission(self) -> None:
        install_fake(self.skills, ["zcode", "opencode", "dsh"])
        repo = str(self.repo)
        self.use_spec({
            "zcode-KPR-i244-one": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max"),
                "send": sent("fp-one"),
            }
        })
        auth = self.authorization()
        one = self.plan([{
            "item_id": "one", "preset": "zcode/default", "session": "zcode-KPR-i244-one", "prompt": "only",
        }])
        payload = self.execute(one, auth, self.availability(["zcode/default"]))
        self.assertEqual(payload["items"][0]["status"], "in-flight")
        self.assertEqual(payload["items"][0]["reason"], "admitted")
        self.assertEqual(len(payload["items"]), 1)

        self.use_spec({
            "zcode-KPR-i244-p1": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max"), "send": sent("fp-p1"),
            },
            "opencode-KPR-i244-p2": {
                "status": absent(repo),
                "start": started(repo, "opencode-go/deepseek-v4.1-flash"), "send": sent("fp-p2"),
            },
            "dsh-KPR-i244-p3": {
                "status": absent(repo),
                "start": started(repo, "opencode-go/deepseek-v4.1-flash"), "send": sent("fp-p3"),
            },
        })
        parallel = self.plan([
            {"item_id": "p1", "preset": "zcode/default", "session": "zcode-KPR-i244-p1", "prompt": "a"},
            {"item_id": "p2", "preset": "opencode/default", "session": "opencode-KPR-i244-p2", "prompt": "b"},
            {"item_id": "p3", "preset": "dsh/default", "session": "dsh-KPR-i244-p3", "prompt": "c"},
        ])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(parallel, auth, self.availability(["zcode/default", "opencode/default", "dsh/default"]))
        self.assertTrue(all(item["status"] == "in-flight" for item in payload["items"]), payload)
        self.assertEqual(len([row for row in commands(self.log) if row["command"] == "start"]), 3)

    def test_production_scope_calls_no_runner(self) -> None:
        install_fake(self.skills, ["zcode"])
        self.use_spec({})
        auth = self.authorization()
        plan = self.plan(
            [{"item_id": "mutate", "preset": "zcode/default", "session": "zcode-KPR-i244-mut", "prompt": "edit"}],
            scope="implement",
        )
        payload = self.execute(plan, auth)
        self.assertEqual(payload["items"][0]["status"], "not-run")
        self.assertEqual(payload["items"][0]["reason"], "scope-outside-bounded")
        self.assertEqual(commands(self.log), [])

        repo = str(self.repo)
        prompt = "u"
        session = "zcode-KPR-i244-refused-replay"
        sha = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        self.use_spec({
            session: {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max", holder="holder-new"),
                "send": sent("fp-replayed"),
            },
        })
        kept = write_json(self.root, "refused-index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [{
                "item_id": "unk",
                "preset": "zcode/default",
                "platform": "zcode",
                "session": session,
                "repo": repo,
                "holder_instance_id": "holder-u",
                "prompt_sha256": sha,
                "prompt_fingerprint": sha,
                "status": "unknown",
                "reason": "send-timeout",
                "dispatch_event_cursor": 4,
                "evidence": {"send": {"marker": "maybe-sent"}},
            }],
        })
        original = kept.read_bytes()
        item = {"item_id": "unk", "preset": "zcode/default", "session": session, "prompt": prompt}
        refused_plan = self.plan([item], mutation=True)
        live = write_json(self.root, "refused-live.json", {"rows": []})
        if self.log.exists():
            self.log.unlink()
        code, refused = run([
            "execute", "--plan", str(refused_plan), "--authorization", str(auth),
            "--availability", str(self.availability(["zcode/default"])),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
            "--index", str(kept), "--live", str(live),
        ], self.env)
        self.assertEqual(code, 0, refused)
        self.assertEqual(refused["items"][0]["reason"], "scope-outside-bounded")
        self.assertEqual(kept.read_bytes(), original)
        self.assertEqual(commands(self.log), [])
        corrected = self.plan([item])
        code, nxt = run([
            "execute", "--plan", str(corrected), "--authorization", str(auth),
            "--availability", str(self.availability(["zcode/default"])),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
            "--index", str(kept), "--live", str(live),
        ], self.env)
        self.assertEqual(code, 0, nxt)
        self.assertEqual(nxt["items"][0]["status"], "unknown")
        self.assertEqual(nxt["items"][0]["reason"], "reconciliation-needed")
        self.assertEqual(Path(nxt["items"][0]["repo"]).resolve(), Path(repo).resolve())
        replay_cmds = [row["command"] for row in commands(self.log) if row["session"] == session]
        self.assertEqual(replay_cmds, ["status"])

    def test_snapshot_round_trips_one_nested_object(self) -> None:
        state = {
            "project": {"goal": "检查 \"引号\" 与中文"},
            "authorization": {"capability_summary": {"text": "Expert not granted"}, "grants": []},
        }
        path = write_json(self.root, "state.json", state)
        out = self.root / "heartbeat-prompt.json"
        code, payload = run(["snapshot", "--state", str(path), "--out", str(out)], self.env)
        self.assertEqual(code, 0, payload)
        outer = json.loads(out.read_text(encoding="utf-8"))
        self.assertIsInstance(outer["body"], str)
        self.assertNotIn("schema", outer)
        self.assertEqual(set(outer), {"body"})
        self.assertEqual(json.loads(outer["body"]), state)

    def test_installed_layout_finds_sibling_platform_manifests(self) -> None:
        skill_scripts = self.root / "skills" / "kaola-project-runner" / "scripts"
        skill_scripts.mkdir(parents=True)
        (skill_scripts / "kaola-dispatch.py").write_bytes(SCRIPT.read_bytes())
        (skill_scripts / "kaola-record-contract.py").write_bytes(RECORD.read_bytes())
        worker = self.root / "skills" / "zcode-kaola-project-runner" / "scripts"
        worker.mkdir(parents=True)
        (worker / "platform.yaml").write_bytes((PLATFORMS / "zcode.yaml").read_bytes())
        auth = self.authorization()
        proc = subprocess.run(
            [sys.executable, str(skill_scripts / "kaola-dispatch.py"), "project",
             "--authorization", str(auth)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertEqual([item["id"] for item in payload["candidates"]], ["zcode/default"])

    def test_applied_evidence_ignores_resolved_values(self) -> None:
        install_fake(self.skills, ["codex", "cursor-cli"])
        repo = str(self.repo)
        self.use_spec({
            "codex-KPR-i244-sol": {
                "status": absent(repo),
                "start": started(repo, "sol", "high", nest=True),
                "send": sent("fp-sol"),
            },
            "codex-KPR-i244-refuse": {
                "status": absent(repo),
                "start": started(repo, "gpt-6-luna", unapplied=True),
                "send": sent("fp-refuse"),
            },
            "cursor-cli-KPR-i244-map": {
                "status": absent(repo),
                "start": started(
                    repo, "grok-4.7", "xhigh", mapped=True, requested_id="grok-4.7-xhigh",
                ),
                "send": sent("fp-map"),
            },
        })
        auth = self.authorization([
            {"id": "codex/luna", "state": "granted"},
            {"id": "cursor-cli/default", "state": "granted"},
        ])
        plan = self.plan([
            {"item_id": "sol", "preset": "codex/luna", "session": "codex-KPR-i244-sol", "prompt": "a"},
            {"item_id": "refuse", "preset": "codex/luna", "session": "codex-KPR-i244-refuse", "prompt": "b"},
            {"item_id": "mapped", "preset": "cursor-cli/default", "session": "cursor-cli-KPR-i244-map", "prompt": "c"},
        ])
        payload = self.execute(plan, auth, self.availability(["codex/luna", "cursor-cli/default"]))
        by_id = {item["item_id"]: item for item in payload["items"]}
        sol = by_id["sol"]["selection"]
        self.assertEqual(sol["source"], "start_evidence.config_application")
        self.assertEqual(sol["applied"]["model_id"], "sol")
        self.assertEqual(sol["applied"]["effort"], "high")
        self.assertNotEqual(sol["applied"]["model_id"], "gpt-6-luna")
        self.assertEqual(sol["fields"]["model_id"]["applied"], "mismatch")
        self.assertEqual(by_id["sol"]["status"], "failed")
        refused = by_id["refuse"]["selection"]
        self.assertIsNone(refused["applied"]["model_id"])
        self.assertEqual(refused["applied_state"]["model_id"], "unapplied")
        self.assertEqual(by_id["refuse"]["status"], "failed")
        mapped = by_id["mapped"]["selection"]
        self.assertEqual(mapped["applied"]["model_id"], "grok-4.7-xhigh")
        self.assertEqual(mapped["fields"]["model_id"]["applied"], "match")
        self.assertEqual(mapped["fields"]["effort"]["applied"], "match")
        self.assertEqual(by_id["mapped"]["status"], "in-flight")
        self.assertNotIn("codex-KPR-i244-sol", {row["session"] for row in commands(self.log) if row["command"] == "send"})

    def test_timeout_and_unknown_mutation_are_not_failed_or_returned(self) -> None:
        install_fake(self.skills, ["zcode"])
        repo = str(self.repo)
        self.env["KAOLA_DISPATCH_RUNNER_TIMEOUT"] = "2"
        self.use_spec({
            "zcode-KPR-i244-hang": {
                "status": absent(repo),
                "hang": ["start"],
                "hang_for": 30,
                "send": sent(),
            },
            "zcode-KPR-i244-junk": {
                "status": absent(repo),
                "garbage": ["start"],
                "send": sent(),
            },
            "zcode-KPR-i244-unksend": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max"),
                "send": {"outcome": "unknown", "mutation_status": "unknown"},
            },
        })
        auth = self.authorization()
        plan = self.plan([
            {"item_id": "hang", "preset": "zcode/default", "session": "zcode-KPR-i244-hang", "prompt": "a"},
            {"item_id": "junk", "preset": "zcode/default", "session": "zcode-KPR-i244-junk", "prompt": "b"},
            {"item_id": "unk", "preset": "zcode/default", "session": "zcode-KPR-i244-unksend", "prompt": "c"},
        ])
        payload = self.execute(plan, auth, self.availability(["zcode/default"]))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["hang"]["status"], "unknown")
        self.assertEqual(by_id["hang"]["reason"], "start-timeout")
        self.assertEqual(by_id["junk"]["status"], "unknown")
        self.assertEqual(by_id["junk"]["reason"], "start-unreadable")
        self.assertEqual(by_id["unk"]["status"], "unknown")
        self.assertEqual(by_id["unk"]["reason"], "mutation-unknown")
        self.assertNotIn("failed", {item["status"] for item in payload["items"]})

    def test_collect_returns_one_finished_branch_and_leaves_the_other(self) -> None:
        install_fake(self.skills, ["zcode", "dsh"])
        repo = str(self.repo)
        self.use_spec({
            "zcode-KPR-i244-done": {
                "status": {
                    "repo": repo,
                    "session": "zcode-KPR-i244-done",
                    "holder_instance_id": "holder-done",
                    "turn_active": False,
                    "turn_outcome": "turn_completed",
                    "stop_reason": "end_turn",
                    "mutation_status": "completed",
                    "last_prompt": {
                        "fingerprint": "fp-done",
                        "stop_reason": "end_turn",
                        "mutation_status": "completed",
                    },
                },
                "capture": {"events": [{"role": "assistant", "text": "finished report"}]},
            },
            "dsh-KPR-i244-slow": {
                "status": {
                    "repo": repo,
                    "session": "dsh-KPR-i244-slow",
                    "holder_instance_id": "holder-slow",
                    "turn_active": True,
                    "turn_outcome": "in_progress",
                    "mutation_status": "in_progress",
                    "last_prompt": {"fingerprint": "fp-slow"},
                },
                "capture": {"events": [{"role": "assistant", "text": "not yet"}]},
            },
            "zcode-KPR-i244-idle": {
                "status": {
                    "repo": repo,
                    "session": "zcode-KPR-i244-idle",
                    "holder_instance_id": "holder-idle",
                    "turn_active": False,
                    "mutation_status": "not_started",
                    "last_prompt": {"fingerprint": "fp-idle"},
                },
                "capture": {"events": []},
            },
        })
        index = write_json(self.root, "index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [
                {
                    "item_id": "done", "preset": "zcode/default", "platform": "zcode",
                    "session": "zcode-KPR-i244-done", "repo": repo,
                    "holder_instance_id": "holder-done", "prompt_fingerprint": "fp-done",
                    "prompt_sha256": "fp-done", "status": "in-flight", "acceptance": "pending",
                    "dispatch_event_cursor": 3,
                },
                {
                    "item_id": "slow", "preset": "dsh/default", "platform": "dsh",
                    "session": "dsh-KPR-i244-slow", "repo": repo,
                    "holder_instance_id": "holder-slow", "prompt_fingerprint": "fp-slow",
                    "prompt_sha256": "fp-slow", "status": "in-flight", "acceptance": "pending",
                },
                {
                    "item_id": "idle", "preset": "zcode/default", "platform": "zcode",
                    "session": "zcode-KPR-i244-idle", "repo": repo,
                    "holder_instance_id": "holder-idle", "prompt_fingerprint": "fp-idle",
                    "prompt_sha256": "fp-idle", "status": "in-flight", "acceptance": "pending",
                },
            ],
        })
        payload = self.collect(index)
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["done"]["status"], "returned")
        self.assertEqual(by_id["done"]["reason"], "collected")
        self.assertEqual(by_id["done"]["acceptance"], "pending")
        self.assertEqual(by_id["done"]["result"]["excerpt"], "finished report")
        self.assertEqual(by_id["done"]["result"]["cursor"], 3)
        self.assertEqual(by_id["slow"]["status"], "in-flight")
        self.assertEqual(by_id["slow"]["reason"], "still-running")
        self.assertEqual(by_id["idle"]["status"], "in-flight")
        self.assertEqual(by_id["idle"]["reason"], "no-result")
        self.assertNotEqual(by_id["idle"]["status"], "returned")
        disk = json.loads(index.read_text(encoding="utf-8"))
        self.assertEqual({item["item_id"] for item in disk["items"]}, {"done", "slow", "idle"})
        self.assertEqual(payload["phase"], "collection")

    def test_collect_excerpt_reads_capture_event_stream(self) -> None:
        install_fake(self.skills, ["dsh"])
        repo = str(self.repo)
        first = "The admission is not the result. "
        second = "Collect reads the reply after end_turn."
        padding = "x" * 500
        self.use_spec({
            "dsh-KPR-i244-research-b": {
                "status": {
                    "repo": repo,
                    "session": "dsh-KPR-i244-research-b",
                    "holder_instance_id": "holder-b",
                    "turn_active": False,
                    "turn_outcome": "turn_completed",
                    "stop_reason": "end_turn",
                    "mutation_status": "completed",
                    "last_prompt": {
                        "fingerprint": "fp-b",
                        "stop_reason": "end_turn",
                        "mutation_status": "completed",
                    },
                },
                "capture": {"events": [
                    {"cursor": 12, "kind": "session_update", "update": {
                        "sessionUpdate": "tool_call",
                        "content": {"type": "text", "text": "tool noise"},
                    }},
                    {"cursor": 13, "kind": "session_update", "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": first},
                    }},
                    {"cursor": 14, "kind": "session_update", "update": {
                        "sessionUpdate": "usage_update", "usage": {"total": 3},
                    }},
                    {"cursor": 15, "kind": "session_update", "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": second + padding},
                    }},
                ]},
            },
        })
        index = write_json(self.root, "stream-index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [{
                "item_id": "research-b", "preset": "dsh/default", "platform": "dsh",
                "session": "dsh-KPR-i244-research-b", "repo": repo,
                "holder_instance_id": "holder-b", "prompt_fingerprint": "fp-b",
                "prompt_sha256": "fp-b", "status": "in-flight", "acceptance": "pending",
                "dispatch_event_cursor": 11,
            }],
        })
        payload = self.collect(index)
        item = payload["items"][0]
        self.assertEqual(item["status"], "returned")
        self.assertEqual(item["reason"], "collected")
        self.assertEqual(item["stop_reason"], "end_turn")
        joined = first + second + padding
        self.assertEqual(item["result"]["excerpt"], joined[:480])
        self.assertEqual(len(item["result"]["excerpt"]), 480)
        self.assertNotIn("tool noise", item["result"]["excerpt"])
        self.assertEqual(item["result"]["cursor"], 11)
        self.assertEqual(item["capture_since"], 11)
        capture = next(row for row in commands(self.log) if row["command"] == "capture")
        self.assertEqual(capture["argv"][capture["argv"].index("--since") + 1], "11")

    def test_collect_excerpt_survives_more_than_forty_events_before_the_reply(self) -> None:
        install_fake(self.skills, ["zcode"])
        repo = str(self.repo)
        reply = "the reply after the thought window"
        events = [
            {"cursor": 12 + index, "kind": "session_update", "update": {
                "sessionUpdate": "agent_thought_chunk",
                "content": {"type": "text", "text": f"thought {index}"},
            }}
            for index in range(41)
        ]
        events.append({"cursor": 53, "kind": "session_update", "update": {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": reply},
        }})
        self.use_spec({
            "zcode-KPR-i244-long": {
                "status": {
                    "repo": repo,
                    "session": "zcode-KPR-i244-long",
                    "holder_instance_id": "holder-long",
                    "turn_active": False,
                    "turn_outcome": "turn_completed",
                    "stop_reason": "end_turn",
                    "mutation_status": "completed",
                    "last_prompt": {
                        "fingerprint": "fp-long",
                        "stop_reason": "end_turn",
                        "mutation_status": "completed",
                    },
                },
                "capture": {"events": events},
            },
        })
        index = write_json(self.root, "long-index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [{
                "item_id": "long", "preset": "zcode/default", "platform": "zcode",
                "session": "zcode-KPR-i244-long", "repo": repo,
                "holder_instance_id": "holder-long", "prompt_fingerprint": "fp-long",
                "prompt_sha256": "fp-long", "status": "in-flight", "acceptance": "pending",
                "dispatch_event_cursor": 11,
            }],
        })
        payload = self.collect(index)
        item = payload["items"][0]
        self.assertEqual(item["status"], "returned")
        self.assertEqual(item["reason"], "collected")
        self.assertEqual(item["result"]["excerpt"], reply)
        self.assertNotIn("thought 0", item["result"]["excerpt"])
        capture = next(row for row in commands(self.log) if row["command"] == "capture")
        self.assertNotIn("--lines", capture["argv"])
        self.assertEqual(capture["argv"][capture["argv"].index("--since") + 1], "11")

    def test_grant_state_cap_and_owner_precedence(self) -> None:
        auth = self.authorization([
            {"id": "claude-code/opus-xhigh", "state": "expired"},
            {"id": "claude-code/sonnet", "state": "withdrawn"},
            {"id": "zcode/default", "state": "unknown"},
            {"id": "codex/default", "state": "0 live"},
        ])
        payload = self.project(auth, self.availability([
            "claude-code/opus-xhigh", "claude-code/sonnet", "zcode/default", "codex/default",
        ]))
        withheld = {row["id"]: row["reason"] for row in payload["withheld"]}
        self.assertEqual(withheld["claude-code/opus-xhigh"], "state-unreadable")
        self.assertEqual(withheld["claude-code/sonnet"], "state-unreadable")
        self.assertEqual(withheld["zcode/default"], "state-unreadable")
        self.assertIn("codex/default", {item["id"] for item in payload["candidates"]})

        install_fake(self.skills, ["claude-code", "codex", "zcode"])
        repo = str(self.repo)
        self.use_spec({
            "claude-code-KPR-i244-opus": {
                "status": absent(repo),
                "start": started(repo, "opus", "xhigh"),
                "send": sent("fp-opus"),
            },
            "claude-code-KPR-i244-sonnet": {
                "status": absent(repo),
                "start": started(repo, "sonnet", "high"),
                "send": sent("fp-sonnet"),
            },
            "codex-KPR-i244-owner": {
                "status": absent(repo),
                "start": started(repo, "gpt-6-luna", "high"),
                "send": sent("fp-owner"),
            },
            "codex-KPR-i244-bare": {
                "status": absent(repo),
                "start": started(repo, "gpt-6.1-sol", "high"),
                "send": sent("fp-bare"),
            },
            "zcode-KPR-i244-switch": {
                "status": absent(repo),
                "start": started(repo, "other-model", "max"),
                "send": sent("fp-switch"),
            },
        })
        capped = self.authorization([
            {"id": "claude-code/opus-xhigh", "state": "granted"},
            {"id": "claude-code/sonnet", "state": "granted"},
        ], elite_cap=1)
        plan = self.plan([
            {"item_id": "opus", "preset": "claude-code/opus-xhigh", "session": "claude-code-KPR-i244-opus", "prompt": "a"},
            {"item_id": "sonnet", "preset": "claude-code/sonnet", "session": "claude-code-KPR-i244-sonnet", "prompt": "b"},
        ])
        payload = self.execute(plan, capped, self.availability(["claude-code/opus-xhigh", "claude-code/sonnet"]))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["opus"]["status"], "in-flight")
        self.assertEqual(by_id["sonnet"]["reason"], "seat-cap")
        wide = self.plan([
            {"item_id": "opus", "preset": "claude-code/opus-xhigh", "session": "claude-code-KPR-i244-opus", "prompt": "a"},
            {"item_id": "sonnet", "preset": "claude-code/sonnet", "session": "claude-code-KPR-i244-sonnet", "prompt": "b"},
        ], seat_cap=5)
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(wide, capped, self.availability(["claude-code/opus-xhigh", "claude-code/sonnet"]))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["sonnet"]["reason"], "seat-cap")
        self.assertEqual(payload["effective_cap"], 1)

        live = write_json(self.root, "live.json", {"rows": [
            {
                "platform": "claude-code",
                "session": "claude-code-KPR-i244-live-worker",
                "repo": repo,
                "state": "ready",
                "holder_instance_id": "holder-live-worker",
                "mutation_status": "in_progress",
                "host_class": False,
            },
        ]})
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(plan, capped, self.availability(["claude-code/opus-xhigh", "claude-code/sonnet"]), live=live)
        self.assertTrue(all(item["reason"] == "occupancy-unknown" for item in payload["items"]), payload)
        self.assertEqual(commands(self.log), [])

        omitted = self.authorization([
            {"id": "claude-code/opus-xhigh", "state": "granted"},
        ], elite_cap=1)
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(plan, omitted, self.availability(["claude-code/opus-xhigh"]), live="omit")
        self.assertEqual(payload["items"][0]["reason"], "occupancy-unknown")

        owner = self.authorization([
            {"id": "codex/luna", "state": "granted", "special_requirements": {"effort": "high", "task_scope": "visual QA"}},
        ])
        owner_plan = self.plan([{
            "item_id": "owner",
            "preset": "codex/luna",
            "session": "codex-KPR-i244-owner",
            "prompt": "look",
            "overrides": {"effort": "max"},
        }])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(owner_plan, owner, self.availability(["codex/luna"]))
        item = payload["items"][0]
        self.assertEqual(item["status"], "not-run")
        self.assertEqual(item["reason"], "override-conflicts-owner")
        self.assertEqual(commands(self.log), [])

        passed = self.plan([{
            "item_id": "owner",
            "preset": "codex/luna",
            "session": "codex-KPR-i244-owner",
            "prompt": "look",
        }])
        payload = self.execute(passed, owner, self.availability(["codex/luna"]))
        item = payload["items"][0]
        self.assertEqual(item["status"], "in-flight")
        self.assertEqual(item["task_scope"], "visual QA")
        start = next(row for row in commands(self.log) if row["command"] == "start")
        self.assertEqual(start["argv"][start["argv"].index("--effort") + 1], "high")

        bare = self.authorization([{"id": "codex/default", "state": "granted"}])
        bare_plan = self.plan([{
            "item_id": "bare",
            "preset": "codex/default",
            "session": "codex-KPR-i244-bare",
            "prompt": "look",
            "overrides": {"model": "gpt-6.1-sol"},
        }])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(bare_plan, bare, self.availability(["codex/default"]))
        item = payload["items"][0]
        self.assertEqual(item["status"], "in-flight")
        self.assertEqual(item["selection"]["requested"]["effort"], None)
        self.assertEqual(item["selection"]["fields"]["effort"]["applied"], "not-requested")
        start = next(row for row in commands(self.log) if row["command"] == "start")
        self.assertNotIn("--effort", start["argv"])
        self.assertEqual(start["argv"][start["argv"].index("--model") + 1], "gpt-6.1-sol")

        switched = self.authorization()
        switch_plan = self.plan([{
            "item_id": "switch",
            "preset": "zcode/default",
            "session": "zcode-KPR-i244-switch",
            "prompt": "look",
            "overrides": {"model": "other-model"},
        }])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(switch_plan, switched, self.availability(["zcode/default"]))
        self.assertEqual(payload["items"][0]["status"], "not-run")
        self.assertEqual(payload["items"][0]["reason"], "model-switch-unauthorized")
        self.assertEqual(commands(self.log), [])

    def test_summary_does_not_advertise_denied_visual(self) -> None:
        auth = self.authorization([
            {"id": "devin/fable", "state": "granted"},
            {"id": "claude-code/opus-xhigh", "state": "granted"},
            {"id": "claude-code/sonnet", "state": "granted"},
        ])
        payload = self.project(auth, self.availability([
            "devin/fable", "claude-code/opus-xhigh", "claude-code/sonnet", "claude-code/fable",
        ]))
        text = payload["capability_summary"]["text"]
        fable = next(item for item in payload["candidates"] if item["id"] == "devin/fable")
        self.assertIn("devin/fable", payload["capability_summary"]["presets"])
        self.assertIn("Non-visual", fable["profile"])
        self.assertNotIn("visual", text.lower())
        self.assertNotIn(fable["profile"], text)
        self.assertNotIn("claude-code/fable", payload["capability_summary"]["presets"])
        self.assertNotIn("Design, goal definition", text)
        self.assertEqual(fable["class"], "Expert")

    def test_authorization_keys_resources_and_launch_edges(self) -> None:
        prose = self.authorization([{"id": "claude-code/opus-xhigh", "state": "已撤销"}])
        payload = self.project(prose, self.availability(["claude-code/opus-xhigh"]))
        prose_row = next(row for row in payload["withheld"] if row["id"] == "claude-code/opus-xhigh")
        self.assertEqual(prose_row["reason"], "state-unreadable")
        self.assertNotIn("claude-code/opus-xhigh", {item["id"] for item in payload["candidates"]})
        refused = self.plan([{
            "item_id": "unread", "preset": "claude-code/opus-xhigh",
            "session": "claude-code-KPR-i244-unread", "prompt": "no",
        }])
        payload = self.execute(refused, prose, self.availability(["claude-code/opus-xhigh"]))
        self.assertEqual(payload["items"][0]["status"], "not-run")
        self.assertEqual(payload["items"][0]["reason"], "state-unreadable")

        rows = write_json(self.root, "rows-auth.json", {
            "rows": [{"id": "claude-code/opus-xhigh", "class": "Elite"}],
            "classes": {"Expert": "e", "Elite": "l", "Worker": "w"},
        })
        payload = self.project(rows, self.availability(["claude-code/opus-xhigh", "zcode/default"]))
        self.assertNotIn("claude-code/opus-xhigh", {item["id"] for item in payload["candidates"]})

        excluded = self.authorization(
            [{"id": "codex/default", "state": "granted"}],
            exclusions=["codex/default"],
            paused=["zcode/default"],
        )
        payload = self.project(excluded, self.availability(["codex/default", "zcode/default"]))
        withheld = {row["id"]: row["reason"] for row in payload["withheld"]}
        self.assertEqual(withheld["codex/default"], "excluded")
        self.assertEqual(withheld["zcode/default"], "paused")

        install_fake(self.skills, ["codex", "zcode"])
        repo = str(self.repo)
        link = self.root / "repo-link"
        link.symlink_to(self.repo, target_is_directory=True)
        real = str(self.repo.resolve())
        self.use_spec({
            "codex-KPR-i244-link": {
                "status": absent(real),
                "start": started(real, "gpt-6-luna", "max"),
                "send": sent("fp-link"),
            },
            "codex-KPR-i244-hold": {
                "status": absent(real),
                "start": started(real, "gpt-6-luna", "max", holder="new-holder"),
                "send": sent("fp-hold"),
            },
            "codex-KPR-i244-live": {
                "status": {
                    "repo": real,
                    "holder_instance_id": "holder-live",
                    "mutation_status": "not_started",
                    "prompt_fingerprint": "sha256:stale",
                },
                "send": sent("fp-first"),
            },
            "zcode-KPR-i244-dup1": {
                "status": absent(real),
                "start": started(real, "GLM-5.3", "max"),
                "send": sent("fp-dup"),
            },
            "codex-KPR-i244-list": {
                "status": absent(real),
                "start": {
                    **started(real, "gpt-6-luna", "max"),
                    "effective_selection": {"effective_model": ["opencode-go", "deepseek-v4.1-flash"], "effective_effort": "max"},
                },
                "send": sent("fp-list"),
            },
            "codex-KPR-i244-reject": {
                "status": absent(real),
                "start": {**started(real, "gpt-6-luna", "max"), "model_verified": False},
                "send": sent("fp-reject"),
            },
        })
        linked = write_json(self.root, "linked-plan.json", {
            "scope": "research",
            "repo": str(link) + "/",
            "items": [{
                "item_id": "linked",
                "preset": "codex/luna",
                "session": "codex-KPR-i244-link",
                "prompt": "look",
                "role": None,
            }],
        })
        auth = self.authorization()
        payload = self.execute(linked, auth, self.availability(["codex/luna"]))
        self.assertEqual(payload["items"][0]["status"], "in-flight")
        self.assertEqual(payload["repo"], real)
        self.assertNotIn("role", payload["items"][0])

        absent_holder = self.plan([{
            "item_id": "orphan",
            "preset": "codex/luna",
            "session": "codex-KPR-i244-hold",
            "prompt": "look",
            "expected_holder_instance_id": "holder-old",
        }])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(absent_holder, auth, self.availability(["codex/luna"]))
        self.assertEqual(payload["items"][0]["status"], "not-run")
        self.assertEqual(payload["items"][0]["reason"], "expected-holder-absent")
        self.assertNotIn("start", {row["command"] for row in commands(self.log)})

        first = self.plan([{
            "item_id": "first",
            "preset": "codex/luna",
            "session": "codex-KPR-i244-live",
            "prompt": "fresh",
        }])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(first, auth, self.availability(["codex/luna"]))
        self.assertEqual(payload["items"][0]["status"], "in-flight")
        self.assertEqual(payload["items"][0]["reason"], "admitted")
        self.assertIn("send", {row["command"] for row in commands(self.log)})

        dup = self.plan([
            {"item_id": "d1", "preset": "zcode/default", "session": "zcode-KPR-i244-dup1", "prompt": "a"},
            {"item_id": "d2", "preset": "zcode/default", "session": "zcode-KPR-i244-dup1", "prompt": "b"},
        ])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(dup, auth, self.availability(["zcode/default"]))
        self.assertTrue(all(item["reason"] == "duplicate-session" for item in payload["items"]))
        self.assertEqual(commands(self.log), [])

        messy = self.plan([{
            "item_id": "w1", "preset": "zcode/default", "session": "zcode-KPR-i244-wA", "prompt": "a",
            "resources": {"writes": "docs/a.md"},
        }])
        payload = self.execute(messy, auth, self.availability(["zcode/default"]))
        self.assertEqual(payload["items"][0]["reason"], "resources-unreadable")
        self.assertEqual(commands(self.log), [])
        ports = self.plan([{
            "item_id": "ports", "preset": "zcode/default", "session": "zcode-KPR-i244-ports", "prompt": "a",
            "resources": {"ports": [8080]},
        }])
        payload = self.execute(ports, auth, self.availability(["zcode/default"]))
        self.assertEqual(payload["items"][0]["reason"], "resources-unreadable")
        self.assertEqual(payload["items"][0]["detail"], "ports must be strings")

        counted = self.authorization([{"id": "codex/luna", "state": "granted", "count": 1}])
        live = write_json(self.root, "unnamed-live.json", {"rows": [
            {"platform": "codex", "repo": real, "state": "running"},
        ]})
        one = self.plan([{"item_id": "c", "preset": "codex/luna", "session": "codex-KPR-i244-count", "prompt": "a"}])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(one, counted, self.availability(["codex/luna"]), live=live)
        self.assertEqual(payload["items"][0]["reason"], "occupancy-unknown")
        named = write_json(self.root, "named-live.json", {"rows": [
            {"preset": "codex/luna", "platform": "codex", "repo": real, "state": "running"},
        ]})
        payload = self.execute(one, counted, self.availability(["codex/luna"]), live=named)
        self.assertEqual(payload["items"][0]["reason"], "count")

        listed = self.plan([{
            "item_id": "listed", "preset": "codex/luna", "session": "codex-KPR-i244-list", "prompt": "a",
        }])
        payload = self.execute(listed, auth, self.availability(["codex/luna"]))
        self.assertEqual(payload["items"][0]["status"], "in-flight")
        self.assertEqual(payload["items"][0]["selection"]["fields"]["model_id"]["advertised"], "unknown")
        self.assertEqual(payload["items"][0]["selection"]["comparison"], "match")

        rejected = self.plan([{
            "item_id": "rejected", "preset": "codex/luna", "session": "codex-KPR-i244-reject", "prompt": "a",
        }])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(rejected, auth, self.availability(["codex/luna"]))
        self.assertEqual(payload["items"][0]["status"], "failed")
        self.assertEqual(payload["items"][0]["reason"], "selection-mismatch")
        self.assertIsNone(payload["items"][0]["selection"]["applied"]["model_id"])
        self.assertNotIn("send", {row["command"] for row in commands(self.log)})

    def test_host_class_row_is_not_a_worker_seat(self) -> None:
        install_fake(self.skills, ["claude-code", "codex"])
        repo = str(self.repo)
        self.use_spec({
            "claude-code-KPR-i244-hostcap": {
                "status": absent(repo),
                "start": started(repo, "opus", "xhigh"),
                "send": sent("fp-hostcap"),
            },
            "codex-KPR-i244-hostcount": {
                "status": absent(repo),
                "start": started(repo, "gpt-6.1-sol", "high"),
                "send": sent("fp-hostcount"),
            },
        })
        host = write_json(self.root, "host-live.json", {"rows": [{
            "platform": "codex",
            "session": "codex-KPR-orchestrator-main",
            "repo": repo,
            "state": "ready",
            "holder_instance_id": "holder-host",
            "mutation_status": "in_progress",
            "host_class": True,
        }]})
        capped = self.authorization(
            [{"id": "claude-code/opus-xhigh", "state": "granted"}], elite_cap=1,
        )
        plan = self.plan([{
            "item_id": "opus", "preset": "claude-code/opus-xhigh",
            "session": "claude-code-KPR-i244-hostcap", "prompt": "a",
        }])
        payload = self.execute(plan, capped, self.availability(["claude-code/opus-xhigh"]), live=host)
        self.assertEqual(payload["items"][0]["status"], "in-flight")
        self.assertEqual(payload["items"][0]["reason"], "admitted")
        self.assertEqual(payload["effective_cap"], 1)

        counted = self.authorization([{"id": "codex/default", "state": "granted", "count": 1}])
        one = self.plan([{
            "item_id": "c", "preset": "codex/default",
            "session": "codex-KPR-i244-hostcount", "prompt": "a",
        }])
        payload = self.execute(one, counted, self.availability(["codex/default"]), live=host)
        self.assertEqual(payload["items"][0]["status"], "in-flight")
        self.assertNotEqual(payload["items"][0]["reason"], "occupancy-unknown")

        shared = self.authorization([
            {"id": "codex/default", "state": "granted", "shared_seat": "codex"},
        ])
        payload = self.execute(one, shared, self.availability(["codex/default"]), live=host)
        self.assertEqual(payload["items"][0]["status"], "in-flight")
        self.assertNotEqual(payload["items"][0]["reason"], "shared-occupied")

    def prestarted(self, session: str, model: str, effort: str, holder: str,
                   mutation: str = "not_started") -> tuple[dict, dict]:
        """A live list row and its matching status receipt: started, unprompted."""
        repo = str(self.repo)
        status = {**started(repo, model, effort, holder=holder), "session": session,
                  "mutation_status": mutation}
        row = {"platform": session.split("-KPR-")[0], "session": session, "repo": repo,
               "state": "ready", "identity": "verified", "holder_instance_id": holder,
               "mutation_status": mutation}
        return row, status

    def test_a_prestarted_unprompted_named_seat_is_the_items_own_occupancy(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        row_a, status_a = self.prestarted("codex-KPR-i255-a", "gpt-6-luna", "max", "h-a")
        row_b, status_b = self.prestarted("codex-KPR-i255-b", "gpt-6-luna", "max", "h-b")
        self.use_spec({
            "codex-KPR-i255-a": {"status": status_a, "send": sent("fp-a")},
            "codex-KPR-i255-b": {"status": status_b, "send": sent("fp-b")},
            "codex-KPR-i255-c": {"status": absent(repo), "start": started(repo, "gpt-6-luna", "max"),
                                 "send": sent("fp-c")},
        })
        live = write_json(self.root, "prestarted.json", {"rows": [row_a, row_b]})
        auth = self.authorization([{"id": "codex/luna", "state": "granted", "count": 2}])
        plan = self.plan([
            {"item_id": item, "preset": "codex/luna", "session": f"codex-KPR-i255-{item}", "prompt": item}
            for item in ("a", "b", "c")
        ])
        index = self.root / "held-index.json"
        payload = self.execute(plan, auth, self.availability(["codex/luna"]), live=live, index=index)
        by_id = {item["item_id"]: item for item in payload["items"]}
        for item, holder in (("a", "h-a"), ("b", "h-b")):
            self.assertEqual((by_id[item]["status"], by_id[item]["reason"]), ("in-flight", "admitted"), payload)
            self.assertEqual(by_id[item]["holder_instance_id"], holder)
            self.assertIn("seat_note", by_id[item]["evidence"])
        self.assertEqual((by_id["c"]["status"], by_id["c"]["reason"]), ("not-run", "count"))
        calls = [(row["command"], row["session"][-1]) for row in commands(self.log)]
        self.assertNotIn("start", {command for command, _ in calls})
        self.assertEqual(sorted(s for c, s in calls if c == "send"), ["a", "b"])
        self.assertNotIn("c", {s for _, s in calls}, "a refused absent item reaches no Runner command")
        holders = {row["session"][-1]: row["argv"][row["argv"].index("--expected-holder-instance-id") + 1]
                   for row in commands(self.log) if row["command"] == "send"}
        self.assertEqual(holders, {"a": "h-a", "b": "h-b"})
        stored = {row["item_id"]: row for row in json.loads(index.read_text())["items"]}
        self.assertEqual(stored["a"]["holder_instance_id"], "h-a")
        self.assertEqual(stored["c"]["reason"], "count")

        # With the count at one, the other live seat fills it; it is not subtracted.
        one = self.authorization([{"id": "codex/luna", "state": "granted", "count": 1}])
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(self.plan([plan_item("a")]), one, self.availability(["codex/luna"]), live=live)
        self.assertEqual(payload["items"][0]["reason"], "count", payload)
        self.assertNotIn("send", {row["command"] for row in commands(self.log)})

    def test_a_held_seat_still_meets_the_global_cap_and_shared_seat(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        row_a, status_a = self.prestarted("codex-KPR-i255-a", "gpt-6.1-sol", "high", "h-a")
        self.use_spec({
            "codex-KPR-i255-a": {"status": status_a, "send": sent("fp-a")},
            "codex-KPR-i255-c": {"status": absent(repo), "start": started(repo, "gpt-6.1-sol", "high"),
                                 "send": sent("fp-c")},
        })
        live = write_json(self.root, "prestarted.json", {"rows": [row_a]})
        items = [{"item_id": item, "preset": "codex/default", "session": f"codex-KPR-i255-{item}", "prompt": item}
                 for item in ("a", "c")]
        capped = self.authorization([{"id": "codex/default", "state": "granted"}], elite_cap=1)
        capped = capped.rename(self.root / "capped.json")
        payload = self.execute(self.plan(items), capped, self.availability(["codex/default"]), live=live)
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["a"]["reason"], "admitted", payload)
        self.assertEqual(by_id["c"]["reason"], "seat-cap")
        self.assertNotIn("start", {row["command"] for row in commands(self.log)})

        shared = self.authorization([{"id": "codex/default", "state": "granted", "shared_seat": "codex"}])
        shared = shared.rename(self.root / "shared.json")
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(self.plan(items[:1]), shared, self.availability(["codex/default"]), live=live)
        self.assertEqual(payload["items"][0]["reason"], "admitted", payload)
        payload = self.execute(self.plan(items[1:]), shared, self.availability(["codex/default"]), live=live)
        self.assertEqual(payload["items"][0]["reason"], "shared-occupied", payload)

        other, _ = self.prestarted("codex-KPR-i255-other", "gpt-6.1-sol", "high", "h-o")
        other["preset"] = "codex/default"
        crowded = write_json(self.root, "crowded.json", {"rows": [row_a, other]})
        payload = self.execute(self.plan(items[:1]), capped, self.availability(["codex/default"]), live=crowded)
        self.assertEqual(payload["items"][0]["reason"], "seat-cap", "another live seat is not subtracted")
        payload = self.execute(self.plan(items[:1]), shared, self.availability(["codex/default"]), live=crowded)
        self.assertEqual(payload["items"][0]["reason"], "shared-occupied")

        # That refusal recorded nothing sent: once the other seat is gone the
        # retry sends the first prompt instead of calling the seat unbound.
        index = self.root / "retry-index.json"
        self.execute(self.plan(items[:1]), capped, self.availability(["codex/default"]), live=crowded, index=index)
        self.assertEqual(json.loads(index.read_text())["items"][0]["reason"], "seat-cap")
        self.log.write_text("", encoding="utf-8")
        payload = self.execute(self.plan(items[:1]), capped, self.availability(["codex/default"]), live=live,
                               prior_index=index, index=index)
        self.assertEqual((payload["items"][0]["status"], payload["items"][0]["reason"]),
                         ("in-flight", "admitted"), payload)
        self.assertEqual([row["command"] for row in commands(self.log) if row["command"] != "status"], ["send"])

    def test_only_an_exact_verified_unprompted_seat_is_held(self) -> None:
        install_fake(self.skills, ["codex"])
        auth = self.authorization([{"id": "codex/luna", "state": "granted", "count": 1}])
        avail = self.availability(["codex/luna"])
        cases = {
            "identity": ({"identity": "unknown"}, {}, {}),
            "prompted": ({"mutation_status": "completed"}, {"mutation_status": "completed"}, {}),
            "holder": ({}, {}, {"expected_holder_instance_id": "h-other"}),
            "foreign": ({"repo": "/elsewhere"}, {"repo": "/elsewhere"}, {}),
            "preset": ({}, {"config_application": {"model": {"applied": True, "value": "gpt-6.1-sol"},
                                                   "effort": {"applied": True, "value": "high"}}}, {}),
            "status-holder": ({}, {"holder_instance_id": "h-swapped"}, {}),
        }
        for name, (row_change, status_change, item_change) in cases.items():
            with self.subTest(name):
                session = "codex-KPR-i255-a"
                row, status = self.prestarted(session, "gpt-6-luna", "max", "h-a")
                row.update(row_change)
                status.update(status_change)
                self.use_spec({session: {"status": status, "send": sent("fp-a")}})
                self.log.write_text("", encoding="utf-8")
                live = write_json(self.root, "edge.json", {"rows": [row]})
                plan = self.plan([{**plan_item("a"), **item_change}])
                payload = self.execute(plan, auth, avail, live=live)
                self.assertNotEqual(payload["items"][0]["status"], "in-flight", payload)
                self.assertNotIn("seat_note", payload["items"][0]["evidence"])
                self.assertNotIn("send", {row["command"] for row in commands(self.log)})
                self.assertNotIn("start", {row["command"] for row in commands(self.log)})

        # Prompted between the list and the send: the first-send path sends nothing.
        session = "codex-KPR-i255-a"
        row, status = self.prestarted(session, "gpt-6-luna", "max", "h-a")
        raced = {**status, "mutation_status": "in_progress", "last_prompt": {"fingerprint": "fp-host"}}
        self.use_spec({session: {"status": status, "status_second": raced, "send": sent("fp-a")}})
        self.log.write_text("", encoding="utf-8")
        live = write_json(self.root, "raced.json", {"rows": [row]})
        payload = self.execute(self.plan([plan_item("a")]), auth, avail, live=live)
        self.assertEqual(payload["items"][0]["status"], "unknown", payload)
        self.assertNotIn("send", {row["command"] for row in commands(self.log)})

    def test_skeleton_example_sets_effective_cap(self) -> None:
        text = (REPO / "templates/orchestrator/references/heartbeat-skeleton.txt").read_text(encoding="utf-8")
        example = json.loads(re.search(r"例：(\{.*\})", text).group(1))
        self.assertEqual(example["authorization"]["elite_cap"], 4)
        self.assertNotIn("limits", example["authorization"])
        self.assertIn("model_switch", text)
        self.assertIn("model_switches", text)
        rendered = (ORCHESTRATOR / "references" / "heartbeat-skeleton.md").read_text(encoding="utf-8")
        self.assertIn('"elite_cap":4', rendered)
        self.assertLessEqual(len(rendered.encode()), 8192)
        install_fake(self.skills, ["zcode"])
        auth = write_json(self.root, "skeleton-auth.json", example["authorization"])
        plan = self.plan([{
            "item_id": "pool", "preset": "zcode/default",
            "session": "zcode-KPR-i244-skel", "prompt": "a",
        }])
        avail = self.availability(["zcode/default"])
        live = write_json(self.root, "live-empty.json", {"rows": []})
        code, payload = run([
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--availability", str(avail), "--platforms", str(PLATFORMS),
            "--skills-root", str(self.skills), "--dry-run", "--live", str(live),
        ], self.env)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["effective_cap"], 4)
        self.assertEqual(payload["items"][0]["reason"], "dry-run")

    def test_collect_terminal_outcome_and_stopped_seat(self) -> None:
        install_fake(self.skills, ["zcode"])
        repo = str(self.repo)
        self.use_spec({
            "zcode-KPR-i244-crash": {
                "status": {
                    "repo": repo,
                    "session": "zcode-KPR-i244-crash",
                    "holder_instance_id": "holder-crash",
                    "turn_active": False,
                    "turn_outcome": "process_exited",
                    "mutation_status": "in_progress",
                    "last_prompt": {"fingerprint": "fp-crash"},
                },
                "capture": {"events": [{"role": "assistant", "text": "should not collect"}]},
            },
            "zcode-KPR-i244-stopped": {
                "status": {
                    "repo": repo,
                    "session": "zcode-KPR-i244-stopped",
                    "outcome": "stopped",
                    "state": "stopped",
                    "stopped": True,
                    "residual_pids": [],
                    "holder_instance_id": "holder-stopped",
                    "mutation_status": "completed",
                    "record": {
                        "state": "stopped",
                        "holder_instance_id": "holder-stopped",
                        "last_prompt": {
                            "fingerprint": "fp-stopped",
                            "stop_reason": "end_turn",
                            "mutation_status": "completed",
                        },
                    },
                },
                "capture": {"events": [{"role": "assistant", "text": "stopped report"}]},
            },
        })
        index = write_json(self.root, "terminal-index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [
                {
                    "item_id": "crash", "preset": "zcode/default", "platform": "zcode",
                    "session": "zcode-KPR-i244-crash", "repo": repo,
                    "holder_instance_id": "holder-crash", "prompt_fingerprint": "fp-crash",
                    "prompt_sha256": "fp-crash", "status": "in-flight", "acceptance": "pending",
                },
                {
                    "item_id": "stopped", "preset": "zcode/default", "platform": "zcode",
                    "session": "zcode-KPR-i244-stopped", "repo": repo,
                    "holder_instance_id": "holder-stopped", "prompt_fingerprint": "fp-stopped",
                    "prompt_sha256": "fp-stopped", "status": "in-flight", "acceptance": "pending",
                    "dispatch_event_cursor": 4,
                },
            ],
        })
        payload = self.collect(index)
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["crash"]["status"], "failed")
        self.assertEqual(by_id["crash"]["reason"], "turn-failed")
        self.assertNotIn("result", by_id["crash"])
        self.assertEqual(by_id["stopped"]["status"], "returned")
        self.assertEqual(by_id["stopped"]["reason"], "collected")
        self.assertEqual(by_id["stopped"]["result"]["excerpt"], "stopped report")
        self.assertEqual(by_id["stopped"]["result"]["stop_reason"], "end_turn")
        self.assertNotIn("zcode-KPR-i244-crash", {row["session"] for row in commands(self.log) if row["command"] == "capture"})

    def test_stopped_session_name_is_not_absent(self) -> None:
        install_fake(self.skills, ["zcode"])
        repo = str(self.repo)
        self.use_spec({
            "zcode-KPR-i244-reuse": {
                "status": {
                    "repo": repo,
                    "outcome": "stopped",
                    "state": "stopped",
                    "stopped": True,
                    "residual_pids": [],
                    "record": {
                        "state": "stopped",
                        "last_prompt": {
                            "fingerprint": "fp-old",
                            "stop_reason": "end_turn",
                            "mutation_status": "completed",
                        },
                    },
                },
                "start": started(repo, "GLM-5.3", "max"),
                "send": sent("fp-reuse"),
            },
        })
        plan = self.plan([{
            "item_id": "reuse", "preset": "zcode/default",
            "session": "zcode-KPR-i244-reuse", "prompt": "again",
        }])
        payload = self.execute(plan, self.authorization(), self.availability(["zcode/default"]))
        self.assertEqual(payload["items"][0]["status"], "unknown")
        self.assertEqual(payload["items"][0]["reason"], "existing-session-ambiguous")
        self.assertNotIn("start", {row["command"] for row in commands(self.log)})

    def test_send_holder_mismatch_is_unknown(self) -> None:
        install_fake(self.skills, ["zcode"])
        repo = str(self.repo)
        self.use_spec({
            "zcode-KPR-i244-mismatch": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max", holder="holder-live"),
                "send": {
                    "error": {"code": "holder-instance-mismatch", "message": "holder"},
                    "mutation_status": "not_started",
                },
            },
            "zcode-KPR-i244-refused": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max"),
                "send": {"result": "refused"},
            },
        })
        mismatch = self.plan([{
            "item_id": "mismatch", "preset": "zcode/default",
            "session": "zcode-KPR-i244-mismatch", "prompt": "a",
        }])
        payload = self.execute(mismatch, self.authorization(), self.availability(["zcode/default"]))
        self.assertEqual(payload["items"][0]["status"], "unknown")
        self.assertEqual(payload["items"][0]["reason"], "holder-mismatch")
        refused = self.plan([{
            "item_id": "refused", "preset": "zcode/default",
            "session": "zcode-KPR-i244-refused", "prompt": "b",
        }])
        payload = self.execute(refused, self.authorization(), self.availability(["zcode/default"]))
        self.assertEqual(payload["items"][0]["status"], "failed")
        self.assertEqual(payload["items"][0]["reason"], "send-failed")

    def test_heartbeat_envelope_feeds_project_and_execute(self) -> None:
        state = {
            "project": {"repo": str(self.repo)},
            "authorization": {
                "grants": [{"id": "claude-code/opus-xhigh", "state": "granted"}],
                "paused": ["codex/luna"],
                "revoked": ["devin/default"],
                "elite_cap": 1,
            },
        }
        auth = write_json(self.root, "heartbeat.json", {"body": json.dumps(state)})
        present = [
            "claude-code/opus-xhigh", "zcode/default", "dsh/default",
            "opencode/default", "codex/luna", "devin/default",
        ]
        payload = self.project(auth, self.availability(present))
        ids = {item["id"] for item in payload["candidates"]}
        self.assertIn("claude-code/opus-xhigh", ids)
        self.assertNotIn("codex/luna", ids)
        self.assertNotIn("devin/default", ids)
        withheld = {row["id"]: row["reason"] for row in payload["withheld"]}
        self.assertEqual(withheld["codex/luna"], "paused")
        self.assertEqual(withheld["devin/default"], "revoked")
        install_fake(self.skills, ["claude-code", "codex", "devin"])
        repo = str(self.repo)
        self.use_spec({
            "claude-code-KPR-i244-env": {
                "status": absent(repo),
                "start": started(repo, "opus", "xhigh"),
                "send": sent("fp-env"),
            },
        })
        plan = self.plan([
            {"item_id": "elite", "preset": "claude-code/opus-xhigh", "session": "claude-code-KPR-i244-env", "prompt": "a"},
            {"item_id": "paused", "preset": "codex/luna", "session": "codex-KPR-i244-paused", "prompt": "b"},
            {"item_id": "revoked", "preset": "devin/default", "session": "devin-KPR-i244-revoked", "prompt": "c"},
        ])
        payload = self.execute(plan, auth, self.availability(present))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["elite"]["status"], "in-flight")
        self.assertEqual(by_id["elite"]["reason"], "admitted")
        self.assertEqual(by_id["paused"]["reason"], "paused")
        self.assertEqual(by_id["revoked"]["reason"], "revoked")
        sessions = {row["session"] for row in commands(self.log)}
        self.assertIn("claude-code-KPR-i244-env", sessions)
        self.assertNotIn("codex-KPR-i244-paused", sessions)
        self.assertNotIn("devin-KPR-i244-revoked", sessions)
        bad = write_json(self.root, "bad-heartbeat.json", {"body": "not-json"})
        code, error = run(
            ["project", "--authorization", str(bad), "--platforms", str(PLATFORMS)],
            self.env,
        )
        self.assertEqual(code, 2)
        self.assertEqual(error["reason"], "invalid-input")
        self.assertNotIn("candidates", error)

    def test_live_rows_use_status_selection_not_platform_class(self) -> None:
        install_fake(self.skills, ["codex", "devin", "claude-code", "zcode", "droid"])
        repo = str(self.repo)
        self.use_spec({
            "codex-KPR-i244-live-luna": {"status": started(repo, "gpt-6-luna", "max")},
            "devin-KPR-i244-live-devin": {"status": started(repo, "swe-2-max", "")},
            "claude-code-KPR-i244-live-opus": {"status": started(repo, "opus", "xhigh")},
            "droid-KPR-i244-live-opus": {"status": started(repo, "claude-opus-5-5", "high")},
            "zcode-KPR-i244-pool": {
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max"),
                "send": sent("fp-pool"),
            },
            "claude-code-KPR-i244-sonnet": {
                "status": absent(repo),
                "start": started(repo, "sonnet", "high"),
                "send": sent("fp-sonnet"),
            },
            "codex-KPR-i244-default": {
                "status": absent(repo),
                "start": started(repo, "gpt-6.1-sol", "high"),
                "send": sent("fp-def"),
            },
            "droid-KPR-i244-new": {
                "status": absent(repo),
                "start": started(repo, "claude-opus-5-5", "high"),
                "send": sent("fp-newd"),
            },
        })

        def live(rows: list[dict]) -> Path:
            return write_json(self.root, "sel-live.json", {"rows": rows})

        workers = [
            {"platform": "codex", "session": "codex-KPR-i244-live-luna", "repo": repo, "state": "ready", "holder_instance_id": "h-luna"},
            {"platform": "devin", "session": "devin-KPR-i244-live-devin", "repo": repo, "state": "ready", "holder_instance_id": "h-devin"},
            {"platform": "claude-code", "session": "claude-code-KPR-i244-live-opus", "repo": repo, "state": "ready", "holder_instance_id": "h-opus"},
        ]
        room = self.authorization([
            {"id": "claude-code/opus-xhigh", "state": "granted"},
            {"id": "claude-code/sonnet", "state": "granted"},
        ], elite_cap=2)
        plan = self.plan([
            {"item_id": "sonnet", "preset": "claude-code/sonnet", "session": "claude-code-KPR-i244-sonnet", "prompt": "a"},
            {"item_id": "pool", "preset": "zcode/default", "session": "zcode-KPR-i244-pool", "prompt": "b"},
        ])
        present = ["claude-code/sonnet", "claude-code/opus-xhigh", "zcode/default"]
        payload = self.execute(plan, room, self.availability(present), live=live(workers))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["sonnet"]["status"], "in-flight", payload)
        self.assertEqual(by_id["pool"]["status"], "in-flight", payload)
        tight = self.authorization([{"id": "claude-code/sonnet", "state": "granted"}], elite_cap=1)
        payload = self.execute(
            self.plan([{"item_id": "sonnet", "preset": "claude-code/sonnet", "session": "claude-code-KPR-i244-sonnet", "prompt": "a"}]),
            tight, self.availability(["claude-code/sonnet"]), live=live(workers),
        )
        self.assertEqual(payload["items"][0]["reason"], "seat-cap")
        shared_auth = self.authorization([
            {"id": "droid/opus", "state": "granted", "shared_seat": "seat-alpha"},
            {"id": "codex/default", "state": "granted", "shared_seat": "codex"},
        ], elite_cap=4)
        shared_rows = [workers[0], {
            "platform": "droid", "session": "droid-KPR-i244-live-opus", "repo": repo,
            "state": "ready", "holder_instance_id": "h-droid",
        }]
        payload = self.execute(self.plan([
            {"item_id": "label", "preset": "codex/default", "session": "codex-KPR-i244-default", "prompt": "a"},
            {"item_id": "seat", "preset": "droid/opus", "session": "droid-KPR-i244-new", "prompt": "b"},
        ]), shared_auth, self.availability(["codex/default", "droid/opus"]), live=live(shared_rows))
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["label"]["status"], "in-flight", payload)
        self.assertNotEqual(by_id["label"]["reason"], "shared-occupied")
        self.assertEqual(by_id["seat"]["reason"], "shared-occupied")

    def test_admitted_assignment_keeps_its_index_at_an_occupied_cap(self) -> None:
        install_fake(self.skills, ["claude-code", "droid"])
        repo = str(self.repo)
        prompt = "stay"
        sha = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        self.use_spec({
            "claude-code-KPR-i244-kept": {
                "status": {
                    "repo": repo,
                    "holder_instance_id": "holder-kept",
                    "mutation_status": "in_progress",
                    "outcome": "in_progress",
                    "prompt_fingerprint": sha,
                },
            },
            "droid-KPR-i244-live": {"status": started(repo, "claude-opus-5-5", "high")},
        })
        index = write_json(self.root, "kept-index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [{
                "item_id": "kept",
                "preset": "claude-code/opus-xhigh",
                "platform": "claude-code",
                "session": "claude-code-KPR-i244-kept",
                "repo": repo,
                "holder_instance_id": "holder-kept",
                "prompt_sha256": sha,
                "prompt_fingerprint": sha,
                "status": "in-flight",
                "acceptance": "pending",
                "dispatch_event_cursor": 12,
                "evidence": {"start": {"marker": "kept-start"}},
            }],
        })
        live = write_json(self.root, "kept-live.json", {"rows": [
            {
                "platform": "claude-code", "session": "claude-code-KPR-i244-kept",
                "repo": repo, "state": "ready", "holder_instance_id": "holder-kept",
            },
            {
                "platform": "droid", "session": "droid-KPR-i244-live",
                "repo": repo, "state": "ready", "holder_instance_id": "holder-droid",
            },
        ]})
        auth = self.authorization([
            {"id": "claude-code/opus-xhigh", "state": "granted", "count": 1},
            {"id": "claude-code/sonnet", "state": "granted"},
            {"id": "droid/opus", "state": "granted", "shared_seat": "seat-alpha", "count": 1},
        ], elite_cap=1)
        plan = self.plan([
            {"item_id": "kept", "preset": "claude-code/opus-xhigh", "session": "claude-code-KPR-i244-kept", "prompt": prompt},
            {"item_id": "cap", "preset": "claude-code/sonnet", "session": "claude-code-KPR-i244-cap", "prompt": "new"},
            {"item_id": "count", "preset": "claude-code/opus-xhigh", "session": "claude-code-KPR-i244-count", "prompt": "other"},
            {"item_id": "seat", "preset": "droid/opus", "session": "droid-KPR-i244-seat", "prompt": "seat"},
        ])
        code, payload = run([
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--availability", str(self.availability([
                "claude-code/opus-xhigh", "claude-code/sonnet", "droid/opus",
            ])),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
            "--index", str(index), "--live", str(live),
        ], self.env)
        self.assertEqual(code, 0, payload)
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["kept"]["reason"], "already-admitted")
        self.assertEqual(by_id["kept"]["holder_instance_id"], "holder-kept")
        self.assertEqual(by_id["kept"]["dispatch_event_cursor"], 12)
        self.assertEqual(by_id["kept"]["evidence"]["start"]["marker"], "kept-start")
        self.assertEqual(by_id["cap"]["reason"], "seat-cap")
        self.assertEqual(by_id["count"]["reason"], "count")
        self.assertEqual(by_id["seat"]["reason"], "shared-occupied")
        seen = commands(self.log)
        self.assertNotIn("send", {row["command"] for row in seen if row["session"] == "claude-code-KPR-i244-kept"})
        self.assertFalse(any(
            row["session"] in {"claude-code-KPR-i244-cap", "claude-code-KPR-i244-count", "droid-KPR-i244-seat"}
            for row in seen
        ))
        disk = json.loads(index.read_text(encoding="utf-8"))
        kept = next(item for item in disk["items"] if item["item_id"] == "kept")
        self.assertEqual(kept["reason"], "already-admitted")
        self.assertEqual(kept["evidence"]["start"]["marker"], "kept-start")

    def test_mapped_dsh_worker_row_admits_authorized_elite(self) -> None:
        install_fake(self.skills, ["dsh", "claude-code"])
        repo = str(self.repo)
        worker = "dsh-KPR-i244-live-worker"
        elite = "claude-code-KPR-i244-mapped-elite"
        extra = "dsh-KPR-i244-another-worker"
        self.use_spec({
            worker: {
                "status": started(
                    repo, '["opencode-go","deepseek-v4.1-flash"]',
                    mapped=True, requested_id="opencode-go/deepseek-v4.1-flash", nest=True,
                    holder="holder-dsh",
                ),
            },
            elite: {
                "status": absent(repo),
                "start": started(repo, "opus", "xhigh", holder="holder-elite"),
                "send": sent(),
            },
            extra: {"status": absent(repo)},
        })
        live = write_json(self.root, "mapped-live.json", {"rows": [{
            "platform": "dsh", "session": worker, "repo": repo,
            "state": "ready", "holder_instance_id": "holder-dsh", "host_class": False,
        }]})
        auth = self.authorization([
            {"id": "dsh/default", "state": "granted", "count": 1},
            {"id": "claude-code/opus-xhigh", "state": "granted"},
        ], elite_cap=1)
        plan = self.plan([
            {"item_id": "elite", "preset": "claude-code/opus-xhigh", "session": elite, "prompt": "design"},
            {"item_id": "extra", "preset": "dsh/default", "session": extra, "prompt": "another"},
        ])
        payload = self.execute(
            plan, auth, self.availability(["dsh/default", "claude-code/opus-xhigh"]), live=live,
        )
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["elite"]["status"], "in-flight", payload)
        self.assertEqual(by_id["elite"]["reason"], "admitted")
        self.assertEqual(by_id["extra"]["status"], "not-run")
        self.assertEqual(by_id["extra"]["reason"], "count")
        self.assertNotIn("occupancy-unknown", {item["reason"] for item in payload["items"]})
        seen = {row["command"] for row in commands(self.log) if row["session"] == worker}
        self.assertIn("status", seen)
        self.assertNotIn("start", seen)

    def test_kept_item_with_absent_session_is_not_sent_again(self) -> None:
        install_fake(self.skills, ["claude-code", "droid"])
        repo = str(self.repo)
        prompt = "stay-gone"
        sha = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        kept_session = "claude-code-KPR-i244-gone"
        live_session = "droid-KPR-i244-fills-cap"
        self.use_spec({
            kept_session: {
                "status": absent(repo),
                "start": started(repo, "opus", "xhigh", holder="holder-new"),
                "send": sent(),
            },
            live_session: {"status": started(repo, "claude-opus-5-5", "high", holder="holder-droid")},
        })
        index = write_json(self.root, "gone-index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [{
                "item_id": "kept",
                "preset": "claude-code/opus-xhigh",
                "platform": "claude-code",
                "session": kept_session,
                "repo": repo,
                "holder_instance_id": "holder-kept",
                "prompt_sha256": sha,
                "prompt_fingerprint": sha,
                "status": "in-flight",
                "acceptance": "pending",
                "dispatch_event_cursor": 12,
                "result": {"excerpt": "still-bound"},
                "evidence": {"start": {"marker": "kept-start"}},
            }],
        })
        live = write_json(self.root, "gone-live.json", {"rows": [{
            "platform": "droid", "session": live_session, "repo": repo,
            "state": "ready", "holder_instance_id": "holder-droid",
        }]})
        auth = self.authorization([
            {"id": "claude-code/opus-xhigh", "state": "granted"},
            {"id": "droid/opus", "state": "granted"},
        ], elite_cap=1)
        plan = self.plan([
            {"item_id": "kept", "preset": "claude-code/opus-xhigh", "session": kept_session, "prompt": prompt},
        ])
        code, payload = run([
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--availability", str(self.availability(["claude-code/opus-xhigh", "droid/opus"])),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
            "--index", str(index), "--live", str(live),
        ], self.env)
        self.assertEqual(code, 0, payload)
        row = payload["items"][0]
        self.assertEqual(row["status"], "in-flight")
        self.assertEqual(row["reason"], "session-gone")
        self.assertNotEqual(row["status"], "not-run")
        self.assertEqual(row["holder_instance_id"], "holder-kept")
        self.assertEqual(row["dispatch_event_cursor"], 12)
        self.assertEqual(row["evidence"]["start"]["marker"], "kept-start")
        self.assertEqual(row["result"], {"excerpt": "still-bound"})
        kept_cmds = [item["command"] for item in commands(self.log) if item["session"] == kept_session]
        self.assertEqual(kept_cmds, ["status"])
        disk = json.loads(index.read_text(encoding="utf-8"))
        stored = disk["items"][0]
        self.assertEqual(stored["status"], "in-flight")
        self.assertEqual(stored["reason"], "session-gone")
        self.assertEqual(stored["holder_instance_id"], "holder-kept")
        self.assertEqual(stored["evidence"]["start"]["marker"], "kept-start")

    def test_dry_run_reconciles_kept_item_without_starting(self) -> None:
        install_fake(self.skills, ["claude-code"])
        repo = str(self.repo)
        prompt = "stay-dry"
        sha = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        session = "claude-code-KPR-i244-dry-kept"
        self.use_spec({
            session: {
                "status": absent(repo),
                "start": started(repo, "opus", "xhigh", holder="holder-new"),
                "send": sent(),
            },
        })
        index = write_json(self.root, "dry-kept-index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [{
                "item_id": "kept",
                "preset": "claude-code/opus-xhigh",
                "platform": "claude-code",
                "session": session,
                "repo": repo,
                "holder_instance_id": "holder-kept",
                "prompt_sha256": sha,
                "prompt_fingerprint": sha,
                "status": "in-flight",
                "acceptance": "pending",
                "dispatch_event_cursor": 12,
                "result": {"excerpt": "still-bound"},
                "evidence": {"start": {"marker": "kept-start"}},
            }],
        })
        auth = self.authorization([
            {"id": "claude-code/opus-xhigh", "state": "granted"},
        ], elite_cap=1)
        plan = self.plan([
            {"item_id": "kept", "preset": "claude-code/opus-xhigh", "session": session, "prompt": prompt},
        ])
        live = write_json(self.root, "dry-live.json", {"rows": []})
        original = index.read_bytes()
        code, payload = run([
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--availability", str(self.availability(["claude-code/opus-xhigh"])),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
            "--index", str(index), "--live", str(live), "--dry-run",
        ], self.env)
        self.assertEqual(code, 0, payload)
        row = payload["items"][0]
        self.assertEqual(row["status"], "not-run")
        self.assertEqual(row["reason"], "reconciled")
        self.assertIs(row["dry_run"], True)
        self.assertEqual(row["holder_instance_id"], "holder-kept")
        self.assertEqual(row["dispatch_event_cursor"], 12)
        self.assertEqual(row["evidence"]["start"]["marker"], "kept-start")
        self.assertEqual(row["result"], {"excerpt": "still-bound"})
        self.assertEqual(commands(self.log), [])
        self.assertEqual(index.read_bytes(), original)
        refused = self.plan([
            {"item_id": "kept", "preset": "claude-code/opus-xhigh", "session": session, "prompt": prompt},
        ], mutation=True)
        code, payload = run([
            "execute", "--plan", str(refused), "--authorization", str(auth),
            "--availability", str(self.availability(["claude-code/opus-xhigh"])),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
            "--index", str(index), "--live", str(live), "--dry-run",
        ], self.env)
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["items"][0]["reason"], "scope-outside-bounded")
        self.assertEqual(index.read_bytes(), original)
        self.assertEqual(json.loads(original)["items"][0]["status"], "in-flight")
        collected = self.collect(index)
        self.assertEqual(collected["items"][0]["item_id"], "kept")
        self.assertIn("status", {item["command"] for item in commands(self.log) if item["session"] == session})

    def test_blocked_row_keeps_prior_binding(self) -> None:
        install_fake(self.skills, ["claude-code"])
        repo = str(self.repo)
        cases = (
            ("unknown", "send-timeout", "maybe-sent"),
            ("failed", "selection-mismatch", "mismatch-start"),
        )
        for prior_status, prior_reason, marker in cases:
            with self.subTest(prior_status=prior_status, prior_reason=prior_reason):
                if self.log.exists():
                    self.log.unlink()
                prompt = "stuck-" + prior_status
                sha = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                session = f"claude-code-KPR-i244-{prior_status}"
                self.use_spec({
                    session: {
                        "status": started(repo, "opus", "xhigh", holder="holder-live"),
                        "start": started(repo, "opus", "xhigh", holder="holder-new"),
                        "send": sent(),
                    },
                })
                index = write_json(self.root, f"blocked-{prior_status}.json", {
                    "schema": "kaola-dispatch-index/1",
                    "correlation_only": True,
                    "repo": repo,
                    "items": [{
                        "item_id": "stuck",
                        "preset": "claude-code/opus-xhigh",
                        "platform": "claude-code",
                        "session": session,
                        "repo": repo,
                        "holder_instance_id": "holder-stuck",
                        "prompt_sha256": sha,
                        "prompt_fingerprint": sha,
                        "status": prior_status,
                        "reason": prior_reason,
                        "acceptance": "pending",
                        "dispatch_event_cursor": 9,
                        "result": {"excerpt": marker},
                        "evidence": {"send": {"marker": marker}},
                    }],
                })
                live = write_json(self.root, f"blocked-live-{prior_status}.json", {"rows": [{
                    "platform": "claude-code", "session": session, "repo": repo,
                    "state": "ready", "holder_instance_id": "holder-live",
                }]})
                auth = self.authorization([
                    {"id": "claude-code/opus-xhigh", "state": "granted"},
                ], elite_cap=1)
                plan = self.plan([
                    {"item_id": "stuck", "preset": "claude-code/opus-xhigh", "session": session, "prompt": prompt},
                ])
                code, payload = run([
                    "execute", "--plan", str(plan), "--authorization", str(auth),
                    "--availability", str(self.availability(["claude-code/opus-xhigh"])),
                    "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
                    "--index", str(index), "--live", str(live),
                ], self.env)
                self.assertEqual(code, 0, payload)
                row = payload["items"][0]
                self.assertEqual(row["status"], prior_status, payload)
                self.assertEqual(row["reason"], prior_reason)
                self.assertNotEqual(row["status"], "not-run")
                self.assertEqual(row["evidence"]["blocked_attempt"]["reason"], "seat-cap")
                self.assertEqual(row["holder_instance_id"], "holder-stuck")
                self.assertEqual(row["dispatch_event_cursor"], 9)
                self.assertEqual(row["evidence"]["send"]["marker"], marker)
                self.assertEqual(row["result"], {"excerpt": marker})
                cmds = [item["command"] for item in commands(self.log) if item["session"] == session]
                self.assertEqual(cmds, ["status"])
                disk = json.loads(index.read_text(encoding="utf-8"))
                stored = disk["items"][0]
                self.assertEqual(stored["status"], prior_status)
                self.assertEqual(stored["reason"], prior_reason)
                self.assertEqual(stored["holder_instance_id"], "holder-stuck")
                self.assertEqual(stored["evidence"]["send"]["marker"], marker)
                self.assertEqual(stored["evidence"]["blocked_attempt"]["reason"], "seat-cap")
                self.assertEqual(stored["result"], {"excerpt": marker})
                self.assertIn("stuck", disk["coverage"][prior_status])
                self.assertNotIn("stuck", disk["coverage"]["not-run"])
                self.assertEqual(stored.get("repo"), repo)
                if prior_status == "unknown":
                    if self.log.exists():
                        self.log.unlink()
                    self.use_spec({
                        session: {
                            "status": absent(repo),
                            "start": started(repo, "opus", "xhigh", holder="holder-new"),
                            "send": sent("fp-replayed"),
                        },
                    })
                    freed = write_json(self.root, "blocked-live-freed.json", {"rows": []})
                    code, payload = run([
                        "execute", "--plan", str(plan), "--authorization", str(auth),
                        "--availability", str(self.availability(["claude-code/opus-xhigh"])),
                        "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
                        "--index", str(index), "--live", str(freed),
                    ], self.env)
                    self.assertEqual(code, 0, payload)
                    again = payload["items"][0]
                    self.assertEqual(again["status"], "unknown")
                    self.assertEqual(again["reason"], "reconciliation-needed")
                    self.assertEqual(Path(again["repo"]).resolve(), Path(repo).resolve())
                    again_cmds = [
                        item["command"] for item in commands(self.log) if item["session"] == session
                    ]
                    self.assertEqual(again_cmds, ["status"])
                    stored_again = json.loads(index.read_text(encoding="utf-8"))["items"][0]
                    self.assertEqual(Path(stored_again["repo"]).resolve(), Path(repo).resolve())
                    self.assertEqual(stored_again["status"], "unknown")
                    self.assertEqual(stored_again["reason"], "reconciliation-needed")
        if self.log.exists():
            self.log.unlink()
        prompt = "changed-assignment"
        sha = "sha256:" + hashlib.sha256(b"stuck-unknown").hexdigest()
        session = "claude-code-KPR-i244-unknown"
        self.use_spec({
            session: {"status": started(repo, "opus", "xhigh", holder="holder-live")},
        })
        index = write_json(self.root, "blocked-changed.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [{
                "item_id": "stuck",
                "preset": "claude-code/opus-xhigh",
                "session": session,
                "repo": repo,
                "holder_instance_id": "holder-stuck",
                "prompt_sha256": sha,
                "status": "unknown",
                "reason": "send-timeout",
                "dispatch_event_cursor": 9,
                "evidence": {"send": {"marker": "maybe-sent"}},
                "result": {"excerpt": "maybe-sent"},
            }],
        })
        live = write_json(self.root, "blocked-live-changed.json", {"rows": [{
            "platform": "claude-code", "session": session, "repo": repo,
            "state": "ready", "holder_instance_id": "holder-live",
        }]})
        auth = self.authorization([
            {"id": "claude-code/opus-xhigh", "state": "granted"},
        ], elite_cap=1)
        plan = self.plan([
            {"item_id": "stuck", "preset": "claude-code/opus-xhigh", "session": session, "prompt": prompt},
        ])
        code, payload = run([
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--availability", str(self.availability(["claude-code/opus-xhigh"])),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
            "--index", str(index), "--live", str(live),
        ], self.env)
        self.assertEqual(code, 0, payload)
        changed = payload["items"][0]
        self.assertEqual(changed["status"], "not-run")
        self.assertEqual(changed["reason"], "seat-cap")
        self.assertNotIn("holder_instance_id", changed)
        self.assertNotIn("blocked_attempt", changed.get("evidence") or {})
        self.assertNotEqual(changed.get("result"), {"excerpt": "maybe-sent"})

    def test_non_object_authorization_is_invalid_on_execute(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        session = "codex-KPR-i244-luna"
        self.use_spec({
            session: {
                "status": absent(repo),
                "start": started(repo, "gpt-6-luna", "max", holder="holder-luna"),
                "send": sent(),
            },
        })
        plan = self.plan([
            {"item_id": "luna", "preset": "codex/luna", "session": session, "prompt": "pool"},
        ])
        for name, body in (
            ("null", {"authorization": None}),
            ("string", {"authorization": "paused codex/luna is not a grant object"}),
        ):
            with self.subTest(shape=name):
                if self.log.exists():
                    self.log.unlink()
                auth = write_json(self.root, f"auth-{name}.json", body)
                live = write_json(self.root, f"luna-live-{name}.json", {"rows": []})
                code, payload = run([
                    "execute", "--plan", str(plan), "--authorization", str(auth),
                    "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
                    "--live", str(live),
                ], self.env)
                self.assertEqual(code, 2, payload)
                self.assertEqual(payload["reason"], "invalid-input")
                self.assertIn("authorization must be an object", payload.get("detail", ""))
                self.assertEqual(commands(self.log), [])

    def test_capability_overview_does_not_copy_the_catalog(self) -> None:
        presets = []
        experts = []
        for path in sorted(PLATFORMS.glob("*.yaml")):
            platform = None
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("id:"):
                    platform = line.split(":", 1)[1].strip().strip('"')
                if "_model_class:" not in line or platform is None:
                    continue
                key, value = line.split(":", 1)
                tier = key.strip()[: -len("_model_class")].replace("_", "-")
                klass = value.strip().strip('"')
                preset = f"{platform}/{tier}"
                if klass == "Expert":
                    experts.append(preset)
                else:
                    presets.append(preset)
        auth = self.authorization([{"id": preset, "state": "granted"} for preset in presets])
        payload = self.project(auth, self.availability(presets))
        text = payload["capability_summary"]["text"]
        self.assertLess(len(text), 1200, text)
        self.assertNotIn("visual:", text)
        self.assertNotIn("execution:", text)
        self.assertNotIn("thinking:", text)
        self.assertNotIn("computer-use:", text)
        for item in payload["candidates"]:
            profile = item["profile"]
            if len(profile) > 40:
                self.assertNotIn(profile, text, item["id"])
            self.assertNotEqual(item["class"], "Expert")
        for preset in experts:
            self.assertNotIn(preset, text)
            self.assertNotIn(preset, payload["capability_summary"]["presets"])


    def turn_view(self, events, *, status_extra=None, item_extra=None, capture_extra=None, row_extra=None):
        install_fake(self.skills, ["codex"])
        if self.log.exists(): self.log.unlink()
        session = "codex-KPR-i252-qa"
        item = {"item_id": "qa", "platform": "codex", "preset": "codex/luna",
                "repo": str(self.repo), "session": session, "holder_instance_id": "holder-252",
                "prompt_fingerprint": "fp-252", "dispatch_event_cursor": 7, "status": "in-flight"}
        item.update(item_extra or {})
        status = {"repo": str(self.repo), "session": session, "holder_instance_id": "holder-252",
                  "prompt_fingerprint": "fp-252", "event_cursor": 7 + len(events),
                  "turn_active": False, "turn_outcome": "turn_completed", "stop_reason": "end_turn",
                  "pending_permissions": []}
        status.update(status_extra or {})
        capture = {"repo": str(self.repo), "session": session, "events": events,
                   "event_log_path": "/raw/events.jsonl"}
        capture.update(capture_extra or {})
        self.use_spec({session: {"status": status, "capture": capture, **(row_extra or {})}})
        index = write_json(self.root, "turn-index.json", {"schema": "kaola-dispatch-index/1",
                  "repo": str(self.repo), "items": [item]})
        before = index.read_bytes()
        files_before = set(self.root.rglob("*"))
        code, view = run(["collect", "--index", str(index), "--skills-root", str(self.skills),
                          "--item", "qa"], self.env)
        self.assertEqual(code, 0, view)
        self.turn_view_bytes = len((json.dumps(view, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode())
        self.assertLessEqual(self.turn_view_bytes, 8192)
        self.assertEqual(index.read_bytes(), before)
        self.assertEqual(set(self.root.rglob("*")) - files_before, {self.log} if self.log.exists() else set())
        self.assertTrue(all(row["command"] in ("status", "capture") for row in commands(self.log)))
        self.assertNotIn("acceptance", view)
        return view

    def test_turn_view_retains_permission_and_failure_outside_excerpt(self):
        events = [
            {"cursor": 8, "kind": "session_update", "update": {
                "sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": "x" * 2000}}},
            {"cursor": 9, "kind": "request_permission", "request": {"request_id": "p1", "title": "read"}},
            {"cursor": 10, "kind": "session_update", "update": {
                "sessionUpdate": "tool_call_update", "toolCallId": "t1", "status": "failed",
                "content": [{"type": "text", "text": "fixture failure"}]}},
            {"cursor": 11, "kind": "permission_answered", "request_id": "p1", "option": "allow_once"},
            {"cursor": 12, "kind": "turn_ended", "prompt_fingerprint": "fp-252",
                "outcome": "turn_failed", "stop_reason": "end_turn"},
            {"cursor": 13, "kind": "request_permission", "request": {"request_id": "other-turn"}},
        ]
        view = self.turn_view(events)
        self.assertEqual(view["outcome"], "turn_failed")
        self.assertEqual(len(view["excerpt"]), 480)
        self.assertEqual([e["cursor"] for e in view["permission_evidence"]], [9, 11])
        self.assertEqual([e["cursor"] for e in view["failure_evidence"]], [10, 12])
        self.assertTrue(view["truncation"]["reply"])
        self.assertFalse(view["truncation"]["evidence"])
        self.assertEqual(view["source"]["event_log_path"], "/raw/events.jsonl")
        self.assertEqual(view["source"]["through"], 12)
        self.assertEqual(view["unknown_reasons"], [])
        capture = next(row for row in commands(self.log) if row["command"] == "capture")
        self.assertIn("--full", capture["argv"])
        self.assertIn("--inline", capture["argv"])

    def test_turn_view_metadata_and_recovered_or_foreign_signals_are_not_failures(self):
        events = [
            {"cursor": 8, "kind": "session_update", "update": {
                "sessionUpdate": "session_info_update", "_meta": {"context_usage": 100}}},
            {"cursor": 9, "kind": "session_update", "sessionId": "acp-252", "update": {
                "sessionUpdate": "session_info_update", "_meta": {
                    "codex": {"threadStatus": {"type": "systemError"}}}}},
            {"cursor": 10, "kind": "session_update", "sessionId": "acp-252", "update": {
                "sessionUpdate": "session_info_update", "_meta": {
                    "codex": {"threadStatus": {"type": "idle"}}}}},
            {"cursor": 11, "kind": "session_update", "sessionId": "child-thread", "update": {
                "sessionUpdate": "session_info_update", "_meta": {
                    "codex": {"threadStatus": {"type": "systemError"}}}}},
            {"cursor": 12, "kind": "turn_ended", "prompt_fingerprint": "fp-252",
                "outcome": "turn_completed", "stop_reason": "end_turn"},
        ]
        view = self.turn_view(events, status_extra={"acp_session_id": "acp-252"})
        self.assertEqual(view["failure_count"], 0)
        self.assertFalse(view["failure_present"])
        self.assertEqual(view["failure_evidence"], [])
        self.assertEqual(view["outcome"], "turn_completed")
        self.assertFalse(view["truncation"]["evidence"])
        self.assertEqual(view["unknown_reasons"], [])

    def test_turn_view_system_error_uses_holder_terminal_and_keeps_raw_provenance(self):
        terminal = {"cursor": 9, "kind": "turn_ended", "prompt_fingerprint": "fp-252",
                    "outcome": "turn_failed", "stop_reason": "end_turn"}
        view = self.turn_view([
            {"cursor": 8, "kind": "session_update", "sessionId": "acp-252", "update": {
                "sessionUpdate": "session_info_update", "_meta": {
                    "codex": {"threadStatus": {"type": "systemError"}}}}},
            terminal,
        ], status_extra={"acp_session_id": "acp-252", "turn_outcome": "turn_failed"})
        self.assertEqual(view["outcome"], "turn_failed")
        self.assertEqual(view["failure_count"], 1)
        self.assertEqual(view["failure_evidence"], [terminal])
        self.assertNotIn("error", view["failure_evidence"][0])
        raw_error = {"cursor": 8, "kind": "error", "error": {"code": "raw-error"}}
        view = self.turn_view([raw_error])
        self.assertEqual(view["failure_evidence"], [raw_error])

    def test_turn_view_compacts_large_bodies_without_losing_evidence(self):
        view = self.turn_view([
            {"cursor": 8, "kind": "session_update", "update": {
                "sessionUpdate": "session_info_update", "_meta": {"context_usage": 100}}},
            {"cursor": 9, "kind": "request_permission", "request": {
                "request_id": "p-large", "tool_call_id": "t-large", "title": "讀" * 60000}},
            {"cursor": 10, "kind": "session_update", "sessionId": "acp-252", "update": {
                "sessionUpdate": "tool_call_update", "toolCallId": "t-large", "status": "failed",
                "content": [{"type": "text", "text": "x" * 60000}]}},
            {"cursor": 11, "kind": "permission_cancelled", "request_id": "p-large",
                "detail": "x" * 60000},
            {"cursor": 12, "kind": "error", "error": {
                "code": "fixture-error", "message": "x" * 60000}},
            {"cursor": 13, "kind": "turn_ended", "prompt_fingerprint": "fp-252",
                "outcome": "turn_completed", "stop_reason": "end_turn"},
            {"cursor": 14, "kind": "request_permission", "request": {"request_id": "later"}},
        ])
        self.assertEqual(view["permission_count"], 2)
        self.assertEqual(view["failure_count"], 2)
        self.assertEqual([e["cursor"] for e in view["permission_evidence"]], [9, 11])
        self.assertEqual([e["cursor"] for e in view["failure_evidence"]], [10, 12])
        self.assertEqual(view["permission_evidence"][0]["request"]["request_id"], "p-large")
        self.assertEqual(view["permission_evidence"][0]["request"]["tool_call_id"], "t-large")
        self.assertEqual(view["permission_evidence"][1]["request_id"], "p-large")
        self.assertEqual(view["failure_evidence"][0]["update"]["toolCallId"], "t-large")
        self.assertEqual(view["failure_evidence"][0]["update"]["status"], "failed")
        self.assertEqual(view["failure_evidence"][0]["sessionId"], "acp-252")
        self.assertEqual(view["failure_evidence"][1]["error"]["code"], "fixture-error")
        for entry in view["permission_evidence"] + view["failure_evidence"]:
            self.assertTrue(entry["truncated"])
            self.assertGreater(entry["payload_bytes"], 60000)
            self.assertEqual(entry["raw"]["cursor"], entry["cursor"])
            self.assertEqual(entry["raw"]["event_log_path"], "/raw/events.jsonl")
            self.assertIn("--full", entry["raw"]["argv"])
        self.assertLess(len(json.dumps(view, ensure_ascii=False).encode()), 12000)
        self.assertTrue(view["truncation"]["evidence"])
        self.assertFalse(view["truncation"]["reply"])
        self.assertEqual(view["source"]["through"], 13)
        self.assertEqual(view["unknown_reasons"], [])

    def test_turn_view_compacts_pending_permission_and_status_error(self):
        view = self.turn_view([], status_extra={
            "turn_active": True, "turn_outcome": None, "stop_reason": None,
            "pending_permissions": [{"request_id": "pending", "tool_call_id": "t1",
                                     "title": "x" * 60000}],
            "fatal_error": {"code": "fixture-fatal", "message": "x" * 60000}})
        pending = view["pending_permissions"][0]
        failure = view["failure_evidence"][0]
        self.assertEqual(pending["request_id"], "pending")
        self.assertEqual(pending["tool_call_id"], "t1")
        self.assertEqual(failure["fatal_error"]["code"], "fixture-fatal")
        for entry in (pending, failure):
            self.assertTrue(entry["truncated"])
            self.assertEqual(entry["raw"]["argv"][0], "status")
        self.assertLess(len(json.dumps(view).encode()), 6000)
        self.assertTrue(view["truncation"]["evidence"])
        self.assertEqual(view["failure_count"], 1)

    def test_turn_view_bounds_whole_view_and_accounts_for_every_entry(self):
        for body in ("x" * 1700, "讀" * 60000):
            with self.subTest(body_bytes=len(body.encode())):
                events = [{"cursor": 8 + n, "kind": "session_update", "update": {
                    "sessionUpdate": "tool_call_update", "toolCallId": str(n),
                    "status": "failed", "content": body}} for n in range(300)]
                events += [{"cursor": 308 + n, "kind": "request_permission", "request": {
                    "request_id": str(n), "title": body}} for n in range(300)]
                events.append({"cursor": 608, "kind": "turn_ended", "prompt_fingerprint": "fp-252",
                               "outcome": "turn_completed", "stop_reason": "end_turn"})
                view = self.turn_view(events, status_extra={"pending_permissions": [
                    {"request_id": str(n), "title": body} for n in range(300)]})
                self.assertLessEqual(self.turn_view_bytes, 8192)
                self.assertEqual(view["failure_count"], 300)
                self.assertEqual(view["permission_count"], 300)
                self.assertEqual(view["pending_permission_count"], 300)
                self.assertTrue(view["failure_present"])
                self.assertTrue(view["permission_present"])
                self.assertTrue(view["range_complete"])
                self.assertTrue(view["truncation"]["evidence"])
                self.assertEqual(view["unknown_reasons"], [])
                for key in ("failure_evidence", "permission_evidence", "pending_permissions"):
                    summary = view["evidence_summary"][key]
                    self.assertEqual(summary["count"], 300)
                    self.assertEqual(summary["shown_entries"], len(view[key]))
                    self.assertEqual(summary["shown_entries"] + summary["omitted_entries"], 300)
                    self.assertGreater(summary["omitted_entries"], 0)
                    self.assertEqual(summary["body_truncated_entries"], 300 if len(body) > 2048 else 0)
                    if key == "pending_permissions":
                        self.assertEqual(view[summary["raw"]["source"]][summary["raw"]["argv_key"]][0], "status")
                    else:
                        raw = summary["raw"]["events"]
                        self.assertEqual(view[raw["source"]]["event_log_path"], "/raw/events.jsonl")
                        self.assertEqual(raw["since"], 7)
                        self.assertEqual(raw["through"], 608)
                        self.assertIn("--full", view[raw["source"]][raw["argv_key"]])
                        first = 8 if key == "failure_evidence" else 308
                        self.assertEqual(summary["first_cursor"], first)
                        self.assertEqual(summary["last_cursor"], first + 299)
                        self.assertEqual(summary["omitted_first_cursor"], first + summary["shown_entries"])
                        self.assertEqual(summary["omitted_last_cursor"], first + 299)

    def test_turn_view_early_returns_keep_counts_and_unknown_ranges(self):
        cases = [
            ([], {"events": None}, {}, "event-range-unavailable", 1),
            ([], {"session": "foreign"}, {}, "capture-identity-unbound", 1),
            ([{"cursor": 8, "kind": "turn_ended", "prompt_fingerprint": "foreign"}], {}, {},
             "turn-fingerprint-differs", 1),
            ([], {}, {"prompt_fingerprint": "foreign"}, "turn-fingerprint-unknown-or-differs", 0),
        ]
        for events, capture, status, reason, known in cases:
            with self.subTest(reason=reason):
                view = self.turn_view(events, capture_extra=capture, status_extra={
                    "fatal_error": {"code": "fixture-fatal", "message": "x" * 60000},
                    "pending_permissions": [{"request_id": "p1"}], **status})
                self.assertIn(reason, view["unknown_reasons"])
                self.assertEqual(view["retained_failure_count"], known)
                self.assertEqual(view["retained_permission_count"], 0)
                self.assertIsNone(view["failure_count"])
                self.assertIsNone(view["permission_count"])
                self.assertIsNone(view["range_complete"])
                self.assertEqual(view["failure_present"], True if known else None)
                self.assertIsNone(view["permission_present"])
                self.assertEqual(view["pending_permission_count"], 1 if known else None)
                self.assertLessEqual(self.turn_view_bytes, 8192)
        view = self.turn_view([], capture_extra={"events": None})
        self.assertEqual(view["retained_failure_count"], 0)
        self.assertIsNone(view["failure_count"])
        self.assertIsNone(view["failure_present"])

    def test_turn_view_reports_unknown_gaps_and_truncation(self):
        view = self.turn_view([
            {"cursor": 10, "kind": "turn_ended", "prompt_fingerprint": "fp-252", "outcome": "turn_canceled"}
        ], status_extra={"event_cursor": 10}, capture_extra={"truncated": {"dropped": 2}})
        self.assertEqual(view["outcome"], "turn_canceled")
        self.assertIn("cursor-range-incomplete", view["unknown_reasons"])
        self.assertIn("capture-truncated", view["unknown_reasons"])
        self.assertTrue(view["truncation"]["evidence"])

    def test_turn_view_never_substitutes_another_holder_or_turn(self):
        for field in ("holder", "fingerprint", "cursor"):
            with self.subTest(field=field):
                if self.log.exists(): self.log.unlink()
                events = [{"cursor": 8, "kind": "turn_ended", "prompt_fingerprint": "foreign",
                           "outcome": "turn_completed"}]
                view = self.turn_view(events,
                    status_extra={"holder_instance_id": "foreign"} if field == "holder" else {},
                    item_extra={"dispatch_event_cursor": None} if field == "cursor" else {})
                self.assertIsNone(view["outcome"] if field != "fingerprint" else view["excerpt"])
                self.assertTrue(view["unknown_reasons"])
                self.assertEqual(view["failure_evidence"], [])

    def test_turn_view_item_repo_must_match_index_repo(self):
        view = self.turn_view([], item_extra={"repo": "/foreign"})
        self.assertEqual(view["unknown_reasons"], ["dispatch-repo-mismatch"])
        self.assertEqual(commands(self.log), [])

    def test_turn_view_keeps_partial_permission_and_process_exit(self):
        view = self.turn_view([
            {"cursor": 8, "kind": "request_permission", "request": {"request_id": "pending"}},
            {"cursor": 9, "kind": "process_exited", "code": 1},
        ], status_extra={"turn_outcome": "process_exited", "stop_reason": None,
                         "pending_permissions": [{"request_id": "pending"}], "state": "stopped"})
        self.assertEqual(view["outcome"], "process_exited")
        self.assertEqual(view["pending_permissions"], [{"request_id": "pending"}])
        self.assertEqual(view["failure_evidence"][0]["code"], 1)
        self.assertEqual(view["unknown_reasons"], [])

    def test_turn_view_missing_capture_is_unknown_without_mutation(self):
        view = self.turn_view([], status_extra={"state": "stopped"}, capture_extra={"events": None})
        self.assertIn("event-range-unavailable", view["unknown_reasons"])
        self.assertEqual(view["outcome"], "turn_completed")
        self.assertIsNone(view["excerpt"])

    def test_turn_view_keeps_status_verdict_when_only_the_capture_read_fails(self):
        self.env["KAOLA_DISPATCH_RUNNER_TIMEOUT"] = "1"
        failing = {"turn_outcome": "turn_failed", "stop_reason": "error"}
        cases = [
            ("capture-timeout", {"hang": ["capture"], "hang_for": 4}),
            ("capture-unreadable", {"garbage": ["capture"]}),
            ("after-status-timeout", {"second_status_hang": True, "hang_for": 4}),
        ]
        for reason, row in cases:
            with self.subTest(reason=reason):
                view = self.turn_view([], status_extra=failing, row_extra=row)
                self.assertIn(reason, view["unknown_reasons"])
                self.assertEqual(view["outcome"], "turn_failed")
                self.assertEqual(view["stop_reason"], "error")
                self.assertIs(view["turn_active"], False)
                self.assertTrue(view["source"]["verdict_as_of"])
                self.assertIsNone(view["range_complete"])
                self.assertIsNone(view["failure_count"])
                self.assertIsNone(view["source"].get("through"))

    def test_turn_view_identity_conflict_clears_the_verdict_before_a_timeout(self):
        self.env["KAOLA_DISPATCH_RUNNER_TIMEOUT"] = "1"
        foreign_after = {"repo": str(self.repo), "session": "codex-KPR-i252-qa",
                         "holder_instance_id": "foreign", "prompt_fingerprint": "fp-252"}
        cases = [
            ("foreign capture", {}, {"session": "foreign"}),
            ("foreign after-status", {"status_second": foreign_after}, {}),
            ("foreign after-status and capture timeout",
             {"status_second": foreign_after, "hang": ["capture"], "hang_for": 4}, {}),
            ("foreign capture and after-status timeout",
             {"second_status_hang": True, "hang_for": 4}, {"session": "foreign"}),
        ]
        for label, row, capture in cases:
            with self.subTest(label=label):
                view = self.turn_view([], row_extra=row, capture_extra=capture)
                self.assertIn("capture-identity-unbound", view["unknown_reasons"])
                self.assertIsNone(view["outcome"])
                self.assertIsNone(view["stop_reason"])
                self.assertIsNone(view["turn_active"])

    def test_turn_view_failure_entries_are_observations_beside_the_turn_verdict(self):
        view = self.turn_view([
            {"cursor": 8, "kind": "session_update", "update": {
                "sessionUpdate": "tool_call_update", "toolCallId": "t1", "status": "failed"}},
            {"cursor": 9, "kind": "turn_ended", "prompt_fingerprint": "fp-252",
                "outcome": "turn_completed", "stop_reason": "end_turn"},
        ])
        self.assertTrue(view["failure_present"])
        self.assertEqual(view["failure_count"], 1)
        self.assertEqual(view["outcome"], "turn_completed")
        self.assertEqual(view["unknown_reasons"], [])

    LIST_STUB = textwrap.dedent(
        """\
        import json, sys
        repo = sys.argv[sys.argv.index("--repo") + 1]
        print(json.dumps({"schema": "kaola-acp-list/1", "rows": [{
            "repo": repo, "identity": "verified", "holder_instance_id": "stub-holder",
            "platform": "zcode", "session": "zcode-KPR-stub", "state": "ready"}]}))
        """
    )

    def installed_dispatch(self, stub_platform: str | None) -> Path:
        scripts = self.skills / "kaola-project-runner" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "kaola-dispatch.py").write_bytes(SCRIPT.read_bytes())
        (scripts / "kaola-record-contract.py").write_bytes(RECORD.read_bytes())
        worker = self.skills / "zcode-kaola-project-runner" / "scripts"
        worker.mkdir(parents=True)
        (worker / "platform.yaml").write_bytes((PLATFORMS / "zcode.yaml").read_bytes())
        if stub_platform:
            stub = self.skills / f"{stub_platform}-kaola-project-runner" / "scripts" / "kaola-acp.py"
            stub.parent.mkdir(parents=True, exist_ok=True)
            stub.write_text(self.LIST_STUB, encoding="utf-8")
            stub.chmod(0o644)
        return scripts / "kaola-dispatch.py"

    def installed_seats(self, dispatch: Path, *extra: str) -> dict:
        auth = self.authorization([{"id": "zcode/default", "state": "granted", "count": 1}])
        proc = subprocess.run(
            [sys.executable, str(dispatch), "project", "--seats", "--repo", str(self.repo),
             "--authorization", str(auth), *extra],
            capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def test_seats_omitted_live_lists_through_a_non_executable_installed_runner(self):
        dispatch = self.installed_dispatch("zcode")
        stub = self.skills / "zcode-kaola-project-runner" / "scripts" / "kaola-acp.py"
        self.assertFalse(os.access(stub, os.X_OK))
        view = self.installed_seats(dispatch)
        self.assertNotIn("live-source-unavailable", view["unknown_reasons"])
        self.assertEqual([row["session"] for row in view["sessions"]], ["zcode-KPR-stub"])
        self.assertEqual(view["source"]["live"], str(stub.resolve()))
        self.assertIsNotNone(view["observed_elite_expert"])

    def test_seats_explicit_skills_root_governs_and_is_not_replaced_by_another(self):
        dispatch = self.installed_dispatch("zcode")
        empty = self.root / "empty-skills"
        empty.mkdir()
        view = self.installed_seats(dispatch, "--skills-root", str(empty))
        self.assertIn("live-source-unavailable", view["unknown_reasons"])
        self.assertIsNone(view["source"]["live"])
        self.assertEqual(view["sessions"], [])
        view = self.installed_seats(dispatch, "--skills-root", str(self.skills))
        self.assertEqual([row["session"] for row in view["sessions"]], ["zcode-KPR-stub"])
        view = self.installed_seats(dispatch, "--skills-root", str(self.root / "missing"))
        self.assertIn("live-source-unavailable", view["unknown_reasons"])

    def test_seats_omitted_live_without_an_installed_runner_stays_unknown(self):
        view = self.installed_seats(self.installed_dispatch(None))
        self.assertIn("live-source-unavailable", view["unknown_reasons"])
        self.assertIsNone(view["source"]["live"])
        self.assertIsNone(view["observed_elite_expert"])

    def test_execute_omitted_live_lists_through_the_skills_root_runner(self):
        install_fake(self.skills, ["claude-code"])
        stub = self.skills / "claude-code-kaola-project-runner" / "scripts" / "kaola-acp.py"
        stub.write_text('import json\nprint(json.dumps({"schema": "kaola-acp-list/1", "rows": []}))\n',
                        encoding="utf-8")
        stub.chmod(0o644)
        repo = str(self.repo)
        self.use_spec({"claude-code-KPR-i252-opus": {
            "status": absent(repo), "start": started(repo, "opus", "xhigh"), "send": sent("fp-opus")}})
        capped = self.authorization([{"id": "claude-code/opus-xhigh", "state": "granted"}], elite_cap=1)
        plan = self.plan([{"item_id": "opus", "preset": "claude-code/opus-xhigh",
                           "session": "claude-code-KPR-i252-opus", "prompt": "a"}])
        payload = self.execute(plan, capped, self.availability(["claude-code/opus-xhigh"]), live="omit")
        self.assertEqual(payload["items"][0]["status"], "in-flight", payload)

    def test_seats_view_binds_identity_and_retains_grant_states(self):
        auth = self.authorization([
            {"id": "droid/opus", "state": "revoked", "shared_seat": "droid", "count": 1},
            {"id": "codex/luna", "state": "granted"}], elite_cap=2)
        rows = [
            {"repo": str(self.repo), "identity": "verified", "holder_instance_id": "h1",
             "platform": "droid", "preset": "droid/opus", "session": "droid-KPR-i252-qa", "state": "ready"},
            {"repo": str(self.repo), "identity": "verified", "holder_instance_id": "h2",
             "platform": "codex", "preset": "codex/luna", "session": "codex-KPR-i252-qa", "state": "ready"},
            {"repo": str(self.repo), "identity": "verified", "holder_instance_id": "host",
             "platform": "codex", "session": "codex-KPR-orchestrator-main", "host_class": True},
            {"repo": "/foreign", "identity": "verified", "holder_instance_id": "foreign",
             "platform": "droid", "preset": "droid/opus", "session": "foreign", "state": "ready"},
            {"repo": str(self.repo), "identity": "unknown", "platform": "codex", "session": "unbound"},
            {"repo": str(self.repo), "state": "stopped", "session": "done"},
        ]
        live = write_json(self.root, "seats-live.json", {"rows": rows})
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        code, view = run(["project", "--seats", "--repo", str(self.repo), "--authorization", str(auth),
                          "--platforms", str(PLATFORMS), "--live", str(live)], self.env)
        self.assertEqual(code, 0, view)
        self.assertEqual(view["observed_elite_expert"], 1)
        self.assertEqual(view["grants"][0]["state"], "revoked")
        self.assertEqual(view["grants"][0]["observed_live"], 1)
        self.assertTrue(view["grants"][0]["shared_occupied"])
        self.assertEqual(len(view["sessions"]), 2)
        self.assertIn("unbound-live-row:unbound", view["unknown_reasons"])
        self.assertNotIn("candidates", view)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_seats_missing_source_does_not_claim_zero_occupancy(self):
        auth = self.authorization([{"id": "codex/default", "state": "granted", "count": 1}])
        code, view = run(["project", "--seats", "--repo", str(self.repo), "--authorization", str(auth),
                          "--live", str(self.root / "missing.json")], self.env)
        self.assertEqual(code, 0, view)
        self.assertIsNone(view["observed_elite_expert"])
        self.assertIsNone(view["grants"][0]["observed_live"])
        self.assertIn("live-source-unavailable", view["unknown_reasons"])

    # Standing Expert grants and breadth (#252). Stub-Runner fixtures only: a
    # pass here is not live evidence and no Expert session was started.
    def candidate(self, payload: dict, preset: str) -> dict | None:
        return next((row for row in payload["candidates"] if row["id"] == preset), None)

    def withheld(self, payload: dict, preset: str) -> str | None:
        return next((row["reason"] for row in payload["withheld"] if row["id"] == preset), None)

    def test_expert_lifetime_is_task_unless_the_grant_says_standing(self) -> None:
        avail = self.availability(["codex/astra", "codex/default", "zcode/default"])
        none = self.project(self.authorization([{"id": "codex/astra", "state": "granted"}]), avail)
        self.assertEqual(self.candidate(none, "codex/astra")["lifetime"], "task")
        self.assertNotIn("expires", self.candidate(none, "codex/astra"))
        task = self.project(self.authorization([
            {"id": "codex/astra", "state": "granted", "lifetime": "task"}]), avail)
        self.assertEqual(self.candidate(task, "codex/astra")["lifetime"], "task")
        standing = self.project(self.authorization([
            {"id": "codex/astra", "state": "granted", "lifetime": "standing"}]), avail)
        self.assertEqual(self.candidate(standing, "codex/astra")["lifetime"], "standing")
        other = self.project(self.authorization([
            {"id": "codex/astra", "state": "granted", "lifetime": "forever"}]), avail)
        self.assertIsNone(self.candidate(other, "codex/astra"))
        self.assertEqual(self.withheld(other, "codex/astra"), "lifetime-unreadable")
        code, payload = run(["project", "--authorization", str(self.authorization([
            {"id": "codex/astra", "state": "granted", "lifetime": 3}])),
            "--platforms", str(PLATFORMS)], self.env)
        self.assertNotEqual(code, 0, payload)

    def test_elite_and_worker_rows_ignore_the_expert_keys(self) -> None:
        avail = self.availability(["codex/default", "zcode/default"])
        plain = self.project(self.authorization([
            {"id": "codex/default", "state": "granted", "count": 1},
            {"id": "zcode/default", "state": "granted"}]), avail)
        keyed = self.project(self.authorization([
            {"id": "codex/default", "state": "granted", "count": 1,
             "lifetime": "standing", "expires": "2000-01-01T00:00:00+00:00"},
            {"id": "zcode/default", "state": "granted",
             "lifetime": "bogus", "expires": "not a time"}]), avail)
        self.assertEqual(plain["candidates"], keyed["candidates"])
        self.assertEqual(plain["withheld"], keyed["withheld"])
        for preset in ("codex/default", "zcode/default"):
            row = self.candidate(keyed, preset)
            self.assertNotIn("lifetime", row)
            self.assertNotIn("expires", row)

    def test_expert_expiry_is_withheld_and_execute_reports_the_reason(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        self.use_spec({
            "codex-KPR-i252-astra": {
                "status": absent(repo), "start": started(repo, "gpt-6-astra", "high"), "send": sent("fp-a"),
            },
        })
        avail = self.availability(["codex/astra"])
        cases = (
            ("2000-01-01T00:00:00+00:00", "expired"),
            ("2000-01-01T00:00:00Z", "expired"),
            ("2999-01-01 not a time", "expiry-unreadable"),
            ("2999-01-01T00:00:00", "expiry-unreadable"),
        )
        for expires, reason in cases:
            with self.subTest(expires=expires):
                auth = self.authorization([
                    {"id": "codex/astra", "state": "granted", "lifetime": "standing", "expires": expires}],
                    elite_cap=1)
                payload = self.project(auth, avail)
                self.assertIsNone(self.candidate(payload, "codex/astra"))
                self.assertEqual(self.withheld(payload, "codex/astra"), reason)
                plan = self.plan([{
                    "item_id": "x", "preset": "codex/astra", "session": "codex-KPR-i252-astra", "prompt": "design"}])
                run_payload = self.execute(plan, auth, avail)
                self.assertEqual(run_payload["items"][0]["status"], "not-run")
                self.assertEqual(run_payload["items"][0]["reason"], reason)
        self.assertEqual(commands(self.log), [])
        future = self.authorization([
            {"id": "codex/astra", "state": "granted", "lifetime": "standing",
             "expires": "2999-01-01T00:00:00+08:00"}], elite_cap=1)
        row = self.candidate(self.project(future, avail), "codex/astra")
        self.assertEqual(row["lifetime"], "standing")
        self.assertEqual(row["expires"], "2999-01-01T00:00:00+08:00")
        revoked = self.authorization([
            {"id": "codex/astra", "state": "revoked", "lifetime": "standing",
             "expires": "2000-01-01T00:00:00+00:00"}])
        self.assertEqual(self.withheld(self.project(revoked, avail), "codex/astra"), "revoked")

    def test_no_expert_is_exposed_without_its_own_grant(self) -> None:
        avail = self.availability(["codex/astra", "codex/default", "claude-code/fable"])
        payload = self.project(self.authorization([
            {"id": "codex/default", "state": "granted", "model_switch": True, "lifetime": "standing"},
        ], model_switches=["codex/default"]), avail)
        ids = {row["id"] for row in payload["candidates"]}
        self.assertNotIn("codex/astra", ids)
        self.assertNotIn("claude-code/fable", ids)
        self.assertNotIn("codex/astra", payload["capability_summary"]["presets"])
        task = self.project(self.authorization([{"id": "codex/astra", "state": "granted"}]), avail)
        self.assertNotEqual(self.candidate(task, "codex/astra")["lifetime"], "standing")

    def test_standing_grant_outlives_its_session_and_a_new_name_admits(self) -> None:
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        self.use_spec({
            "codex-KPR-i252-second": {
                "status": absent(repo), "start": started(repo, "gpt-6-astra", "high"), "send": sent("fp-s"),
            },
        })
        avail = self.availability(["codex/astra"])
        auth = self.authorization([
            {"id": "codex/astra", "state": "granted", "count": 1, "lifetime": "standing"}], elite_cap=1)
        self.assertEqual(self.candidate(self.project(auth, avail), "codex/astra")["lifetime"], "standing")
        stopped = write_json(self.root, "stopped-live.json", {"rows": [{
            "repo": os.path.realpath(repo), "state": "stopped", "session": "codex-KPR-i252-first"}]})
        code, view = run(["project", "--seats", "--repo", repo, "--authorization", str(auth),
                          "--platforms", str(PLATFORMS), "--live", str(stopped)], self.env)
        self.assertEqual(code, 0, view)
        grant = view["grants"][0]
        self.assertEqual(grant["id"], "codex/astra")
        self.assertEqual(grant["observed_live"], 0)
        self.assertEqual(grant["lifetime"], "standing")
        plan = self.plan([{
            "item_id": "second", "preset": "codex/astra", "session": "codex-KPR-i252-second", "prompt": "review"}])
        payload = self.execute(plan, auth, avail)
        self.assertEqual(payload["items"][0]["status"], "in-flight", payload)
        removed = self.project(self.authorization([]), avail)
        self.assertIsNone(self.candidate(removed, "codex/astra"))

    def test_seats_view_without_the_new_keys_is_unchanged(self) -> None:
        auth = self.authorization([{"id": "codex/default", "state": "granted", "count": 1}], elite_cap=1)
        live = write_json(self.root, "empty-live.json", {"rows": []})
        code, view = run(["project", "--seats", "--repo", str(self.repo), "--authorization", str(auth),
                          "--platforms", str(PLATFORMS), "--live", str(live)], self.env)
        self.assertEqual(code, 0, view)
        self.assertNotIn("lifetime", view["grants"][0])
        self.assertNotIn("expires", view["grants"][0])

    def test_worker_fan_out_ignores_a_full_elite_cap_and_expert_count_still_binds(self) -> None:
        install_fake(self.skills, ["codex", "devin", "dsh", "opencode", "zcode"])
        repo = str(self.repo)
        real = os.path.realpath(repo)
        pool = (
            ("codex/luna", "codex-KPR-i252-luna", started(repo, "gpt-6-luna", "max")),
            ("devin/default", "devin-KPR-i252-def", started(repo, "swe-2-max")),
            ("dsh/default", "dsh-KPR-i252-def", started(repo, "opencode-go/deepseek-v4.1-flash")),
            ("opencode/default", "opencode-KPR-i252-def", started(repo, "opencode-go/deepseek-v4.1-flash")),
            ("zcode/default", "zcode-KPR-i252-def", started(repo, "GLM-5.3", "max")),
        )
        spec = {session: {"status": absent(repo), "start": receipt, "send": sent("fp-" + preset)}
                for preset, session, receipt in pool}
        spec["codex-KPR-i252-astra1"] = {
            "status": absent(repo), "start": started(repo, "gpt-6-astra", "high"), "send": sent("fp-astra1")}
        spec["codex-KPR-i252-astra2"] = {
            "status": absent(repo), "start": started(repo, "gpt-6-astra", "high"), "send": sent("fp-astra2")}
        spec["codex-KPR-i252-elite"] = {
            "status": absent(repo), "start": started(repo, "gpt-6.1-sol", "high"), "send": sent("fp-elite")}
        self.use_spec(spec)
        live = write_json(self.root, "full-cap-live.json", {"rows": [{
            "preset": "codex/default", "platform": "codex", "repo": real, "state": "running",
            "session": "codex-KPR-i252-held", "identity": "verified", "holder_instance_id": "h-held"}]})
        auth = self.authorization([
            {"id": "codex/default", "state": "granted"},
            {"id": "codex/astra", "state": "granted", "count": 1, "lifetime": "standing"},
        ], elite_cap=1)
        items = [
            {"item_id": preset, "preset": preset, "session": session, "prompt": "gather " + preset}
            for preset, session, _ in pool
        ]
        items.append({"item_id": "elite", "preset": "codex/default",
                      "session": "codex-KPR-i252-elite", "prompt": "more"})
        avail = self.availability([preset for preset, _, _ in pool] + ["codex/default", "codex/astra"])
        payload = self.execute(self.plan(items), auth, avail, live=live)
        by_id = {row["item_id"]: row for row in payload["items"]}
        for preset, _, _ in pool:
            self.assertEqual(by_id[preset]["status"], "in-flight", payload)
        self.assertEqual(by_id["elite"]["status"], "not-run")
        self.assertEqual(by_id["elite"]["reason"], "seat-cap")

        roomy = self.authorization([
            {"id": "codex/astra", "state": "granted", "count": 1, "lifetime": "standing"}], elite_cap=2)
        two = self.plan([
            {"item_id": "e1", "preset": "codex/astra", "session": "codex-KPR-i252-astra1", "prompt": "a"},
            {"item_id": "e2", "preset": "codex/astra", "session": "codex-KPR-i252-astra2", "prompt": "b"},
        ])
        payload = self.execute(two, roomy, self.availability(["codex/astra"]))
        statuses = sorted((row["status"], row["reason"]) for row in payload["items"])
        self.assertEqual(statuses, [("in-flight", "admitted"), ("not-run", "count")], payload)

    def test_changed_authorization_refuses_the_item_and_keeps_an_admitted_binding(self) -> None:
        install_fake(self.skills, ["codex", "zcode"])
        repo = str(self.repo)
        prompt = "kept"
        sha = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        session = "codex-KPR-i252-kept"
        self.use_spec({
            "zcode-KPR-i252-free": {
                "status": absent(repo), "start": started(repo, "GLM-5.3", "max"), "send": sent("fp-free")},
            session: {"status": started(repo, "gpt-6-astra", "high", holder="holder-live")},
        })
        index = write_json(self.root, "kept-index.json", {
            "schema": "kaola-dispatch-index/1", "correlation_only": True, "repo": repo,
            "items": [{
                "item_id": "kept", "preset": "codex/astra", "platform": "codex", "session": session,
                "repo": repo, "holder_instance_id": "holder-kept", "prompt_sha256": sha,
                "prompt_fingerprint": sha, "status": "in-flight", "reason": "admitted",
                "acceptance": "pending", "dispatch_event_cursor": 4,
            }],
        })
        live = write_json(self.root, "kept-live.json", {"rows": [{
            "platform": "codex", "session": session, "repo": repo, "state": "ready",
            "holder_instance_id": "holder-kept", "preset": "codex/astra"}]})
        avail = self.availability(["codex/astra", "zcode/default"])
        for grant, reason in (
            ({"id": "codex/astra", "state": "granted", "lifetime": "standing",
              "expires": "2000-01-01T00:00:00+00:00"}, "expired"),
            ({"id": "codex/astra", "state": "revoked", "lifetime": "standing"}, "revoked"),
        ):
            with self.subTest(reason=reason):
                auth = self.authorization([grant], elite_cap=1)
                plan = self.plan([
                    {"item_id": "kept", "preset": "codex/astra", "session": session, "prompt": prompt},
                    {"item_id": "free", "preset": "zcode/default", "session": "zcode-KPR-i252-free", "prompt": "w"},
                ])
                payload = self.execute(plan, auth, avail, live=live, index=index)
                by_id = {row["item_id"]: row for row in payload["items"]}
                self.assertEqual(by_id["free"]["status"], "in-flight", payload)
                kept = by_id["kept"]
                self.assertEqual(kept["status"], "in-flight")
                self.assertEqual(kept["holder_instance_id"], "holder-kept")
                self.assertEqual(kept["dispatch_event_cursor"], 4)
                self.assertEqual(kept["evidence"]["blocked_attempt"], {"reason": reason})
                self.log.write_text("", encoding="utf-8")
                self.use_spec({
                    "zcode-KPR-i252-free": {
                        "status": absent(repo), "start": started(repo, "GLM-5.3", "max"), "send": sent("fp-free")},
                    session: {"status": started(repo, "gpt-6-astra", "high", holder="holder-live")},
                })
        fresh = self.plan([{
            "item_id": "new", "preset": "codex/astra", "session": "codex-KPR-i252-new", "prompt": "n"}])
        payload = self.execute(fresh, self.authorization([
            {"id": "codex/astra", "state": "granted", "lifetime": "standing",
             "expires": "2000-01-01T00:00:00+00:00"}], elite_cap=1), avail)
        self.assertEqual(payload["items"][0]["reason"], "expired")

    def test_first_publish_does_not_stamp_missing_before_the_executor(self) -> None:
        """The index written before the executor must not invent reason missing.

        A kept ready item has no blocked row yet. A failed retry that is free
        to run still carries its earlier real stamp until that run finishes.
        An uninterrupted admission clears the real stamp.
        """
        install_fake(self.skills, ["zcode"])
        repo = str(self.repo)
        kept_prompt = "stay-ready"
        retry_prompt = "try-again"
        kept_sha = "sha256:" + hashlib.sha256(kept_prompt.encode("utf-8")).hexdigest()
        retry_sha = "sha256:" + hashlib.sha256(retry_prompt.encode("utf-8")).hexdigest()
        kept_session = "zcode-KPR-i253-kept"
        retry_session = "zcode-KPR-i253-retry"
        gate = self.root / "release-status"
        self.use_spec({
            kept_session: {
                "wait_for": str(gate),
                "status": {
                    "repo": repo,
                    "holder_instance_id": "holder-kept",
                    "mutation_status": "in_progress",
                    "outcome": "in_progress",
                    "prompt_fingerprint": kept_sha,
                },
            },
            retry_session: {
                "wait_for": str(gate),
                "status": absent(repo),
                "start": started(repo, "GLM-5.3", "max", holder="holder-retry"),
                "send": sent("fp-retry"),
            },
        })
        index = write_json(self.root, "first-publish.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [
                {
                    "item_id": "kept",
                    "preset": "zcode/default",
                    "platform": "zcode",
                    "session": kept_session,
                    "repo": repo,
                    "holder_instance_id": "holder-kept",
                    "prompt_sha256": kept_sha,
                    "prompt_fingerprint": kept_sha,
                    "status": "in-flight",
                    "reason": "admitted",
                    "acceptance": "pending",
                    "dispatch_event_cursor": 12,
                    "evidence": {"start": {"marker": "kept-start"}},
                },
                {
                    "item_id": "retry",
                    "preset": "zcode/default",
                    "platform": "zcode",
                    "session": retry_session,
                    "repo": repo,
                    "holder_instance_id": "holder-old",
                    "prompt_sha256": retry_sha,
                    "prompt_fingerprint": retry_sha,
                    "status": "failed",
                    "reason": "selection-mismatch",
                    "acceptance": "pending",
                    "evidence": {
                        "send": {"marker": "old-send"},
                        "blocked_attempt": {"reason": "seat-cap"},
                    },
                },
            ],
        })
        live = write_json(self.root, "first-publish-live.json", {"rows": []})
        plan = self.plan([
            {"item_id": "kept", "preset": "zcode/default", "session": kept_session, "prompt": kept_prompt},
            {"item_id": "retry", "preset": "zcode/default", "session": retry_session, "prompt": retry_prompt},
        ])
        auth = self.authorization()
        proc = subprocess.Popen(
            [
                sys.executable, str(SCRIPT), "execute",
                "--plan", str(plan), "--authorization", str(auth),
                "--availability", str(self.availability(["zcode/default"])),
                "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
                "--index", str(index), "--live", str(live),
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env,
        )
        seen = None
        try:
            deadline = time.time() + 15
            while time.time() < deadline and proc.poll() is None:
                try:
                    disk = json.loads(index.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    time.sleep(0.02)
                    continue
                rows = {row["item_id"]: row for row in disk.get("items") or [] if isinstance(row, dict)}
                kept = rows.get("kept")
                retry = rows.get("retry")
                if (
                    disk.get("phase") == "admission"
                    and isinstance(kept, dict) and kept.get("reason") == "admitted"
                    and "status" not in (kept.get("evidence") or {})
                    and isinstance(retry, dict) and retry.get("reason") == "selection-mismatch"
                ):
                    seen = rows
                    break
                time.sleep(0.02)
            self.assertIsNotNone(seen, "execute did not leave a first-publish index to read")
            self.assertIsNone(proc.poll(), "execute finished before the first-publish read")
            kept = seen["kept"]
            retry = seen["retry"]
            self.assertEqual(kept["status"], "in-flight")
            self.assertEqual(kept["reason"], "admitted")
            self.assertEqual(kept["holder_instance_id"], "holder-kept")
            self.assertEqual(kept["dispatch_event_cursor"], 12)
            self.assertEqual(kept["evidence"]["start"]["marker"], "kept-start")
            self.assertNotIn("blocked_attempt", kept["evidence"])
            self.assertEqual(retry["status"], "failed")
            self.assertEqual(retry["reason"], "selection-mismatch")
            self.assertEqual(retry["evidence"]["blocked_attempt"], {"reason": "seat-cap"})
        finally:
            gate.write_text("go", encoding="utf-8")
        stdout, stderr = proc.communicate(timeout=20)
        self.assertEqual(proc.returncode, 0, stderr + stdout)
        payload = json.loads(stdout)
        final = {row["item_id"]: row for row in payload["items"]}
        self.assertEqual(final["kept"]["status"], "in-flight", payload)
        self.assertEqual(final["kept"]["reason"], "already-admitted")
        self.assertEqual(final["kept"]["holder_instance_id"], "holder-kept")
        self.assertNotIn("blocked_attempt", final["kept"].get("evidence") or {})
        self.assertEqual(final["retry"]["status"], "in-flight", payload)
        self.assertEqual(final["retry"]["reason"], "admitted")
        self.assertNotIn("blocked_attempt", final["retry"].get("evidence") or {})
        stored = {row["item_id"]: row for row in json.loads(index.read_text(encoding="utf-8"))["items"]}
        self.assertNotIn("blocked_attempt", stored["kept"].get("evidence") or {})
        self.assertNotIn("blocked_attempt", stored["retry"].get("evidence") or {})
        self.assertEqual(stored["retry"]["reason"], "admitted")
        kept_cmds = [row["command"] for row in commands(self.log) if row["session"] == kept_session]
        retry_cmds = [row["command"] for row in commands(self.log) if row["session"] == retry_session]
        self.assertEqual(kept_cmds, ["status"])
        self.assertEqual(retry_cmds, ["status", "start", "send"])



    def test_later_plan_keeps_an_unresolved_index_row(self) -> None:
        """Another plan must not drop a pending row from the same index."""
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        for key in list(self.env):
            if key.startswith("KAOLA_"):
                del self.env[key]
        flight_prompt = "sha256:" + hashlib.sha256(b"prior-flight").hexdigest()
        returned_prompt = "sha256:" + hashlib.sha256(b"prior-returned").hexdigest()
        flight = {
            "item_id": "prior-flight",
            "preset": "devin/default",
            "platform": "devin",
            "session": "devin-KPR-i259-preserve",
            "repo": repo,
            "holder_instance_id": "cae5-fixture",
            "prompt_sha256": flight_prompt,
            "prompt_fingerprint": flight_prompt,
            "status": "in-flight",
            "reason": "admitted",
            "acceptance": "repair",
            "acceptance_source": {"state": "fixture", "task_id": "i259-impl", "task_rev": 2},
            "dispatch_event_cursor": 15,
            "evidence": {"start": {"marker": "flight-start"}, "send": {"marker": "flight-send"}},
        }
        returned = {
            "item_id": "prior-returned",
            "preset": "devin/default",
            "platform": "devin",
            "session": "devin-KPR-i259-returned",
            "repo": repo,
            "holder_instance_id": "holder-returned",
            "prompt_sha256": returned_prompt,
            "prompt_fingerprint": returned_prompt,
            "status": "returned",
            "reason": "collected",
            "acceptance": "pending",
            "dispatch_event_cursor": 9,
            "result": {"excerpt": "collect-update"},
            "evidence": {"capture": {"marker": "collected"}},
        }
        closed = {
            "item_id": "closed-accepted",
            "preset": "devin/default",
            "session": "devin-KPR-i259-closed",
            "repo": repo,
            "holder_instance_id": "holder-closed",
            "prompt_sha256": "sha256:closed",
            "status": "returned",
            "reason": "collected",
            "acceptance": "accepted",
        }
        refused = {
            "item_id": "refused-once",
            "preset": "codex/default",
            "session": "codex-KPR-i259-refused",
            "repo": repo,
            "status": "not-run",
            "reason": "count",
        }
        index = write_json(self.root, "overlap-index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [flight, returned, closed, refused],
        })
        original = index.read_bytes()
        session = "codex-KPR-i259-next"
        self.use_spec({
            session: {
                "status": absent(repo),
                "start": started(repo, "gpt-6.1-sol", "high", holder="holder-next"),
                "send": sent("fp-next", 4),
            },
        })
        auth = self.authorization([{"id": "codex/default", "state": "granted"}])
        avail = self.availability(["codex/default"])
        plan = self.plan([{
            "item_id": "next-plan",
            "preset": "codex/default",
            "session": session,
            "prompt": "next batch",
        }])
        live = write_json(self.root, "overlap-live.json", {"rows": []})
        code, dry = run([
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--availability", str(avail), "--platforms", str(PLATFORMS),
            "--skills-root", str(self.skills), "--index", str(index),
            "--live", str(live), "--dry-run",
        ], self.env)
        self.assertEqual(code, 0, dry)
        self.assertEqual(index.read_bytes(), original)
        self.assertEqual(commands(self.log), [])
        code, payload = run([
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--availability", str(avail), "--platforms", str(PLATFORMS),
            "--skills-root", str(self.skills), "--index", str(index),
            "--live", str(live),
        ], self.env)
        self.assertEqual(code, 0, payload)
        by_id = {item["item_id"]: item for item in payload["items"]}
        self.assertEqual(by_id["next-plan"]["status"], "in-flight", payload)
        self.assertEqual(by_id["next-plan"]["reason"], "admitted")
        self.assertIn("prior-flight", by_id)
        self.assertIn("prior-returned", by_id)
        self.assertEqual(by_id["prior-flight"], flight)
        self.assertEqual(by_id["prior-returned"], returned)
        self.assertNotIn("closed-accepted", by_id)
        self.assertNotIn("refused-once", by_id)
        disk = {item["item_id"]: item for item in json.loads(index.read_text(encoding="utf-8"))["items"]}
        self.assertEqual(disk["prior-flight"], flight)
        self.assertEqual(disk["prior-returned"], returned)
        self.assertEqual(disk["next-plan"]["status"], "in-flight")
        self.assertNotIn("closed-accepted", disk)
        self.assertNotIn("refused-once", disk)
        self.assertIn("prior-flight", json.loads(index.read_text(encoding="utf-8"))["coverage"]["in-flight"])
        seen = {row["session"] for row in commands(self.log)}
        self.assertIn(session, seen)
        self.assertNotIn("devin-KPR-i259-preserve", seen)
        self.assertNotIn("devin-KPR-i259-returned", seen)
        self.assertNotIn("devin-KPR-i259-closed", seen)

    def test_unknown_and_repair_rows_stay_when_another_plan_publishes(self) -> None:
        """Unknown correlation and an open repair stay. Closed dispositions do not."""
        install_fake(self.skills, ["codex"])
        repo = str(self.repo)
        for key in list(self.env):
            if key.startswith("KAOLA_"):
                del self.env[key]
        unknown_prompt = "sha256:" + hashlib.sha256(b"unknown-verdict").hexdigest()
        repair_prompt = "sha256:" + hashlib.sha256(b"returned-repair").hexdigest()
        failed_prompt = "sha256:" + hashlib.sha256(b"failed-repair").hexdigest()
        unknown = {
            "item_id": "unknown-accepted",
            "preset": "devin/default",
            "platform": "devin",
            "session": "devin-KPR-i259-unknown",
            "repo": repo,
            "holder_instance_id": "holder-unknown",
            "prompt_sha256": unknown_prompt,
            "prompt_fingerprint": unknown_prompt,
            "status": "unknown",
            "reason": "mutation-unknown",
            "acceptance": "accepted",
            "acceptance_source": {"state": "fixture", "task_id": "i259-impl", "task_rev": 4},
            "dispatch_event_cursor": 11,
        }
        returned_repair = {
            "item_id": "returned-repair",
            "preset": "devin/default",
            "platform": "devin",
            "session": "devin-KPR-i259-repair",
            "repo": repo,
            "holder_instance_id": "holder-repair",
            "prompt_sha256": repair_prompt,
            "prompt_fingerprint": repair_prompt,
            "status": "returned",
            "reason": "collected",
            "acceptance": "repair",
            "result": {"excerpt": "needs-repair"},
        }
        failed_repair = {
            "item_id": "failed-repair",
            "preset": "devin/default",
            "platform": "devin",
            "session": "devin-KPR-i259-failed-repair",
            "repo": repo,
            "holder_instance_id": "holder-failed-repair",
            "prompt_sha256": failed_prompt,
            "prompt_fingerprint": failed_prompt,
            "status": "failed",
            "reason": "turn-failed",
            "acceptance": "repair",
        }
        omitted = [
            ("returned-cancelled", "returned", "cancelled"),
            ("failed-superseded", "failed", "superseded"),
            ("returned-handed", "returned", "handed-off"),
            ("failed-accepted", "failed", "accepted"),
            ("not-run-again", "not-run", "pending"),
        ]
        extras = []
        for item_id, status, acceptance in omitted:
            extras.append({
                "item_id": item_id,
                "preset": "devin/default",
                "session": f"devin-KPR-i259-{item_id}",
                "repo": repo,
                "holder_instance_id": f"holder-{item_id}",
                "status": status,
                "acceptance": acceptance,
            })
        index = write_json(self.root, "repair-index.json", {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "items": [unknown, returned_repair, failed_repair, *extras],
        })
        session = "codex-KPR-i259-next2"
        self.use_spec({
            session: {
                "status": absent(repo),
                "start": started(repo, "gpt-6.1-sol", "high", holder="holder-next2"),
                "send": sent("fp-next2", 5),
            },
        })
        auth = self.authorization([{"id": "codex/default", "state": "granted"}])
        plan = self.plan([{
            "item_id": "next-plan",
            "preset": "codex/default",
            "session": session,
            "prompt": "second batch",
        }])
        live = write_json(self.root, "repair-live.json", {"rows": []})
        code, payload = run([
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--availability", str(self.availability(["codex/default"])),
            "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
            "--index", str(index), "--live", str(live),
        ], self.env)
        self.assertEqual(code, 0, payload)
        disk = {item["item_id"]: item for item in json.loads(index.read_text(encoding="utf-8"))["items"]}
        self.assertEqual(disk["unknown-accepted"], unknown)
        self.assertEqual(disk["returned-repair"], returned_repair)
        self.assertEqual(disk["failed-repair"], failed_repair)
        self.assertEqual(disk["next-plan"]["status"], "in-flight")
        self.assertEqual(disk["next-plan"]["reason"], "admitted")
        for item_id, _status, _acceptance in omitted:
            self.assertNotIn(item_id, disk)
        seen = {row["session"] for row in commands(self.log)}
        self.assertIn(session, seen)
        self.assertNotIn("devin-KPR-i259-unknown", seen)
        self.assertNotIn("devin-KPR-i259-repair", seen)
        self.assertNotIn("devin-KPR-i259-failed-repair", seen)

    def test_omitted_row_follows_the_locked_disk_status(self) -> None:
        """The lock decides an omitted row. The older baseline status does not."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("kpr_i259_dispatch_merge", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        identity = {
            "item_id": "prior-flight",
            "holder_instance_id": "owned-holder",
            "prompt_sha256": "sha256:owned-prompt",
        }
        pending = {**identity, "status": "in-flight", "acceptance": "pending"}
        settled = {**identity, "status": "returned", "acceptance": "accepted",
                   "result": {"locator": "original-return"}}
        self.assertEqual(module.merge_index_rows([settled], [pending], []), [])
        fresh = {**identity, "status": "in-flight", "acceptance": "pending"}
        self.assertEqual(module.merge_index_rows([fresh], [settled], []), [fresh])
        unknown = {**identity, "status": "unknown", "acceptance": "accepted"}
        self.assertEqual(module.merge_index_rows([unknown], [settled], []), [unknown])
        repair = {**identity, "status": "returned", "acceptance": "repair"}
        failed_repair = {**identity, "status": "failed", "acceptance": "repair"}
        self.assertEqual(module.merge_index_rows([repair], [settled], []), [repair])
        self.assertEqual(module.merge_index_rows([failed_repair], [settled], []), [failed_repair])
        added = {
            "item_id": "other-writer",
            "status": "returned",
            "acceptance": "accepted",
            "holder_instance_id": "holder-added",
            "prompt_sha256": "sha256:added",
        }
        self.assertEqual(module.merge_index_rows([added], [], []), [added])
        mine = {**pending, "reason": "admitted"}
        prior = {**pending, "reason": "old"}
        disk_row = {**prior, "result": {"locator": "disk-result"}}
        merged = module.merge_index_rows([disk_row], [prior], [mine])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["reason"], "admitted")
        self.assertEqual(merged[0]["result"], {"locator": "disk-result"})
        self.assertEqual(merged[0]["holder_instance_id"], "owned-holder")
        self.assertEqual(merged[0]["prompt_sha256"], "sha256:owned-prompt")
        self.assertEqual(commands(self.log), [])


class RenderedGuidance(unittest.TestCase):
    def test_dispatch_guidance_preserves_authorization_and_unknown_selection(self) -> None:
        template = (REPO / "templates/orchestrator/references/dispatch-collect.md").read_bytes()
        generated = (ORCHESTRATOR / "references/dispatch-collect.md").read_bytes()
        self.assertEqual(template, generated)
        self.assertLessEqual(len(template), 8192)
        text = generated.decode()
        self.assertIn("does not choose workers,\ngrant, accept or stop seats", text)
        self.assertIn("Host allocates within authorization", text)
        self.assertIn("Explicit `applied: false` or `model_verified: false`", text)
        self.assertIn("Missing application, unknown observations", text)
        self.assertIn("advertised differences stay unknown and do not block send", text)
        self.assertNotIn("Host chooses, grants", text)
        self.assertNotIn("Explicit unapplied/unverified", text)

    def test_planned_dispatch_of_every_scope_routes_through_execute(self) -> None:
        def flat(name: str) -> str:
            return re.sub(r"\s+", " ", (ORCHESTRATOR / name).read_text(encoding="utf-8"))
        skill = flat("SKILL.md")
        self.assertIn("Planned dispatch (research, QA, report or implementation) uses `execute`", skill)
        self.assertIn("it starts absent seats at the preset `--tier`", skill)
        self.assertIn("Direct Runner `start`/`send` is standalone, degraded or same-assignment recovery", skill)
        self.assertNotIn("Pass the selected authorized `--tier`", skill)
        self.assertNotIn("An adopted research, QA, or report plan", skill)
        host = flat("references/zcode-host-dispatch.md")
        self.assertIn("### Execute first; direct start as fallback", host)
        self.assertNotIn("Start a worker from this Host", host)
        self.assertIn("Direct Host sends (continuation, repair, finalize, degraded dispatch)", host)
        collect = flat("references/dispatch-collect.md")
        self.assertNotIn("Capacity applies only to new starts", collect)
        self.assertIn("own verified, unprompted live seat is its count, not a new start", collect)
        startup = flat("references/host-startup.md")
        self.assertNotIn("starting workers here", startup)
        worktree = flat("references/workflow-worktree.md")
        self.assertIn("through `execute` (`scope: implementation`", worktree)
        issue = flat("references/issue-dispatch.md")
        self.assertIn("`evidence.start`", issue)

    def test_entry_prefers_spread_breadth_without_a_quota_and_states_b1(self) -> None:
        text = (ORCHESTRATOR / "references/dispatch-collect.md").read_text(encoding="utf-8")
        self.assertIn("as evenly as reasonably possible", text)
        self.assertIn("not one habitual runtime", text)
        self.assertIn("no invented work or fixed quota", text)
        self.assertIn("Rejected re-execution keeps correlation, adds `evidence.blocked_attempt`.", text)
        self.assertNotIn("force model balance", text)
        self.assertLessEqual(len(text.encode("utf-8")), 8192)
        skill = (ORCHESTRATOR / "SKILL.md").read_bytes()
        self.assertLessEqual(len(skill), 17408)
        profiles = (ORCHESTRATOR / "references/worker-profiles.md").read_text(encoding="utf-8")
        self.assertIn("fix per-runtime quotas", profiles)
        self.assertNotIn("force equal runtime distribution", profiles)
        self.assertIn("never infer one from a task or finished grant", profiles)
        self.assertLessEqual(len(profiles.encode("utf-8")), 8192)
        self.assertIn("`lifetime`", text)
        self.assertIn("`expires`", text)
        self.assertIn("standing grant", skill.decode("utf-8"))

    def test_entry_is_discoverable_and_sideagent_includes_light_work(self) -> None:
        skill = (ORCHESTRATOR / "SKILL.md").read_text(encoding="utf-8")
        reference = (ORCHESTRATOR / "references" / "dispatch-collect.md").read_text(encoding="utf-8")
        profiles = (ORCHESTRATOR / "references" / "worker-profiles.md").read_text(encoding="utf-8")
        skeleton = (ORCHESTRATOR / "references" / "heartbeat-skeleton.md").read_text(encoding="utf-8")
        snapshot = (DELEGATOR / "references" / "snapshot.md").read_text(encoding="utf-8")
        for text in (skill, reference, skeleton, snapshot):
            self.assertIn("Sideagent", text)
            self.assertNotIn("Sidekick", text)
        for name in ("duty-reconcile.md", "public-research.md"):
            text = (ORCHESTRATOR / "references" / name).read_text(encoding="utf-8")
            self.assertIn("Sideagent", text)
            self.assertNotIn("Sidekick", text)
        for name in ("README.md", "docs/api.md", "docs/dispatch-collect.md",
                     "docs/acp-watch/list-view.md", "docs/acp-watch/follow.md"):
            text = (REPO / name).read_text(encoding="utf-8")
            self.assertIn("Sideagent", text)
            self.assertNotIn("Sidekick", text)
        self.assertIn("explicitly scoped light work", skill)
        self.assertIn("another scheduling loop", skill)
        self.assertIn("dispatch-collect.md", skill)
        self.assertIn("explicitly scoped light work", reference)
        self.assertIn("zcode/default", reference)
        self.assertIn("owner-selected authorized available", reference)
        self.assertNotIn("such as `dsh/default`", reference)
        self.assertIn("not start other workers", reference)
        self.assertNotIn("目录单行 profile 原文", skeleton)
        self.assertIn("capability_summary", skeleton)
        self.assertIn("单一 JSON 对象", skeleton)
        self.assertIn("dispatch-collect.md", profiles)
        self.assertIn("compact capability summary", snapshot)
        self.assertNotIn("ID/Class/profile row per authorized preset", snapshot)
        generated = (ORCHESTRATOR / "scripts" / "kaola-dispatch.py").read_bytes()
        self.assertEqual(generated, SCRIPT.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
