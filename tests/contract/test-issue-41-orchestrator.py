#!/usr/bin/env python3
"""Issue #41/#44 acceptance: generated control-plane Skill kaola-project-runner.

Pins generation, renderer inventory, installer identity, golden freeze, worker
transport preservation, Issue #41 scenario meanings, and Issue #44
ACP/idle-stop-on-complete meaning. Inspects policy obligations (correct vs
incorrect next action), not isolated keywords. Does not simulate a live Agent.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RENDERER = PROJECT / "scripts" / "render-skills.py"
INSTALLER = PROJECT / "scripts" / "install-local.sh"
ORCHESTRATOR_ID = "kaola-project-runner"
WORKER_IDS = (
    "claude-code",
    "codex",
    "cursor-cli",
    "devin",
    "grok",
    "kimi-cli",
    "opencode",
)
GOLDEN_SHA256 = {
    "SKILL.md": "ae74d354ef1059a60edbde8cb4a99dad09d2d25cc47e0fc637e2c9164cc70dbe",
    "agents/openai.yaml": "66699c5188eb10c53ab166572d530bbe77132c64d5b666c7258f68188bc64ddd",
    "references/closing.md": "2fda2a5726fa39abbbeb87ce7e80815e2d2870f001d7198e949e26f46a2b60c1",
    "references/codex-supervision.md": "b9c3ec5d4aa7081faccf7773d84b08b10bad828cc8e15f4221de9435be7cb2d4",
    "references/grok-tui.md": "818f9c7496d7d9a132112ceeb4d29c03d10d0c7a7765945026353d8e4033a6f8",
    "references/human-decisions.md": "f7abfdda3d3590fcefd10316cf3bc51a6ffcf79834ae7b23cf7c25f1ba621a2c",
    "references/kaola-lifecycle.md": "2c545d92737fee3bf3b3f1d147ac1e425999f698d0aa3e69a4afe210106dd9ea",
    "references/pr-claim-handoff.md": "d7b452943c5775aa2fc79db402ded3aab9a0cc332230b59f910ce334415c2377",
    "references/project-run.md": "742ec446152abd484fb4c7368da27183878d0f2075c63cec10a1327a8923187f",
    "references/scheduling.md": "6ea889913d7e8109767b61695b9d0030e393941861023a2a9955f093e2558e9e",
    "references/status-monitoring.md": "a113eee36c698c8c85d7e2e9a303837a8cc8dfd9c27a6e7e944789758776db20",
    "references/task-modes.md": "c9e8333d82a44edbdf8eb1d2bbb2f3f4f317b9ed34a02aea69fa2240aff3ca23",
}

COPY_IGNORE = shutil.ignore_patterns(".git", ".kw", "__pycache__", "node_modules")

# Worker transport contract that must survive Issue #41 (optional pointer to the
# main Skill is allowed elsewhere; these obligations must not be rewritten).
WORKER_STOP_RESUME = (
    "Before stopping, the Agent may keep whatever resume facts are already available",
    "Later work resumes through the Agent's choice: `start --resume",
    "The Runner never auto-falls back, resends an old prompt, or restarts on its own",
)
WORKER_RECEIPT_NOT_COMPLETION = (
    "A finished reply is not a finished task",
    "An `end_turn` event, an idle terminal, or a successful `send` receipt never establishes completion",
)
WORKER_NO_PROJECT_POLICY = (
    "At every heartbeat, match authorized idle workers",
    "Mission-frontier done triggers review, not automatic finalize",
    "PROJECT_RUNNER_HEARTBEAT",
    "30 minutes unless specified",
)
# Issue #44: orchestrator completion policy that must not leak into worker
# templates or generated worker Skills. Markers are absent from current
# workers (ACP/`stop` as transport is allowed) and would appear if copied
# into templates/SKILL.md.tmpl. Scan only worker surfaces — not
# templates/orchestrator/ — so a later orchestrator edit can go green.
WORKER_NO_IDLE_STOP_ON_COMPLETE_POLICY = (
    "Idle is not keep-alive",
    "ACP idle left running is not completion",
    "stop remaining idle owned sessions",
    "including ACP holders",
    "Then cancel heartbeat",
    "in-hand authorized",
    "stop here and continue later",
    "scoped pause",
    "Time-up is not drop-everything",
    "do not accept or dispatch new tasks",
    "do not claim or start new issues",
    "leave no leftover branch tails",
    "do not park unfinished branches",
)
# Issue #47: delivery/merge preference must stay on the orchestrator.
WORKER_NO_OPEN_PR_PRIORITY_POLICY = (
    "Prefer the selected, authorized Workflow sync/merge",
    "not opened merely for handoff",
    "advance actionable ones first",
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def markdown_tree(root: Path) -> str:
    if not root.is_dir():
        return ""
    parts: list[str] = []
    for path in sorted(root.rglob("*.md")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


WORKER_GENERATED_SKILL_IDS = (
    "grok-kaola-project-runner",
    "claude-code-kaola-project-runner",
    "opencode-kaola-project-runner",
    "kimi-cli-kaola-project-runner",
    "cursor-cli-kaola-project-runner",
    "devin-kaola-project-runner",
    "codex-kaola-project-runner",
)


def worker_idle_stop_policy_surfaces() -> list[tuple[str, str]]:
    """Worker template + generated worker Skills only (not orchestrator)."""
    surfaces: list[tuple[str, str]] = []
    templates = PROJECT / "templates"
    for path in sorted(templates.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(templates)
        if "grok-golden" in relative.parts or "orchestrator" in relative.parts:
            continue
        if path.suffix.lower() in {".tmpl", ".md"}:
            surfaces.append((relative.as_posix(), path.read_text(encoding="utf-8")))
    for skill_id in WORKER_GENERATED_SKILL_IDS:
        body = (PROJECT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")
        surfaces.append((f"skills/{skill_id}/SKILL.md", body))
    return surfaces


def worker_template_text() -> str:
    templates = PROJECT / "templates"
    parts: list[str] = []
    for path in sorted(templates.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(templates)
        if "grok-golden" in relative.parts:
            continue
        if path.suffix.lower() in {".tmpl", ".md"}:
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def copy_repo(temporary: str) -> Path:
    destination = Path(temporary) / "repo"
    shutil.copytree(PROJECT, destination, ignore=COPY_IGNORE)
    # No .git in the copy: a pinned Grok Bot bridge cannot be verified there, so the copy starts at the content stage.
    (destination / "templates" / "grok-bot" / "accepted-revision.json").write_text('{"stage": "content"}\n', encoding="utf-8")
    return destination


def run_renderer(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "render-skills.py"), *args],
        cwd=root,
        text=True,
        capture_output=True,
    )


def orchestrator_package(root: Path | None = None) -> Path:
    return (root or PROJECT) / "skills" / ORCHESTRATOR_ID


def require_orchestrator_markdown(root: Path | None = None) -> str:
    package = orchestrator_package(root)
    skill = package / "SKILL.md"
    if not skill.is_file():
        raise AssertionError(
            f"missing generated orchestrator Skill at {skill}; "
            "render-skills.py --write must emit skills/kaola-project-runner/"
        )
    return markdown_tree(package)


def clause_present(text: str, patterns: tuple[str, ...]) -> re.Match[str] | None:
    lowered = normalize(text)
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return match
    return None


def authorizes_wrong_move(text: str, patterns: tuple[str, ...]) -> str | None:
    """Return a matching wrong-policy clause that is not a prohibition."""
    for raw in re.split(r"(?<=[.!?])\s+|\n+", text):
        sentence = normalize(raw)
        if not sentence:
            continue
        if re.match(
            r"(do not|don't|never|must not|cannot|without|rather than|instead of|not automatic)\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            continue
        if re.search(
            r"\b(do not|don't|never|must not|cannot|not automatic)\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            continue
        for pattern in patterns:
            if re.search(pattern, sentence, flags=re.IGNORECASE):
                return sentence
    return None


class Issue41RendererContract(unittest.TestCase):
    def test_orchestrator_is_not_an_eighth_platform(self) -> None:
        platforms = sorted(path.stem for path in (PROJECT / "platforms").glob("*.yaml"))
        self.assertEqual(platforms, list(WORKER_IDS))
        self.assertFalse((PROJECT / "platforms" / f"{ORCHESTRATOR_ID}.yaml").exists())
        self.assertFalse((PROJECT / "scripts" / "adapters" / f"{ORCHESTRATOR_ID}.sh").exists())
        renderer = RENDERER.read_text(encoding="utf-8")
        self.assertNotIn(f"{ORCHESTRATOR_ID}.yaml", renderer)
        installer = INSTALLER.read_text(encoding="utf-8")
        skill_name_for = installer.split("skill_name_for()", 1)[1].split("runtime_skills_dir()", 1)[0]
        self.assertIsNone(
            re.search(r"(?m)^\s*kaola-project-runner\)", skill_name_for),
            "skill_name_for must not treat kaola-project-runner as a --platform id",
        )
        result = subprocess.run(
            ["bash", str(INSTALLER), "--platform", ORCHESTRATOR_ID, "--skills-dir", "/tmp/kaola-issue-41-unused"],
            cwd=PROJECT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        combined = f"{result.stderr}\n{result.stdout}"
        self.assertIn("unknown platform", combined)

    def test_write_and_check_include_orchestrator_without_platform_manifest(self) -> None:
        self.assertFalse((PROJECT / "platforms" / f"{ORCHESTRATOR_ID}.yaml").exists())
        with tempfile.TemporaryDirectory(prefix="kaola-issue-41-render-") as temporary:
            copy = copy_repo(temporary)
            written = run_renderer(copy, "--write")
            self.assertEqual(
                written.returncode,
                0,
                written.stderr or written.stdout,
            )
            package = orchestrator_package(copy)
            skill = package / "SKILL.md"
            marker = package / ".generated-by-kaola-project-runner"
            self.assertTrue(skill.is_file(), " --write must emit skills/kaola-project-runner/SKILL.md")
            self.assertTrue(marker.is_file(), " --write must emit the generated marker")
            self.assertEqual(marker.read_text(encoding="utf-8"), f"{ORCHESTRATOR_ID}\n")
            front = skill.read_text(encoding="utf-8")
            self.assertRegex(front, r"(?m)^name:\s*kaola-project-runner\s*$")
            openai = package / "agents" / "openai.yaml"
            named = (
                re.search(r"(?m)^# Project Runner\s*$", front) is not None
                or re.search(r'(?m)^display_name:\s*"?Project Runner"?\s*$', front) is not None
                or (
                    openai.is_file()
                    and re.search(
                        r'(?m)^\s*display_name:\s*"?Project Runner"?\s*$',
                        openai.read_text(encoding="utf-8"),
                    )
                    is not None
                )
            )
            self.assertTrue(named, "generated Skill must display as Project Runner")
            checked = run_renderer(copy, "--check")
            self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)
            shutil.rmtree(package)
            missing = run_renderer(copy, "--check")
            self.assertNotEqual(
                missing.returncode,
                0,
                "--check must expect kaola-project-runner in generated names; "
                "absence must fail rather than treat the orchestrator as optional",
            )
            detail = f"{missing.stderr}\n{missing.stdout}"
            self.assertIn(ORCHESTRATOR_ID, detail)

    def test_orchestrator_description_json_quotes_colon_space_for_yaml(self) -> None:
        """Unquoted 'Skills: recover' is invalid YAML; renderer must JSON-quote it."""
        spec = importlib.util.spec_from_file_location("render_skills", RENDERER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        quoted = module.orchestrator_values([])["DESCRIPTION"]
        self.assertTrue(quoted.startswith('"') and quoted.endswith('"'), quoted)
        description = json.loads(quoted)
        self.assertIn("Skills: recover", description)
        self.assertIn(": ", description)

        with tempfile.TemporaryDirectory(prefix="kaola-issue-41-yaml-desc-") as temporary:
            copy = copy_repo(temporary)
            written = run_renderer(copy, "--write")
            self.assertEqual(written.returncode, 0, written.stderr or written.stdout)
            text = (orchestrator_package(copy) / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        line = next(raw for raw in frontmatter.splitlines() if raw.startswith("description:"))
        scalar = line.split(":", 1)[1].lstrip()
        self.assertEqual(json.loads(scalar), description)
        try:
            import yaml
        except ImportError:
            yaml = None
        if yaml is not None:
            loaded = yaml.safe_load(frontmatter)
            self.assertEqual(loaded["name"], ORCHESTRATOR_ID)
            self.assertEqual(loaded["description"], description)

    def test_supported_worker_summary_is_derived_from_manifests(self) -> None:
        unique_skill = "grok-probe-worker-zx41"
        unique_display = "Probe Worker ZX41 Token"
        with tempfile.TemporaryDirectory(prefix="kaola-issue-41-summary-") as temporary:
            copy = copy_repo(temporary)
            grok = copy / "platforms" / "grok.yaml"
            original = grok.read_text(encoding="utf-8")
            grok.write_text(
                original.replace(
                    'skill_name: "grok-kaola-project-runner"',
                    f'skill_name: "{unique_skill}"',
                ).replace(
                    'display_name: "Grok Kaola Project Runner"',
                    f'display_name: "{unique_display}"',
                ),
                encoding="utf-8",
            )
            stale = copy / "skills" / "grok-kaola-project-runner"
            if stale.exists():
                shutil.rmtree(stale)
            written = run_renderer(copy, "--write")
            self.assertEqual(written.returncode, 0, written.stderr or written.stdout)
            text = require_orchestrator_markdown(copy)
            self.assertIn(
                unique_skill,
                text,
                "supported-worker summary must come from platform manifests, not a hardcoded worker list",
            )
            self.assertIn(
                unique_display,
                text,
                "supported-worker summary must include manifest display names",
            )
            for platform_id in WORKER_IDS:
                self.assertRegex(
                    normalize(text),
                    rf"\b{re.escape(platform_id)}\b",
                    f"supported-worker summary omitted platform id {platform_id}",
                )


class Issue41GoldenAndWorkerPreservation(unittest.TestCase):
    def test_grok_golden_bytes_stay_identical(self) -> None:
        golden = PROJECT / "templates" / "grok-golden"
        actual = {path.relative_to(golden).as_posix() for path in golden.rglob("*") if path.is_file()}
        self.assertEqual(actual, set(GOLDEN_SHA256))
        for relative, expected in GOLDEN_SHA256.items():
            path = golden / relative
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected, relative)

    def test_worker_templates_keep_stop_resume_and_receipt_meaning(self) -> None:
        template = normalize((PROJECT / "templates" / "SKILL.md.tmpl").read_text(encoding="utf-8"))
        for marker in WORKER_STOP_RESUME + WORKER_RECEIPT_NOT_COMPLETION:
            self.assertIn(normalize(marker), template, marker)
        active = normalize(worker_template_text())
        for forbidden in WORKER_NO_PROJECT_POLICY:
            self.assertNotIn(
                normalize(forbidden),
                active,
                f"worker templates gained project-level orchestrator policy: {forbidden!r}",
            )
        for skill_id in (
            "grok-kaola-project-runner",
            "claude-code-kaola-project-runner",
            "opencode-kaola-project-runner",
            "kimi-cli-kaola-project-runner",
            "cursor-cli-kaola-project-runner",
            "devin-kaola-project-runner",
            "codex-kaola-project-runner",
        ):
            body = normalize((PROJECT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8"))
            for marker in WORKER_STOP_RESUME + WORKER_RECEIPT_NOT_COMPLETION:
                self.assertIn(normalize(marker), body, f"{skill_id}: {marker}")
            for forbidden in WORKER_NO_PROJECT_POLICY:
                self.assertNotIn(normalize(forbidden), body, f"{skill_id}: {forbidden}")

    def test_worker_skills_omit_idle_stop_on_complete_policy(self) -> None:
        """Issue #44: workers stay transport-only; no completion/idle-stop policy."""
        for label, raw in worker_idle_stop_policy_surfaces():
            body = normalize(raw)
            for forbidden in WORKER_NO_IDLE_STOP_ON_COMPLETE_POLICY:
                self.assertNotIn(
                    normalize(forbidden),
                    body,
                    f"{label} gained orchestrator idle-stop-on-complete policy: {forbidden!r}",
                )


