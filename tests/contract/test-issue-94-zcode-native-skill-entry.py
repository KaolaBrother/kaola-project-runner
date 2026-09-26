#!/usr/bin/env python3
"""Issue #94: the ZCode Host's one native Skill entry, end to end.

Every turn-opening prompt to a ZCode Host — first handoff, resume or live
attach, a new Host continuing the run, every worker-event heartbeat, and the
round after any compaction — opens with ``/kaola-project-runner`` on its own
first line. ZCode resolves it through the Skill tool against the installed
``kaola-project-runner`` Skill; re-invocation is idempotent. A busy ``steer``
guide is different: it enters the already-running turn verbatim, keeps the
loaded context, and is no new ``Skill`` invocation — none is promised. The
composite ``steer --steer-mode interrupt`` resends on a new turn but is NOT
a Host recovery entry: the holder sends the Agent's text verbatim on every
session, infers no Host identity from prompt content, and adds no entry
line — a caller wanting the resend to open a Host round supplies
``/kaola-project-runner`` itself. This
replaces the Issue #75 carrier: no durable ``AGENTS.md`` block is planted in
a consuming project, ordinary Agents carry no Host instruction, and no role
filtering, compaction detection, or manual ``SKILL.md`` read is required.

These tests pin the contract across the authoritative templates, the
generated Skills, the holder envelope, and the docs — and keep the
live-evidence boundaries honest.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ORCH_T = PROJECT / "templates" / "orchestrator"
DELEG_T = PROJECT / "templates" / "kaola-delegator"
SKILLS = PROJECT / "skills"
ORCH = SKILLS / "kaola-project-runner"
DELEG = SKILLS / "kaola-delegator"
HOLDER = PROJECT / "scripts" / "kaola-acp-holder.py"
DOC = PROJECT / "docs" / "zcode-host.md"
# Issue #157 (PR-M2): the dated measurement record left the loaded reference.
EVIDENCE = PROJECT / "docs" / "host-entry-evidence.md"

ENTRY = "/kaola-project-runner"


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class Templates(unittest.TestCase):
    """The authoritative sources carry the one entry and no old carrier."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.entry_ref = (ORCH_T / "references" / "zcode-native-skill-entry.md").read_text(
            encoding="utf-8")
        cls.startup = (ORCH_T / "references" / "host-startup.md.tmpl").read_text(
            encoding="utf-8")
        cls.main = (ORCH_T / "SKILL.md.tmpl").read_text(encoding="utf-8")
        cls.dispatch = (ORCH_T / "references" / "zcode-host-dispatch.md.tmpl").read_text(
            encoding="utf-8")
        cls.skeleton = (ORCH_T / "references" / "heartbeat-skeleton.txt").read_text(
            encoding="utf-8")
        cls.handoff = (DELEG_T / "references" / "handoff.md.tmpl").read_text(
            encoding="utf-8")
        cls.evidence = EVIDENCE.read_text(encoding="utf-8")

    def test_old_carrier_reference_is_deleted(self) -> None:
        self.assertFalse((ORCH_T / "references" / "zcode-compact-recovery.md").exists())
        for name, text in (("startup", self.startup), ("main", self.main),
                           ("dispatch", self.dispatch), ("skeleton", self.skeleton),
                           ("handoff", self.handoff)):
            with self.subTest(surface=name):
                self.assertNotIn("zcode-compact-recovery", text)

    def test_reference_covers_every_entry_point(self) -> None:
        text = flat(self.entry_ref)
        for needle in ("first startup", "resume or live attach",
                       "new Host continuing", "worker-event heartbeat",
                       "round after any context compaction"):
            self.assertIn(needle, text)
        self.assertIn("opens with the native Skill command\n"
                      "`/kaola-project-runner` on its own first line", self.entry_ref)

    def test_reference_scopes_the_entry_to_turn_opening_prompts(self) -> None:
        text = flat(self.entry_ref)
        self.assertIn("Every prompt that opens a Host turn", text)
        for needle in ("idle `send`", "first handoff", "resume or attach update",
                       "worker-event notification", "round after any compaction"):
            self.assertIn(needle, text)
        self.assertNotIn("send`/`steer`", text)

    def test_reference_busy_steer_is_no_skill_reentry(self) -> None:
        text = flat(self.entry_ref)
        self.assertIn("Busy `steer`", text)
        self.assertIn("forwards its guide text into the already-running turn "
                      "verbatim", text)
        self.assertIn("no new `Skill` tool_call is produced, needed, or "
                      "promised", text)
        self.assertIn("a `Skill` tool_call from a busy `steer` guide", flat(self.evidence))

    def test_reference_interrupt_steer_is_not_a_host_entry(self) -> None:
        text = flat(self.entry_ref)
        self.assertIn("Composite `steer --steer-mode interrupt`", text)
        self.assertIn("its resend *is* a turn-opening prompt", text)
        self.assertIn("cancels the running turn", text)
        self.assertIn("**not** a Host recovery entry", text)
        self.assertIn("verbatim", text)
        self.assertIn("never infers Host identity from prompt content", text)
        self.assertIn("the caller supplies `/kaola-project-runner`", text)
        self.assertIn("Composite interrupt steer", flat(self.evidence))
        self.assertIn("contract-tested", flat(self.evidence))
        self.assertNotIn("host_skill_entry_prepended", text)
        self.assertNotIn("entry Host", text)

    def test_reference_discovery_roots_cover_agents_skills(self) -> None:
        text = flat(self.entry_ref)
        for needle in ("`<repo>/.zcode/skills/`", "`<repo>/.agents/skills/`",
                       "`~/.zcode/skills/`", "`~/.agents/skills/`"):
            self.assertIn(needle, text)
        # the verified root set is stated as defaults, not implied
        # exhaustive: ancestors are scanned too, configured plugin roots add
        # more, and plugin cache roots are named separate
        self.assertIn("default", text)
        self.assertIn("ancestor", text)
        self.assertIn("plugin cache", text)
        self.assertIn("createSkillsService", flat(self.evidence))

    def test_reference_names_configured_roots(self) -> None:
        text = flat(self.entry_ref)
        self.assertIn("`skills.roots` in `~/.zcode/cli/config.json`", text)
        self.assertIn("extraRoots", flat(self.evidence))
        self.assertIn("`plugins.dirs`", text)
        self.assertIn("`<plugin>:<skill>`", text)
        self.assertIn("kpr-extra:kaola-project-runner", flat(self.evidence))
        self.assertIn("outside every discovered root", text)
        self.assertIn("default or configured", text)

    def test_reference_denies_the_old_dependencies(self) -> None:
        text = flat(self.entry_ref)
        self.assertIn("No `AGENTS.md` block, no role-scoping judgement, "
                      "no compaction detection, and no manual `read` of a "
                      "`SKILL.md` file is involved anywhere", text)
        self.assertIn("ordinary Agents in the same repo carry no Host "
                      "instruction at all", flat(self.evidence))
        self.assertIn("no hook, plugin, command registry, scheduler, "
                      "polling loop, role classifier, session marker, "
                      "cursor ledger, or state machine", text)

    def test_reference_keeps_honest_runtime_facts_and_bounds(self) -> None:
        # Issue #157 (PR-M2): the loaded reference points at the evidence and
        # carries no dated version claim; the record keeps the honest bounds.
        self.assertIn("`docs/host-entry-evidence.md`", flat(self.entry_ref))
        self.assertNotIn("3.12.3", self.entry_ref)
        self.assertIn("do not fall back to reading `SKILL.md` by hand", flat(self.entry_ref))
        text = flat(self.evidence)
        for needle in ("no compaction hook", "`startup`/`resume`",
                       "no compaction through ACP", "context_usage` stays null",
                       "trigger:\"auto\"", "contextWindow",
                       "mock provider"):
            self.assertIn(needle, text)
        not_verified = text.split("Not verified:", 1)[1]
        self.assertIn("auto-compaction", not_verified)
        self.assertIn("1M-window", not_verified)
        self.assertIn("compact-specific ACP event", not_verified)

    def test_startup_teaches_the_same_entry(self) -> None:
        text = flat(self.startup)
        self.assertIn("opens with `/kaola-project-runner` as its first line", text)
        self.assertIn("first handoff, a resume or attach update, a "
                      "worker-event notification, and the round after any "
                      "compaction", text)
        self.assertIn("busy `steer` guide is not a new prompt", text)
        self.assertIn("keeps the already-loaded context", text)
        self.assertIn("no new Skill invocation", text)
        self.assertIn("steer --steer-mode interrupt", text)
        self.assertIn("not a Host recovery entry", text)
        self.assertIn("never `read` a `SKILL.md` path by hand", text)
        self.assertIn("zcode-native-skill-entry.md](zcode-native-skill-entry.md)", text)
        self.assertNotIn("AGENTS.md` instruction planted", text)
        self.assertNotIn("automatic same-turn", text)

    def test_main_skill_points_at_the_entry_reference(self) -> None:
        self.assertIn("references/zcode-native-skill-entry.md", self.main)
        self.assertIn("native `/kaola-project-runner` Skill invocation", self.main)

    def test_dispatch_names_the_entry_line(self) -> None:
        self.assertIn("first line `/kaola-project-runner`", self.dispatch)

    def test_skeleton_body_excludes_the_entry_and_skill_text(self) -> None:
        text = flat(self.skeleton)
        self.assertIn("载体自带首行 Skill 入口", text)
        self.assertIn("不重复入口行，也不复制 Skill 正文", text)
        # the body itself must not pre-bake the entry line
        self.assertNotIn("\n/kaola-project-runner\n", "\n" + self.skeleton)

    def test_delegator_handoff_uses_the_same_entry(self) -> None:
        # Issue #187: the handoff opens with the selected platform's entry;
        # the ZCode row of host-platforms.md is still /kaola-project-runner.
        self.assertIn("```text\n<host_skill_entry>\nYou are the <runtime_name> Host", self.handoff)
        text = flat(self.handoff)
        self.assertIn("turn-opening Host prompt", text)
        self.assertIn("opens with that platform's `host_skill_entry` as its own first line", text)
        self.assertIn("(zcode: `/kaola-project-runner`;", text)
        self.assertIn("idempotent across re-invocation and after compaction", text)
        # Issue #157 (KD-A3): install roots are Project Runner's discovery
        # precondition; the handoff points there instead of restating them.
        self.assertIn("Install per Project Runner's discovery precondition", text)
        self.assertIn("No `AGENTS.md` block or manual `SKILL.md` read is the "
                      "carrier", text)
        self.assertIn("E1 `Skill` tool_call or E2 quote ([host-platforms.md](host-platforms.md) "
                      "§Startup proof)", text)
        self.assertIn("startup_proof=quote one Skill-body-only sentence; no tool read", self.handoff)
        self.assertNotIn("Load <skills>", self.handoff)

    def test_delegator_handoff_marks_busy_steer_as_no_reentry(self) -> None:
        text = flat(self.handoff)
        self.assertIn("`steer` injects the running turn verbatim", text)
        self.assertIn("no new `Skill` invocation", text)
        self.assertIn("steer --steer-mode interrupt", text)
        self.assertIn("resends verbatim on a new turn", text)
        self.assertIn("not a Host entry", text)
        self.assertNotIn("entry Host", text)


