#!/usr/bin/env python3
"""Progressive disclosure: a locked, platform-neutral invariant with measured budgets.

Discovery exposes only a stable name and a short description. Activating Project
Runner loads its body only, never a worker body. Selecting one worker loads that
worker only. References load only when the current operation needs them. Scripts
execute mechanically; the model never reads their source. Ordinary tool outputs are
bounded receipts on both transports -- PTY ``capture`` through ``bound-text`` and PTY
``observe``/``status`` through ``bound_observation``; ACP ``capture`` through
``bound_capture_receipt`` and ACP ``observe``/``status`` through ``bound_state_receipt``
(``capture --full`` is the explicit exception on both) -- proven behaviourally here
against the observation helper and the mock ACP agent, and on the live wrapper path by
``tests/contract/test-kaola-tmux.sh``. Host adapters may not
flatten, concatenate, eagerly preload, or duplicate canonical Skill bodies. Budgets
live in ``templates/budgets.json``; ``render-skills.py --check`` and this suite fail
when a budget or a loading boundary regresses.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RENDERER = PROJECT / "scripts" / "render-skills.py"
OBSERVATION = PROJECT / "scripts" / "kaola-observation.py"
TMUX_CORE = PROJECT / "scripts" / "kaola-tmux.sh"
ACP_CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK_ACP_AGENT = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
BUDGETS = json.loads((PROJECT / "templates" / "budgets.json").read_text(encoding="utf-8"))
ORCHESTRATOR_ID = "kaola-project-runner"
WORKER_IDS = ("claude-code", "codex", "cursor-cli", "devin", "droid", "grok", "kimi-cli", "opencode", "zcode")
WORKER_SKILL_IDS = tuple(f"{wid}-{ORCHESTRATOR_ID}" for wid in WORKER_IDS)
WORKER_BODY_MARKERS = ("## Communication loop", 'runtime-tmux.sh" send', 'runtime-tmux.sh" capture', "mutation_status", "raw_current_frame", "SKILL_DIR=")
ORCHESTRATOR_MARKERS = ("## Heartbeat", "## Main execution loop", "Mission-frontier", "Allowed CLIs", "PROJECT_RUNNER_HEARTBEAT", "Accept the delivery")
READ_SOURCE_PATTERNS = (r"\bcat scripts/", r"\bcat \"?\$SKILL_DIR/scripts", r"read the script", r"open (?:the )?scripts?/", r"read (?:its|their|the) source", r"inspect (?:the )?script source")
# A sentence is exempt only where a negation stands right before the matched phrase in the
# same clause ("never read script source"); a negation elsewhere in the sentence is not enough.
NEGATION_BEFORE = re.compile(r"\b(never|not|no|nor|without)\b[^.;:]{0,40}$", re.IGNORECASE)
COPY_IGNORE = shutil.ignore_patterns(".git", ".kw", "__pycache__", "node_modules", "build")


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.split("\n")
    assert lines[0] == "---"
    end = lines.index("---", 1)
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = json.loads(value)
        meta[key.strip()] = value
    return meta, "\n".join(lines[end + 1:])


def products() -> dict[str, Path]:
    result = {ORCHESTRATOR_ID: PROJECT / "skills" / ORCHESTRATOR_ID}
    for skill_id in WORKER_SKILL_IDS:
        result[skill_id] = PROJECT / "skills" / skill_id
    return result


def emitted_line_size(value) -> int:
    """Bytes of the receipt line the helpers print: sorted-key JSON plus its newline."""
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")) + 1


def render(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(root / "scripts" / "render-skills.py"), *args], cwd=root, text=True, capture_output=True)


class BudgetsDeclared(unittest.TestCase):
    def test_budget_table_is_complete_and_positive(self) -> None:
        for key in ("description_chars", "main_skill_bytes", "worker_skill_bytes", "reference_bytes", "bridge_bytes",
                    "bridge_guide_bytes", "locator_receipt_bytes", "capture_receipt_bytes"):
            self.assertIsInstance(BUDGETS.get(key), int, key)
            self.assertGreater(BUDGETS[key], 0, key)
        # Budgets are ordered the way disclosure is: discovery < bridge < worker < main.
        self.assertLess(BUDGETS["bridge_bytes"], BUDGETS["worker_skill_bytes"])
        self.assertLess(BUDGETS["worker_skill_bytes"], BUDGETS["main_skill_bytes"])
        self.assertLess(BUDGETS["reference_bytes"], BUDGETS["worker_skill_bytes"])

    def test_helper_constants_agree_with_the_budget_table(self) -> None:
        observation = OBSERVATION.read_text(encoding="utf-8")
        self.assertIn(f"CAPTURE_RECEIPT_BYTES = {BUDGETS['capture_receipt_bytes']}", observation)
        locator = (PROJECT / "scripts" / "kaola-locate.py").read_text(encoding="utf-8")
        self.assertIn(f"RECEIPT_LIMIT = {BUDGETS['locator_receipt_bytes']}", locator)
        acp = ACP_CLI.read_text(encoding="utf-8")
        self.assertIn(f"CAPTURE_RECEIPT_BYTES = {BUDGETS['capture_receipt_bytes']}", acp)


class DiscoveryIsNameAndShortDescription(unittest.TestCase):
    def test_every_generated_description_is_short_and_name_is_the_stable_id(self) -> None:
        for skill_id, path in products().items():
            meta, _ = frontmatter((path / "SKILL.md").read_text(encoding="utf-8"))
            self.assertEqual(meta["name"], skill_id)
            self.assertLessEqual(len(meta["description"]), BUDGETS["description_chars"], skill_id)
            self.assertNotIn("\n", meta["description"])
        bridge = PROJECT / "hosts" / "grok-bot" / f"{ORCHESTRATOR_ID}.md"
        meta, _ = frontmatter(bridge.read_text(encoding="utf-8"))
        self.assertEqual(meta["name"], ORCHESTRATOR_ID)
        self.assertLessEqual(len(meta["description"]), BUDGETS["description_chars"])


class ActivationBoundaries(unittest.TestCase):
    def test_main_body_is_within_budget_and_embeds_no_worker(self) -> None:
        main = (PROJECT / "skills" / ORCHESTRATOR_ID / "SKILL.md").read_bytes()
        self.assertLessEqual(len(main), BUDGETS["main_skill_bytes"])
        text = main.decode("utf-8")
        for marker in WORKER_BODY_MARKERS:
            self.assertNotIn(marker, text, marker)
        self.assertFalse((PROJECT / "skills" / ORCHESTRATOR_ID / "workers").exists())
        self.assertFalse((PROJECT / "skills" / ORCHESTRATOR_ID / "scripts").exists(), "control plane ships no transport scripts")
        self.assertIn("Load one selected worker Skill only at dispatch", text)

    def test_each_worker_is_within_budget_separate_and_free_of_orchestrator_policy(self) -> None:
        bodies: dict[str, str] = {}
        for skill_id in WORKER_SKILL_IDS:
            raw = (PROJECT / "skills" / skill_id / "SKILL.md").read_bytes()
            self.assertLessEqual(len(raw), BUDGETS["worker_skill_bytes"], skill_id)
            text = raw.decode("utf-8")
            for marker in ORCHESTRATOR_MARKERS:
                self.assertNotIn(marker, text, f"{skill_id}: {marker}")
            self.assertIn("Progressive disclosure: load this Skill only when this platform is selected", re.sub(r"\s+", " ", text))
            bodies[skill_id] = frontmatter(text)[1]
        main_body = frontmatter((PROJECT / "skills" / ORCHESTRATOR_ID / "SKILL.md").read_text(encoding="utf-8"))[1]
        for skill_id, body in bodies.items():
            self.assertNotIn(body, main_body, f"main embeds {skill_id}")
            for other_id, other in bodies.items():
                if other_id != skill_id:
                    self.assertNotIn(body, other, f"{other_id} embeds {skill_id}")

    def test_references_are_within_budget_linked_by_relative_path_and_never_inlined(self) -> None:
        for skill_id, path in products().items():
            skill = (path / "SKILL.md").read_text(encoding="utf-8")
            references = sorted((path / "references").glob("*.md"))
            self.assertTrue(references, skill_id)
            for reference in references:
                self.assertLessEqual(reference.stat().st_size, BUDGETS["reference_bytes"], f"{skill_id}/{reference.name}")
                self.assertIn(f"](references/{reference.name})", skill, f"{skill_id} must link {reference.name} by relative path")
                heading = reference.read_text(encoding="utf-8").splitlines()[0]
                self.assertTrue(heading.startswith("# "), f"{skill_id}/{reference.name}")
                self.assertNotIn(heading + "\n", skill, f"{skill_id} inlines {reference.name}")
            self.assertNotIn("## Bundled reference", skill)

    def test_skill_text_never_instructs_reading_script_source(self) -> None:
        surfaces = [path / "SKILL.md" for path in products().values()]
        surfaces += list((PROJECT / "hosts" / "grok-bot").glob("*.md"))
        surfaces += [PROJECT / "templates" / "SKILL.md.tmpl", PROJECT / "templates" / "orchestrator" / "SKILL.md.tmpl"]
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            for raw in re.split(r"(?<=[.!?:])\s+|\n\n+", text):
                sentence = re.sub(r"\s+", " ", raw).strip()
                for pattern in READ_SOURCE_PATTERNS:
                    for match in re.finditer(pattern, sentence, flags=re.IGNORECASE):
                        # A prohibition ("never read script source") is not an instruction to read source.
                        self.assertIsNotNone(NEGATION_BEFORE.search(sentence[:match.start()]),
                                             f"{path.relative_to(PROJECT)}: {pattern}: {sentence[:100]}")

    def test_no_host_product_exceeds_its_canonical_source(self) -> None:
        bridge = PROJECT / "hosts" / "grok-bot" / f"{ORCHESTRATOR_ID}.md"
        self.assertLessEqual(bridge.stat().st_size, BUDGETS["bridge_bytes"])
        self.assertLess(bridge.stat().st_size, (PROJECT / "skills" / ORCHESTRATOR_ID / "SKILL.md").stat().st_size)
        self.assertEqual(sorted(p.name for p in (PROJECT / "hosts" / "grok-bot").iterdir() if p.suffix == ".md"), ["INSTALL.md", f"{ORCHESTRATOR_ID}.md"])


class RendererEnforcesBudgets(unittest.TestCase):
    def test_check_fails_naming_surface_and_size_when_a_budget_regresses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(PROJECT, root, ignore=COPY_IGNORE)
            # No .git in the copy, so no pin can be verified there: budgets are tested at the content stage.
            (root / "templates" / "grok-bot" / "accepted-revision.json").write_text('{"stage": "content"}\n', encoding="utf-8")
            self.assertEqual(render(root, "--write").returncode, 0)
            self.assertEqual(render(root, "--check").returncode, 0)
            cases = {
                "templates/orchestrator/SKILL.md.tmpl": (r"budget: kaola-project-runner/SKILL\.md is \d+ B > \d+ B \(main_skill_bytes\)", "\n" + "padding " * 400 + "\n"),
                "templates/SKILL.md.tmpl": (r"budget: claude-code-kaola-project-runner/SKILL\.md is \d+ B > \d+ B \(worker_skill_bytes\)", "\n" + "padding " * 400 + "\n"),
                "templates/references/transport.md.tmpl": (r"budget: codex-kaola-project-runner/references/transport\.md is \d+ B > \d+ B \(reference_bytes\)", "\n" + "padding " * 400 + "\n"),
                "templates/grok-bot/INSTALL.md.tmpl": (r"budget: grok-bot/INSTALL\.md is \d+ B > \d+ B \(bridge_guide_bytes\)", "\n" + "padding " * 600 + "\n"),
            }
            for relative, (pattern, padding) in cases.items():
                path = root / relative
                original = path.read_text(encoding="utf-8")
                path.write_text(original + padding, encoding="utf-8")
                check = render(root, "--check")
                self.assertNotEqual(check.returncode, 0, relative)
                self.assertRegex(check.stderr, pattern)
                write = render(root, "--write")
                self.assertNotEqual(write.returncode, 0, "an over-budget product must never be written")
                path.write_text(original, encoding="utf-8")
            # A too-long description is a discovery regression.
            manifest = root / "platforms" / "grok.yaml"
            text = manifest.read_text(encoding="utf-8")
            text = re.sub(r'(?m)^description: "(.*)"$', lambda m: f'description: "{m.group(1)}{" more words" * 40}"', text)
            manifest.write_text(text, encoding="utf-8")
            check = render(root, "--check")
            self.assertNotEqual(check.returncode, 0)
            self.assertRegex(check.stderr, r"budget: grok-kaola-project-runner/SKILL\.md description is \d+ chars > \d+ chars \(description_chars\)")
            self.assertEqual(render(root, "--check").returncode, 1)
            self.assertEqual((root / "skills" / "grok-kaola-project-runner" / "SKILL.md").read_bytes(),
                             (PROJECT / "skills" / "grok-kaola-project-runner" / "SKILL.md").read_bytes(), "nothing was written")


class BoundedOrdinaryOutputs(unittest.TestCase):
    def bound(self, data: bytes, *args: str) -> bytes:
        completed = subprocess.run([sys.executable, str(OBSERVATION), "bound-text", *args], input=data, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        return completed.stdout

    def test_capture_within_budget_passes_through_unchanged(self) -> None:
        data = b"line\n" * 100
        self.assertEqual(self.bound(data), data)
        exact = b"x" * (BUDGETS["capture_receipt_bytes"] - 1) + b"\n"
        self.assertEqual(self.bound(exact), exact)

    def test_capture_over_budget_keeps_newest_lines_and_a_verifiable_marker(self) -> None:
        lines = [f"line {i:06d} " + "x" * 90 + "\n" for i in range(2000)]
        data = "".join(lines).encode("utf-8")
        self.assertGreater(len(data), BUDGETS["capture_receipt_bytes"])
        bounded = self.bound(data)
        self.assertLessEqual(len(bounded), BUDGETS["capture_receipt_bytes"])
        text = bounded.decode("utf-8")
        self.assertTrue(text.endswith("pass --full for the whole capture]\n"))
        self.assertIn(f"of {len(data)} bytes", text)
        self.assertIn(hashlib.sha256(data).hexdigest(), text)
        self.assertIn("line 001999", text, "the newest output is kept")
        self.assertNotIn("line 000000", text, "the oldest output is dropped")
        body = text.rsplit("[kaola capture truncated", 1)[0]
        self.assertTrue(body.startswith("line "), "truncation lands on a line boundary")
        kept = int(re.search(r"kept last (\d+) of", text).group(1))
        self.assertEqual(kept, len(body.encode("utf-8")))
        # An explicit smaller limit is honoured the same way.
        small = self.bound(data, "4096")
        self.assertLessEqual(len(small), 4096)
        self.assertIn("pass --full", small.decode("utf-8"))

    def test_tmux_core_bounds_ordinary_capture_and_leaves_full_unbounded(self) -> None:
        core = TMUX_CORE.read_text(encoding="utf-8")
        capture = core.split("  capture)", 1)[1].split("  start)", 1)[0]
        self.assertIn('if [[ "$capture_full" == true ]]; then', capture)
        self.assertIn('"$OBSERVATION_HELPER" bound-text', capture)
        self.assertRegex(capture, r'capture_full" == true \]\]; then "\$TMUX_BIN" capture-pane -p -t "\$STATE_PANE_ID" -S "-\$lines"; else')
        self.assertIn("[--lines N] [--full]", core)
        acp = ACP_CLI.read_text(encoding="utf-8")
        capture_branch = acp.split('elif args.command == "capture":', 1)[1].split("elif args.command ==", 1)[0]
        self.assertIn("if not args.full:\n            receipt = bound_capture_receipt(receipt)", capture_branch)
        state_branch = acp.split('elif args.command in ("observe", "status"):', 1)[1].split("elif args.command ==", 1)[0]
        self.assertIn("receipt = bound_state_receipt(receipt)", state_branch)
        observation = OBSERVATION.read_text(encoding="utf-8")
        self.assertIn("print(json.dumps(bound_observation(build_from_environment())", observation)
        self.assertIn('view = emit_status_view(json.load(sys.stdin), os.environ.get("KPR_STATUS_RESULT"), os.environ.get("KPR_STATUS_LEGACY"))', observation)
        # The status/start wrapper adds nothing after the final bound: result (and legacy_ownership for
        # grok) travel into status-view as environment and the helper bounds the line it emits.
        self.assertIn('KPR_STATUS_RESULT="$1" KPR_STATUS_LEGACY="$STATE_LEGACY_OWNERSHIP" "$PYTHON_BIN" "$OBSERVATION_HELPER" status-view', core)
        self.assertIn('KPR_STATUS_RESULT=started "$PYTHON_BIN" "$OBSERVATION_HELPER" status-view; exit 0', core)
        self.assertNotIn("STATUS_JSON=", core)
        self.assertNotIn('d["result"]=', core)
        for skill_id in WORKER_SKILL_IDS:
            shipped = PROJECT / "skills" / skill_id / "scripts" / "kaola-tmux.sh"
            self.assertEqual(shipped.read_bytes(), TMUX_CORE.read_bytes(), skill_id)
            self.assertEqual((PROJECT / "skills" / skill_id / "scripts" / "kaola-observation.py").read_bytes(), OBSERVATION.read_bytes(), skill_id)
            self.assertEqual((PROJECT / "skills" / skill_id / "scripts" / "kaola-acp.py").read_bytes(), ACP_CLI.read_bytes(), skill_id)

    def test_locator_receipt_is_bounded(self) -> None:
        completed = subprocess.run([sys.executable, str(PROJECT / "scripts" / "kaola-locate.py")], text=True, capture_output=True, cwd=PROJECT)
        self.assertTrue(completed.stdout.strip(), completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(receipt["schema"], "kaola-project-runner-locator/1")
        self.assertLessEqual(len(completed.stdout.encode("utf-8")), BUDGETS["locator_receipt_bytes"])
        self.assertEqual(len(completed.stdout.strip().splitlines()), 1)


class BoundedObserveAndStatus(unittest.TestCase):
    """Ordinary PTY observe/status receipts are bounded by the same budget, verifiably."""

    RELAY = {
        "managed": True, "protocol_version": 1, "epoch": "1" * 32, "pid": 100, "start_fingerprint": "sha256:" + "1" * 64,
        "socket_path": "/tmp/relay-" + "2" * 32 + ".sock", "socket_owner_uid": 501, "socket_mode": "0600", "peer_pid_verified": True,
        "state": "running", "child_pid": 101, "child_pgid": 101, "child_start_fingerprint": "sha256:" + "3" * 64,
        "child_runtime_path": "/usr/local/bin/claude", "child_process": "claude", "child_process_state": "S", "child_process_match": True,
        "process_group_running": True, "lease_active": False, "child_input_offset": 10, "child_output_offset": 20,
        "child_output_digest": "sha256:" + "8" * 64, "resize_revision": 0, "bracketed_paste": True, "terminal_fence": "decrqm-nonce-v1",
    }

    def environment(self, root: Path, frame_file: Path, processes: list) -> dict[str, str]:
        env = {name: value for name, value in os.environ.items() if not name.startswith("KPR_")}
        env.update({
            "KPR_FRAME_FILE": str(frame_file), "KPR_PRESENT": "true", "KPR_OWNED": "true", "KPR_PLATFORM_MATCH": "true",
            "KPR_REPO_MATCH": "true", "KPR_PANE_COUNT": "1", "KPR_PANE_ID": "%1", "KPR_PANE_DEAD": "false", "KPR_PANE_INPUT_OFF": "false",
            "KPR_PANE_PATH": str(root), "KPR_PANE_PID": "100", "KPR_PANE_COMMAND": "python3", "KPR_PANE_TITLE": "Claude Code",
            "KPR_PANE_PROCESS": "python3 kaola-pane-relay.py", "KPR_RELAY_PROCESS_MATCH": "true", "KPR_PROCESS_MATCH": "true",
            "KPR_TUI": "true", "KPR_PANE_WIDTH": "400", "KPR_PANE_HEIGHT": "300", "KPR_CURSOR_X": "0", "KPR_CURSOR_Y": "0",
            "KPR_CURSOR_FLAG": "true", "KPR_ALTERNATE_ON": "false", "KPR_HISTORY_SIZE": "10", "KPR_HISTORY_BYTES": "100",
            "KPR_ADAPTER_JSON": json.dumps({"editor_state": "empty", "editor_fingerprint": None, "visible_shell_count": 0,
                                            "visible_agent_count": 0, "native_approval": {"state": "absent", "kind": None, "fingerprint": None},
                                            "structured_decision_marker": None, "activity_hint": "idle"}),
            "KPR_RELAY_JSON": json.dumps(self.RELAY), "KPR_PROCESS_JSON": json.dumps(processes), "KPR_BARRIER_JSON": "null",
            "KPR_RESULT": "observed", "KPR_PLATFORM": "claude-code", "KPR_RUNTIME": "Claude Code", "KPR_SESSION": "pd-observe",
            "KPR_REPO": str(root), "KPR_RUNTIME_SESSION_ID": "", "KPR_MODEL_JSON": "{}",
        })
        return env

    def helper(self, command: str, env: dict[str, str], stdin: bytes = b"") -> dict:
        completed = subprocess.run([sys.executable, str(OBSERVATION), command], input=stdin, capture_output=True, env=env)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        line = completed.stdout
        self.assertEqual(len(line.strip().splitlines()), 1)
        self.assertLessEqual(len(line.strip()), BUDGETS["capture_receipt_bytes"], command)
        return json.loads(line)

    def test_pty_observe_and_status_over_budget_keep_newest_frame_lines_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            frame = "".join(f"line {i:06d} " + "x" * 90 + "\n" for i in range(1200))
            frame_file = Path(temporary) / "frame.txt"
            frame_file.write_text(frame, encoding="utf-8")
            processes = [{"pid": 200 + i, "ppid": 101, "state": "S", "command": f"worker {i} " + "y" * 60} for i in range(1500)]
            env = self.environment(root, frame_file, processes)
            frame_bytes = frame.encode("utf-8")
            self.assertGreater(len(frame_bytes), BUDGETS["capture_receipt_bytes"])
            # The unbounded observation (in-process) decides snapshot_id and pane_revision from the full frame.
            spec = importlib.util.spec_from_file_location("kaola_observation_pd", OBSERVATION)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader
            spec.loader.exec_module(module)
            saved = dict(os.environ)
            os.environ.clear()
            os.environ.update(env)
            try:
                unbounded = module.build_from_environment()
            finally:
                os.environ.clear()
                os.environ.update(saved)
            self.assertGreater(len(json.dumps(unbounded, ensure_ascii=False, sort_keys=True).encode("utf-8")), BUDGETS["capture_receipt_bytes"])
            observed = self.helper("build", env)
            self.assertEqual(observed["result"], "observed")
            self.assertEqual(observed["snapshot_id"], unbounded["snapshot_id"], "snapshot_id is computed from the full frame")
            self.assertEqual(observed["pane_revision"], unbounded["pane_revision"])
            fields = observed["truncated"]["fields"]
            self.assertEqual(fields["raw_current_frame"]["total_bytes"], len(frame_bytes))
            self.assertEqual(fields["raw_current_frame"]["sha256"], hashlib.sha256(frame_bytes).hexdigest())
            self.assertEqual(fields["raw_current_frame"]["kept_bytes"], len(observed["raw_current_frame"].encode("utf-8")))
            self.assertLess(fields["raw_current_frame"]["kept_bytes"], len(frame_bytes))
            self.assertTrue(observed["raw_current_frame"].startswith("line "), "truncation lands on a line boundary")
            self.assertIn("line 001199", observed["raw_current_frame"], "the newest frame lines are kept")
            self.assertNotIn("line 000000", observed["raw_current_frame"])
            self.assertEqual(fields["child_processes"]["total"], len(processes))
            self.assertEqual(fields["child_processes"]["kept"], len(observed["child_processes"]))
            self.assertEqual(fields["child_processes"]["kept"], 32, "a short process excerpt survives beside the frame excerpt")
            self.assertEqual(observed["child_processes"], processes[:32], "the first process entries are kept")
            stream = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in processes).encode("utf-8")
            self.assertEqual(fields["child_processes"]["stream_sha256"], hashlib.sha256(stream).hexdigest())
            self.assertEqual(observed["child_process_count"], len(processes), "counts stay whole")
            self.assertEqual(observed["hard_evidence"], unbounded["hard_evidence"], "structural facts stay whole")
            self.assertEqual(observed["relay"], unbounded["relay"])
            self.assertIn("capture --full", observed["truncated"]["hint"])
            # status-view keeps the original totals and digests of an already bounded observation.
            status = self.helper("status-view", env, json.dumps(observed).encode("utf-8"))
            self.assertEqual(status["result"], "observed")
            self.assertEqual(status["truncated"]["fields"]["raw_current_frame"]["total_bytes"], len(frame_bytes))
            self.assertEqual(status["truncated"]["fields"]["raw_current_frame"]["sha256"], hashlib.sha256(frame_bytes).hexdigest())
            self.assertEqual(status["truncated"]["fields"]["raw_current_frame"]["kept_bytes"], len(status["raw_current_frame"].encode("utf-8")))
            self.assertEqual(status["truncated"]["fields"]["child_processes"]["total"], len(processes))
            self.assertTrue(status["tui_detected"] and status["present"])
            # A receipt within budget passes through unchanged.
            frame_file.write_text("small frame\n❯\n", encoding="utf-8")
            small = self.helper("build", self.environment(root, frame_file, processes[:3]))
            self.assertNotIn("truncated", small)
            self.assertEqual(small["raw_current_frame"], "small frame\n❯\n")


class BoundedStatusIsIdempotentAndFinal(BoundedObserveAndStatus):
    """The status path bounds twice (build, then status-view with the wrapper fields).

    Repeated bounding must merge, never replace, the ``truncated`` block: original totals,
    counts, and digests survive, the newest frame lines and the process excerpt stay, and the
    line that is finally emitted (with ``result`` and, for grok, ``legacy_ownership``) is the
    one that stays within budget. 1 500 child processes and a 400-column, 340-row frame.
    """

    ROWS = 340

    def load_module(self):
        spec = importlib.util.spec_from_file_location("kaola_observation_final", OBSERVATION)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        return module

    def build_in_process(self, module, env: dict[str, str]) -> dict:
        saved = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            return module.build_from_environment()
        finally:
            os.environ.clear()
            os.environ.update(saved)

    @staticmethod
    def frame_text(width: int, rows: int) -> str:
        return "".join(f"fill {i:05d} " + "x" * (width - 11) + "\n" for i in range(1, rows + 1))

    def assert_evidence(self, receipt: dict, frame_bytes: bytes, processes: list, where: str) -> None:
        self.assertIn("truncated", receipt, where)
        fields = receipt["truncated"]["fields"]
        self.assertIn("raw_current_frame", fields, f"{where}: the frame evidence must survive")
        self.assertIn("child_processes", fields, f"{where}: the process evidence must survive")
        frame = fields["raw_current_frame"]
        self.assertEqual(frame["total_bytes"], len(frame_bytes), where)
        self.assertEqual(frame["sha256"], hashlib.sha256(frame_bytes).hexdigest(), where)
        self.assertEqual(frame["kept_bytes"], len(receipt["raw_current_frame"].encode("utf-8")), where)
        self.assertLess(frame["kept_bytes"], frame["total_bytes"], where)
        self.assertIn(f"fill {self.ROWS:05d}", receipt["raw_current_frame"], f"{where}: the newest frame line is kept")
        self.assertNotIn("fill 00001", receipt["raw_current_frame"], where)
        self.assertTrue(receipt["raw_current_frame"].startswith("fill "), f"{where}: whole lines only")
        stream = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in processes).encode("utf-8")
        procs = fields["child_processes"]
        self.assertEqual(procs["total"], len(processes), where)
        self.assertEqual(procs["stream_bytes"], len(stream), where)
        self.assertEqual(procs["stream_sha256"], hashlib.sha256(stream).hexdigest(), where)
        self.assertEqual(procs["kept"], len(receipt["child_processes"]), where)
        self.assertEqual(receipt["child_processes"], processes[:procs["kept"]], f"{where}: the process excerpt stays the first entries")
        self.assertEqual(receipt["child_process_count"], len(processes), f"{where}: counts stay whole")
        self.assertIn("capture --full", receipt["truncated"]["hint"], where)

    def test_repeated_bounding_merges_prior_truncation_metadata(self) -> None:
        module = self.load_module()
        limit = BUDGETS["capture_receipt_bytes"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            frame = self.frame_text(400, self.ROWS)
            frame_file = Path(temporary) / "frame.txt"
            frame_file.write_text(frame, encoding="utf-8")
            frame_bytes = frame.encode("utf-8")
            processes = [{"pid": 200 + i, "ppid": 101, "state": "S", "command": f"worker {i} " + "y" * 60} for i in range(1500)]
            unbounded = self.build_in_process(module, self.environment(root, frame_file, processes))
            self.assertGreater(emitted_line_size(unbounded), limit)
            first = module.bound_observation(unbounded, limit)
            self.assertLessEqual(emitted_line_size(first), limit)
            self.assert_evidence(first, frame_bytes, processes, "first bound")
            self.assertEqual(first["truncated"]["fields"]["child_processes"]["kept"], 32)
            # Idempotent: bounding an already bounded receipt at the same limit changes nothing.
            self.assertEqual(module.bound_observation(first, limit), first)
            self.assertEqual(module.bound_observation(json.loads(json.dumps(first)), limit), first)
            # Monotone: a tighter second bound (what status-view's added fields force) keeps every
            # original total, count, and digest, lowers only the kept figures, and keeps the newest line.
            tighter = module.bound_observation(json.loads(json.dumps(first)), emitted_line_size(first) - 700)
            self.assertLessEqual(emitted_line_size(tighter), emitted_line_size(first) - 700)
            self.assert_evidence(tighter, frame_bytes, processes, "second bound")
            self.assertLess(tighter["truncated"]["fields"]["raw_current_frame"]["kept_bytes"], first["truncated"]["fields"]["raw_current_frame"]["kept_bytes"])
            self.assertEqual(tighter["truncated"]["fields"]["child_processes"]["kept"], 32, "the process excerpt outlives a frame cut")
            self.assertEqual(tighter["snapshot_id"], unbounded["snapshot_id"])
            self.assertEqual(tighter["pane_revision"], unbounded["pane_revision"])
            # A third, much tighter bound may drop the process excerpt entirely, but never its evidence.
            third = module.bound_observation(json.loads(json.dumps(tighter)), 24000)
            self.assertLessEqual(emitted_line_size(third), 24000)
            fields = third["truncated"]["fields"]
            self.assertEqual(fields["child_processes"]["total"], len(processes))
            self.assertEqual(fields["child_processes"]["stream_sha256"], first["truncated"]["fields"]["child_processes"]["stream_sha256"])
            self.assertEqual(fields["child_processes"]["kept"], len(third["child_processes"]))
            self.assertEqual(fields["raw_current_frame"]["total_bytes"], len(frame_bytes))
            self.assertEqual(fields["raw_current_frame"]["sha256"], hashlib.sha256(frame_bytes).hexdigest())
            self.assertIn(f"fill {self.ROWS:05d}", third["raw_current_frame"])
            # And bounding that one again is still a no-op.
            self.assertEqual(module.bound_observation(json.loads(json.dumps(third)), 24000), third)

    def test_real_build_to_status_path_keeps_evidence_and_wrapper_fields_within_budget(self) -> None:
        """Drive build then status-view exactly as emit_status/start do, over a width sweep that
        forces the second bound, and measure the line the wrapper actually emits."""
        module = self.load_module()
        limit = BUDGETS["capture_receipt_bytes"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            processes = [{"pid": 200 + i, "ppid": 101, "state": "S", "command": f"worker {i} " + "y" * 60} for i in range(1500)]
            frame_file = Path(temporary) / "frame.txt"
            forced = 0
            for width in (*range(200, 400, 10), 399, 400):
                frame = self.frame_text(width, self.ROWS)
                frame_file.write_text(frame, encoding="utf-8")
                frame_bytes = frame.encode("utf-8")
                self.assertGreater(len(frame_bytes), limit)
                for platform, result, legacy in (("grok", "present", "false"), ("claude-code", "started", None)):
                    env = self.environment(root, frame_file, processes)
                    env.update(KPR_PLATFORM=platform, KPR_RUNTIME=platform)
                    build = subprocess.run([sys.executable, str(OBSERVATION), "build"], capture_output=True, env=env)
                    self.assertEqual(build.returncode, 0, build.stderr.decode())
                    self.assertLessEqual(len(build.stdout), limit, "the emitted observe line, newline included")
                    observed = json.loads(build.stdout)
                    self.assert_evidence(observed, frame_bytes, processes, f"width {width} build")
                    # Does the status view plus the wrapper fields push this bounded receipt over the limit?
                    intermediate = module.status_view(observed)
                    intermediate["result"] = result
                    if legacy is not None:
                        intermediate["legacy_ownership"] = legacy == "true"
                    if emitted_line_size(intermediate) > limit:
                        forced += 1
                    wrapper_env = dict(env, KPR_STATUS_RESULT=result)
                    if legacy is not None:
                        wrapper_env["KPR_STATUS_LEGACY"] = legacy
                    status = subprocess.run([sys.executable, str(OBSERVATION), "status-view"], input=build.stdout, capture_output=True, env=wrapper_env)
                    self.assertEqual(status.returncode, 0, status.stderr.decode())
                    self.assertEqual(len(status.stdout.splitlines()), 1)
                    self.assertLessEqual(len(status.stdout), limit, f"width {width}: the emitted status line, newline included")
                    receipt = json.loads(status.stdout)
                    self.assert_evidence(receipt, frame_bytes, processes, f"width {width} status")
                    self.assertEqual(receipt["result"], result, f"width {width}: the wrapper field is inside the bounded line")
                    if platform == "grok":
                        self.assertIs(receipt["legacy_ownership"], False)
                        self.assertIn("grok_tui", receipt)
                    else:
                        self.assertNotIn("legacy_ownership", receipt)
                    self.assertTrue(receipt["present"] and receipt["tui_detected"])
                    self.assertEqual(receipt["snapshot_id"], observed["snapshot_id"])
                    self.assertEqual(receipt["truncated"]["fields"]["child_processes"]["kept"], 32)
                    self.assertLessEqual(receipt["truncated"]["fields"]["raw_current_frame"]["kept_bytes"], observed["truncated"]["fields"]["raw_current_frame"]["kept_bytes"])
            self.assertGreater(forced, 0, "the sweep must force the second bound at least once")


class BoundedAcpStateIsFinal(unittest.TestCase):
    """bound_state_receipt measures the line it emits, so no summary entry can push it over."""

    def test_state_receipt_never_exceeds_the_limit_when_pending_permissions_decide(self) -> None:
        spec = importlib.util.spec_from_file_location("kaola_acp_final", ACP_CLI)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        pending = [{"request_id": f"req-{i:04d}", "title": "permission " + "p" * 40, "options": ["allow", "reject"]} for i in range(400)]
        receipt = {"schema": "kaola-acp-state/1", "state": "waiting-permission", "activity_hint": "blocked", "holder_pid": 4242,
                   "event_cursor": 12, "pending_permissions": pending,
                   "record": {"platform": "grok", "session": "s", "repo": "/r", "notes": "n" * 3000}}
        raw = json.dumps(pending, ensure_ascii=False, sort_keys=True).encode("utf-8")
        for limit in range(6000, 6400, 7):
            bounded = module.bound_state_receipt(json.loads(json.dumps(receipt)), limit)
            self.assertLessEqual(emitted_line_size(bounded), limit, f"limit {limit}")
            summary = bounded["truncated"]["fields"]["pending_permissions"]
            self.assertEqual(summary["total"], len(pending))
            self.assertEqual(summary["kept"], len(bounded["pending_permissions"]))
            self.assertEqual(summary["kept"] + summary["dropped"], summary["total"])
            self.assertGreater(summary["kept"], 0, "the newest permissions survive")
            self.assertEqual(bounded["pending_permissions"], pending[-summary["kept"]:], "the newest entries are the ones kept")
            self.assertEqual(summary["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(bounded["truncated"]["fields"]["record"]["kind"], "object")
            self.assertEqual(bounded["state"], "waiting-permission")
        self.assertEqual(module.bound_state_receipt(json.loads(json.dumps(receipt)), 10 ** 6), receipt, "within budget passes through")


class BoundedAcpCapture(unittest.TestCase):
    """Ordinary ACP capture is bounded the same way as PTY capture, proven against the mock agent."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-pd-acp-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.session = f"pdacp-{os.getpid()}"
        cls.started = False

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.started:
            cls.cli("stop", "--force", check=False)
        cls._tmp.cleanup()

    @classmethod
    def cli(cls, command: str, *args: str, check: bool = True) -> dict:
        env = dict(os.environ, KAOLA_ACP_RECORD_ROOT=str(cls.root / "records"), MOCK_ACP_LOG=str(cls.root / "mock.jsonl"))
        argv = [sys.executable, str(ACP_CLI), "grok", command, "--repo", str(cls.repo), "--session", cls.session,
                "--command", f"{sys.executable} {MOCK_ACP_AGENT} --scenario follow_flood", *args]
        completed = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120)
        if check and completed.returncode != 0:
            raise AssertionError(f"{command} failed: {completed.stderr}\n{completed.stdout}")
        return json.loads(completed.stdout) if completed.stdout.strip() else {}

    @staticmethod
    def stream_sha256(events: list) -> str:
        return hashlib.sha256("".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in events).encode("utf-8")).hexdigest()

    def test_ordinary_capture_is_bounded_verifiable_and_full_is_exempt(self) -> None:
        type(self).started = True
        self.cli("start")
        for _ in range(2):  # follow_flood emits 280 session updates per turn
            self.cli("send", "--text", "flood please")
        full = self.cli("capture", "--full", "--inline")
        events = full["events"]
        self.assertGreater(len(json.dumps(full).encode("utf-8")), BUDGETS["capture_receipt_bytes"], "--full is the explicit, unbounded request")
        self.assertNotIn("truncated", full)
        self.assertGreater(len(events), 500)
        lines = 1000
        bounded = self.cli("capture", "--lines", str(lines))
        line = json.dumps(bounded, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.assertLessEqual(len(line), BUDGETS["capture_receipt_bytes"])
        truncated = bounded["truncated"]
        selected = events[-lines:]
        self.assertEqual(truncated["list"], "events")
        self.assertEqual(truncated["total"], len(selected))
        self.assertEqual(truncated["kept"], len(bounded["events"]))
        self.assertEqual(truncated["dropped"] + truncated["kept"], truncated["total"])
        self.assertGreater(truncated["dropped"], 0)
        self.assertEqual(truncated["stream_sha256"], self.stream_sha256(selected), "the marker names the untruncated stream")
        self.assertEqual(truncated["stream_bytes"], len("".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in selected).encode("utf-8")))
        self.assertEqual(bounded["events"], selected[-truncated["kept"]:], "the newest events are the ones kept")
        self.assertEqual(bounded["events"][-1]["cursor"], events[-1]["cursor"])
        self.assertIn("--full", truncated["hint"])
        since = self.cli("capture", "--since", "0")
        self.assertLessEqual(len(json.dumps(since, ensure_ascii=False, sort_keys=True).encode("utf-8")), BUDGETS["capture_receipt_bytes"])
        self.assertIn("truncated", since)
        small = self.cli("capture", "--lines", "5")
        self.assertNotIn("truncated", small, "a receipt within budget passes through unchanged")
        self.assertEqual(len(small["events"]), 5)
        for command in ("observe", "status"):
            plain = self.cli(command)
            self.assertNotIn("truncated", plain, f"{command} within budget passes through unchanged")