class Issue41ScenarioMeaning(unittest.TestCase):
    def orchestrator_text(self) -> str:
        text = require_orchestrator_markdown(PROJECT)
        self.assertTrue(text.strip(), "generated orchestrator markdown is empty")
        return text

    def test_recovery_does_not_duplicate_a_start(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"must not restart intake, workers, claims or assignments already established",
                    r"recover existing explicit authorization and live work before asking",
                    r"skill update or resumed conversation must not restart",
                    r"recover(?:y| and observe).{0,120}(?:do not|don't|without).{0,80}(?:duplicate|replay|restart).{0,80}start",
                    r"avoid(?:ing)? duplicate (?:a )?start",
                    r"existing (?:owned )?sessions?.{0,80}(?:do not|don't|without).{0,40}start",
                ),
            ),
            "orchestrator must require recovering live authorization/sessions instead of starting again",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"on (?:every|each) invocation,? start workers",
                r"treat (?:a )?resumed conversation as (?:a )?blank intake",
                r"always start(?: a)? new worker",
                r"restart intake even if.{0,40}already established",
            ),
        )
        self.assertIsNone(wrong, f"recovery policy authorizes a duplicate start: {wrong!r}")

    def test_each_heartbeat_matches_idle_workers_to_safe_parallel_work(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"at every heartbeat.{0,80}authorized idle workers.{0,80}safe parallel work",
                    r"dispatch every suitable match.{0,80}leave capacity idle.{0,80}invent work or expand authorization",
                ),
            ),
            "every heartbeat must match authorized idle workers to safe executable parallel work without inventing work or authorization",
        )
        heartbeat = (orchestrator_package(PROJECT) / "references" / "heartbeat-skeleton.md").read_text(encoding="utf-8")
        self.assertIn("每拍核对已授权的空闲线程和可安全并行的工作，派出所有合适匹配", heartbeat)
        wrong = authorizes_wrong_move(
            text,
            (
                r"stop idle workers immediately",
                r"an idle worker should be stopped before looking for (?:suitable )?work",
                r"prefer stop(?:ping)? idle workers instead of (?:re-?)?dispatch",
            ),
        )
        self.assertIsNone(wrong, f"idle-worker policy authorizes stop-first: {wrong!r}")

    def test_completion_prose_without_evidence_causes_verification_not_finalize(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"mission-frontier done triggers review, not automatic finalize",
                    r"do not lower assertions or substitute worker prose, idle, green ci or a successful script exit for acceptance",
                    r"completion prose without sufficient evidence.{0,80}verif",
                    r"inspect the actual diff, verification evidence and project acceptance",
                    r"dispatch missing proof or repairs; do not.{0,40}finalize",
                ),
            ),
            "orchestrator must treat incomplete evidence as verification/repair, not finalize",
        )
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"not automatic finalize",
                    r"rather than finalize",
                    r"do not finalize",
                    r"causes verification rather than finalize",
                    r"review, not automatic finalize",
                ),
            ),
            "orchestrator must refuse finalize on completion prose alone",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"when the worker (?:says|reports) (?:done|complete), finalize",
                r"green ci (?:is|means|counts as) acceptance",
                r"worker prose.{0,40}is (?:enough|sufficient)(?: evidence)? to finalize",
                r"idle.{0,20}means.{0,20}finalize",
            ),
        )
        self.assertIsNone(wrong, f"acceptance policy authorizes prose-as-finalize: {wrong!r}")

    def test_stopping_a_session_does_not_lose_unfinished_close_out_duties(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"give any remaining delivery/sync/cleanup a named owner",
                    r"remaining (?:delivery|sync|cleanup|close-out).{0,80}named owner",
                    r"session stop.{0,80}not.{0,40}(?:issue closure|interchangeable completion)",
                    r"stopping a session does not lose.{0,40}close-out",
                    r"preserve.{0,60}recovery information.{0,80}named owner",
                ),
            ),
            "orchestrator must keep unfinished close-out duties after session stop",
        )
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"session stop, candidate acceptance, merge, issue closure and workspace cleanup are different facts",
                    r"not interchangeable completion labels",
                    r"session stop is not issue closure",
                    r"stop an idle exact session.{0,80}named owner",
                ),
            ),
            "session stop must stay distinct from close-out completion labels",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"stopping a session completes the issue",
                r"session stop means (?:the )?(?:issue|workspace) is (?:closed|cleaned)",
                r"drop remaining close-out duties when the session stops",
            ),
        )
        self.assertIsNone(wrong, f"stop policy drops close-out duties: {wrong!r}")


