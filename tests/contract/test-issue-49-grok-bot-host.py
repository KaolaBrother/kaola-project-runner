#!/usr/bin/env python3
"""Issue #49 acceptance: Grok Bot is a first-class host, not an eighth worker.

Covers generated Cursor-plugin packaging of the orchestrator plus seven
workers, installer host-id vs ``--platform grok``, control-plane Routine
semantics, worker isolation, unofficial Sand API ban, and honest UAT
boundary. Does not claim live Grok Bot UI adoption.
"""

from __future__ import annotations

import hashlib
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
VERIFIER = PROJECT / "scripts" / "kaola-grok-bot-verify.py"
ORCHESTRATOR_ID = "kaola-project-runner"
HOST_ID = "grok-bot"
HOST_BUNDLE = PROJECT / "hosts" / HOST_ID
WORKER_IDS = (
    "claude-code",
    "codex",
    "cursor-cli",
    "devin",
    "grok",
    "kimi-cli",
    "opencode",
)
WORKER_SKILL_IDS = (
    "claude-code-kaola-project-runner",
    "codex-kaola-project-runner",
    "cursor-cli-kaola-project-runner",
    "devin-kaola-project-runner",
    "grok-kaola-project-runner",
    "kimi-cli-kaola-project-runner",
    "opencode-kaola-project-runner",
)
UNOFFICIAL_API = (
    "GrokBotService",
    "EnsureSandBox",
    "SAND_GATEWAY",
    "sand-host",
    "grokbot-sdk",
    "aiserver.v1",
    "/local-exec/",
)
COPY_IGNORE = shutil.ignore_patterns(".git", ".kw", "__pycache__", "node_modules")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def markdown_tree(root: Path) -> str:
    if not root.is_dir():
        return ""
    parts: list[str] = []
    for path in sorted(root.rglob("*.md")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def run_renderer(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "render-skills.py"), *args],
        cwd=root,
        text=True,
        capture_output=True,
    )


def copy_repo(temporary: str) -> Path:
    destination = Path(temporary) / "repo"
    shutil.copytree(PROJECT, destination, ignore=COPY_IGNORE)
    return destination


def clause_present(text: str, patterns: tuple[str, ...]) -> re.Match[str] | None:
    lowered = normalize(text)
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return match
    return None


def authorizes_wrong_move(text: str, patterns: tuple[str, ...]) -> str | None:
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


