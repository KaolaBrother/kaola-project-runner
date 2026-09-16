#!/usr/bin/env python3
"""Issue #49 acceptance: Grok Bot is a bridge host with ONE thin account Skill.

Owner corrections of 2026-09-16 (Issue #49): progressive disclosure is a locked,
platform-neutral invariant, and Grok Bot receives exactly one very small
account/cloud Skill named ``kaola-project-runner`` (the bridge) generated into
``hosts/grok-bot/``. The bridge names the repository, the accepted pinned
revision, the device-local locator command ``kaola-project-runner-locate``, and
the two canonical entry paths; it binds the execution target first (Local
Computer or the cloud Agent Computer), never assumes one target can reach the
other, never installs on Local Computer from the cloud, and loads only the main
Skill and, at dispatch, one selected worker from the verified checkout on that
target. It carries no canonical body, reference, transport, path convention,
runtime copy, per-worker account Skills, or credential handling. The locator
(``scripts/kaola-locate.py``, registered as a bin link the way ``--bin-links``
already does) produces the fail-closed host-target attestation. Seven
platforms, not an eighth; ``templates/grok-golden/`` frozen; nothing here claims
live Grok Bot adoption -- the owner's read-only Local Computer UAT is the boundary.
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
INSTALLER = PROJECT / "scripts" / "install-local.sh"
VERIFIER = PROJECT / "scripts" / "kaola-grok-bot-verify.py"
LOCATOR = PROJECT / "scripts" / "kaola-locate.py"
ORCHESTRATOR_ID = "kaola-project-runner"
HOST_ID = "grok-bot"
HOST_BUNDLE = PROJECT / "hosts" / HOST_ID
BRIDGE = HOST_BUNDLE / f"{ORCHESTRATOR_ID}.md"
MANIFEST = HOST_BUNDLE / "bridge.json"
INSTALL_GUIDE = HOST_BUNDLE / "INSTALL.md"
GROK_BOT_TEMPLATES = PROJECT / "templates" / HOST_ID
ACCEPTED_REVISION = GROK_BOT_TEMPLATES / "accepted-revision.json"
BUDGETS = json.loads((PROJECT / "templates" / "budgets.json").read_text(encoding="utf-8"))
WORKER_IDS = ("claude-code", "codex", "cursor-cli", "devin", "grok", "kimi-cli", "opencode")
WORKER_SKILL_IDS = tuple(f"{wid}-kaola-project-runner" for wid in WORKER_IDS)
LOCATOR_COMMAND = "kaola-project-runner-locate"
EXPECTED_ORIGIN = "github.com/KaolaBrother/kaola-project-runner"
UNOFFICIAL_API = ("GrokBotService", "EnsureSandBox", "SAND_GATEWAY", "sand-host", "grokbot-sdk", "aiserver.v1", "/local-exec/")
TRANSPORT_MARKERS = ("## Transport facts", "## Communication loop", 'runtime-tmux.sh" send', 'runtime-tmux.sh" observe',
                     'runtime-tmux.sh" capture', 'runtime-tmux.sh" key', "mutation_status", "raw_current_frame", "--transport acp|pty", "SKILL_DIR=")
ORCHESTRATOR_MARKERS = ("PROJECT_RUNNER_HEARTBEAT", "## Heartbeat", "## Main execution loop", "Allowed CLIs", "Needs attention",
                        "Routine", "Mission-frontier", "Accept the delivery", "## Authorization", "## Ending a run", "## Bundled reference")
PATH_PATTERNS = (r"\$HOME", r"~/", r"/Users/", r"/home/", r"/workspace", r"/Volumes/", r"KAOLA_GROK_BOT_HOME", r"current ->",
                 r"\bln -s\b", r"checkouts/", r"\.kaola/", r"\.local/bin", r"WORKER\.md", r"runtime copy", r"private-skills")
CREDENTIAL_PATTERNS = (r"GH_TOKEN", r"GITHUB_TOKEN", r"x-access-token", r"Authorization", r"--show-token", r"credential\.helper",
                       r"GIT_ASKPASS", r"http\.extraheader", r"://[^/\s]+@")
REMOVED_SURFACES = ("KAOLA_GROK_BOT_HOME", "private-skills.json", "hosts/grok-bot/private-skills", "kaola-grok-bot-package",
                    "--runtime grok-bot", "hosts/grok-bot/kaola-project-runner/", "workers/<id>/WORKER.md", "embedded as a supporting resource")
COPY_IGNORE = shutil.ignore_patterns(".git", ".kw", "__pycache__", "node_modules", "build")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def run(argv: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, env=env)


def git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> str:
    base = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
                GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    if env:
        base.update(env)
    completed = subprocess.run(["git", "-C", str(cwd), *args], text=True, capture_output=True, env=base)
    if completed.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {completed.stderr}")
    return completed.stdout.strip()


def copy_repo(temporary: str) -> Path:
    destination = Path(temporary) / "repo"
    shutil.copytree(PROJECT, destination, ignore=COPY_IGNORE)
    return destination


def render(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(root / "scripts" / "render-skills.py"), *args], root)


def verify(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(root / "scripts" / "kaola-grok-bot-verify.py"), str(root / "hosts" / HOST_ID), *args], root)


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.split("\n")
    assert lines[0] == "---", "single-Markdown Skill must start with frontmatter"
    end = lines.index("---", 1)
    meta = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = json.loads(value)
        meta[key.strip()] = value
    return meta, "\n".join(lines[end + 1:])


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


def markdown_tree(root: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(root.rglob("*.md")))


def canonical_sentences() -> set[str]:
    sentences: set[str] = set()
    for path in sorted((PROJECT / "skills").rglob("*.md")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = normalize(raw)
            if len(line) >= 40 and not line.startswith(("|", "```", "#", "-", "name:", "description:")):
                sentences.add(line)
    return sentences


class LocatorFixture:
    """A bare 'origin' plus a clone that carries scripts/kaola-locate.py, no network."""

    def __init__(self, temporary: str, origin_url: str | None = None) -> None:
        self.base = Path(temporary)
        self.bare = self.base / "origin.git"
        self.bare.mkdir()
        git(self.bare, "init", "--bare", "-q")
        seed = self.base / "seed"
        seed.mkdir()
        git(seed, "init", "-q")
        (seed / "scripts").mkdir()
        shutil.copy2(LOCATOR, seed / "scripts" / "kaola-locate.py")
        (seed / "platforms").mkdir()
        (seed / "platforms" / "claude-code.yaml").write_text("id: \"claude-code\"\n", encoding="utf-8")
        worker = seed / "skills" / "claude-code-kaola-project-runner" / "scripts"
        worker.mkdir(parents=True)
        (worker / "runtime-tmux.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (worker / "runtime-tmux.sh").chmod(0o755)
        git(seed, "add", "-A")
        git(seed, "commit", "-q", "-m", "seed")
        git(seed, "push", "-q", str(self.bare), "HEAD:refs/heads/main")
        self.revision = git(seed, "rev-parse", "HEAD")
        self.checkout = self.base / "work dir with spaces" / "kaola-project-runner"
        self.checkout.parent.mkdir(parents=True)
        git(self.base, "clone", "-q", str(self.bare), str(self.checkout))
        git(self.checkout, "remote", "set-url", "origin", origin_url or f"https://github.com/KaolaBrother/kaola-project-runner.git")
        git(self.checkout, "checkout", "-q", "--detach", self.revision)
        self.project = self.base / "consumer project"
        self.project.mkdir()
        git(self.project, "init", "-q")
        (self.project / "README").write_text("consumer\n", encoding="utf-8")
        git(self.project, "add", "-A")
        git(self.project, "commit", "-q", "-m", "consumer")

    def locate(self, *args: str, env: dict[str, str] | None = None) -> tuple[int, dict]:
        base = dict(os.environ, HOME=str(self.base / "home"), GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
        if env:
            base.update(env)
        completed = subprocess.run([sys.executable, str(self.checkout / "scripts" / "kaola-locate.py"), *args],
                                   text=True, capture_output=True, env=base, cwd=str(self.base))
        assert completed.stdout.strip(), completed.stderr
        return completed.returncode, json.loads(completed.stdout)


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

    def test_runtime_grok_and_grok_bot_are_not_installer_destinations(self) -> None:
        for alias in ("grok", "grok-bot", "grokbot"):
            result = run(["bash", str(INSTALLER), "--runtime", alias, "--platform", "codex"], PROJECT)
            self.assertNotEqual(result.returncode, 0, alias)
            combined = result.stderr + result.stdout
            self.assertRegex(combined, rf"unknown runtime:\s*{re.escape(alias)}")
            self.assertIn("bridge host", combined)
            self.assertIn("--platform grok", combined)
        installer = INSTALLER.read_text(encoding="utf-8")
        self.assertNotIn("KAOLA_GROK_BOT_HOME", installer)
        self.assertIsNone(re.search(r"(?m)^\s*grok-bot\)\s*printf", installer))

    def test_golden_is_frozen_and_no_generated_hand_edits(self) -> None:
        golden = PROJECT / "templates" / "grok-golden"
        self.assertEqual(len([p for p in golden.rglob("*") if p.is_file()]), 12)
        result = render(PROJECT, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("budgets OK", result.stdout)


class Issue49SingleBridge(unittest.TestCase):
    def setUp(self) -> None:
        self.text = BRIDGE.read_text(encoding="utf-8")
        self.meta, self.body = frontmatter(self.text)

    def test_bundle_is_exactly_one_bridge_manifest_and_guide(self) -> None:
        self.assertEqual(sorted(p.name for p in HOST_BUNDLE.iterdir()),
                         sorted([".generated-by-kaola-project-runner", f"{ORCHESTRATOR_ID}.md", "bridge.json", "INSTALL.md"]))
        self.assertFalse((HOST_BUNDLE / "private-skills").exists())
        self.assertFalse((HOST_BUNDLE / ORCHESTRATOR_ID).exists(), "no runtime copy")
        self.assertEqual(list(HOST_BUNDLE.rglob("SKILL.md")), [])
        self.assertEqual(list(HOST_BUNDLE.rglob("WORKER.md")), [])
        self.assertFalse((PROJECT / "scripts" / "kaola-grok-bot-package.py").exists())

    def test_bridge_identity_budget_and_revision(self) -> None:
        self.assertEqual(self.meta["name"], ORCHESTRATOR_ID)
        self.assertLessEqual(len(self.meta["description"]), BUDGETS["description_chars"])
        self.assertLessEqual(len(self.text.encode("utf-8")), BUDGETS["bridge_bytes"])
        revisions = re.findall(r"\b[0-9a-f]{40}\b", self.text)
        self.assertEqual(len(revisions), 1)
        accepted = json.loads(ACCEPTED_REVISION.read_text(encoding="utf-8"))
        self.assertEqual(revisions[0], accepted["commit"])
        self.assertIn(f"release {accepted['release']}", self.text)
        self.assertIn("KaolaBrother/kaola-project-runner", self.text)
        self.assertIn(EXPECTED_ORIGIN, self.text)
        self.assertIn(f"`{LOCATOR_COMMAND}`", self.text)
        self.assertIn(f"`ROOT/skills/{ORCHESTRATOR_ID}/SKILL.md`", self.text)
        self.assertIn(f"`ROOT/skills/<platform>-{ORCHESTRATOR_ID}/SKILL.md`", self.text)

    def test_bridge_binds_target_first_and_never_crosses_hosts(self) -> None:
        lowered = normalize(self.body).lower()
        bind = lowered.find("bind the execution target first")
        locate = lowered.find(f"`{LOCATOR_COMMAND}`")
        load = lowered.find(f"load `root/skills/{ORCHESTRATOR_ID}/skill.md`")
        self.assertTrue(0 <= bind < locate < load, "target binding must precede the locator, which precedes loading")
        self.assertIn("local computer", lowered)
        self.assertIn("cloud agent computer", lowered)
        self.assertIn("nothing on one target is reachable from the other", lowered)
        self.assertIn("never clone, install, update, or change anything on local computer", lowered)
        self.assertIn("only on the cloud target may you fetch", lowered)
        self.assertIn("consumer project root (a separate path on the same target)", lowered)
        self.assertIn("on the same target; never read script source", lowered)
        self.assertIn("never enter, print, or pass a token", lowered)
        wrong = authorizes_wrong_move(self.body, (r"clone .{0,40}on local computer", r"install .{0,40}on the mac", r"search the filesystem"))
        self.assertIsNone(wrong, wrong)

    def test_bridge_carries_no_canonical_transport_reference_or_path_content(self) -> None:
        for marker in TRANSPORT_MARKERS + ORCHESTRATOR_MARKERS:
            self.assertNotIn(marker, self.text, marker)
        for pattern in PATH_PATTERNS:
            self.assertIsNone(re.search(pattern, self.text), pattern)
        for pattern in CREDENTIAL_PATTERNS:
            self.assertIsNone(re.search(pattern, self.text, flags=re.IGNORECASE), pattern)
        self.assertIsNone(re.search(r"\]\((?:\./)?(?:references|workers|scripts|agents)/", self.text))
        bridge_lines = {normalize(line) for line in self.text.splitlines()}
        self.assertEqual(sorted(bridge_lines & canonical_sentences()), [], "no canonical sentence may be copied into the bridge")
        for name in WORKER_SKILL_IDS:
            self.assertNotIn(name, self.text, "only the selected `<platform>` placeholder is named at dispatch")
        self.assertLess(len(self.text), len((PROJECT / "skills" / ORCHESTRATOR_ID / "SKILL.md").read_text(encoding="utf-8")) / 5)

    def test_manifest_fingerprints_the_bridge(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        raw = BRIDGE.read_bytes()
        self.assertEqual(data["skill_count"], 1)
        self.assertEqual(data["host"], HOST_ID)
        self.assertEqual(data["locator"], LOCATOR_COMMAND)
        self.assertEqual(data["repository"], EXPECTED_ORIGIN)
        self.assertEqual(data["accepted_commit"], json.loads(ACCEPTED_REVISION.read_text(encoding="utf-8"))["commit"])
        skill = data["skill"]
        self.assertEqual(skill["name"], ORCHESTRATOR_ID)
        self.assertEqual(skill["description"], self.meta["description"])
        self.assertFalse(skill["description"].startswith('"'))
        self.assertEqual(skill["bytes"], len(raw))
        self.assertEqual(skill["file_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(skill["body_sha256"], hashlib.sha256(self.body.encode("utf-8")).hexdigest())

    def test_guide_is_one_write_read_only_mac_uat_and_not_a_skill(self) -> None:
        text = INSTALL_GUIDE.read_text(encoding="utf-8")
        self.assertFalse(text.startswith("---"))
        self.assertLessEqual(len(text.encode("utf-8")), BUDGETS["bridge_guide_bytes"])
        self.assertEqual(set(re.findall(r"hosts/grok-bot/([a-z0-9-]+)\.md", text)), {ORCHESTRATOR_ID})
        lowered = normalize(text).lower()
        for clause in ("exactly one", "one write", "update it in place", "no_supported_path", "execution on local computer",
                       "never clones, installs, updates, or manages anything on the mac", "kaola-locate.py\" register",
                       f"{LOCATOR_COMMAND} --target local --expect-revision", "--target cloud", "read-only preflight",
                       "nothing was started, sent, stopped, cloned, fetched, checked out, or installed",
                       "cloud agent computer executed nothing", "never publish this skill to a public or team marketplace"):
            self.assertIn(clause, lowered, clause)
        for stale in REMOVED_SURFACES:
            self.assertNotIn(stale, text, stale)
        for pattern in CREDENTIAL_PATTERNS:
            self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE), pattern)
        wrong = authorizes_wrong_move(text, (r"cloud .{0,30}(?:clone|install|update).{0,40}(?:mac|local computer)", r"publish.{0,40}marketplace"))
        self.assertIsNone(wrong, wrong)

    def test_verifier_passes_generated_state_and_rejects_drift(self) -> None:
        self.assertEqual(verify(PROJECT, "--repo", ".").returncode, 0)
        with tempfile.TemporaryDirectory() as temporary:
            root = copy_repo(temporary)
            bundle = root / "hosts" / HOST_ID
            bridge = bundle / f"{ORCHESTRATOR_ID}.md"
            cases = {
                "extra-doc": lambda: (bundle / "claude-code-kaola-project-runner.md").write_text("---\nname: x\n---\nx\n", encoding="utf-8"),
                "hand-edit": lambda: bridge.write_text(bridge.read_text(encoding="utf-8") + "\nextra sentence.\n", encoding="utf-8"),
                "two-revisions": lambda: bridge.write_text(bridge.read_text(encoding="utf-8") + "\n" + "0" * 40 + "\n", encoding="utf-8"),
                "fixed-path": lambda: bridge.write_text(bridge.read_text(encoding="utf-8").replace("ROOT/skills", "$HOME/.kaola/ROOT/skills"), encoding="utf-8"),
                "credential": lambda: bridge.write_text(bridge.read_text(encoding="utf-8") + "\nexport GH_TOKEN=... before cloning.\n", encoding="utf-8"),
                "canonical-copy": lambda: bridge.write_text(bridge.read_text(encoding="utf-8") + "\n## Communication loop\n", encoding="utf-8"),
                "worker-named": lambda: bridge.write_text(bridge.read_text(encoding="utf-8").replace("<platform>-", "claude-code-", 1), encoding="utf-8"),
                "runtime-copy": lambda: ((bundle / ORCHESTRATOR_ID).mkdir(), (bundle / ORCHESTRATOR_ID / "SKILL.md").write_text("x", encoding="utf-8")),
                "manifest-stale": lambda: (bundle / "bridge.json").write_text((bundle / "bridge.json").read_text(encoding="utf-8").replace('"bytes": ', '"bytes": 1'), encoding="utf-8"),
            }
            original = bridge.read_bytes()
            for label, mutate in cases.items():
                bridge.write_bytes(original)
                shutil.rmtree(bundle / ORCHESTRATOR_ID, ignore_errors=True)
                (bundle / "claude-code-kaola-project-runner.md").unlink(missing_ok=True)
                render(root, "--write")
                mutate()
                self.assertNotEqual(verify(root, "--repo", ".").returncode, 0, label)
                self.assertNotEqual(render(root, "--check").returncode, 0, label)


class Issue49BridgeInvariance(unittest.TestCase):
    def test_accepted_revision_changes_exactly_one_line_and_canonical_edits_change_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = copy_repo(temporary)
            bridge = root / "hosts" / HOST_ID / f"{ORCHESTRATOR_ID}.md"
            self.assertEqual(render(root, "--write").returncode, 0)
            before = bridge.read_text(encoding="utf-8").splitlines()
            # Canonical edits: orchestrator body, worker template, a worker reference, a manifest.
            for relative, marker in (("templates/orchestrator/SKILL.md.tmpl", "\n\nCanonical policy sentence added for the invariance test.\n"),
                                     ("templates/SKILL.md.tmpl", "\n\nCanonical transport sentence added for the invariance test.\n"),
                                     ("templates/references/transport.md.tmpl", "\n\nReference sentence added for the invariance test.\n"),
                                     ("templates/orchestrator/references/grok-bot-host.md", "\n\nHost reference sentence added for the invariance test.\n")):
                path = root / relative
                path.write_text(path.read_text(encoding="utf-8") + marker, encoding="utf-8")
            self.assertEqual(render(root, "--write").returncode, 0)
            self.assertEqual(bridge.read_text(encoding="utf-8").splitlines(), before, "canonical edits must not touch the bridge")
            self.assertIn("Canonical policy sentence", (root / "skills" / ORCHESTRATOR_ID / "SKILL.md").read_text(encoding="utf-8"))
            # Accepted revision: exactly one line of the bridge changes.
            accepted = root / "templates" / HOST_ID / "accepted-revision.json"
            data = json.loads(accepted.read_text(encoding="utf-8"))
            data["commit"] = "f" * 40
            data["release"] = "v9.9.9"
            accepted.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(render(root, "--write").returncode, 0)
            after = bridge.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(before), len(after))
            changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
            self.assertEqual(len(changed), 1, f"expected exactly one changed line, got {changed}")
            self.assertIn("f" * 40, after[changed[0]])
            self.assertIn("v9.9.9", after[changed[0]])
            self.assertEqual(verify(root, "--repo", ".").returncode, 0)

    def test_renderer_refuses_a_non_40_hex_revision_or_over_budget_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = copy_repo(temporary)
            accepted = root / "templates" / HOST_ID / "accepted-revision.json"
            data = json.loads(accepted.read_text(encoding="utf-8"))
            for bad in ("main", "v0.2.3", "ba3d14f", "G" * 40):
                data["commit"] = bad
                accepted.write_text(json.dumps(data) + "\n", encoding="utf-8")
                result = render(root, "--check")
                self.assertNotEqual(result.returncode, 0, bad)
                self.assertIn("40-hex", result.stderr)
            data["commit"] = "a" * 40
            accepted.write_text(json.dumps(data) + "\n", encoding="utf-8")
            template = root / "templates" / HOST_ID / "bridge.md.tmpl"
            template.write_text(template.read_text(encoding="utf-8") + "\n" + ("padding " * 400) + "\n", encoding="utf-8")
            result = render(root, "--write")
            self.assertNotEqual(result.returncode, 0)
            self.assertRegex(result.stderr, r"budget: grok-bot/kaola-project-runner\.md is \d+ B > \d+ B \(bridge_bytes\)")


class Issue49LocatorAttestation(unittest.TestCase):
    def test_receipt_is_ok_bounded_and_credential_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary, origin_url="https://user:secret@github.com/KaolaBrother/kaola-project-runner.git")
            rc, receipt = fx.locate("--target", "local", "--expect-revision", fx.revision, "--project", str(fx.project),
                                    "--worker", "claude-code", "--session", "kaola-issue-49-no-such-session")
            self.assertEqual(rc, 0, receipt)
            self.assertEqual(receipt["result"], "ok")
            self.assertEqual(receipt["target"], "local")
            self.assertEqual(receipt["root"]["origin"], EXPECTED_ORIGIN)
            self.assertEqual(receipt["root"]["head"], fx.revision)
            self.assertTrue(receipt["root"]["clean"] and receipt["root"]["revision_match"])
            self.assertEqual(Path(receipt["root"]["path"]), fx.checkout.resolve())
            self.assertEqual(Path(receipt["project"]["toplevel"]), fx.project.resolve())
            self.assertEqual(receipt["worker"]["script"], "skills/claude-code-kaola-project-runner/scripts/runtime-tmux.sh")
            self.assertTrue(receipt["worker"]["under_root"] and receipt["worker"]["executable"])
            self.assertEqual(receipt["session"]["name"], "kaola-issue-49-no-such-session")
            self.assertIn(receipt["session"]["present"], (False, None))
            self.assertIn("fingerprint", receipt["host"])
            line = json.dumps(receipt)
            self.assertLessEqual(len(line.encode("utf-8")), BUDGETS["locator_receipt_bytes"])
            self.assertNotIn("secret", line)
            self.assertNotIn("user:", line)
            self.assertNotIn("@github", line)

    def test_fails_closed_on_origin_revision_dirty_and_unknown_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            rc, receipt = fx.locate("--target", "local", "--expect-revision", "0" * 40)
            self.assertEqual(rc, 1)
            self.assertIn("revision-mismatch", receipt["reasons"])
            rc, receipt = fx.locate("--target", "local", "--worker", "bogus")
            self.assertIn("worker-unknown", receipt["reasons"])
            rc, receipt = fx.locate("--expect-revision", "abc")
            self.assertIn("expect-revision-not-40-hex", receipt["reasons"])
            rc, receipt = fx.locate("--project", str(fx.project))
            self.assertIn("target-required", receipt["reasons"])
            (fx.checkout / "scratch.txt").write_text("dirty\n", encoding="utf-8")
            rc, receipt = fx.locate("--target", "local")
            self.assertEqual(receipt["result"], "refused")
            self.assertIn("dirty", receipt["reasons"])
            (fx.checkout / "scratch.txt").unlink()
            git(fx.checkout, "remote", "set-url", "origin", "https://github.com/someone-else/kaola-project-runner.git")
            rc, receipt = fx.locate("--target", "local")
            self.assertIn("origin-mismatch", receipt["reasons"])
            self.assertNotIn("someone-else/kaola-project-runner.git", json.dumps(receipt).replace(receipt["root"]["origin"], ""))

    def test_rejects_cross_host_paths_in_both_directions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            # A cloud Agent Computer path handed to a Local Computer dispatch is not on this host.
            rc, receipt = fx.locate("--target", "local", "--expect-revision", fx.revision, "--project", "/workspace/consumer-project",
                                    "--worker", "claude-code", "--session", "s")
            self.assertEqual(receipt["result"], "refused")
            self.assertIn("project-not-on-this-host", receipt["reasons"])
            self.assertFalse(receipt["project"]["on_this_host"])
            # A Mac path handed to a cloud dispatch is likewise not on that host.
            rc, receipt = fx.locate("--target", "cloud", "--expect-revision", fx.revision, "--project", "/Users/owner/projects/consumer",
                                    "--worker", "claude-code", "--session", "s")
            self.assertEqual(receipt["result"], "refused")
            self.assertIn("project-not-on-this-host", receipt["reasons"])
            # A relative path is never accepted as a project identity.
            rc, receipt = fx.locate("--target", "local", "--project", "consumer project")
            self.assertIn("project-not-on-this-host", receipt["reasons"])
            # A non-git directory has no project identity.
            plain = fx.base / "plain"
            plain.mkdir()
            rc, receipt = fx.locate("--target", "cloud", "--project", str(plain))
            self.assertIn("project-not-a-checkout", receipt["reasons"])

    def test_worker_script_must_live_under_the_same_canonical_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            script = fx.checkout / "skills" / "claude-code-kaola-project-runner" / "scripts" / "runtime-tmux.sh"
            outside = fx.base / "elsewhere.sh"
            outside.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            outside.chmod(0o755)
            script.unlink()
            script.symlink_to(outside)
            rc, receipt = fx.locate("--target", "local", "--worker", "claude-code")
            self.assertIn("script-outside-root", receipt["reasons"])
            script.unlink()
            rc, receipt = fx.locate("--target", "local", "--worker", "claude-code")
            self.assertIn("script-missing", receipt["reasons"])

    def test_register_links_the_locator_and_rediscovery_follows_a_moved_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            bin_dir = fx.base / "bin dir"
            rc, receipt = fx.locate("register", "--bin-dir", str(bin_dir))
            self.assertEqual(rc, 0, receipt)
            link = bin_dir / LOCATOR_COMMAND
            self.assertTrue(link.is_symlink())
            self.assertEqual(Path(os.readlink(link)), (fx.checkout / "scripts" / "kaola-locate.py").resolve())
            self.assertFalse(receipt["locator"]["replaced"])
            # The link is the whole locator: running it resolves the same ROOT.
            completed = subprocess.run([sys.executable, str(link), "--target", "local", "--expect-revision", fx.revision],
                                       text=True, capture_output=True, env=dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null"))
            via_link = json.loads(completed.stdout)
            self.assertEqual(via_link["result"], "ok", via_link)
            self.assertEqual(Path(via_link["root"]["path"]), fx.checkout.resolve())
            # Path change = re-registration from the new location; no Skill changes.
            moved = fx.base / "moved checkout"
            shutil.move(str(fx.checkout), str(moved))
            stale = subprocess.run([sys.executable, str(link)], text=True, capture_output=True)
            self.assertNotEqual(stale.returncode, 0)
            completed = subprocess.run([sys.executable, str(moved / "scripts" / "kaola-locate.py"), "register", "--bin-dir", str(bin_dir)],
                                       text=True, capture_output=True, env=dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null"))
            receipt = json.loads(completed.stdout)
            self.assertEqual(receipt["result"], "ok", receipt)
            self.assertTrue(receipt["locator"]["replaced"])
            self.assertEqual(Path(os.readlink(link)), (moved / "scripts" / "kaola-locate.py").resolve())
            # A foreign link or file at the locator path is never replaced.
            link.unlink()
            link.symlink_to(fx.base / "foreign")
            completed = subprocess.run([sys.executable, str(moved / "scripts" / "kaola-locate.py"), "register", "--bin-dir", str(bin_dir)],
                                       text=True, capture_output=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("foreign-locator-link", completed.stdout)
            self.assertEqual(Path(os.readlink(link)), fx.base / "foreign")

    def test_locator_has_no_credential_handling_or_filesystem_scan(self) -> None:
        text = LOCATOR.read_text(encoding="utf-8")
        code = text.split('"""', 2)[2]  # module docstring describes what the locator is not
        for pattern in CREDENTIAL_PATTERNS:
            self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE), pattern)
        self.assertIn('"GIT_TERMINAL_PROMPT": "0"', code)
        for forbidden in ("os.walk(", "rglob(", ".glob(", "mdfind", "import socket", "import http", "urllib", "daemon"):
            self.assertNotIn(forbidden, code, forbidden)
        self.assertIn("kaola-project-runner-locate", INSTALLER.read_text(encoding="utf-8"))


