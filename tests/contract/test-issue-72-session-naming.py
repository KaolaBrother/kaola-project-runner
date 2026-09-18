#!/usr/bin/env python3
"""Issue #72 contract: issue-scoped dispatch names, one issue per run.

What a contract check can honestly check is asserted here:

* the rendered control-plane surfaces (main Skill, heartbeat skeleton, the new
  ``issue-dispatch.md`` reference) carry the naming grammar, the project-code slot,
  and the one-issue-per-run rule, and the templates they are generated from agree;
* the documented anchored grammar is a strict subset of the Runner's existing
  ``--session`` syntax -- it accepts the contract's own examples and rejects the
  cross-bind negatives (different issue, missing ``i`` delimiter, issue read out of
  the purpose token, an old unanchored name);
* the transport gained nothing: the session validator is still the single 1-80
  syntax, no worker Skill learned an issue rule, and no budget, Workflow state
  field, registry, or daemon appeared.

What it deliberately does NOT check: that any consumer displays the bar. Nothing in
this repository was verified end to end against KaolaTerminal, and the run records
say so. The live two-session ACP evidence for acceptance item 2 lives with the run,
in ``kaola-workflow/issue-72/evidence/``, not here.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
ORCHESTRATOR = PROJECT / "skills" / "kaola-project-runner"
SKILL = ORCHESTRATOR / "SKILL.md"
SKELETON = ORCHESTRATOR / "references" / "heartbeat-skeleton.md"
DISPATCH = ORCHESTRATOR / "references" / "issue-dispatch.md"
WORKTREE_REF = ORCHESTRATOR / "references" / "workflow-worktree.md"
TEMPLATES = PROJECT / "templates" / "orchestrator"
BUDGETS = PROJECT / "templates" / "budgets.json"
WORKER_IDS = ("claude-code", "codex", "cursor-cli", "devin", "droid", "grok",
              "kimi-cli", "opencode", "zcode")

# The contract's own grammar, read off references/issue-dispatch.md:
# <platform>-<PROJECT>-i<ISSUE>-<unique-purpose>, fixed field order, literal `i`
# delimiter, decimal issue number, platform equal to a Runner platform id.
PLATFORM_ALTERNATION = "|".join(re.escape(p) for p in WORKER_IDS)
ANCHORED_NAME = re.compile(
    rf"^(?P<platform>{PLATFORM_ALTERNATION})-(?P<project>[A-Za-z0-9]+)-i(?P<issue>[0-9]+)-(?P<purpose>[A-Za-z0-9][A-Za-z0-9_.-]*)$"
)


def load_acp():
    path = PROJECT / "scripts" / "kaola-acp.py"
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("kaola_acp_issue72", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class RenderedSurfacesStateTheRule(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = normalize(SKILL.read_text(encoding="utf-8"))
        self.skeleton = SKELETON.read_text(encoding="utf-8")
        self.dispatch = DISPATCH.read_text(encoding="utf-8")

    def test_main_skill_states_the_name_the_code_slot_and_one_issue_per_run(self) -> None:
        self.assertIn("`<platform>-<CODE>-i<ISSUE>-<purpose>`", self.skill)
        self.assertIn("droid-KT-i274-parser", self.skill)
        self.assertIn("heartbeat's declared project short code", self.skill)
        self.assertIn("verify it in the start receipt", self.skill)
        self.assertIn("keep the rule on later dispatches and restarts", self.skill)
        self.assertIn("One run claims one real issue", self.skill)
        self.assertIn("never a bundle claim, worktree, Mission List or session spanning several", self.skill)
        self.assertIn("issue-less tasks carry no issue number and never an invented one", self.skill)
        self.assertIn("](references/issue-dispatch.md)", self.skill)

    def test_heartbeat_skeleton_carries_the_project_code_slot_and_both_rules(self) -> None:
        self.assertIn("本项目短码与仓库身份：", self.skeleton)
        self.assertIn("`--session <platform>-<本项目短码>-i<ISSUE>-<用途>`", self.skeleton)
        self.assertIn("droid-KT-i274-parser", self.skeleton)
        self.assertIn("在 start 回执里核对该名字", self.skeleton)
        self.assertIn("一个 Workflow run 只认领一个真实 Issue", self.skeleton)
        self.assertIn("不用 bundle/多 Issue 模式", self.skeleton)
        # The project code must survive the per-beat subtraction of Issue #68.
        keep = self.skeleton.split("保留：", 1)[1]
        self.assertIn("本项目短码与派工命名/单 Issue 约束", keep)

    def test_reference_states_the_grammar_negatives_and_non_goals(self) -> None:
        self.assertIn("<platform>-<PROJECT>-i<ISSUE>-<unique-purpose>", self.dispatch)
        self.assertIn("kimi-cli-KT-i274-review-2", self.dispatch)
        self.assertIn("^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$", self.dispatch)
        self.assertIn("adds no second validator", self.dispatch)
        self.assertIn("never infer an issue from an arbitrary substring or from the purpose", normalize(self.dispatch))
        self.assertIn("never stop or restart a live session solely to rename it", normalize(self.dispatch))
        self.assertIn("native ACP session id is unchanged by this rule", normalize(self.dispatch))
        self.assertIn("grandfathered for safe close-out", self.dispatch)
        joined = normalize(self.dispatch)
        self.assertIn("`claim_repository_id` and `issue_number`", joined)
        self.assertIn("It never predicts when one ACP process will finish", joined)
        self.assertIn("`all missions done` does not by itself mean review, finalize, merge, or issue close-out happened", joined)
        for fallback in ("missing or malformed name", "repository mismatch", "no active run",
                         "two active runs for one issue"):
            self.assertIn(fallback, joined, f"unknown-fallback case missing: {fallback}")
        self.assertIn("no mtime, newest-file, `session_marker`, worktree location, or native ACP id may override a conflict", joined)

    def test_templates_and_rendered_surfaces_agree(self) -> None:
        for template, rendered in (
            (TEMPLATES / "references" / "issue-dispatch.md", DISPATCH),
            (TEMPLATES / "references" / "workflow-worktree.md", WORKTREE_REF),
        ):
            self.assertTrue(template.is_file(), f"{template} must exist as source")
            self.assertEqual(template.read_text(encoding="utf-8"),
                             rendered.read_text(encoding="utf-8"),
                             f"{rendered.name} must be the rendered copy of its template")
        skill_template = normalize((TEMPLATES / "SKILL.md.tmpl").read_text(encoding="utf-8"))
        for marker in ("`<platform>-<CODE>-i<ISSUE>-<purpose>`", "One run claims one real issue",
                       "](references/issue-dispatch.md)"):
            self.assertIn(marker, skill_template, f"orchestrator template missing {marker!r}")

    def test_the_worktree_reference_no_longer_calls_a_run_a_bundle(self) -> None:
        body = WORKTREE_REF.read_text(encoding="utf-8")
        self.assertNotIn("reconcile the\n   bundle", body)
        self.assertNotIn("bundle-52", body)
        self.assertNotIn("branches/bundles/Mission Lists", body)
        self.assertNotIn("adopt an existing bundle", body)
        self.assertIn("issue-dispatch.md", body)


class ExamplesDoNotTeachTheOldName(unittest.TestCase):
    """An Agent copies the examples. Owner review of 6d78c61 caught
    `codex-kaola-issue-77` still being taught in the startup reference."""

    # Documented exemptions, each with its owner. Nothing else may bypass the rule.
    #   zcode-kaola-host     - a Host, not an issue-backed worker; dressing it up as one
    #                          would misstate what it is. Its naming belongs to Issue #74's
    #                          Delegator integration.
    #   codex-kaola-feature-a - a genuine violation, in zcode-host-dispatch.md, which Issue
    #                          #70's in-flight candidate is rewriting line by line (the name
    #                          also appears inside its event-id payloads). Out of this run's
    #                          authorized scope; raised to the outer Agent instead of
    #                          conflicting with a live branch.
    NOT_ISSUE_BACKED = {"zcode-kaola-host"}
    OWNED_ELSEWHERE = {"codex-kaola-feature-a"}

    def rendered_session_examples(self):
        found = []
        surfaces = [SKILL] + sorted((ORCHESTRATOR / "references").glob("*.md"))
        for path in surfaces:
            for name in re.findall(r"--session ([A-Za-z0-9][A-Za-z0-9_.-]*)", path.read_text(encoding="utf-8")):
                found.append((path.name, name))
        return found

    def test_every_worker_example_uses_an_issue_scoped_name(self) -> None:
        examples = self.rendered_session_examples()
        self.assertTrue(examples, "the orchestrator package must still show session examples")
        for surface, name in examples:
            with self.subTest(surface=surface, session=name):
                if name in self.NOT_ISSUE_BACKED or name in self.OWNED_ELSEWHERE:
                    continue
                self.assertIsNotNone(
                    ANCHORED_NAME.match(name),
                    f"{surface} teaches {name!r}, which bypasses the Issue #72 contract",
                )

    def test_the_startup_reference_keeps_one_exact_name_across_the_five_operations(self) -> None:
        body = (ORCHESTRATOR / "references" / "host-startup.md").read_text(encoding="utf-8")
        self.assertNotIn("codex-kaola-issue-77", body)
        worker = [n for s, n in self.rendered_session_examples()
                  if s == "host-startup.md" and n not in self.NOT_ISSUE_BACKED]
        self.assertEqual(len(set(worker)), 1, f"the worker example must be one exact name: {worker}")
        for operation in ("start", "send", "observe", "capture", "stop"):
            self.assertRegex(body, rf'"\$WORKER" {operation}\s+--repo "\$PROJECT" --session {worker[0]}')
        self.assertIn("](issue-dispatch.md)", body, "the example must point at the rule it follows")


class AnchoredGrammarSeparatesIssues(unittest.TestCase):
    def setUp(self) -> None:
        self.acp = load_acp()

    def parse(self, name: str):
        """The consumer's reading: anchored, or nothing."""
        match = ANCHORED_NAME.match(name)
        return match.groupdict() if match else None

    def test_contract_examples_parse_and_stay_inside_the_existing_session_syntax(self) -> None:
        for name, platform, project, issue in (
            ("droid-KT-i274-parser", "droid", "KT", "274"),
            ("kimi-cli-KT-i274-review-2", "kimi-cli", "KT", "274"),
            ("claude-code-KPR-i72-naming", "claude-code", "KPR", "72"),
        ):
            with self.subTest(name=name):
                self.assertIsNotNone(self.acp.SESSION_PATTERN.match(name),
                                     "the contract name must satisfy the existing 1-80 syntax")
                parsed = self.parse(name)
                self.assertIsNotNone(parsed, "the anchored grammar must accept the contract example")
                self.assertEqual((parsed["platform"], parsed["project"], parsed["issue"]),
                                 (platform, project, issue))
                self.assertIn(parsed["platform"], WORKER_IDS)

    def test_two_simultaneous_workers_on_one_issue_stay_distinct_but_share_the_issue(self) -> None:
        a, b = "droid-KT-i274-parser", "kimi-cli-KT-i274-review-2"
        self.assertNotEqual(a, b, "simultaneous same-issue sessions must have distinct names")
        first, second = self.parse(a), self.parse(b)
        self.assertEqual((first["project"], first["issue"]), (second["project"], second["issue"]))
        self.assertNotEqual(first["platform"], second["platform"])
        self.assertNotEqual(first["purpose"], second["purpose"])

    def test_a_different_issue_or_project_never_cross_binds(self) -> None:
        base = self.parse("droid-KT-i274-parser")
        other_issue = self.parse("droid-KT-i275-parser")
        other_project = self.parse("droid-KPR-i274-parser")
        self.assertNotEqual(base["issue"], other_issue["issue"])
        self.assertNotEqual(base["project"], other_project["project"])
        # 274 on another repository is the same decimal: the repository identity, not
        # the name, is what keeps them apart, which is why the reference requires it.
        self.assertEqual(base["issue"], other_project["issue"])
        self.assertIn("under the same repository identity",
                      normalize(DISPATCH.read_text(encoding="utf-8")))

    def test_malformed_and_old_names_fall_back_to_unknown(self) -> None:
        for name in (
            "zcode-kaola-refactor",          # the old example in the issue's repro
            "droid-KT-274-parser",           # no literal `i` delimiter
            "droid-KT-i-parser",             # no decimal issue
            "droid-i274-parser",             # no project code field
            "KT-droid-i274-parser",          # field order swapped
            "droid-KT-i274",                 # no purpose token, no distinctness
            "unknown-platform-KT-i274-x",    # platform is not a Runner platform id
            "droid-KT-ix274-parser",         # issue read out of the purpose token
        ):
            with self.subTest(name=name):
                self.assertIsNone(self.parse(name), f"{name!r} must not yield an issue binding")

    def test_an_issue_shaped_substring_elsewhere_is_not_an_issue(self) -> None:
        # The purpose token may legitimately contain `i` and digits; the anchored
        # fields are what bind, so this name binds issue 274 and not 999.
        parsed = self.parse("droid-KT-i274-retry-i999")
        self.assertEqual(parsed["issue"], "274")
        self.assertEqual(parsed["purpose"], "retry-i999")


