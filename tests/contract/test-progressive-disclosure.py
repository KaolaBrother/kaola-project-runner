#!/usr/bin/env python3
"""Progressive disclosure: a locked, platform-neutral invariant with measured budgets.

Discovery exposes only a stable name and a short description. Activating Project
Runner loads its body only, never a worker body. Selecting one worker loads that
worker only. References load only when the current operation needs them. Scripts
execute mechanically; the model never reads their source. Ordinary tool outputs are
bounded receipts on both transports -- PTY ``capture`` through ``bound-text``, ACP
``capture`` through ``bound_capture_receipt`` (``capture --full`` is the explicit
exception on both) -- proven behaviourally here against the mock ACP agent. Host adapters may not
flatten, concatenate, eagerly preload, or duplicate canonical Skill bodies. Budgets
live in ``templates/budgets.json``; ``render-skills.py --check`` and this suite fail
when a budget or a loading boundary regresses.
"""

from __future__ import annotations

import hashlib
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
WORKER_IDS = ("claude-code", "codex", "cursor-cli", "devin", "grok", "kimi-cli", "opencode")
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