class Issue49OrchestratorSemantics(unittest.TestCase):
    def orchestrator_text(self) -> str:
        text = markdown_tree(PROJECT / "skills" / ORCHESTRATOR_ID)
        self.assertTrue(text.strip())
        return text

    def test_main_skill_names_bridge_hosts_target_binding_and_attestation(self) -> None:
        text = self.orchestrator_text()
        self.assertIsNotNone(clause_present(text, (r"Grok Bot is a host", r"Grok Bot.{0,60}host, not a worker")))
        self.assertIsNotNone(clause_present(text, (r"not an eighth platform",)))
        self.assertIsNotNone(clause_present(text, (r"--platform grok.{0,40}Grok CLI worker",)))
        self.assertIsNotNone(clause_present(text, (r"binds an execution target first",)))
        self.assertIsNotNone(clause_present(text, (rf"`{LOCATOR_COMMAND}`",)))
        self.assertIsNotNone(clause_present(text, (rf"--target local\|cloud --expect-revision",)))
        self.assertIsNotNone(clause_present(text, (r"never reach each other's files, CLIs, tmux, or sessions",)))
        self.assertIsNotNone(clause_present(text, (r"nothing clones, installs, or updates Local Computer from the cloud",)))
        self.assertIsNotNone(clause_present(text, (rf"one selected `ROOT/skills/<platform id>-{ORCHESTRATOR_ID}`",)))
        reference = (PROJECT / "skills" / ORCHESTRATOR_ID / "references" / "grok-bot-host.md").read_text(encoding="utf-8")
        self.assertIsNotNone(clause_present(reference, (r"project-not-on-this-host",)))
        self.assertIsNotNone(clause_present(reference, (r"A cloud path on a Local Computer dispatch, or a Mac path on a cloud dispatch",)))
        for stale in REMOVED_SURFACES + ("eight account-private Skills", "one single Markdown"):
            self.assertNotIn(stale, text, stale)

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
        self.assertIsNotNone(clause_present(combined, (r"read-only.{0,40}Local Computer UAT", r"not live adoption")))
        self.assertIsNotNone(clause_present(combined, (r"NO_SUPPORTED_PATH",)))
        wrong = authorizes_wrong_move(combined, (r"(?:bridge|payload) (?:means|proves) live Grok Bot adoption", r"Grok Bot 0\.51.{0,40}(?:is proven to|automatically) load"))
        self.assertIsNone(wrong, wrong)

    def test_no_unofficial_sand_api_in_host_surfaces(self) -> None:
        surfaces = [BRIDGE, INSTALL_GUIDE, PROJECT / "skills" / ORCHESTRATOR_ID / "SKILL.md", PROJECT / "templates" / "orchestrator" / "SKILL.md.tmpl",
                    PROJECT / "templates" / "orchestrator" / "references" / "grok-bot-host.md", PROJECT / "docs" / "grok-bot-host.md", INSTALLER, RENDERER, LOCATOR]
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            for token in UNOFFICIAL_API:
                self.assertNotIn(token, text, f"{path}: {token}")