class BoundedAcpObserveAndStatus(unittest.TestCase):
    """Ordinary ACP observe/status receipts are bounded the same way, proven against the mock agent."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-pd-acp-state-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.session = f"pdstate-{os.getpid()}"
        # A native option list large enough that the session/new result alone exceeds the budget.
        cls.options = [{"id": f"option_{i:04d}", "name": f"Option {i}", "category": "mode",
                        "description": "d" * 120, "currentValue": "a",
                        "options": [{"value": "a", "name": "A"}, {"value": "b", "name": "B"}]} for i in range(600)]
        cls.started = False

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.started:
            cls.cli("stop", "--force", check=False)
        cls._tmp.cleanup()

    @classmethod
    def cli(cls, command: str, *args: str, check: bool = True) -> dict:
        env = dict(os.environ, KAOLA_ACP_RECORD_ROOT=str(cls.root / "records"), MOCK_ACP_LOG=str(cls.root / "mock.jsonl"),
                   MOCK_ACP_CONFIG=json.dumps({"new": cls.options}))
        argv = [sys.executable, str(ACP_CLI), "grok", command, "--repo", str(cls.repo), "--session", cls.session,
                "--command", f"{sys.executable} {MOCK_ACP_AGENT} --scenario tool_call_only", *args]
        completed = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120)
        if check and completed.returncode != 0:
            raise AssertionError(f"{command} failed: {completed.stderr}\n{completed.stdout}")
        return json.loads(completed.stdout) if completed.stdout.strip() else {}

    def test_observe_and_status_over_budget_summarise_structures_by_size_and_sha256(self) -> None:
        type(self).started = True
        self.cli("start")
        stream = json.dumps(self.options, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.assertGreater(len(stream), BUDGETS["capture_receipt_bytes"])
        for command in ("observe", "status"):
            receipt = self.cli(command)
            line = json.dumps(receipt, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.assertLessEqual(len(line), BUDGETS["capture_receipt_bytes"], command)
            fields = receipt["truncated"]["fields"]
            self.assertIn("initial_config_options", fields, command)
            self.assertEqual(fields["initial_config_options"]["kind"], "list")
            self.assertEqual(fields["initial_config_options"]["count"], len(self.options))
            self.assertEqual(fields["initial_config_options"]["bytes"], len(stream))
            self.assertEqual(fields["initial_config_options"]["sha256"], hashlib.sha256(stream).hexdigest(), "the digest names the full value")
            self.assertEqual(receipt["initial_config_options"], {"omitted": True, "bytes": len(stream), "sha256": hashlib.sha256(stream).hexdigest()})
            for name, summary in fields.items():
                self.assertEqual(len(summary["sha256"]), 64, name)
                self.assertEqual(receipt[name]["omitted"], True, name)
                self.assertEqual(receipt[name]["bytes"], summary["bytes"], name)
            self.assertEqual(fields["record"]["kind"], "object")
            self.assertIn("initial_config_options", fields["record"]["keys"], "the on-disk record carried the same list")
            for scalar in ("state", "activity_hint", "holder_pid", "event_cursor", "mutation_status", "acp_session_id"):
                self.assertIn(scalar, receipt, f"{command}: scalar facts stay whole")
            self.assertNotIsInstance(receipt["state"], dict)
            self.assertIn("sha256", receipt["truncated"]["hint"])


class InvariantIsDocumented(unittest.TestCase):
    def test_conventions_architecture_agents_and_both_templates_state_the_invariant(self) -> None:
        conventions = re.sub(r"\s+", " ", (PROJECT / "docs" / "conventions.md").read_text(encoding="utf-8"))
        self.assertIn("## Progressive disclosure", conventions)
        for clause in ("Discovery exposes only a stable name and a short description", "never a worker body", "Selecting one worker loads that worker only",
                       "the model never reads their source", "Host adapters may not flatten", "templates/budgets.json"):
            self.assertIn(clause, conventions, clause)
        architecture = (PROJECT / "docs" / "architecture.md").read_text(encoding="utf-8")
        self.assertIn("### Progressive disclosure", architecture)
        self.assertIn("progressive disclosure is a locked invariant", (PROJECT / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("### Progressive disclosure", (PROJECT / "templates" / "orchestrator" / "SKILL.md.tmpl").read_text(encoding="utf-8"))
        self.assertIn("Progressive\ndisclosure:", (PROJECT / "templates" / "SKILL.md.tmpl").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
