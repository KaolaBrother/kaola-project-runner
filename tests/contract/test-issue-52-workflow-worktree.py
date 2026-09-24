#!/usr/bin/env python3
"""Issue #52: canonical-root start and worker-owned Workflow worktree decisions.

Guidance is a decision default, not a transport gate. Tests pin template/doc
consistency, keep adapters free of a hardcoded ``.kw/worktrees`` refusal, and
prove the ACP transport (the only one since Issue #130) accepts a linked
worktree as a Git top-level.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_ID = "kaola-project-runner"
WORKER_IDS = (
    "claude-code",
    "codex",
    "cursor-cli",
    "devin",
    "droid",
    "dsh",
    "grok",
    "kimi-cli",
    "opencode",
    "zcode",
)
WORKER_SKILL_IDS = tuple(f"{wid}-{ORCHESTRATOR_ID}" for wid in WORKER_IDS)
TRANSPORT_SCRIPT_NAMES = (
    "kaola-tmux.sh",
    "kaola-acp.py",
    "runtime-tmux.sh",
)
GROK_BOT_OWNED = (
    PROJECT / "templates" / "grok-bot",
    PROJECT / "docs" / "grok-bot-host.md",
    PROJECT / "hosts" / "grok-bot",
)

WORKER_MARKERS = (
    "canonical Git root",
    "installed `workflow-next`",
    "Agent decisions, not transport gates",
)
ORCHESTRATOR_MARKERS = (
    "canonical project root",
    "workflow-next",
    "recovery are Agent decisions, not transport gates",
    "](references/workflow-worktree.md)",
)
REFERENCE_MARKERS = (
    "canonical project root",
    "child worktree",
    "Agent decisions rather than transport gates",
    "The transport never classifies Workflow mode, and standalone Runner use is unchanged",
    "## Normal path",
    "## Evidence-backed exception",
    "## Concurrent sessions",
    "## Recovery and migration",  # Issue #157 (§1.4): Recovery and Migration merged
)
DOC_MARKERS = (
    "canonical project root",
    "workflow-next",
    "child worktree",
)
AUTHORIZING_GATE = (
    r"reject linked worktrees?",
    r"refuse .{0,60}linked worktree",
    r"must not start .{0,40}(?:in|inside) .{0,40}worktree",
    r"runtime-tmux\.sh .{0,40}reject .{0,40}worktree",
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load_acp(path: Path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("kaola_acp_issue52", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def authorizes_gate(text: str) -> str | None:
    for raw in re.split(r"(?<=[.!?])\s+|\n+", text):
        sentence = normalize(raw)
        if not sentence:
            continue
        if re.search(
            r"\b(do not|don't|did not|does not|never|must not|cannot|not a|rather than|instead of)\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            continue
        for pattern in AUTHORIZING_GATE:
            if re.search(pattern, sentence, flags=re.IGNORECASE):
                return sentence
    return None


def make_linked_worktree(temporary: str) -> tuple[Path, Path, Path]:
    root = Path(temporary) / "project"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Issue 52"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "issue-52@example.invalid"],
        cwd=root,
        check=True,
    )
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True)
    nested = root / "docs"
    nested.mkdir()
    child = root / ".kw" / "worktrees" / "bundle-demo"
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "workflow/demo", str(child)],
        cwd=root,
        check=True,
    )
    return root.resolve(), nested, child.resolve()


class Issue52GuidanceConsistency(unittest.TestCase):
    def test_worker_template_and_generated_skills_share_root_start_guidance(self) -> None:
        template = normalize((PROJECT / "templates" / "SKILL.md.tmpl").read_text(encoding="utf-8"))
        for marker in WORKER_MARKERS:
            self.assertIn(normalize(marker), template, f"worker template missing {marker!r}")
        for skill_id in WORKER_SKILL_IDS:
            body = normalize((PROJECT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8"))
            for marker in WORKER_MARKERS:
                self.assertIn(normalize(marker), body, f"{skill_id} missing {marker!r}")

    def test_orchestrator_template_generated_skill_and_reference_agree(self) -> None:
        template = normalize(
            (PROJECT / "templates" / "orchestrator" / "SKILL.md.tmpl").read_text(encoding="utf-8")
        )
        generated = normalize(
            (PROJECT / "skills" / ORCHESTRATOR_ID / "SKILL.md").read_text(encoding="utf-8")
        )
        for marker in ORCHESTRATOR_MARKERS:
            self.assertIn(normalize(marker), template, f"orchestrator template missing {marker!r}")
            self.assertIn(normalize(marker), generated, f"generated orchestrator missing {marker!r}")
        reference = (
            PROJECT / "templates" / "orchestrator" / "references" / "workflow-worktree.md"
        )
        self.assertTrue(reference.is_file(), "orchestrator reference must exist as source")
        rendered = PROJECT / "skills" / ORCHESTRATOR_ID / "references" / "workflow-worktree.md"
        self.assertTrue(rendered.is_file(), "renderer must copy the worktree reference")
        body = reference.read_text(encoding="utf-8")
        self.assertEqual(body, rendered.read_text(encoding="utf-8"))
        normalized_body = normalize(body)
        for marker in REFERENCE_MARKERS:
            self.assertIn(normalize(marker), normalized_body, f"worktree reference missing {marker!r}")

    def test_docs_and_agents_state_the_same_default(self) -> None:
        surfaces = (
            PROJECT / "README.md",
            PROJECT / "docs" / "architecture.md",
            PROJECT / "docs" / "conventions.md",
            PROJECT / "docs" / "api.md",
            PROJECT / "AGENTS.md",
        )
        for path in surfaces:
            text = normalize(path.read_text(encoding="utf-8"))
            for marker in DOC_MARKERS:
                self.assertIn(normalize(marker), text, f"{path.relative_to(PROJECT)} missing {marker!r}")
        readme = (PROJECT / "README.md").read_text(encoding="utf-8")
        self.assertIn("### Normal path", readme)
        self.assertIn("### Evidence-backed exception", readme)
        api = (PROJECT / "docs" / "api.md").read_text(encoding="utf-8")
        self.assertIn("linked worktree is a valid Git top-level", api)
        self.assertIn("not a transport refusal", api)

    def test_grok_bot_host_surfaces_are_out_of_scope(self) -> None:
        """Issue #56 owns Grok Bot host install/UAT; this issue must not rewrite them."""
        for path in GROK_BOT_OWNED:
            self.assertTrue(path.exists(), path)
        bridge = PROJECT / "hosts" / "grok-bot" / "kaola-delegator.md"
        guide = PROJECT / "hosts" / "grok-bot" / "INSTALL.md"
        for path in (bridge, guide):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("workflow-worktree.md", text)
            self.assertNotIn("root-start", text)