class Issue49HostAdapterBoundary(unittest.TestCase):
    def test_grok_bot_is_a_packaging_adapter_with_adapter_only_inputs(self) -> None:
        renderer = RENDERER.read_text(encoding="utf-8")
        self.assertIn("# Host adapter: grok-bot", renderer)
        inputs = re.search(r"GROK_BOT_ADAPTER_INPUTS = \((.*?)\)\n", renderer, flags=re.DOTALL)
        self.assertIsNotNone(inputs)
        declared = re.findall(r'"([^"]+)"', inputs.group(1))
        self.assertEqual(declared, ["templates/grok-bot"], "the bridge is rendered from adapter prose only; no canonical source is copied")
        self.assertEqual(sorted(p.name for p in GROK_BOT_TEMPLATES.iterdir()), ["INSTALL.md.tmpl", "accepted-revision.json", "bridge.md.tmpl"])
        self.assertFalse((PROJECT / "platforms" / "grok-bot.yaml").exists())
        self.assertFalse((PROJECT / "scripts" / "adapters" / "grok-bot.sh").exists())
        for name in ("embedded_worker_files", "private_skill_documents", "worker_private_skill", "bundled_references", "GROK_BOT_HOME", "LOCAL_RUNTIME_COPY"):
            self.assertNotIn(name, renderer, name)

    def test_removed_surfaces_are_gone_everywhere(self) -> None:
        roots = [PROJECT / "scripts", PROJECT / "templates", PROJECT / "docs", PROJECT / "README.md", PROJECT / "CHANGELOG.md",
                 PROJECT / "AGENTS.md", PROJECT / "skills", PROJECT / "hosts", PROJECT / "tests" / "contract" / "test-installer-runtimes.sh"]
        offenders: list[str] = []
        for root in roots:
            files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file() and p.suffix in {".md", ".py", ".sh", ".tmpl", ".json", ".yaml"}]
            for path in files:
                if "grok-golden" in path.parts or path.name in {"kaola-grok-bot-verify.py", "test-issue-49-grok-bot-host.py"}:
                    continue  # these list the removed strings as forbidden patterns
                text = path.read_text(encoding="utf-8", errors="replace")
                for stale in ("KAOLA_GROK_BOT_HOME", "private-skills.json", "kaola-grok-bot-package", "workers/<id>/WORKER.md",
                              "embedded as a supporting resource"):
                    if stale in text and not (path == PROJECT / "CHANGELOG.md" and "removed" in text.lower()):
                        offenders.append(f"{path.relative_to(PROJECT)}: {stale}")
                for line in text.splitlines():
                    if path.name == "CHANGELOG.md":
                        break  # the changelog records the removal itself
                    if "--runtime grok-bot" in line and not re.search(r"refused|no `--runtime grok-bot`|removed", line):
                        offenders.append(f"{path.relative_to(PROJECT)}: --runtime grok-bot offered: {line.strip()[:60]}")
        self.assertEqual(offenders, [])