def worker_policy_surfaces() -> list[tuple[str, str]]:
    surfaces: list[tuple[str, str]] = []
    templates = PROJECT / "templates"
    for path in sorted(templates.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(templates)
        if "grok-golden" in relative.parts or "orchestrator" in relative.parts:
            continue
        if "hosts" in relative.parts:
            continue
        if path.suffix.lower() in {".tmpl", ".md"}:
            surfaces.append((relative.as_posix(), path.read_text(encoding="utf-8")))
    for skill_id in WORKER_SKILL_IDS:
        body = (PROJECT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")
        surfaces.append((f"skills/{skill_id}/SKILL.md", body))
    return surfaces


class Issue49NotAnEighthPlatform(unittest.TestCase):
    def test_no_grok_bot_platform_manifest_or_adapter(self) -> None:
        platforms = sorted(path.stem for path in (PROJECT / "platforms").glob("*.yaml"))
        self.assertEqual(platforms, list(WORKER_IDS))
        self.assertFalse((PROJECT / "platforms" / "grok-bot.yaml").exists())
        self.assertFalse((PROJECT / "scripts" / "adapters" / "grok-bot.sh").exists())
        renderer = RENDERER.read_text(encoding="utf-8")
        self.assertNotIn("platforms/grok-bot.yaml", renderer)
        installer = INSTALLER.read_text(encoding="utf-8")
        skill_name_for = installer.split("skill_name_for()", 1)[1].split(
            "runtime_skills_dir()", 1
        )[0]
        self.assertIsNone(
            re.search(r"(?m)^\s*grok-bot\)", skill_name_for),
            "skill_name_for must not treat grok-bot as a --platform id",
        )

    def test_platform_grok_bot_is_unknown(self) -> None:
        result = subprocess.run(
            [
                "bash",
                str(INSTALLER),
                "--platform",
                "grok-bot",
                "--skills-dir",
                "/tmp/kaola-issue-49-unused",
            ],
            cwd=PROJECT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        combined = f"{result.stderr}\n{result.stdout}"
        self.assertIn("unknown platform", combined)

    def test_runtime_grok_is_not_the_grok_bot_host(self) -> None:
        result = subprocess.run(
            ["bash", str(INSTALLER), "--runtime", "grok", "--platform", "codex"],
            cwd=PROJECT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        combined = f"{result.stderr}\n{result.stdout}"
        self.assertRegex(combined, r"unknown runtime:\s*grok")
        self.assertIn("--runtime grok-bot", combined)
        self.assertIn("--platform grok", combined)


class Issue49HostBundle(unittest.TestCase):
    def test_renderer_emits_and_checks_host_bundle(self) -> None:
        self.assertTrue(
            HOST_BUNDLE.is_dir(),
            "render --write must emit hosts/grok-bot/",
        )
        marker = HOST_BUNDLE / ".generated-by-kaola-project-runner"
        self.assertTrue(marker.is_file())
        self.assertEqual(marker.read_text(encoding="utf-8"), "grok-bot\n")
        plugin = HOST_BUNDLE / ".cursor-plugin" / "plugin.json"
        self.assertTrue(plugin.is_file(), "Cursor plugin manifest is required")
        manifest = json.loads(plugin.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("name"), ORCHESTRATOR_ID)
        self.assertEqual(manifest.get("skills"), "./skills/")
        skills_root = HOST_BUNDLE / "skills"
        bundled = sorted(path.name for path in skills_root.iterdir() if path.is_dir())
        expected = sorted(WORKER_SKILL_IDS + (ORCHESTRATOR_ID,))
        self.assertEqual(bundled, expected)

    def test_host_skill_trees_match_generated_skills(self) -> None:
        for skill_id in WORKER_SKILL_IDS + (ORCHESTRATOR_ID,):
            source = PROJECT / "skills" / skill_id
            bundled = HOST_BUNDLE / "skills" / skill_id
            self.assertTrue(source.is_dir(), source)
            self.assertTrue(bundled.is_dir(), bundled)
            src_files = {
                path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in source.rglob("*")
                if path.is_file()
            }
            dst_files = {
                path.relative_to(bundled).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in bundled.rglob("*")
                if path.is_file()
            }
            self.assertEqual(src_files, dst_files, skill_id)

    def test_write_and_check_include_host_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-render-") as temporary:
            copy = copy_repo(temporary)
            written = run_renderer(copy, "--write")
            self.assertEqual(written.returncode, 0, written.stderr or written.stdout)
            bundle = copy / "hosts" / HOST_ID
            self.assertTrue((bundle / ".cursor-plugin" / "plugin.json").is_file())
            checked = run_renderer(copy, "--check")
            self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)
            shutil.rmtree(bundle)
            missing = run_renderer(copy, "--check")
            self.assertNotEqual(missing.returncode, 0)
            detail = f"{missing.stderr}\n{missing.stdout}"
            self.assertIn(HOST_ID, detail)

    def test_offline_verifier_accepts_generated_bundle(self) -> None:
        self.assertTrue(VERIFIER.is_file(), "offline verifier script is required")
        result = subprocess.run(
            [sys.executable, str(VERIFIER), str(HOST_BUNDLE), "--repo", str(PROJECT)],
            cwd=PROJECT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_unofficial_sand_api_absent_from_host_and_orchestrator_packaging(self) -> None:
        surfaces = [
            HOST_BUNDLE / ".cursor-plugin" / "plugin.json",
            PROJECT / "skills" / ORCHESTRATOR_ID / "SKILL.md",
            PROJECT / "templates" / "orchestrator" / "SKILL.md.tmpl",
            PROJECT / "templates" / "orchestrator" / "references" / "grok-bot-host.md",
            PROJECT / "docs" / "grok-bot-host.md",
            INSTALLER,
            RENDERER,
        ]
        for path in surfaces:
            self.assertTrue(path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            for token in UNOFFICIAL_API:
                self.assertNotIn(token, text, f"{path}: {token}")


class Issue49InstallerHost(unittest.TestCase):
    def test_runtime_grok_bot_installs_plugin_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-install-") as temporary:
            home = Path(temporary) / "home"
            dest = home / ".cursor" / "plugins" / "local" / ORCHESTRATOR_ID
            result = subprocess.run(
                ["bash", str(INSTALLER), "--runtime", "grok-bot", "--method", "copy"],
                cwd=PROJECT,
                text=True,
                capture_output=True,
                env={
                    **dict(__import__("os").environ),
                    "HOME": str(home),
                    "CODEX_HOME": str(home / "codex-unused"),
                    "CLAUDE_CONFIG_DIR": str(home / "claude-unused"),
                    "DEVIN_CONFIG_DIR": str(home / "devin-unused"),
                },
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue((dest / ".cursor-plugin" / "plugin.json").is_file())
            self.assertTrue((dest / "skills" / ORCHESTRATOR_ID / "SKILL.md").is_file())
            for skill_id in WORKER_SKILL_IDS:
                self.assertTrue((dest / "skills" / skill_id / "SKILL.md").is_file(), skill_id)
            self.assertFalse((home / ".codex").exists() or (home / "codex-unused" / "skills").exists())
            self.assertFalse((home / ".local" / "bin" / "kaola-acp").exists())

    def test_runtime_grok_bot_platform_grok_keeps_only_grok_worker_plus_orchestrator(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-subset-") as temporary:
            home = Path(temporary) / "home"
            dest = home / ".cursor" / "plugins" / "local" / ORCHESTRATOR_ID
            result = subprocess.run(
                [
                    "bash",
                    str(INSTALLER),
                    "--runtime",
                    "grok-bot",
                    "--platform",
                    "grok",
                    "--method",
                    "copy",
                ],
                cwd=PROJECT,
                text=True,
                capture_output=True,
                env={
                    **dict(__import__("os").environ),
                    "HOME": str(home),
                },
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            bundled = sorted(path.name for path in (dest / "skills").iterdir() if path.is_dir())
            self.assertEqual(bundled, ["grok-kaola-project-runner", ORCHESTRATOR_ID])


class Issue49OrchestratorSemantics(unittest.TestCase):
    def orchestrator_text(self) -> str:
        package = PROJECT / "skills" / ORCHESTRATOR_ID
        text = markdown_tree(package)
        self.assertTrue(text.strip(), "generated orchestrator markdown is empty")
        return text

    def test_names_grok_bot_as_a_first_class_host_not_a_worker(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"Grok Bot.{0,80}(?:is )?(?:a )?(?:first-class |optional )?host",
                    r"--runtime grok-bot",
                    r"Grok Bot is (?:a host|not a worker|not an eighth)",
                ),
            ),
            "orchestrator must name Grok Bot as a host",
        )
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"--platform grok.{0,80}Grok CLI worker",
                    r"Grok CLI worker.{0,40}--platform grok",
                    r"not an eighth (?:CLI |platform )?worker",
                    r"not an eighth platform",
                ),
            ),
            "orchestrator must distinguish --platform grok from the Grok Bot host",
        )

    def test_grok_bot_routine_is_the_only_heartbeat_on_that_host(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"Grok Bot.{0,80}Routine.{0,80}(?:only|unique|single|one).{0,40}heartbeat",
                    r"one Grok Bot Routine.{0,80}heartbeat",
                    r"Routine.{0,40}(?:is|as) the (?:only|unique) heartbeat",
                ),
            ),
            "Grok Bot host must use one Routine as the only heartbeat carrier",
        )
        heartbeat = (
            PROJECT / "skills" / ORCHESTRATOR_ID / "references" / "heartbeat-skeleton.md"
        ).read_text(encoding="utf-8")
        self.assertRegex(heartbeat, r"Grok Bot")
        self.assertRegex(heartbeat, r"Routine")
        wrong = authorizes_wrong_move(
            text + "\n" + heartbeat,
            (
                r"stack (?:a )?Grok Bot Routine with (?:a )?Codex heartbeat",
                r"use both a Routine and (?:blocking )?sleep",
                r"keep the Codex heartbeat (?:running )?after.{0,40}Grok Bot Routine",
            ),
        )
        self.assertIsNone(wrong, f"heartbeat policy stacks carriers: {wrong!r}")

    def test_human_decision_returns_to_this_bot_conversation(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"HUMAN_DECISION_REQUIRED.{0,120}(?:this Bot|Grok Bot).{0,40}(?:conversation|session)",
                    r"Needs attention",
                    r"HUMAN_DECISION_REQUIRED.{0,80}Notifications",
                ),
            ),
            "HUMAN_DECISION_REQUIRED must return to the Grok Bot main session",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"use Agent Computer takeover for HUMAN_DECISION_REQUIRED",
                r"treat computer takeover as exact-session stop",
                r"open a new Bot.{0,40}HUMAN_DECISION_REQUIRED",
            ),
        )
        self.assertIsNone(wrong, f"decision policy misroutes HUMAN_DECISION_REQUIRED: {wrong!r}")

    def test_takeover_cancels_prior_host_heartbeat_without_stopping_workers(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"cancel.{0,40}(?:previous|prior|old) host heartbeat.{0,80}(?:do not|without|must not).{0,40}stop",
                    r"takeover.{0,80}cancel.{0,60}heartbeat.{0,80}(?:not|without).{0,40}stop.{0,40}worker",
                    r"do not stop in-flight.{0,40}(?:exact owned )?worker",
                ),
            ),
            "Grok Bot takeover must cancel only the previous host heartbeat",
        )
        wrong = authorizes_wrong_move(
            text,
            (
                r"stop (?:all )?(?:in-flight )?workers when (?:taking over|cancelling the heartbeat)",
                r"Reset Agent Computer.{0,40}takeover",
                r"use Stop now to end worker sessions",
            ),
        )
        self.assertIsNone(wrong, f"takeover policy stops workers: {wrong!r}")

    def test_acceptance_before_finalize_and_exact_session_stop_remain(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"mission-frontier done triggers review, not automatic finalize",
                    r"not automatic finalize",
                ),
            )
        )
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"exact owned session `stop` via the matching platform Runner Skill",
                    r"ACP and PTY/tmux are the same stop action",
                ),
            )
        )
        self.assertIsNotNone(
            clause_present(
                text,
                (
                    r"must not restart intake, workers, claims or assignments already established",
                    r"recover existing explicit authorization and live work",
                ),
            )
        )

    def test_live_ui_is_an_explicit_uat_boundary_not_claimed_adoption(self) -> None:
        text = self.orchestrator_text()
        docs = (PROJECT / "docs" / "grok-bot-host.md").read_text(encoding="utf-8")
        combined = text + "\n" + docs
        self.assertIsNotNone(
            clause_present(
                combined,
                (
                    r"live.{0,40}UAT",
                    r"not.{0,40}(?:claim|claimed|prove).{0,40}live adoption",
                    r"Grok Bot UI.{0,80}(?:human|UAT|unproven)",
                ),
            ),
            "must mark live Grok Bot UI enablement as UAT, not claimed adoption",
        )
        wrong = authorizes_wrong_move(
            combined,
            (
                r"installer copy (?:means|proves|is) live Grok Bot adoption",
                r"Grok Bot 0\.51.{0,40}(?:is proven to|automatically) load",
            ),
        )
        self.assertIsNone(wrong, f"docs claim live adoption: {wrong!r}")


class Issue49WorkerIsolation(unittest.TestCase):
    def test_workers_do_not_absorb_grok_bot_host_policy(self) -> None:
        forbidden = (
            "Grok Bot Routine",
            "--runtime grok-bot",
            "Needs attention",
            "PROJECT_RUNNER_HEARTBEAT",
            "Mission-frontier done triggers review, not automatic finalize",
        )
        for label, raw in worker_policy_surfaces():
            body = normalize(raw)
            for marker in forbidden:
                self.assertNotIn(
                    normalize(marker),
                    body,
                    f"{label} gained Grok Bot host/orchestrator policy: {marker!r}",
                )

    def test_worker_template_keeps_skill_dir_inside_plugin_packaging(self) -> None:
        template = (PROJECT / "templates" / "SKILL.md.tmpl").read_text(encoding="utf-8")
        self.assertRegex(
            normalize(template),
            r"host plugin.{0,80}SKILL_DIR is still this Skill",
        )
        self.assertNotIn("Grok Bot", template)
        self.assertNotIn("grok-bot", template)


if __name__ == "__main__":
    unittest.main()