class NoNewMechanism(unittest.TestCase):
    def test_the_session_validator_is_still_the_single_1_80_syntax(self) -> None:
        acp = load_acp()
        self.assertEqual(acp.SESSION_PATTERN.pattern, r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
        tmux = (PROJECT / "scripts" / "kaola-tmux.sh").read_text(encoding="utf-8")
        self.assertIn(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$', tmux)
        # A name with no issue must still start: this is scheduling policy, not a gate.
        for issue_less in ("kaola-diagnostic", "zcode-host-1", "droid-probe.2"):
            self.assertIsNotNone(acp.SESSION_PATTERN.match(issue_less),
                                 f"{issue_less!r} must remain a valid session name")

    def test_no_worker_skill_learned_an_issue_rule(self) -> None:
        for worker in WORKER_IDS:
            body = (PROJECT / "skills" / f"{worker}-kaola-project-runner" / "SKILL.md").read_text(encoding="utf-8")
            for leak in ("i<ISSUE>", "one issue per run", "issue-dispatch.md", "project short code"):
                self.assertNotIn(leak, body, f"{worker} worker Skill must stay transport-only ({leak!r})")

    def test_no_budget_was_raised_and_the_main_skill_clears_the_probe_ceiling(self) -> None:
        limits = json.loads(BUDGETS.read_text(encoding="utf-8"))
        self.assertLessEqual(limits["main_skill_bytes"], 17408)
        self.assertLessEqual(limits["reference_bytes"], 8192)
        self.assertLessEqual(len(SKILL.read_bytes()), limits["main_skill_bytes"])
        # Issue #71: test-issue-49-grok-bot-host.py appends 59 B to the orchestrator
        # template and then requires a successful render, so the honest ceiling is lower.
        self.assertLessEqual(len(SKILL.read_bytes()), limits["main_skill_bytes"] - 59,
                             "the main Skill must still render after the Issue #49 probe's 59 B")
        for reference in sorted((ORCHESTRATOR / "references").glob("*.md")):
            self.assertLessEqual(len(reference.read_bytes()), limits["reference_bytes"], reference.name)

    def test_no_new_workflow_state_field_registry_or_daemon(self) -> None:
        text = DISPATCH.read_text(encoding="utf-8") + SKILL.read_text(encoding="utf-8")
        for invented in ("session_identity", "session registry", "naming daemon", "name_index"):
            self.assertNotIn(invented, text, f"Issue #72 must not introduce {invented!r}")
        joined = normalize(DISPATCH.read_text(encoding="utf-8"))
        self.assertIn("Do not add a blocking classifier, a registry, a daemon, or a new Workflow state field", joined)
        self.assertIn("Nothing here was verified end to end against a consumer", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