class Issue49WorkerIsolation(unittest.TestCase):
    def test_workers_do_not_absorb_grok_bot_host_policy(self) -> None:
        forbidden = ("Grok Bot", "grok-bot", "Needs attention", "Private Skill", "Settings → Plugins", "kaola-project-runner-locate",
                     "PROJECT_RUNNER_HEARTBEAT", "Mission-frontier done triggers review, not automatic finalize", "WORKER.md")
        templates = PROJECT / "templates"
        surfaces: list[tuple[str, str]] = []
        for path in sorted(templates.rglob("*")):
            if path.is_file() and path.relative_to(templates).parts[0] not in {"grok-golden", "orchestrator", "grok-bot"} and path.suffix in {".tmpl", ".md"}:
                surfaces.append((path.relative_to(templates).as_posix(), path.read_text(encoding="utf-8")))
        for skill_id in WORKER_SKILL_IDS:
            surfaces.append((f"skills/{skill_id}/SKILL.md", (PROJECT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")))
        for label, raw in surfaces:
            body = normalize(raw)
            for marker in forbidden:
                self.assertNotIn(normalize(marker), body, f"{label} gained host/orchestrator policy: {marker!r}")

    def test_each_worker_is_a_separate_skill_and_main_embeds_none(self) -> None:
        main = (PROJECT / "skills" / ORCHESTRATOR_ID / "SKILL.md").read_text(encoding="utf-8")
        for marker in ("## Communication loop", 'runtime-tmux.sh" send', "mutation_status", "SKILL_DIR="):
            self.assertNotIn(marker, main, marker)
        self.assertFalse((PROJECT / "skills" / ORCHESTRATOR_ID / "workers").exists())
        for skill_id in WORKER_SKILL_IDS:
            skill = PROJECT / "skills" / skill_id / "SKILL.md"
            self.assertTrue(skill.is_file())
            text = skill.read_text(encoding="utf-8")
            self.assertRegex(text, rf"(?m)^name: {re.escape(skill_id)}$")
            self.assertNotIn(text, main)


if __name__ == "__main__":
    unittest.main()