class Issue44IdleStopOnCompleteMeaning(unittest.TestCase):
    """Issue #44: completion stops leftover idle owned sessions, including ACP."""

    def orchestrator_text(self) -> str:
        text = require_orchestrator_markdown(PROJECT)
        self.assertTrue(text.strip(), "generated orchestrator markdown is empty")
        return text

    def test_acp_and_pty_share_the_same_owned_session_stop(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"ACP.{0,80}(?:the )?same (?:way|stop action).{0,40}(?:as )?(?:PTY|tmux)",
                    r"ACP and PTY.{0,40}(?:are )?(?:the )?same stop",
                    r"leftover ACP holder.{0,100}(?:exact owned )?`?stop`?",
                    r"idle owned ACP.{0,80}matching platform Runner Skill",
                    r"including ACP holders?.{0,80}matching platform Runner Skill",
                    r"ACP (?:idle|holder|session).{0,80}(?:exact owned session )?stop.{0,80}(?:PTY|tmux)",
                ),
            ),
            "orchestrator must require stopping an idle owned ACP session the same "
            "way as PTY/tmux: exact owned stop via the matching platform Runner Skill",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"leave (?:an )?ACP (?:holder|session) running as (?:completion|keep-alive)",
                r"ACP idle is (?:a )?(?:special |separate )?non-stoppable",
                r"treat ACP idle as (?:a )?(?:keep-alive|non-stoppable|completion)",
                r"ACP (?:holder|idle) does not (?:need|require) (?:a )?stop",
                r"keep (?:an |the )?ACP (?:holder|session) running as keep-alive",
            ),
        )
        self.assertIsNone(
            wrong,
            f"ACP idle-stop policy authorizes leaving an ACP holder running: {wrong!r}",
        )

    def test_complete_or_no_executable_work_stops_idle_then_cancels_heartbeat(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"idle is not keep-alive",
                    r"when the authorized goal is complete.{0,40}or.{0,80}no suitable authorized work.{0,80}stop remaining idle.{0,60}ACP",
                    r"stop remaining idle owned sessions.{0,80}including ACP.{0,80}(?:then|after).{0,40}cancel.{0,20}heartbeat",
                    r"(?:goal is complete|no suitable authorized work is executable).{0,160}including ACP holders?",
                    r"leftover idle owned.{0,60}(?:ACP|PTY).{0,80}then cancel.{0,20}heartbeat",
                ),
            ),
            "orchestrator must stop remaining idle owned sessions including ACP when "
            "the authorized goal is complete or no suitable authorized work is "
            "executable, then cancel heartbeat; idle is not keep-alive",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"keep idle owned sessions running as keep-alive after.{0,40}(?:authorized )?goal is complete",
                r"cancel (?:the )?heartbeat while leftover idle owned.{0,40}(?:ACP|PTY) remain",
                r"idle owned sessions?.{0,40}(?:are|is) keep-alive after.{0,40}complete",
                r"leave leftover idle owned.{0,40}(?:ACP|PTY).{0,40}running as holders?",
            ),
        )
        self.assertIsNone(
            wrong,
            f"idle-stop-on-complete policy authorizes keep-alive or heartbeat-cancel-first: {wrong!r}",
        )

    def test_later_work_starts_or_resumes_only_after_idle_stops(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"after.{0,80}(?:idle owned sessions? (?:were |have been )?stopped|those stops).{0,100}later (?:authorized )?work.{0,80}(?:start|resume|--resume|--continue)",
                    r"later (?:authorized )?work.{0,80}(?:starts?|resumes?).{0,80}only (?:then|after)",
                    r"do not keep an idle.{0,40}(?:ACP|PTY|session).{0,80}(?:holder|future work|without start)",
                    r"restart a session only when there is new authorized work",
                    r"new authorized work.{0,80}(?:--resume|--continue|fresh `start`|starts or resumes)",
                ),
            ),
            "orchestrator must start or resume later authorized work only after idle "
            "sessions were stopped; reuse --resume / --continue / fresh start",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"keep an idle session.{0,80}so later work can continue without start",
                r"leave (?:an )?idle.{0,40}(?:ACP|PTY|session).{0,60}running.{0,40}(?:for|until) (?:later|future) work",
                r"keep-alive.{0,40}(?:so|for) later work.{0,40}without start",
            ),
        )
        self.assertIsNone(
            wrong,
            f"later-work policy authorizes keeping an idle holder for future work: {wrong!r}",
        )

    def test_idle_stop_reuses_runner_stop_without_a_new_engine(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"reuse existing Runner.{0,40}`?stop`?.{0,40}`?start`?",
                    r"Skill guidance only.{0,80}reuse existing Runner",
                    r"do not.{0,40}(?:add|invent|require).{0,40}(?:a )?session state machine, quota engine, or extra dashboards",
                    r"quota engine.{0,40}extra dashboards.{0,80}(?:idle|ACP|stop)",
                    r"without.{0,20}(?:adding )?(?:a )?session state machine.{0,40}quota engine",
                ),
            ),
            "orchestrator must implement idle-stop-on-complete by reusing Runner "
            "stop/start, not a session state machine, quota engine, or extra dashboards",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"implement (?:idle-?stop|this) with a session state machine",
                r"add a quota engine.{0,40}(?:idle|session)",
                r"require extra dashboards to (?:stop|track) (?:idle )?sessions",
                r"build a session state machine for ACP",
            ),
        )
        self.assertIsNone(
            wrong,
            f"idle-stop policy authorizes a new engine instead of Runner stop: {wrong!r}",
        )

    def test_ending_a_run_defaults_to_finish_then_merge_and_clean_workspace(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"ending a project run.{0,80}defaults?",
                    r"defaults? to finish(?:ing)?.{0,80}in-hand authorized",
                    r"finish(?:ing)? every in-hand authorized.{0,80}merg",
                    r"in-hand authorized.{0,80}then.{0,40}merge.{0,60}worktrees?",
                    r"leave(?:s|ing)? (?:the |a )?workspace clean.{0,100}(?:Workflow close-out|finalize/archive/sink)",
                    r"matching.{0,40}(?:Kaola )?Workflow close-out.{0,80}(?:finalize|archive|sink|worktree)",
                ),
            ),
            "orchestrator must default ending a project run to finishing in-hand "
            "authorized work, then merging worktrees/branches and leaving a clean "
            "workspace, matching Workflow close-out — not a new subsystem",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"skip (?:the )?default (?:merge|cleanup) when the human did not pause",
                r"leave worktrees unmerged by default when ending a (?:project )?run",
                r"ending a (?:project )?run does not (?:require|need) merge",
                r"invent a new close-out (?:engine|dashboard|subsystem)",
            ),
        )
        self.assertIsNone(
            wrong,
            f"close-out default authorizes skipping merge/cleanup or a new engine: {wrong!r}",
        )

    def test_explicit_stop_here_and_continue_later_is_a_scoped_pause(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"stop here and continue later",
                    r"explicit.{0,40}(?:human )?(?:say|said|ask).{0,40}stop here.{0,80}continue later",
                    r"scoped pause.{0,80}(?:do not force|must not force|without forcing).{0,40}(?:merge|cleanup)",
                    r"do not force (?:merge|cleanup).{0,40}beyond.{0,40}(?:that |the )?(?:stated )?scope",
                    r"stop here.{0,60}continue later.{0,80}preserve.{0,40}recovery",
                ),
            ),
            "orchestrator must treat an explicit 'stop here and continue later' as a "
            "scoped pause: do not force merge/cleanup beyond that scope; preserve "
            "recovery for resume",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"force merge.{0,40}cleanup after.{0,40}(?:an )?explicit (?:pause|stop here)",
                r"merge and clean(?:up)? anyway when the human said stop here",
                r"ignore an explicit stop here and continue later",
                r"scoped pause still requires full merge and cleanup",
            ),
        )
        self.assertIsNone(
            wrong,
            f"pause-scope policy authorizes forcing close-out after an explicit pause: {wrong!r}",
        )

    def test_stop_boundary_blocks_new_tasks_without_dropping_in_hand_work(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"run until (?:5pm|done|CONDITION).{0,120}(?:do not|must not).{0,40}(?:accept|dispatch) new tasks",
                    r"stop boundary.{0,80}after that line.{0,80}(?:do not|must not).{0,40}(?:accept|dispatch) new",
                    r"after that line.{0,80}(?:do not|must not).{0,40}(?:accept|dispatch) new tasks",
                    r"(?:time|clock|condition) (?:boundary|limit).{0,80}(?:do not|must not).{0,40}(?:accept|dispatch) new tasks",
                    r"do not accept or dispatch new tasks.{0,80}(?:stop boundary|after that line|run until)",
                ),
            ),
            "orchestrator must treat a stated run-until time/condition as a line after "
            "which it must not accept or dispatch new tasks",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"after.{0,40}(?:the )?(?:stop boundary|time-up|run until).{0,40}(?:still )?(?:accept|dispatch) new tasks",
                r"time-up means drop-everything",
                r"abandon in-hand.{0,40}(?:work|tasks).{0,40}(?:when|after).{0,40}(?:time-up|stop boundary)",
                r"drop in-hand authorized work at (?:the )?stop boundary",
            ),
        )
        self.assertIsNone(
            wrong,
            f"stop-boundary policy authorizes new tasks after the line or drop-everything: {wrong!r}",
        )

    def test_stop_boundary_termination_still_does_default_close_out(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"time-up is not drop-everything",
                    r"after.{0,60}(?:any )?(?:such )?termination.{0,80}(?:still )?finish.{0,40}in-hand",
                    r"stop boundary.{0,80}(?:still )?finish.{0,40}in-hand authorized.{0,80}merg",
                    r"(?:after|at) time-up.{0,80}(?:still )?(?:default )?(?:close-out|finish in-hand|merge worktrees)",
                    r"termination.{0,40}still.{0,60}(?:finish in-hand|merge worktrees|workspace clean)",
                ),
            ),
            "orchestrator must still finish in-hand work and do default merge/cleanup "
            "after a stop-boundary termination; time-up is not drop-everything",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"time-up means skip (?:merge|cleanup)",
                r"time-up means abandon in-hand",
                r"skip merge.{0,40}cleanup.{0,40}after.{0,40}(?:a )?stop boundary",
                r"drop-everything when (?:time is up|the stop boundary hits)",
            ),
        )
        self.assertIsNone(
            wrong,
            f"stop-boundary close-out authorizes skipping merge/cleanup or abandoning in-hand work: {wrong!r}",
        )

    def test_clock_or_condition_boundary_is_not_a_skip_cleanup_pause(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"only.{0,40}(?:an )?explicit.{0,40}stop here.{0,40}continue later.{0,80}skips.{0,20}(?:that )?cleanup",
                    r"run until 5pm.{0,80}(?:is )?not.{0,40}(?:a )?(?:skip-cleanup |scoped )?pause",
                    r"(?:clock|condition|time) boundary.{0,60}(?:must not|do not|is not).{0,40}(?:be )?treated as.{0,40}(?:that |a )?(?:skip-cleanup )?pause",
                    r"only.{0,50}stop here.{0,20}continue later.{0,60}skips.{0,40}(?:merge|cleanup)",
                    r"(?:run until|stop boundary).{0,80}(?:is )?not.{0,40}stop here.{0,20}continue later",
                ),
            ),
            "orchestrator must not treat a clock/condition stop boundary as the "
            "explicit skip-cleanup pause; only 'stop here, continue later' skips cleanup",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"treat.{0,20}(?:run until 5pm|a stop boundary|time-up) as.{0,40}(?:a )?skip(?:-cleanup)? pause",
                r"run until 5pm.{0,40}(?:means|is).{0,40}skip.{0,20}cleanup",
                r"a (?:clock|condition) boundary skips (?:merge|cleanup) like stop here",
            ),
        )
        self.assertIsNone(
            wrong,
            f"stop-boundary policy treats a clock/condition line as skip-cleanup pause: {wrong!r}",
        )

    def test_stop_boundary_does_not_claim_or_start_new_issues(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"after (?:a |the )?stop boundary.{0,80}(?:do not|must not).{0,40}claim or start new issues",
                    r"do not claim or start new issues",
                    r"stop boundary.{0,80}(?:do not|must not).{0,40}(?:claim|start) new issues",
                    r"after that line.{0,80}(?:do not|must not).{0,60}claim or start new issues",
                ),
            ),
            "orchestrator must not claim or start new issues after a stop boundary",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"after (?:a )?stop boundary.{0,40}(?:still |continue to )?claim.{0,20}new issues",
                r"start new issues after.{0,40}(?:the )?(?:stop boundary|time-up)",
                r"claim new issues at time-up",
            ),
        )
        self.assertIsNone(
            wrong,
            f"stop-boundary policy authorizes claiming or starting new issues: {wrong!r}",
        )

    def test_in_hand_issues_merge_without_parking_unfinished_branches(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"finish every in-hand issue.{0,80}(?:already claimed|in flight)",
                    r"leave no leftover branch tails",
                    r"do not park unfinished branches.{0,80}normal end",
                    r"only.{0,40}(?:an )?explicit.{0,40}stop here.{0,40}continue later.{0,80}(?:may leave|unfinished branches)",
                ),
            ),
            "orchestrator must finish in-hand issues of this run, merge without leftover "
            "branch tails, and must not park unfinished branches as the normal end; only "
            "an explicit pause may leave recovery-preserving unfinished branches",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"park unfinished branches as the normal end",
                r"leave leftover branch tails by default",
                r"normal end of a project run.{0,40}park unfinished branches",
            ),
        )
        self.assertIsNone(
            wrong,
            f"close-out default authorizes parking unfinished branches: {wrong!r}",
        )