class HolderEnvelope(unittest.TestCase):
    """The worker-event notification carries the entry as its first line."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.src = HOLDER.read_text(encoding="utf-8")

    def test_host_skill_entry_constant(self) -> None:
        self.assertIn('HOST_SKILL_ENTRY = "/kaola-project-runner"', self.src)

    def test_entry_is_the_first_payload_line(self) -> None:
        # Issue #119: the payload opens with the holder's own entry line,
        # which is HOST_SKILL_ENTRY for ZCode.
        m = re.search(r"lines = \[\s*\n\s*self\.host_entry,", self.src)
        self.assertIsNotNone(m, "the payload list must start with the host entry")
        self.assertLess(m.start(), self.src.index("kaola-host-notify/1"))

    def test_no_second_mechanism(self) -> None:
        for banned in ("KPR-ZCODE-RECOVERY", "KPR-SKILL-RELOAD",
                       "zcode-compact-recovery", "UserPromptSubmit"):
            self.assertNotIn(banned, self.src)

    def test_interrupt_resend_is_verbatim_with_no_host_marker(self) -> None:
        """The composite interrupt resend carries the Agent's text verbatim
        on every session. The holder has no Host marker, no role classifier,
        no persistent flag: nothing infers Host identity from literal prompt
        content, and a stop/resume cannot lose or restore a marker that does
        not exist. The only use of HOST_SKILL_ENTRY is the worker-event
        notification envelope's own first line."""
        self.assertNotIn("host_entry_session", self.src)
        self.assertNotIn("host_skill_entry_prepended", self.src)
        self.assertNotIn("entry Host", self.src)
        # the resend goes through op_prompt with the caller's text unchanged
        m = re.search(r'self\.op_prompt\(\{"text": text, "wait": False\}\)',
                      self.src)
        self.assertIsNotNone(m, "interrupt resend must send text verbatim")
        # HOST_SKILL_ENTRY is used exactly twice: its definition and the
        # ZCode fallback of the holder's own entry (Issue #119). That entry is
        # read only by the constructor, the notification payload's first line,
        # the carrier-op capability guard, and the record - never as
        # prompt-content inspection or a resend prepend.
        uses = [ln for ln in self.src.splitlines()
                if "HOST_SKILL_ENTRY" in ln]
        self.assertEqual(len(uses), 2, uses)
        self.assertIn('HOST_SKILL_ENTRY = "/kaola-project-runner"', uses[0])
        self.assertIn('entry = HOST_SKILL_ENTRY if args.platform == "zcode"', uses[1])
        entry_uses = [ln.strip() for ln in self.src.splitlines()
                      if "self.host_entry" in ln]
        self.assertEqual(entry_uses, [
            "self.host_entry: str = entry",
            '"host_skill_entry": self.host_entry,',
            "self.host_entry,",
            "if not self.host_entry:",
        ], entry_uses)

    def test_holder_documents_interrupt_is_no_recovery_entry(self) -> None:
        text = flat(self.src)
        self.assertIn("NOT a Host recovery entry", text)
        self.assertIn("never infers a Host", text)
        self.assertIn("never adds the native Skill entry line", text)


