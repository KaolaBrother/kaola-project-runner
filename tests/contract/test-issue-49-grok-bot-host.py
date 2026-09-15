#!/usr/bin/env python3
"""Issue #49 acceptance: Grok Bot is a host that receives EIGHT single-Markdown Private Skills.

Owner UAT (2026-09-16) found that a Grok Bot private skill is one single
Markdown (name, description, body): no ZIP or file-tree import. So
``hosts/grok-bot/private-skills/`` carries exactly eight standalone account
Skill documents rendered from the shared templates -- ``kaola-project-runner``
(Project Runner: authorization, heartbeat, dispatch, acceptance, close-out;
routes to workers by stable Skill name) plus one ``<id>-kaola-project-runner``
per platform worker (full transport contract, bundled references, Local
Computer script location) -- and ``hosts/grok-bot/INSTALL.md``, a repo-based
guide that Grok Bot itself follows to create or update the eight Skills (not a
ninth Skill). ``hosts/grok-bot/kaola-project-runner/`` stays the Local Computer
runtime copy: one root ``SKILL.md`` with the seven workers embedded
(``workers/<id>/WORKER.md``). Seven platforms, not an eighth. Settings →
Plugins → Yours is only the documented review/enable surface and no upload or
import control is claimed; never a public Marketplace. Nothing here claims live
Grok Bot UI adoption. Everything under ``hosts/grok-bot/`` must stay
byte-identical to a fresh render; the verifier and packager refuse any drift.
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
PRIVATE_SKILLS = HOST_BUNDLE / "private-skills"
PRIVATE_SKILLS_MANIFEST = HOST_BUNDLE / "private-skills.json"
INSTALL_GUIDE = HOST_BUNDLE / "INSTALL.md"
GUIDE_TEMPLATE = PROJECT / "templates" / "grok-bot" / "INSTALL.md.tmpl"
ACCOUNT_SKILL_NAMES = (ORCHESTRATOR_ID, *WORKER_SKILL_IDS)
LOCAL_RUNTIME_COPY = "${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}/skills/kaola-project-runner"
WORKER_OPERATIONS = ("preflight", "start", "observe", "send", "capture", "key", "stop")
TRANSPORT_MARKERS = ("## Transport facts", "## Communication loop", 'runtime-tmux.sh" send', 'runtime-tmux.sh" observe',
                     'runtime-tmux.sh" capture', 'runtime-tmux.sh" key', "mutation_status", "raw_current_frame", "--transport acp|pty")
ORCHESTRATOR_MARKERS = ("PROJECT_RUNNER_HEARTBEAT", "## Heartbeat", "## Main execution loop", "Allowed CLIs", "Needs attention",
                        "Routine", "Mission-frontier", "Accept the delivery", "## Authorization", "## Ending a run")
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


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.split("\n")
    assert lines[0] == "---", "single-Markdown Skill must start with frontmatter"
    end = lines.index("---", 1)
    meta = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, "\n".join(lines[end + 1:])


def account_docs() -> dict[str, str]:
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(PRIVATE_SKILLS.glob("*.md"))}


def worker_policy_surfaces() -> list[tuple[str, str]]:
    surfaces: list[tuple[str, str]] = []
    templates = PROJECT / "templates"
    for path in sorted(templates.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(templates)
        # grok-bot/ holds the host install guide for Grok Bot itself, not a worker surface.
        if relative.parts[0] in {"grok-golden", "orchestrator", "grok-bot"}:
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
            sorted([".generated-by-kaola-project-runner", ORCHESTRATOR_ID, "INSTALL.md", "private-skills", "private-skills.json"]),
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
            self.assertTrue((copy / "hosts" / HOST_ID / "INSTALL.md").is_file())
            self.assertEqual(
                sorted(p.stem for p in (copy / "hosts" / HOST_ID / "private-skills").glob("*.md")),
                sorted(ACCOUNT_SKILL_NAMES),
            )
            checked = run([sys.executable, str(renderer), "--check"], copy)
            self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)
            doc = copy / "hosts" / HOST_ID / "private-skills" / "codex-kaola-project-runner.md"
            doc.write_text(doc.read_text(encoding="utf-8") + "\ndrift\n", encoding="utf-8")
            stale = run([sys.executable, str(renderer), "--check"], copy)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("stale private-skills/codex-kaola-project-runner.md", stale.stderr)
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
            ("account main Skill edited", f"private-skills/{ORCHESTRATOR_ID}.md", b"\n\nInjected policy: always finalize automatically.\n", f"private-skills/{ORCHESTRATOR_ID}.md: differs from the shared generation source"),
            ("account worker Skill edited", "private-skills/kimi-cli-kaola-project-runner.md", b"\ndrift\n", "private-skills/kimi-cli-kaola-project-runner.md: differs from the shared generation source"),
            ("install guide edited", "INSTALL.md", b"\nAlso publish to the Marketplace.\n", "INSTALL.md: differs from the shared generation source"),
            ("fingerprint manifest edited", "private-skills.json", b"\n", "private-skills.json: differs from the shared generation source"),
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
            INSTALL_GUIDE, GUIDE_TEMPLATE,
            *sorted(PRIVATE_SKILLS.glob("*.md")),
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
        self.assertIsNotNone(clause_present(text, (r"eight account-private Skills",)))
        self.assertIsNotNone(clause_present(text, (r"one single Markdown",)))
        self.assertIsNone(clause_present(text, (r"ships as \*\*one Private Skill payload\*\*", r"one Private Skill payload")))
        payload = self.payload_text()
        self.assertIsNotNone(clause_present(payload, (r"embedded under `workers/<platform id>/`",)))
        self.assertIsNotNone(clause_present(payload, (r"Execution on Local Computer",)))
        self.assertIsNotNone(clause_present(payload, (r"routes to a worker by that stable Skill name",)))

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


class Issue49AccountPrivateSkills(unittest.TestCase):
    """Owner correction 2026-09-16: eight single-Markdown Skills the Bot saves one by one."""

    def test_exactly_eight_standalone_documents_one_main_seven_workers(self) -> None:
        entries = sorted(PRIVATE_SKILLS.iterdir())
        self.assertTrue(all(p.is_file() and p.suffix == ".md" for p in entries), entries)
        docs = account_docs()
        self.assertEqual(sorted(docs), sorted(ACCOUNT_SKILL_NAMES))
        self.assertEqual(len(docs), 8)
        names = []
        for stem, text in docs.items():
            meta, body = frontmatter(text)
            self.assertEqual(meta["name"], stem)
            self.assertTrue(meta["description"], stem)
            self.assertTrue(body.strip(), stem)
            names.append(meta["name"])
        self.assertEqual(len(set(names)), 8)
        self.assertEqual(sorted(n for n in names if n != ORCHESTRATOR_ID), sorted(WORKER_SKILL_IDS))
        self.assertFalse((PRIVATE_SKILLS / "grok-bot-kaola-project-runner.md").exists())
        self.assertFalse(any("grok-bot" in n for n in names), "Grok Bot is a host, not an eighth worker")

    def test_worker_documents_carry_canonical_contract_references_and_local_computer_location(self) -> None:
        docs = account_docs()
        for wid, skill_id in zip(WORKER_IDS, WORKER_SKILL_IDS):
            text = docs[skill_id]
            canonical = (PROJECT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith(canonical), f"{skill_id}: does not begin with skills/{skill_id}/SKILL.md")
            self.assertIn(f'SKILL_DIR="{LOCAL_RUNTIME_COPY}/workers/{wid}"', text)
            self.assertIn("`KAOLA_GROK_BOT_HOME` overrides the root `$HOME/.kaola/grok-bot`", text)
            self.assertIn("install-local.sh --runtime grok-bot", text)
            for operation in WORKER_OPERATIONS:
                self.assertIn(f'"$SKILL_DIR/scripts/runtime-tmux.sh" {operation} ', text, f"{skill_id}: {operation}")
            for ref in ("platform.md", "transport.md", "acp.md"):
                self.assertIn(f"## Bundled reference: references/{ref}", text, skill_id)
                self.assertIn((PROJECT / "skills" / skill_id / "references" / ref).read_text(encoding="utf-8").rstrip(), text, f"{skill_id}: {ref}")
            self.assertIsNotNone(clause_present(text, (r"never on the cloud Agent Computer",)))

    def test_main_document_routes_by_stable_name_without_transport_or_inlined_workers(self) -> None:
        text = account_docs()[ORCHESTRATOR_ID]
        for skill_id in WORKER_SKILL_IDS:
            self.assertIn(f"`{skill_id}`", text)
        for marker in TRANSPORT_MARKERS:
            self.assertNotIn(marker, text, marker)
        self.assertNotIn("WORKER.md", text)
        self.assertNotIn("This Skill is a communication driver for", text)
        for skill_id in WORKER_SKILL_IDS:
            _, body = frontmatter((PROJECT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8"))
            self.assertNotIn(body.strip()[:200], text, f"{skill_id} text inlined into the main Skill")
        self.assertIsNotNone(clause_present(text, (r"select a worker by the stable Skill name",)))
        self.assertIsNotNone(clause_present(text, (r"carries no transport contract, no scripts, and none of the worker text",)))
        for ref in ("grok-bot-host.md", "heartbeat-skeleton.md"):
            self.assertIn(f"## Bundled reference: references/{ref}", text)
            self.assertIn((PROJECT / "skills" / ORCHESTRATOR_ID / "references" / ref).read_text(encoding="utf-8").rstrip(), text, ref)
        for clause in (r"recover existing explicit authorization and live work", r"only heartbeat carrier", r"not automatic finalize",
                       r"HUMAN_DECISION_REQUIRED.{0,120}this Bot conversation", r"## Ending a run"):
            self.assertIsNotNone(clause_present(text, (clause,)), clause)

    def test_worker_documents_do_not_absorb_orchestrator_policy(self) -> None:
        docs = account_docs()
        for skill_id in WORKER_SKILL_IDS:
            for marker in ORCHESTRATOR_MARKERS:
                self.assertNotIn(marker, docs[skill_id], f"{skill_id} absorbed {marker!r}")
            self.assertIsNotNone(clause_present(docs[skill_id], (r"stays transport-only and carries no orchestrator policy",)))

    def test_every_document_is_standalone_without_sibling_tree_dependency(self) -> None:
        for stem, text in account_docs().items():
            self.assertNotIn("../", text, stem)
            for other in ACCOUNT_SKILL_NAMES:
                self.assertNotRegex(text, rf"(?<![\w/-])(?:\.\./|skills/){re.escape(other)}\b", f"{stem} depends on {other}")
            for link in set(re.findall(r"\]\((references/[^)#]+)\)", text)):
                self.assertIn(f"## Bundled reference: {link}", text, f"{stem} links {link} without bundling it")
            self.assertNotRegex(text, r"\]\((?:\./)?(?:workers|scripts|agents)/[^)]*\)", stem)
            meta, body = frontmatter(text)
            self.assertEqual(f"---\nname: {meta['name']}\ndescription: {meta['description']}\n---\n{body}", text,
                             f"{stem}: name/description/body must reassemble the file exactly")

    def test_verifier_rejects_ninth_doc_missing_worker_duplicate_name_and_broken_routing(self) -> None:
        verifier = load_verifier()
        self.assertEqual(verifier.validate(HOST_BUNDLE, PROJECT), [])

        def mutated(temporary: str) -> Path:
            bundle = Path(temporary) / HOST_ID
            shutil.copytree(HOST_BUNDLE, bundle)
            return bundle

        def findings_with(label: str, mutate, needle: str, repo: Path | None = None) -> None:
            with tempfile.TemporaryDirectory(prefix="kaola-issue-49-account-") as temporary:
                bundle = mutated(temporary)
                mutate(bundle / "private-skills")
                findings = verifier.validate(bundle, repo)
                self.assertTrue(any(needle in f for f in findings), f"{label}: {findings}")

        def ninth(d: Path) -> None:
            (d / "grok-bot-kaola-project-runner.md").write_text("---\nname: grok-bot-kaola-project-runner\ndescription: x\n---\nbody\n", encoding="utf-8")

        def missing(d: Path) -> None:
            (d / "devin-kaola-project-runner.md").unlink()

        def duplicate(d: Path) -> None:
            p = d / "codex-kaola-project-runner.md"
            p.write_text(p.read_text(encoding="utf-8").replace("name: codex-kaola-project-runner", "name: claude-code-kaola-project-runner", 1), encoding="utf-8")

        def broken_routing(d: Path) -> None:
            p = d / f"{ORCHESTRATOR_ID}.md"
            p.write_text(p.read_text(encoding="utf-8").replace("`opencode-kaola-project-runner`", "`opencode`"), encoding="utf-8")

        def main_absorbs_transport(d: Path) -> None:
            p = d / f"{ORCHESTRATOR_ID}.md"
            p.write_text(p.read_text(encoding="utf-8") + "\n## Communication loop\n", encoding="utf-8")

        def worker_absorbs_policy(d: Path) -> None:
            p = d / "grok-kaola-project-runner.md"
            p.write_text(p.read_text(encoding="utf-8") + "\n## Heartbeat\n", encoding="utf-8")

        def unbundled_reference(d: Path) -> None:
            p = d / "kimi-cli-kaola-project-runner.md"
            p.write_text(p.read_text(encoding="utf-8").replace("## Bundled reference: references/acp.md", "## acp"), encoding="utf-8")

        def lost_location(d: Path) -> None:
            p = d / "cursor-cli-kaola-project-runner.md"
            p.write_text(p.read_text(encoding="utf-8").replace(f'SKILL_DIR="{LOCAL_RUNTIME_COPY}/workers/cursor-cli"', 'SKILL_DIR="/workspace/cursor-cli"'), encoding="utf-8")

        def no_frontmatter(d: Path) -> None:
            p = d / "claude-code-kaola-project-runner.md"
            p.write_text("# no frontmatter\n" + p.read_text(encoding="utf-8"), encoding="utf-8")

        findings_with("ninth document", ninth, "expected exactly 8 account-private Skill documents")
        findings_with("missing worker", missing, "expected exactly 8 account-private Skill documents")
        findings_with("duplicate name", duplicate, "duplicate Skill name 'claude-code-kaola-project-runner'")
        findings_with("broken routing", broken_routing, "does not route to worker Skill opencode-kaola-project-runner")
        findings_with("main absorbs transport", main_absorbs_transport, "main Skill absorbs worker transport")
        findings_with("worker absorbs policy", worker_absorbs_policy, "worker Skill absorbs orchestrator policy")
        findings_with("unbundled reference", unbundled_reference, "links references/acp.md without bundling it")
        findings_with("lost location", lost_location, "missing Local Computer script location for cursor-cli")
        findings_with("no frontmatter", no_frontmatter, "must start with a `---` frontmatter block")
        findings_with("worker drift with repo", lambda d: (d / "devin-kaola-project-runner.md").write_bytes(b"---\nname: devin-kaola-project-runner\ndescription: x\n---\n" + (d / "devin-kaola-project-runner.md").read_bytes()),
                      "does not begin with the canonical contract skills/devin-kaola-project-runner/SKILL.md", PROJECT)

    def test_install_guide_is_repo_based_idempotent_bounded_and_not_a_ninth_skill(self) -> None:
        text = INSTALL_GUIDE.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# "), "guide is prose for Grok Bot, not a Skill document")
        self.assertNotIn(INSTALL_GUIDE.name, [p.name for p in PRIVATE_SKILLS.iterdir()])
        self.assertTrue(GUIDE_TEMPLATE.is_file())
        sources = re.findall(r"hosts/grok-bot/private-skills/([a-z0-9-]+)\.md", text)
        self.assertEqual(sorted(set(sources)), sorted(ACCOUNT_SKILL_NAMES))
        self.assertEqual(len(sources), 8, "one source row per Skill, eight rows")
        for name in ACCOUNT_SKILL_NAMES:
            self.assertIn(f"`{name}`", text)
        for clause in (
            r"for \*\*Grok Bot itself\*\*", r"not a ninth Skill", r"git rev-parse HEAD", r"render-skills\.py --check",
            r"kaola-grok-bot-verify\.py hosts/grok-bot --repo \.", r"one write per file", r"8 calls, one per source file",
            r"`name` and `description` from its frontmatter", r"everything after the closing `---`", r"update it in place",
            r"`description` value is the text \*\*without YAML quotes\*\*", r"never the quotes themselves",
            r"`hosts/grok-bot/private-skills\.json` is that already-resolved value and is the exact string to save",
            r"Never create a second Skill with the same name", r"idempotent", r"no other Skill on the account is touched",
            r"`created`, `updated`, `FAILED \(reason\)`, or `not attempted`", r"repeat step 2 for the failed rows only",
            r"Partial completion is reported as partial", r"Settings > Plugins > Yours lists exactly these 8",
            r"`/` in this Bot offers all 8", r"select that worker by the stable Skill name",
            re.escape(f"{LOCAL_RUNTIME_COPY}/workers/claude-code/scripts/runtime-tmux.sh"), r"install-local\.sh --runtime grok-bot",
            r"never a script on the cloud Agent Computer", r"Never publish or submit any of these Skills to a public Marketplace",
            r"or account credentials", r"Record the exact outcome or gap",
        ):
            self.assertIsNotNone(clause_present(text, (clause,)), clause)
        wrong = authorizes_wrong_move(text, (r"import (?:the |a )?(?:zip|archive)", r"upload (?:the |a )?(?:zip|archive|tree)",
                                             r"publish.{0,40}Marketplace", r"submit.{0,40}Marketplace", r"copy (?:each |every |the )?body by hand"))
        self.assertIsNone(wrong, wrong)
        for token in UNOFFICIAL_API:
            self.assertNotIn(token, text)
        self.assertNotIn("curl ", text)
        self.assertNotIn("token", text.lower())

    def test_local_install_isolation_is_unchanged_by_the_account_documents(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-account-install-") as temporary:
            home = Path(temporary) / "home"
            result = run(["bash", str(INSTALLER), "--runtime", "grok-bot"], PROJECT, sandbox_env(home))
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            dest = home / ".kaola" / HOST_ID / "skills" / ORCHESTRATOR_ID
            self.assertTrue((dest / "SKILL.md").is_file())
            self.assertTrue((dest / "workers" / "codex" / "scripts" / "runtime-tmux.sh").is_file())
            self.assertFalse((dest / "private-skills").exists())
            self.assertFalse((dest / "INSTALL.md").exists())
            self.assertFalse((home / ".kaola" / HOST_ID / "private-skills").exists())
            self.assertEqual(sorted(p.name for p in home.iterdir()), [".kaola"])


class Issue49HostAdapterBoundary(unittest.TestCase):
    """Owner requirement 2026-09-16: one canonical Skill system; Grok Bot is a packaging adapter in the renderer."""

    def load_renderer(self):
        spec = importlib.util.spec_from_file_location("render_skills", RENDERER)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        return module

    def test_grok_bot_is_a_packaging_adapter_not_a_transport_platform(self) -> None:
        renderer = self.load_renderer()
        self.assertFalse((PROJECT / "platforms" / "grok-bot.yaml").exists())
        self.assertFalse((PROJECT / "scripts" / "adapters" / "grok-bot.sh").exists())
        self.assertEqual(sorted(p.name for p in (PROJECT / "templates" / "grok-bot").iterdir()), ["INSTALL.md.tmpl"],
                         "the adapter template dir holds only install prose: no second Skill body")
        inputs = set(renderer.GROK_BOT_ADAPTER_INPUTS)
        self.assertEqual(inputs, {"templates/orchestrator", "templates/SKILL.md.tmpl", "templates/agents", "templates/references",
                                  "platforms", "scripts", "templates/grok-bot"})
        for root in inputs:
            self.assertTrue((PROJECT / root).exists(), root)
        source = RENDERER.read_text(encoding="utf-8")
        adapter_section = source.split("# Host adapter: grok-bot", 1)[1].split("def main()", 1)[0]
        for canonical_only in ("def expected_files(", "def expected_orchestrator_files(", "def parse_manifest("):
            self.assertNotIn(canonical_only, adapter_section, f"{canonical_only} belongs to the canonical system, not the adapter")
        for product in ("def private_skill_documents(", "def private_skill_manifest(", "def install_guide(", "def expected_grok_bot_host_files("):
            self.assertIn(product, adapter_section, product)

    def test_account_documents_carry_no_second_handwritten_body(self) -> None:
        import difflib
        docs = account_docs()
        canonical_root = PROJECT / "skills"
        for name in ACCOUNT_SKILL_NAMES:
            skill_dir = canonical_root / name
            residue = docs[name]
            canonical = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            if name == ORCHESTRATOR_ID:
                # The main document is the same orchestrator template; the only allowed
                # difference from skills/kaola-project-runner/SKILL.md is the host routing
                # block (sibling-directory sentence -> worker Private Skill table).
                head, marker, _ = residue.partition("\n## Grok Bot account-private form")
                self.assertTrue(marker, name)
                a = canonical.rstrip("\n").splitlines()
                b = head.rstrip("\n").splitlines()
                changes = [(tag, a[i1:i2], b[j1:j2]) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes() if tag != "equal"]
                self.assertEqual(len(changes), 1, f"{name}: more than the routing block differs: {changes}")
                tag, removed, added = changes[0]
                self.assertEqual(tag, "replace")
                self.assertIn("In a native skill-directory install the seven workers are sibling Skill", "\n".join(removed))
                self.assertEqual(added[0], "#### Worker Private Skills (Grok Bot account)")
                for skill_id in WORKER_SKILL_IDS:
                    self.assertTrue(any(f"`{skill_id}`" in line and line.startswith("|") for line in added), skill_id)
                residue = marker + residue[len(head) + len(marker):]
            else:
                self.assertTrue(residue.startswith(canonical), name)
                residue = residue[len(canonical):]
            for ref in sorted((skill_dir / "references").glob("*.md")):
                text = ref.read_text(encoding="utf-8").rstrip()
                self.assertIn(text, residue, f"{name}: {ref.name} not bundled verbatim")
                residue = residue.replace(f"## Bundled reference: references/{ref.name}\n\n{text}\n", "", 1)
            residue_lines = [line for line in residue.strip().splitlines() if line.strip()]
            self.assertTrue(residue_lines and residue_lines[0] == "## Grok Bot account-private form", f"{name}: {residue_lines[:3]}")
            self.assertLess(len(residue_lines), 25, f"{name}: adapter section grew beyond a path hint and framing:\n{residue}")
            self.assertEqual([l for l in residue_lines if l.startswith("## ")], ["## Grok Bot account-private form"], name)
            for forbidden in ("mutation_status", "raw_current_frame", "PROJECT_RUNNER_HEARTBEAT", "Allowed CLIs", "--transport"):
                self.assertNotIn(forbidden, residue, f"{name}: adapter section authors canonical semantics ({forbidden})")

    def test_quoted_main_description_is_never_saved_with_its_quotes(self) -> None:
        """Review F3 of 4133601: the main document's frontmatter description is a YAML/JSON-quoted
        scalar (colon-space inside) while the seven workers are bare. Grok Bot saves the resolved
        value: the manifest carries it unquoted, the guide says so, and the verifier refuses a
        manifest that carries the raw quotes."""
        import json
        data = json.loads(PRIVATE_SKILLS_MANIFEST.read_text(encoding="utf-8"))
        manifest_description = {entry["name"]: entry["description"] for entry in data["skills"]}
        docs = account_docs()
        raw_main = frontmatter(docs[ORCHESTRATOR_ID])[0]["description"]
        self.assertTrue(raw_main.startswith('"') and raw_main.endswith('"'), "main frontmatter description is a quoted scalar (F3 premise)")
        for name, text in docs.items():
            raw = frontmatter(text)[0]["description"]
            resolved = json.loads(raw) if raw.startswith('"') else raw
            self.assertFalse(resolved.startswith('"') or resolved.endswith('"'), f"{name}: resolved description keeps YAML quotes")
            self.assertNotIn('\\"', resolved, f"{name}: resolved description keeps JSON escapes")
            self.assertEqual(manifest_description[name], resolved, f"{name}: manifest must carry the resolved description")
        self.assertEqual(manifest_description[ORCHESTRATOR_ID], json.loads(raw_main))
        self.assertNotEqual(manifest_description[ORCHESTRATOR_ID], raw_main, "manifest must not carry the quoted scalar verbatim")
        guide = normalize(INSTALL_GUIDE.read_text(encoding="utf-8"))
        self.assertIn("`description` value is the text **without YAML quotes**", guide)
        self.assertIn("`hosts/grok-bot/private-skills.json` is that already-resolved value and is the exact string to save", guide)
        self.assertIsNone(authorizes_wrong_move(INSTALL_GUIDE.read_text(encoding="utf-8"), (r"including (?:the |its )?quotes", r"with (?:the |its )?(?:surrounding |yaml )?quotes")))
        verifier = load_verifier()
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-quoted-") as temporary:
            bundle = Path(temporary) / HOST_ID
            shutil.copytree(HOST_BUNDLE, bundle)
            manifest = bundle / "private-skills.json"
            edited = json.loads(manifest.read_text(encoding="utf-8"))
            main = next(entry for entry in edited["skills"] if entry["name"] == ORCHESTRATOR_ID)
            main["description"] = raw_main
            manifest.write_text(json.dumps(edited, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            findings = verifier.validate(bundle, None)
            self.assertTrue(any(f"{ORCHESTRATOR_ID}: description does not match the document frontmatter" in f for f in findings), findings)

    def test_fingerprint_manifest_matches_the_documents(self) -> None:
        import json
        data = json.loads(PRIVATE_SKILLS_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["host"], HOST_ID)
        self.assertEqual(data["install_guide"], "INSTALL.md")
        self.assertEqual(data["skill_count"], 8)
        self.assertEqual([entry["name"] for entry in data["skills"]], list(ACCOUNT_SKILL_NAMES))
        docs = account_docs()
        for entry in data["skills"]:
            raw = (PRIVATE_SKILLS / f"{entry['name']}.md").read_bytes()
            meta, body = frontmatter(raw.decode("utf-8"))
            self.assertEqual(entry["source"], f"private-skills/{entry['name']}.md")
            self.assertEqual(entry["file_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(entry["body_sha256"], hashlib.sha256(body.encode("utf-8")).hexdigest())
            self.assertEqual(entry["role"], "orchestrator" if entry["name"] == ORCHESTRATOR_ID else "worker")
            self.assertEqual(entry["platform_id"], None if entry["name"] == ORCHESTRATOR_ID else entry["name"].removesuffix("-kaola-project-runner"))
            description = meta["description"]
            if description.startswith('"'):
                description = json.loads(description)
            self.assertEqual(entry["description"], description)
        verifier = load_verifier()
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-manifest-") as temporary:
            bundle = Path(temporary) / HOST_ID
            shutil.copytree(HOST_BUNDLE, bundle)
            manifest = bundle / "private-skills.json"
            edited = json.loads(manifest.read_text(encoding="utf-8"))
            edited["skills"][2]["file_sha256"] = "0" * 64
            manifest.write_text(json.dumps(edited, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            findings = verifier.validate(bundle, None)
            self.assertTrue(any("file_sha256 does not match" in f for f in findings), findings)
            del edited["skills"][2]
            edited["skill_count"] = 7
            manifest.write_text(json.dumps(edited, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            findings = verifier.validate(bundle, None)
            self.assertTrue(any("must fingerprint exactly" in f for f in findings), findings)

    def test_canonical_source_changes_propagate_to_every_account_product(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-49-propagate-") as temporary:
            copy = copy_repo(temporary)
            renderer = copy / "scripts" / "render-skills.py"
            edits = {
                copy / "templates" / "SKILL.md.tmpl": "\nCanonical worker sentence 7f3a.\n",
                copy / "templates" / "references" / "acp.md.tmpl": "\nCanonical acp sentence 9c1d.\n",
                copy / "templates" / "orchestrator" / "SKILL.md.tmpl": "\nCanonical orchestrator sentence 4e2b.\n",
                copy / "templates" / "orchestrator" / "references" / "grok-bot-host.md": "\nCanonical host reference sentence 5d6f.\n",
            }
            for path, suffix in edits.items():
                path.write_text(path.read_text(encoding="utf-8") + suffix, encoding="utf-8")
            manifest_path = copy / "platforms" / "codex.yaml"
            manifest_path.write_text(re.sub(
                r'(?m)^description: "', 'description: "Canonical codex description 8a9b. ',
                manifest_path.read_text(encoding="utf-8"), count=1), encoding="utf-8")
            stale = run([sys.executable, str(renderer), "--check"], copy)
            self.assertNotEqual(stale.returncode, 0)
            for product in ("private-skills/kaola-project-runner.md", "private-skills/codex-kaola-project-runner.md",
                            "private-skills/grok-kaola-project-runner.md", "private-skills.json", f"{ORCHESTRATOR_ID}/SKILL.md"):
                self.assertIn(f"stale {product}", stale.stderr, product)
            written = run([sys.executable, str(renderer), "--write"], copy)
            self.assertEqual(written.returncode, 0, written.stderr)
            docs = {p.stem: p.read_text(encoding="utf-8") for p in (copy / "hosts" / HOST_ID / "private-skills").glob("*.md")}
            for skill_id in WORKER_SKILL_IDS:
                self.assertIn("Canonical worker sentence 7f3a.", docs[skill_id], skill_id)
                self.assertIn("Canonical acp sentence 9c1d.", docs[skill_id], skill_id)
            self.assertIn("Canonical codex description 8a9b.", docs["codex-kaola-project-runner"].split("---", 2)[1])
            self.assertIn("Canonical codex description 8a9b.", (copy / "hosts" / HOST_ID / "private-skills.json").read_text(encoding="utf-8"))
            self.assertIn("Canonical orchestrator sentence 4e2b.", docs[ORCHESTRATOR_ID])
            self.assertIn("Canonical host reference sentence 5d6f.", docs[ORCHESTRATOR_ID])
            self.assertNotIn("Canonical orchestrator sentence 4e2b.", docs["codex-kaola-project-runner"])
            self.assertNotIn("Canonical worker sentence 7f3a.", docs[ORCHESTRATOR_ID])
            verified = run([sys.executable, str(copy / "scripts" / "kaola-grok-bot-verify.py"), str(copy / "hosts" / HOST_ID), "--repo", str(copy)], copy)
            self.assertEqual(verified.returncode, 0, verified.stderr)


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
