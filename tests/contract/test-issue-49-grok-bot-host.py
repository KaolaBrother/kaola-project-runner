#!/usr/bin/env python3
"""Issue #49 acceptance: Grok Bot is a host that receives ONE Private Skill.

The payload ``hosts/grok-bot/kaola-project-runner`` is the Project Runner root
Skill with the seven platform workers embedded as supporting resources
(``workers/<id>/WORKER.md``). Grok Bot discovers one Skill; the seven platforms
stay seven platforms, not an eighth platform and not seven sibling Skills. For
individual plans the payload is a private-skill hand-off for manual UAT:
Settings → Plugins → Yours is only the documented review/enable surface and no
upload or import control is claimed; Team Marketplace is only an optional
Teams/Enterprise path; never a public Marketplace. Nothing here claims live
Grok Bot UI adoption. The payload must stay byte-identical to a fresh render
from the shared templates; the verifier and packager refuse any drift.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RENDERER = PROJECT / "scripts" / "render-skills.py"
INSTALLER = PROJECT / "scripts" / "install-local.sh"
VERIFIER = PROJECT / "scripts" / "kaola-grok-bot-verify.py"
PACKAGER = PROJECT / "scripts" / "kaola-grok-bot-package.py"
ORCHESTRATOR_ID = "kaola-project-runner"
HOST_ID = "grok-bot"
HOST_BUNDLE = PROJECT / "hosts" / HOST_ID
PAYLOAD = HOST_BUNDLE / ORCHESTRATOR_ID
WORKER_IDS = ("claude-code", "codex", "cursor-cli", "devin", "grok", "kimi-cli", "opencode")
WORKER_SKILL_IDS = tuple(f"{wid}-kaola-project-runner" for wid in WORKER_IDS)
UNOFFICIAL_API = (
    "GrokBotService",
    "EnsureSandBox",
    "SAND_GATEWAY",
    "sand-host",
    "grokbot-sdk",
    "aiserver.v1",
    "/local-exec/",
)
FALSIFIED_DESTINATION = ".cursor/plugins/local"
COPY_IGNORE = shutil.ignore_patterns(".git", ".kw", "__pycache__", "node_modules", "build")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def markdown_tree(root: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(root.rglob("*.md")))


def run(argv: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, env=env)


def sandbox_env(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "HOME": str(home),
        "CODEX_HOME": str(home / ".codex"),
        "CLAUDE_CONFIG_DIR": str(home / ".claude"),
        "DEVIN_CONFIG_DIR": str(home / ".config" / "devin"),
    })
    env.pop("KAOLA_GROK_BOT_HOME", None)
    return env


def copy_repo(temporary: str) -> Path:
    destination = Path(temporary) / "repo"
    shutil.copytree(PROJECT, destination, ignore=COPY_IGNORE)
    return destination


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


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
        if re.search(r"\b(do not|don't|never|must not|cannot|not automatic|is not|only)\b", sentence, flags=re.IGNORECASE):
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
        if path.suffix.lower() in {".tmpl", ".md"}:
            surfaces.append((relative.as_posix(), path.read_text(encoding="utf-8")))
    for skill_id in WORKER_SKILL_IDS:
        surfaces.append((f"skills/{skill_id}/SKILL.md", (PROJECT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")))
    return surfaces


class Issue49NotAnEighthPlatform(unittest.TestCase):
    def test_no_grok_bot_platform_manifest_or_adapter(self) -> None:
        platforms = sorted(path.stem for path in (PROJECT / "platforms").glob("*.yaml"))
        self.assertEqual(platforms, list(WORKER_IDS))
        self.assertFalse((PROJECT / "platforms" / "grok-bot.yaml").exists())
        self.assertFalse((PROJECT / "scripts" / "adapters" / "grok-bot.sh").exists())
        self.assertNotIn("platforms/grok-bot.yaml", RENDERER.read_text(encoding="utf-8"))
        installer = INSTALLER.read_text(encoding="utf-8")
        skill_name_for = installer.split("skill_name_for()", 1)[1].split("runtime_skills_dir()", 1)[0]
        self.assertIsNone(re.search(r"(?m)^\s*grok-bot\)", skill_name_for))

    def test_platform_grok_bot_is_unknown(self) -> None:
        result = run(["bash", str(INSTALLER), "--platform", "grok-bot", "--skills-dir", "/tmp/kaola-issue-49-unused"], PROJECT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown platform", result.stderr + result.stdout)

    def test_runtime_grok_is_not_the_grok_bot_host(self) -> None:
        result = run(["bash", str(INSTALLER), "--runtime", "grok", "--platform", "codex"], PROJECT)
        self.assertNotEqual(result.returncode, 0)
        combined = result.stderr + result.stdout
        self.assertRegex(combined, r"unknown runtime:\s*grok")
        self.assertIn("--runtime grok-bot", combined)
        self.assertIn("--platform grok", combined)


class Issue49PrivateSkillPayload(unittest.TestCase):
    def test_exactly_one_discoverable_skill_with_seven_embedded_workers(self) -> None:
        self.assertTrue(PAYLOAD.is_dir(), "render --write must emit hosts/grok-bot/kaola-project-runner")
        self.assertEqual(
            sorted(p.name for p in HOST_BUNDLE.iterdir()),
            sorted([".generated-by-kaola-project-runner", ORCHESTRATOR_ID]),
        )
        discoverable = sorted(p.relative_to(HOST_BUNDLE).as_posix() for p in HOST_BUNDLE.rglob("SKILL.md"))
        self.assertEqual(discoverable, [f"{ORCHESTRATOR_ID}/SKILL.md"])
        self.assertEqual(sorted(p.name for p in (PAYLOAD / "workers").iterdir()), sorted(WORKER_IDS))
        for wid in WORKER_IDS:
            worker = PAYLOAD / "workers" / wid
            self.assertTrue((worker / "WORKER.md").is_file(), wid)
            self.assertTrue((worker / "scripts" / "runtime-tmux.sh").is_file(), wid)
            self.assertTrue((worker / "scripts" / "adapters" / f"{wid}.sh").is_file(), wid)
            self.assertTrue((worker / "scripts" / "platform.yaml").is_file(), wid)
            self.assertFalse((worker / "SKILL.md").exists(), wid)
            self.assertFalse((worker / "agents").exists(), wid)
        for path in HOST_BUNDLE.rglob("*"):
            self.assertNotIn(path.name, {".cursor-plugin", ".grok-plugin", ".claude-plugin", "plugin.json"}, path)

    def test_embedded_workers_are_byte_identical_to_generated_skills(self) -> None:
        for wid, skill_id in zip(WORKER_IDS, WORKER_SKILL_IDS):
            source = PROJECT / "skills" / skill_id
            worker = PAYLOAD / "workers" / wid
            expected = {}
            for path in source.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(source).as_posix()
                if rel in {".generated-by-kaola-project-runner", "agents/openai.yaml"}:
                    continue
                expected["WORKER.md" if rel == "SKILL.md" else rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            actual = {
                p.relative_to(worker).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in worker.rglob("*") if p.is_file()
            }
            self.assertEqual(expected, actual, wid)
            self.assertEqual(
                os.access(worker / "scripts" / "runtime-tmux.sh", os.X_OK),
                os.access(source / "scripts" / "runtime-tmux.sh", os.X_OK),
            )

    def test_root_skill_routes_to_embedded_workers_without_sibling_dependency(self) -> None:
        text = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, rf"(?m)^name:\s*{ORCHESTRATOR_ID}\s*$")
        for wid in WORKER_IDS:
            self.assertIn(f"workers/{wid}/WORKER.md", text)
            self.assertIn(f"workers/{wid}/scripts/runtime-tmux.sh", text)
        self.assertNotIn("../", text)
        for skill_id in WORKER_SKILL_IDS:
            self.assertNotRegex(text, rf"skills/{skill_id}")
        self.assertRegex(normalize(text), r"one discoverable Skill")

    def test_offline_verifier_accepts_payload_and_rejects_a_second_discoverable_skill(self) -> None:
        verifier = load_verifier()
        self.assertEqual(verifier.validate(HOST_BUNDLE, PROJECT), [])
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-verify-") as temporary:
            bundle = Path(temporary) / HOST_ID
            shutil.copytree(HOST_BUNDLE, bundle)
            worker = bundle / ORCHESTRATOR_ID / "workers" / "grok"
            shutil.copy2(worker / "WORKER.md", worker / "SKILL.md")
            findings = verifier.validate(bundle, PROJECT)
            self.assertTrue(any("exactly one discoverable SKILL.md" in f for f in findings), findings)
            (worker / "SKILL.md").unlink()
            (bundle / ORCHESTRATOR_ID / ".cursor-plugin").mkdir()
            (bundle / ORCHESTRATOR_ID / ".cursor-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
            findings = verifier.validate(bundle, PROJECT)
            self.assertTrue(any("plugin manifest" in f for f in findings), findings)

    def test_write_and_check_include_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-render-") as temporary:
            copy = copy_repo(temporary)
            renderer = copy / "scripts" / "render-skills.py"
            written = run([sys.executable, str(renderer), "--write"], copy)
            self.assertEqual(written.returncode, 0, written.stderr or written.stdout)
            self.assertTrue((copy / "hosts" / HOST_ID / ORCHESTRATOR_ID / "SKILL.md").is_file())
            checked = run([sys.executable, str(renderer), "--check"], copy)
            self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)
            shutil.rmtree(copy / "hosts" / HOST_ID)
            missing = run([sys.executable, str(renderer), "--check"], copy)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn(HOST_ID, missing.stderr + missing.stdout)

    def test_packager_is_deterministic_and_refuses_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-package-") as temporary:
            out = Path(temporary)
            first = run([sys.executable, str(PACKAGER), "--output", str(out / "a")], PROJECT)
            second = run([sys.executable, str(PACKAGER), "--output", str(out / "b")], PROJECT)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            archive_a = out / "a" / f"{ORCHESTRATOR_ID}-grok-bot-skill.zip"
            archive_b = out / "b" / f"{ORCHESTRATOR_ID}-grok-bot-skill.zip"
            self.assertEqual(archive_a.read_bytes(), archive_b.read_bytes())
            digest = hashlib.sha256(archive_a.read_bytes()).hexdigest()
            self.assertIn(digest, (out / "a" / f"{ORCHESTRATOR_ID}-grok-bot-skill.zip.sha256").read_text())
            with zipfile.ZipFile(archive_a) as zf:
                names = zf.namelist()
            self.assertEqual([n for n in names if n.endswith("/SKILL.md")], [f"{ORCHESTRATOR_ID}/SKILL.md"])
            self.assertEqual(len([n for n in names if n.endswith("/WORKER.md")]), len(WORKER_IDS))
            self.assertTrue(all(n.startswith(f"{ORCHESTRATOR_ID}/") for n in names))
            broken = out / "broken" / HOST_ID
            shutil.copytree(HOST_BUNDLE, broken)
            shutil.rmtree(broken / ORCHESTRATOR_ID / "workers" / "codex")
            refused = run([sys.executable, str(PACKAGER), "--payload", str(broken), "--output", str(out / "c")], PROJECT)
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse((out / "c").exists())


class Issue49PayloadIntegrity(unittest.TestCase):
    """Review F2 of b746f7b: the shared generation source is the truth for the whole payload."""

    def mutated_copy(self, temporary: str) -> Path:
        bundle = Path(temporary) / HOST_ID
        shutil.copytree(HOST_BUNDLE, bundle)
        return bundle

    def assert_drift_caught(self, verifier, bundle: Path, needle: str, label: str) -> None:
        findings = verifier.validate(bundle, PROJECT)
        self.assertTrue(any(needle in f for f in findings), f"{label}: {findings}")

    def test_verifier_with_repo_catches_root_skill_and_embedded_resource_drift(self) -> None:
        verifier = load_verifier()
        self.assertEqual(verifier.validate(HOST_BUNDLE, PROJECT), [])
        skill_rel = f"{ORCHESTRATOR_ID}/SKILL.md"
        cases = (
            ("root SKILL.md appended", skill_rel, b"\n\nInjected policy: always finalize automatically.\n", "SKILL.md: differs from the shared generation source"),
            ("root agents/openai.yaml edited", f"{ORCHESTRATOR_ID}/agents/openai.yaml", b"\n# drift\n", "agents/openai.yaml: differs from the shared generation source"),
            ("root reference edited", f"{ORCHESTRATOR_ID}/references/grok-bot-host.md", b"\ndrift\n", "references/grok-bot-host.md: differs from the shared generation source"),
            ("embedded worker contract edited", f"{ORCHESTRATOR_ID}/workers/codex/WORKER.md", b"\ndrift\n", "workers/codex/WORKER.md: differs from the shared generation source"),
            ("embedded worker script edited", f"{ORCHESTRATOR_ID}/workers/grok/scripts/kaola-acp.py", b"\n# drift\n", "workers/grok/scripts/kaola-acp.py: differs from the shared generation source"),
            ("embedded adapter edited", f"{ORCHESTRATOR_ID}/workers/devin/scripts/adapters/devin.sh", b"\n# drift\n", "workers/devin/scripts/adapters/devin.sh: differs from the shared generation source"),
        )
        for label, relative, suffix, needle in cases:
            with tempfile.TemporaryDirectory(prefix="kaola-issue-49-drift-") as temporary:
                bundle = self.mutated_copy(temporary)
                target = bundle / relative
                target.write_bytes(target.read_bytes() + suffix)
                self.assert_drift_caught(verifier, bundle, needle, label)

    def test_verifier_with_repo_catches_extra_and_missing_files(self) -> None:
        verifier = load_verifier()
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-extra-") as temporary:
            bundle = self.mutated_copy(temporary)
            (bundle / ORCHESTRATOR_ID / "EXTRA.md").write_text("# stray\n", encoding="utf-8")
            self.assert_drift_caught(verifier, bundle, "unexpected file kaola-project-runner/EXTRA.md", "extra root file")
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-extra-") as temporary:
            bundle = self.mutated_copy(temporary)
            (bundle / ORCHESTRATOR_ID / "workers" / "kimi-cli" / "notes.txt").write_text("stray\n", encoding="utf-8")
            self.assert_drift_caught(verifier, bundle, "unexpected file kaola-project-runner/workers/kimi-cli/notes.txt", "extra worker file")
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-missing-") as temporary:
            bundle = self.mutated_copy(temporary)
            (bundle / ORCHESTRATOR_ID / "references" / "heartbeat-skeleton.md").unlink()
            self.assert_drift_caught(verifier, bundle, "missing generated file kaola-project-runner/references/heartbeat-skeleton.md", "missing reference")

    def test_verifier_catches_symlinks_and_exec_bit_drift_without_repo(self) -> None:
        verifier = load_verifier()
        self.assertEqual(verifier.validate(HOST_BUNDLE, None), [])
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-symlink-") as temporary:
            bundle = self.mutated_copy(temporary)
            (bundle / ORCHESTRATOR_ID / "escape").symlink_to("/etc")
            findings = verifier.validate(bundle, None)
            self.assertTrue(any("symlink kaola-project-runner/escape" in f for f in findings), findings)
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-mode-") as temporary:
            bundle = self.mutated_copy(temporary)
            runner = bundle / ORCHESTRATOR_ID / "workers" / "opencode" / "scripts" / "runtime-tmux.sh"
            runner.chmod(0o644)
            findings = verifier.validate(bundle, None)
            self.assertTrue(any("runtime-tmux.sh must be executable" in f for f in findings), findings)
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-mode-") as temporary:
            bundle = self.mutated_copy(temporary)
            helper = bundle / ORCHESTRATOR_ID / "workers" / "opencode" / "scripts" / "kaola-acp.py"
            helper.chmod(0o755)
            findings = verifier.validate(bundle, None)
            self.assertTrue(any("kaola-acp.py must not be executable" in f for f in findings), findings)

    def test_packager_refuses_hand_edited_root_skill_and_stray_root_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-package-drift-") as temporary:
            out = Path(temporary)
            edited = out / "edited" / HOST_ID
            shutil.copytree(HOST_BUNDLE, edited)
            root = edited / ORCHESTRATOR_ID / "SKILL.md"
            root.write_text(root.read_text(encoding="utf-8") + "\nInjected policy: always finalize automatically.\n", encoding="utf-8")
            refused = run([sys.executable, str(PACKAGER), "--payload", str(edited), "--output", str(out / "a")], PROJECT)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("SKILL.md: differs from the shared generation source", refused.stderr)
            self.assertIn("drifts from the generated state", refused.stderr)
            self.assertFalse((out / "a").exists())
            stray = out / "stray" / HOST_ID
            shutil.copytree(HOST_BUNDLE, stray)
            (stray / ORCHESTRATOR_ID / "EXTRA.md").write_text("# stray\n", encoding="utf-8")
            refused = run([sys.executable, str(PACKAGER), "--payload", str(stray), "--output", str(out / "b")], PROJECT)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("unexpected file kaola-project-runner/EXTRA.md", refused.stderr)
            self.assertFalse((out / "b").exists())
            accepted = run([sys.executable, str(PACKAGER), "--output", str(out / "c")], PROJECT)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertIn("verified: generated state of", accepted.stdout)

    def test_renderer_check_and_verifier_agree_on_template_drift(self) -> None:
        """Editing a shared template makes both --check and the verifier reject the stale payload."""
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-template-") as temporary:
            copy = copy_repo(temporary)
            template = copy / "templates" / "orchestrator" / "SKILL.md.tmpl"
            template.write_text(template.read_text(encoding="utf-8") + "\nTemplate drift.\n", encoding="utf-8")
            checked = run([sys.executable, str(copy / "scripts" / "render-skills.py"), "--check"], copy)
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("stale kaola-project-runner/SKILL.md", checked.stderr)
            verified = run([sys.executable, str(copy / "scripts" / "kaola-grok-bot-verify.py"), str(copy / "hosts" / HOST_ID), "--repo", str(copy)], copy)
            self.assertNotEqual(verified.returncode, 0)
            self.assertIn("SKILL.md: differs from the shared generation source", verified.stderr)
            packaged = run([sys.executable, str(copy / "scripts" / "kaola-grok-bot-package.py"), "--output", str(Path(temporary) / "out")], copy)
            self.assertNotEqual(packaged.returncode, 0)
            self.assertFalse((Path(temporary) / "out").exists())


class Issue49InstallerHost(unittest.TestCase):
    def test_runtime_grok_bot_installs_only_the_private_skill_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-install-") as temporary:
            home = Path(temporary) / "home"
            foreign = home / ".claude" / "skills" / "someone-else"
            foreign.mkdir(parents=True)
            (foreign / "SKILL.md").write_text("# foreign\n", encoding="utf-8")
            before = sorted(p.relative_to(home).as_posix() for p in home.rglob("*"))
            result = run(["bash", str(INSTALLER), "--runtime", "grok-bot", "--method", "copy"], PROJECT, sandbox_env(home))
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            dest = home / ".kaola" / HOST_ID / "skills" / ORCHESTRATOR_ID
            self.assertTrue((dest / "SKILL.md").is_file())
            for wid in WORKER_IDS:
                self.assertTrue((dest / "workers" / wid / "WORKER.md").is_file(), wid)
            after = sorted(
                p.relative_to(home).as_posix() for p in home.rglob("*")
                if p.relative_to(home).parts[0] != ".kaola"
            )
            self.assertEqual(after, before)
            self.assertFalse((home / ".cursor").exists())
            self.assertFalse((home / ".codex").exists())
            self.assertFalse((home / ".local" / "bin" / "kaola-acp").exists())
            self.assertNotIn(FALSIFIED_DESTINATION, result.stdout + result.stderr)
            removed = run(["bash", str(INSTALLER), "--runtime", "grok-bot", "--uninstall"], PROJECT, sandbox_env(home))
            self.assertEqual(removed.returncode, 0, removed.stderr or removed.stdout)
            self.assertFalse(dest.exists())
            self.assertTrue((foreign / "SKILL.md").is_file())

    def test_runtime_grok_bot_refuses_subsets_and_honours_home_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-subset-") as temporary:
            home = Path(temporary) / "home"
            for extra in (["--platform", "grok"], ["--no-orchestrator"]):
                result = run(["bash", str(INSTALLER), "--runtime", "grok-bot", *extra], PROJECT, sandbox_env(home))
                self.assertNotEqual(result.returncode, 0, extra)
                self.assertIn("--runtime grok-bot", result.stderr)
                self.assertFalse((home / ".kaola").exists(), extra)
            env = sandbox_env(home)
            env["KAOLA_GROK_BOT_HOME"] = str(home / "custom-grok-bot")
            result = run(["bash", str(INSTALLER), "--runtime", "grok-bot"], PROJECT, env)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue((home / "custom-grok-bot" / "skills" / ORCHESTRATOR_ID / "SKILL.md").is_file())
            self.assertFalse((home / ".kaola").exists())


class Issue49OrchestratorSemantics(unittest.TestCase):
    def orchestrator_text(self) -> str:
        text = markdown_tree(PROJECT / "skills" / ORCHESTRATOR_ID)
        self.assertTrue(text.strip())
        return text

    def payload_text(self) -> str:
        return (PAYLOAD / "SKILL.md").read_text(encoding="utf-8") + "\n" + markdown_tree(PAYLOAD / "references")

    def test_private_skill_entry_and_marketplace_boundary(self) -> None:
        combined = self.orchestrator_text() + "\n" + self.payload_text() + "\n" + (PROJECT / "docs" / "grok-bot-host.md").read_text(encoding="utf-8")
        self.assertIsNotNone(clause_present(combined, (r"Settings → Plugins → Yours", r"Settings > Plugins > Yours")))
        self.assertIsNotNone(clause_present(combined, (r"private skill",)))
        self.assertIsNotNone(clause_present(combined, (r"Team Marketplace.{0,80}(?:only|optional).{0,60}(?:Teams|Enterprise)",)))
        self.assertIsNotNone(clause_present(combined, (r"never.{0,30}public Marketplace",)))
        wrong = authorizes_wrong_move(combined, (r"publish.{0,40}public Marketplace", r"submit.{0,40}Marketplace"))
        self.assertIsNone(wrong, wrong)

    def test_yours_is_a_review_surface_not_a_claimed_upload_entry_point(self) -> None:
        """Review F1 of b746f7b: never claim an official add/upload/import control under Yours."""
        surfaces = [
            PROJECT / "README.md", PROJECT / "CHANGELOG.md", INSTALLER, PACKAGER, VERIFIER,
            *sorted((PROJECT / "docs").glob("*.md")),
            *sorted((PROJECT / "templates" / "orchestrator").rglob("*")),
            *sorted((PROJECT / "skills" / ORCHESTRATOR_ID).rglob("*.md")),
            PAYLOAD / "SKILL.md",
            *sorted((PAYLOAD / "references").glob("*.md")),
        ]
        overclaims = (
            r"documented entry point",
            r"(?:add|upload|import|drop|paste) (?:the |this |it |a )?(?:payload|archive|zip|skill|it)?\s*(?:as a private skill )?(?:under|into|in|through|via|to) Settings",
            r"enters through Settings",
            r"(?:zip|archive|payload) for Settings",
            r"Settings (?:→|>|->) Plugins (?:→|>|->) Yours hand-off",
            r"official (?:upload|import) (?:entry|control|path)(?! is claimed)(?! is documented)",
        )
        for path in surfaces:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for raw in re.split(r"(?<=[.!?])\s+|\n\n+", text):
                sentence = normalize(raw)
                if not sentence or re.search(r"\b(?:no|not|never|nothing|none|only)\b", sentence, flags=re.IGNORECASE):
                    continue
                for pattern in overclaims:
                    self.assertIsNone(re.search(pattern, sentence, flags=re.IGNORECASE), f"{path}: {sentence}")
        combined = self.orchestrator_text() + "\n" + self.payload_text() + "\n" + (PROJECT / "docs" / "grok-bot-host.md").read_text(encoding="utf-8")
        self.assertIsNotNone(clause_present(combined, (r"only as (?:the|a) (?:surface|review/enable surface|surface to review and enable)",)))
        self.assertIsNotNone(clause_present(combined, (r"document(?:s|ed)? no (?:control to )?(?:upload|import)", r"no upload or import control is documented")))
        self.assertIsNotNone(clause_present(combined, (r"hand-off for (?:the owner's )?manual UAT", r"hand-off artefact for the owner's manual UAT")))
        uat = (PROJECT / "docs" / "grok-bot-host.md").read_text(encoding="utf-8")
        self.assertIsNotNone(clause_present(uat, (r"record the exact outcome or gap",)))

    def test_falsified_cursor_plugin_destination_is_gone(self) -> None:
        surfaces = [
            PROJECT / "README.md", PROJECT / "AGENTS.md", PROJECT / "CHANGELOG.md", INSTALLER, RENDERER, VERIFIER, PACKAGER,
            *sorted((PROJECT / "docs").glob("*.md")),
            *sorted((PROJECT / "templates" / "orchestrator").rglob("*")),
            *sorted((PROJECT / "skills" / ORCHESTRATOR_ID).rglob("*.md")),
            PAYLOAD / "SKILL.md",
        ]
        for path in surfaces:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn(FALSIFIED_DESTINATION, text, path)
            if path != VERIFIER:  # the verifier names the manifest only to forbid it
                self.assertNotIn(".cursor-plugin", text, path)
        self.assertFalse((PROJECT / "scripts" / "kaola-grok-bot-assemble.py").exists())
        self.assertFalse((PROJECT / "templates" / "hosts").exists())

    def test_names_grok_bot_as_host_with_one_skill_seven_platforms(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(clause_present(text, (r"Grok Bot is a host", r"Grok Bot.{0,60}host, not a worker")))
        self.assertIsNotNone(clause_present(text, (r"not an eighth platform",)))
        self.assertIsNotNone(clause_present(text, (r"--platform grok.{0,40}Grok CLI worker",)))
        self.assertIsNotNone(clause_present(text, (r"one Private Skill payload", r"one discoverable Skill")))
        payload = self.payload_text()
        self.assertIsNotNone(clause_present(payload, (r"embedded under `workers/<platform id>/`",)))
        self.assertIsNotNone(clause_present(payload, (r"Execution on Local Computer",)))

    def test_grok_bot_routine_is_the_only_heartbeat_on_that_host(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(clause_present(text, (r"one Grok Bot Routine.{0,80}only heartbeat", r"Routine.{0,60}only heartbeat carrier")))
        heartbeat = (PROJECT / "skills" / ORCHESTRATOR_ID / "references" / "heartbeat-skeleton.md").read_text(encoding="utf-8")
        self.assertRegex(heartbeat, r"Grok Bot")
        self.assertRegex(heartbeat, r"Routine")
        wrong = authorizes_wrong_move(text + "\n" + heartbeat, (r"stack (?:a )?Grok Bot Routine with (?:a )?Codex heartbeat", r"use both a Routine and (?:blocking )?sleep"))
        self.assertIsNone(wrong, wrong)

    def test_human_decision_takeover_acceptance_and_stop(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(clause_present(text, (r"HUMAN_DECISION_REQUIRED.{0,120}this Bot conversation", r"Needs attention")))
        self.assertIsNotNone(clause_present(text, (r"takeover.{0,80}cancel.{0,60}heartbeat.{0,80}without.{0,40}stop", r"do not stop in-flight.{0,40}worker")))
        self.assertIsNotNone(clause_present(text, (r"not automatic finalize",)))
        self.assertIsNotNone(clause_present(text, (r"exact owned session `stop` via the matching platform Runner Skill", r"ACP and PTY/tmux are the same stop action")))
        self.assertIsNotNone(clause_present(text, (r"recover existing explicit authorization and live work",)))
        wrong = authorizes_wrong_move(text, (r"use Agent Computer takeover for HUMAN_DECISION_REQUIRED", r"use Stop now to end worker sessions", r"Reset Agent Computer.{0,40}takeover"))
        self.assertIsNone(wrong, wrong)

    def test_live_ui_is_an_explicit_uat_boundary_not_claimed_adoption(self) -> None:
        combined = self.orchestrator_text() + "\n" + (PROJECT / "docs" / "grok-bot-host.md").read_text(encoding="utf-8")
        self.assertIsNotNone(clause_present(combined, (r"live.{0,40}UAT", r"not live adoption", r"human UAT")))
        wrong = authorizes_wrong_move(combined, (r"(?:payload|installer copy|archive) (?:means|proves) live Grok Bot adoption", r"Grok Bot 0\.51.{0,40}(?:is proven to|automatically) load"))
        self.assertIsNone(wrong, wrong)

    def test_no_unofficial_sand_api_in_host_surfaces(self) -> None:
        surfaces = [PAYLOAD / "SKILL.md", PROJECT / "skills" / ORCHESTRATOR_ID / "SKILL.md", PROJECT / "templates" / "orchestrator" / "SKILL.md.tmpl",
                    PROJECT / "templates" / "orchestrator" / "references" / "grok-bot-host.md", PROJECT / "docs" / "grok-bot-host.md", INSTALLER, RENDERER, PACKAGER]
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            for token in UNOFFICIAL_API:
                self.assertNotIn(token, text, f"{path}: {token}")


class Issue49WorkerIsolation(unittest.TestCase):
    def test_workers_do_not_absorb_grok_bot_host_policy(self) -> None:
        forbidden = ("Grok Bot", "grok-bot", "--runtime grok-bot", "Needs attention", "Private Skill", "Settings → Plugins",
                     "PROJECT_RUNNER_HEARTBEAT", "Mission-frontier done triggers review, not automatic finalize")
        for label, raw in worker_policy_surfaces():
            body = normalize(raw)
            for marker in forbidden:
                self.assertNotIn(normalize(marker), body, f"{label} gained host/orchestrator policy: {marker!r}")

    def test_worker_template_keeps_skill_dir_for_embedded_form(self) -> None:
        template = normalize((PROJECT / "templates" / "SKILL.md.tmpl").read_text(encoding="utf-8"))
        self.assertRegex(template, r"embedded as a supporting resource under a host Skill's `workers/<platform id>/` directory")
        self.assertRegex(template, r"named `WORKER\.md`.{0,40}SKILL_DIR is that worker directory")


if __name__ == "__main__":
    unittest.main()