class GeneratedSurface(unittest.TestCase):
    """The generated Skills render the same contract (renderer stays in sync)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.main = (ORCH / "SKILL.md").read_text(encoding="utf-8")
        cls.entry_ref = (ORCH / "references" / "zcode-native-skill-entry.md")
        cls.startup = (ORCH / "references" / "host-startup.md").read_text(encoding="utf-8")
        cls.dispatch = (ORCH / "references" / "zcode-host-dispatch.md").read_text(
            encoding="utf-8")
        cls.skeleton = (ORCH / "references" / "heartbeat-skeleton.md").read_text(
            encoding="utf-8")
        cls.handoff = (DELEG / "references" / "handoff.md").read_text(encoding="utf-8")

    def test_generated_files_exist_and_link(self) -> None:
        self.assertTrue(self.entry_ref.is_file())
        self.assertIn("references/zcode-native-skill-entry.md", self.main)
        self.assertFalse((ORCH / "references" / "zcode-compact-recovery.md").exists())

    def test_generated_handoff_block(self) -> None:
        self.assertIn("```text\n<host_skill_entry>\nYou are the <runtime_name> Host", self.handoff)
        platforms = (DELEG / "references" / "host-platforms.md").read_text(encoding="utf-8")
        self.assertIn("| zcode (`ZCode`) | `zcode-kaola-project-runner` | `" + ENTRY + "` |", platforms)
        self.assertNotIn("Load <skills>", self.handoff)
        self.assertNotIn("{{", self.handoff)

    def test_generated_surface_carries_steer_and_root_facts(self) -> None:
        text = flat(self.handoff)
        self.assertIn("Install per Project Runner's discovery precondition", text)
        self.assertIn("`steer` injects the running turn verbatim", text)
        self.assertIn("steer --steer-mode interrupt", text)
        self.assertIn("busy `steer` guide is not a new prompt", flat(self.startup))
        self.assertIn("steer --steer-mode interrupt", flat(self.startup))

    def test_generated_skeleton_body_has_no_entry_line(self) -> None:
        self.assertIn("不重复入口行，也不复制 Skill 正文", flat(self.skeleton))


class Doc(unittest.TestCase):
    """docs/zcode-host.md records the mechanism and its honest limits."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = flat(DOC.read_text(encoding="utf-8"))

    def test_doc_states_the_entry(self) -> None:
        self.assertIn("opens with `/kaola-project-runner` on its own first line",
                      self.text)
        self.assertIn("native `Skill` tool_call", self.text)

    def test_doc_names_every_entry_point(self) -> None:
        for needle in ("first handoff, a resume or attach update",
                       "worker-event notification", "round after any compaction"):
            self.assertIn(needle, self.text)

    def test_doc_marks_busy_steer_as_no_reentry(self) -> None:
        self.assertIn("busy `steer` guide", self.text)
        self.assertIn("forwards it into the already-running turn verbatim", self.text)
        self.assertIn("no new `Skill` tool_call", self.text)
        self.assertIn("no re-invocation is claimed", self.text)

    def test_doc_interrupt_steer_is_not_a_host_entry(self) -> None:
        self.assertIn("steer --steer-mode interrupt", self.text)
        self.assertIn("not a Host recovery entry", self.text)
        self.assertIn("verbatim on every session", self.text)
        self.assertIn("caller supplies `/kaola-project-runner`", self.text)
        self.assertNotIn("host_skill_entry_prepended", self.text)
        self.assertNotIn("entry Host", self.text)

    def test_doc_discovery_roots_cover_agents_skills(self) -> None:
        for needle in ("`<repo>/.zcode/skills/`", "`<repo>/.agents/skills/`",
                       "`~/.zcode/skills/`", "`~/.agents/skills/`"):
            self.assertIn(needle, self.text)
        self.assertIn("ancestor", self.text)
        self.assertIn("plugin cache", self.text)
        self.assertIn("plugins.dirs", self.text)
        self.assertIn("skills.roots", self.text)
        self.assertIn("extraRoots", self.text)
        self.assertIn("`~/.zcode/cli/config.json`", self.text)
        self.assertIn("kpr-extra:kaola-project-runner", self.text)
        self.assertIn("default roots", self.text)
        self.assertIn("outside every discovered root", self.text)

    def test_doc_bounds_the_evidence(self) -> None:
        self.assertIn("isolated mock provider", self.text)
        self.assertIn("1M-window", self.text)
        self.assertIn("no `Skill` tool_call, the install is wrong", self.text)
        self.assertIn("no project `AGENTS.md` block is planted", self.text)
        self.assertIn("a `Skill` tool_call from a busy `steer` guide", self.text)
        self.assertNotIn("KPR-SKILL-RELOAD-V1", self.text)
        self.assertNotIn("trigger-agnostic carrier", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
