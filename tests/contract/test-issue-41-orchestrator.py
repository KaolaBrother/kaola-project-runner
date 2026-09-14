#!/usr/bin/env python3
"""Issue #41 acceptance: generated control-plane Skill kaola-project-runner.

Pins generation, renderer inventory, installer identity, golden freeze, worker
transport preservation, and four scenario meanings from the issue. Inspects
policy obligations (correct vs incorrect next action), not isolated keywords.
Does not simulate a live Agent.
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
    "Give an idle worker suitable work before considering stop",
    "Mission-frontier done triggers review, not automatic finalize",
    "PROJECT_RUNNER_HEARTBEAT",
    "30 minutes unless specified",
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

    def test_idle_worker_gets_suitable_work_before_stop(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"give an idle worker suitable work before considering stop",
                    r"idle worker.{0,100}suitable work.{0,80}before.{0,40}stop",
                    r"stop an idle exact session only when no suitable authorized work",
                    r"suitable authorized work.{0,80}before.{0,40}stop",
                ),
            ),
            "orchestrator must dispatch suitable authorized work to an idle worker before stop",
        )
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


class Issue46ConsumerIsolation(unittest.TestCase):
    def test_consumer_project_facts_stay_out_of_this_skill(self) -> None:
        text = require_orchestrator_markdown(PROJECT)
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"installed Skill payload are read-only",
                    r"store project-specific authorization, heartbeat, and run facts in the consuming project",
                    r"consuming project's run records, not in this Skill",
                ),
            ),
            "orchestrator must keep consumer-project authorization/heartbeat/run facts out of this Skill",
        )
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"unless a human explicitly assigned Project Runner development",
                    r"only when a human explicitly assigned Project Runner development",
                ),
            ),
            "edits to this checkout or installed payload require an explicit Project Runner assignment",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"write (?:project-specific )?authorization into (?:this|the installed) Skill",
                r"edit the installed Skill payload for consumer-project work",
                r"keep project-specific authorization in this Skill",
            ),
        )
        self.assertIsNone(wrong, f"consumer-project policy authorizes Skill mutation: {wrong!r}")

    def test_installer_default_is_copy(self) -> None:
        installer = INSTALLER.read_text(encoding="utf-8")
        self.assertRegex(
            installer,
            r"(?m)^method=copy\s*$",
            "install-local.sh must default to copy when --method is omitted",
        )
        self.assertNotRegex(installer, r"(?m)^method=link\s*$")
        self.assertRegex(
            installer,
            r"--method copy \(default\)",
            "usage must describe copy as the omitted --method default",
        )


if __name__ == "__main__":
    unittest.main()