class Issue52NoTransportGate(unittest.TestCase):
    def transport_files(self) -> list[Path]:
        files = [
            PROJECT / "scripts" / "kaola-tmux.sh",
            PROJECT / "scripts" / "kaola-acp.py",
        ]
        files.extend(sorted((PROJECT / "scripts" / "adapters").glob("*.sh")))
        for skill_id in WORKER_SKILL_IDS:
            scripts = PROJECT / "skills" / skill_id / "scripts"
            for name in TRANSPORT_SCRIPT_NAMES:
                path = scripts / name
                if path.is_file():
                    files.append(path)
            files.extend(sorted((scripts / "adapters").glob("*.sh")))
        return files

    def test_runtime_scripts_have_no_hardcoded_kw_worktrees_refusal(self) -> None:
        for path in self.transport_files():
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                ".kw/worktrees",
                text,
                f"{path.relative_to(PROJECT)} hardcoded .kw/worktrees",
            )
            self.assertIsNone(
                authorizes_gate(text),
                f"{path.relative_to(PROJECT)} authorized a worktree transport gate",
            )

    def test_guidance_forbids_a_worktree_transport_gate(self) -> None:
        surfaces = [
            PROJECT / "templates" / "SKILL.md.tmpl",
            PROJECT / "templates" / "orchestrator" / "SKILL.md.tmpl",
            PROJECT / "templates" / "orchestrator" / "references" / "workflow-worktree.md",
            PROJECT / "templates" / "references" / "acp.md.tmpl",
            PROJECT / "templates" / "references" / "platform.md.tmpl",
            PROJECT / "README.md",
            PROJECT / "docs" / "architecture.md",
            PROJECT / "docs" / "conventions.md",
            PROJECT / "docs" / "api.md",
        ]
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            wrong = authorizes_gate(text)
            self.assertIsNone(wrong, f"{path.relative_to(PROJECT)}: {wrong!r}")

    def test_validate_sh_runs_this_suite(self) -> None:
        text = (PROJECT / "scripts" / "validate.sh").read_text(encoding="utf-8")
        self.assertIn("test-issue-52-workflow-worktree.py", text)


class Issue52LinkedWorktreeIsValidRepo(unittest.TestCase):
    def test_acp_accepts_canonical_root_and_linked_worktree(self) -> None:
        # Issue #130: the PTY `--repo` identity check went with the tmux
        # branch; kaola-acp.py resolve_repo is the one Git-root check.
        acp = load_acp(PROJECT / "scripts" / "kaola-acp.py")
        source = (PROJECT / "scripts" / "kaola-acp.py").read_text(encoding="utf-8")
        self.assertIn('"rev-parse", "--show-toplevel"', source)
        self.assertIn("--repo must name the Git root", source)
        with tempfile.TemporaryDirectory(prefix="kaola-issue-52-wt-") as temporary:
            root, nested, child = make_linked_worktree(temporary)
            self.assertEqual(acp.resolve_repo(str(root)), str(root))
            self.assertEqual(acp.resolve_repo(str(child)), str(child))
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit):
                    acp.resolve_repo(str(nested))
            self.assertIn("--repo must name the Git root", stderr.getvalue(),
                          "a non-root subdirectory must remain invalid")


class Issue52BehavioralExamples(unittest.TestCase):
    def test_reference_examples_do_not_claim_transport_made_the_decision(self) -> None:
        body = (
            PROJECT
            / "templates"
            / "orchestrator"
            / "references"
            / "workflow-worktree.md"
        ).read_text(encoding="utf-8")
        normal = body.split("## Normal path", 1)[1].split("## Evidence-backed exception", 1)[0]
        exception = body.split("## Evidence-backed exception", 1)[1].split("## ", 1)[0]
        self.assertIn("canonical", normal.lower())
        self.assertIn("workflow-next", normal)
        self.assertIn("worktree", normal.lower())
        self.assertIn("Agent", exception)
        self.assertNotIn("transport refused", exception.lower())
        self.assertNotIn("transport decided", exception.lower())
        self.assertIn("inspect", body.lower())
        self.assertIn("preserve", body.lower())


if __name__ == "__main__":
    unittest.main()