class Issue47DeliveryPathMeaning(unittest.TestCase):
    """Issue #47: Workflow merge preference and conditional open-PR priority."""

    def test_delivery_path_heartbeat_and_worker_isolation(self) -> None:
        text = require_orchestrator_markdown(PROJECT)
        heartbeat = (
            PROJECT
            / "templates"
            / "orchestrator"
            / "references"
            / "heartbeat-skeleton.txt"
        ).read_text(encoding="utf-8")
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"prefer the selected, authorized Workflow sync/merge when a PR is not required"
                    r".{0,80}a PR is not opened merely for handoff when that sink is suitable",
                ),
            ),
            "prefer selected authorized Workflow sync/merge; no PR merely for handoff",
        )
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"advance actionable ones first on contested suitable capacity"
                    r".{0,80}parallel across permitted CLIs"
                    r".{0,80}blocked PR keeps an owner and next action without a global hold",
                ),
            ),
            "actionable PR priority, permitted-CLI parallel work, blocked-PR ownership",
        )
        self.assertIsNotNone(
            clause_present(
                heartbeat,
                (
                    r"已选 Workflow 同步/合并.{0,20}不为交接单独开 PR.{0,80}"
                    r"有开放 PR 时争用容量优先推进可执行项.{0,80}已许可 CLI",
                ),
            ),
            "heartbeat recalls merge path and conditional PR priority on permitted CLIs",
        )
        for label, raw in worker_idle_stop_policy_surfaces():
            body = normalize(raw)
            for marker in WORKER_NO_OPEN_PR_PRIORITY_POLICY:
                self.assertNotIn(
                    normalize(marker),
                    body,
                    f"{label} gained orchestrator delivery-path policy: {marker!r}",
                )


if __name__ == "__main__":
    unittest.main()
