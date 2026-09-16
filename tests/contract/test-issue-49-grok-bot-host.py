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
already does) produces the fail-closed host-target attestation; ``--target`` is
the Agent's declaration (the script cannot prove physical host kind), so the
real safety is device-local execution, the host fingerprint compared with the
value recorded at registration, and root/project/script co-location on the
executing host. Mission 8 (review FAIL of ``fb65c51``): the bridge follows an
honest two-commit content/pin model (content commit R at stage ``content``,
pin commit P naming R at stage ``pinned``) whose pin is proven by ``--check``,
the verifier, and ``Issue49PinModel``. Seven platforms, not an eighth;
``templates/grok-golden/`` frozen; nothing here claims live Grok Bot adoption --
the owner's read-only Local Computer UAT is the boundary.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
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
    """A plain copy (no .git): a pin cannot be verified here, so the copy starts at the content stage."""
    destination = Path(temporary) / "repo"
    shutil.copytree(PROJECT, destination, ignore=COPY_IGNORE)
    (destination / "templates" / HOST_ID / "accepted-revision.json").write_text('{"stage": "content"}\n', encoding="utf-8")
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


NEGATION_BEFORE = re.compile(r"\b(do not|don't|never|must not|cannot|not|no|refuse[sd]?|without)\b[^.;:]{0,60}$", re.IGNORECASE)


def authorizes_wrong_move(text: str, patterns: tuple[str, ...]) -> str | None:
    """The first sentence that states a forbidden move without a negation right before it.

    A sentence is exempt only where a negation precedes the matched phrase within the
    same clause (``never clone ... on Local Computer``); a negation elsewhere in the
    sentence, or a word such as ``only``, does not exempt it.
    """
    for raw in re.split(r"(?<=[.!?])\s+|\n+", text):
        sentence = normalize(raw)
        if not sentence:
            continue
        for pattern in patterns:
            for match in re.finditer(pattern, sentence, flags=re.IGNORECASE):
                if not NEGATION_BEFORE.search(sentence[:match.start()]):
                    return sentence
    return None


def git_repo(temporary: str) -> tuple[Path, str]:
    """A copy of the project as a real Git checkout (one content-stage commit), for pin tests.

    The copy is re-rendered at the content stage before its first commit, so the fixture is
    the same whether the project itself currently sits at a content or a pinned stage: a
    content commit holds content-stage products, which is what the pin gate demands of R.
    """
    root = copy_repo(temporary)
    written = render(root, "--write")
    assert written.returncode == 0, written.stderr
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "content")
    return root, git(root, "rev-parse", "HEAD")


def set_stage(root: Path, stage: str, commit: str | None = None, label: str | None = None, release: str | None = None) -> None:
    data: dict[str, object] = {"stage": stage}
    if commit is not None:
        data["commit"] = commit
    if label is not None:
        data["label"] = label
    if release is not None:
        data["release"] = release
    (root / "templates" / HOST_ID / "accepted-revision.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def host_products(root: Path) -> dict[str, bytes]:
    bundle = root / "hosts" / HOST_ID
    return {name: (bundle / name).read_bytes() for name in (f"{ORCHESTRATOR_ID}.md", "bridge.json", "INSTALL.md")}


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

        self.bin = self.base / "bin dir"

    def locate(self, *args: str, env: dict[str, str] | None = None) -> tuple[int, dict]:
        base = dict(os.environ, HOME=str(self.base / "home"), GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
        if env:
            base.update(env)
        completed = subprocess.run([sys.executable, str(self.checkout / "scripts" / "kaola-locate.py"), *args],
                                   text=True, capture_output=True, env=base, cwd=str(self.base))
        assert completed.stdout.strip(), completed.stderr
        return completed.returncode, json.loads(completed.stdout)

    def register(self, *args: str, target: str = "local") -> tuple[int, dict]:
        """register --target into the fixture bin directory (the owner-chosen directory on PATH)."""
        return self.locate("register", "--target", target, "--bin-dir", str(self.bin), *args)

    def attest(self, *args: str) -> tuple[int, dict]:
        """A direct script call that names the registration directory explicitly."""
        return self.locate(*args, "--bin-dir", str(self.bin))

    def via_link(self, *args: str) -> tuple[int, dict]:
        """Run the registered link itself in a fresh process: a fresh conversation with no memory."""
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(self.base / "home"),
               "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
        completed = subprocess.run([sys.executable, str(self.bin / LOCATOR_COMMAND), *args],
                                   text=True, capture_output=True, env=env, cwd=str(self.base))
        assert completed.stdout.strip(), completed.stderr
        return completed.returncode, json.loads(completed.stdout)

    @property
    def registration(self) -> Path:
        return self.bin / f".{LOCATOR_COMMAND}.json"


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
        accepted = json.loads(ACCEPTED_REVISION.read_text(encoding="utf-8"))
        self.assertIn(accepted["stage"], ("content", "pinned"))
        if accepted["stage"] == "content":
            # Content commit R: no pin yet, and the bridge says so instead of pretending.
            self.assertEqual(revisions, [])
            self.assertIn("Accepted revision: none yet", self.text)
            self.assertIn("do not save it to any account", self.text)
            self.assertNotIn("commit", accepted)
        else:
            self.assertEqual(len(revisions), 1)
            self.assertEqual(revisions[0], accepted["commit"])
            tag = f"release {accepted['release']}" if accepted.get("release") else accepted["label"]
            self.assertIn(f"Accepted revision: `{accepted['commit']}` ({tag}).", self.text)
            self.assertNotIn("do not save it to any account", self.text)
        self.assertIn("`--target` only echoes your declaration", self.text)
        self.assertIn("host fingerprint", self.text)
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
        accepted = json.loads(ACCEPTED_REVISION.read_text(encoding="utf-8"))
        self.assertEqual(data["stage"], accepted["stage"])
        self.assertEqual(data["accepted_commit"], accepted.get("commit"))
        self.assertEqual(data["release"], accepted.get("release"))
        self.assertEqual(data["label"], accepted.get("label"))
        self.assertEqual(data["saveable"], accepted["stage"] == "pinned")
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
                       "never clones, installs, updates, or manages anything on the mac",
                       "kaola-locate.py\" register --target local --bin-dir \"$bin\" --expect-revision",
                       f"{LOCATOR_COMMAND} --target local --expect-revision", "--target cloud", "read-only preflight",
                       # Mission 9: cloud registration mirrors Local Computer; the registration receipt; UAT bin directory.
                       "register --target cloud --bin-dir", "registration receipt", f"$bin/.{LOCATOR_COMMAND}.json",
                       "owner-selected persistent directory on path", "installer-managed `--bin-links` link is left alone",
                       "install-local.sh --bin-links", "fresh conversation needs no memory", "link and receipt stay device-local",
                       "presence only, not existence elsewhere",
                       # Mission 9: never rewrite an accepted pair; release and rollback shape.
                       "never rebase, squash, or amend an accepted r/p pair", "create a fresh r and p", "a release is a tag at r",
                       "rollback is a new p naming an older r", "one-line bridge diff",
                       "nothing was started, sent, stopped, cloned, fetched, checked out, or installed",
                       "cloud agent computer executed nothing", "never publish this skill to a public or team marketplace",
                       # Two-commit model and the honest UAT checkout (Mission 8).
                       "two commits", "content commit r", "pin commit p", "--check --require-pinned", "save the bridge **from p**",
                       "untracked workflow records", "git worktree add --detach <owner-chosen path>", "do not assume any fixed path",
                       "must not be saved",
                       # Target kind, fingerprint, session presence, path evidence (security cut).
                       "`--target` is the agent's declaration", "host.fingerprint", "ownership is proven by the worker preflight",
                       "may include the user's home", "none of it enters the account skill", "refused registration leaves an existing locator unchanged"):
            self.assertIn(clause, lowered, clause)
        for stale in REMOVED_SURFACES:
            self.assertNotIn(stale, text, stale)
        # The guide is rendered from adapter prose only: no worker id, Skill name, or runtime name may leak in.
        for wid in WORKER_IDS:
            self.assertNotIn(f"{wid}-{ORCHESTRATOR_ID}", text, f"guide names worker Skill {wid}; use the <platform id> placeholder")
            self.assertIsNone(re.search(rf"--worker {re.escape(wid)}\b", text), wid)
            if wid != "grok":  # "grok" is a substring of the host name grok-bot
                self.assertNotIn(wid, text, wid)
        for runtime in ("Claude Code", "Codex", "Cursor", "Devin", "Kimi", "OpenCode", "Grok CLI"):
            self.assertNotIn(runtime, text, runtime)
        self.assertIn("<platform id>", text)
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
            cases["content-stage-revision"] = lambda: bridge.write_text(
                bridge.read_text(encoding="utf-8").replace("Accepted revision: none yet.", "Accepted revision: `" + "a" * 40 + "` (v0.0.0)."), encoding="utf-8")
            original = bridge.read_bytes()
            for label, mutate in cases.items():
                bridge.write_bytes(original)
                shutil.rmtree(bundle / ORCHESTRATOR_ID, ignore_errors=True)
                (bundle / "claude-code-kaola-project-runner.md").unlink(missing_ok=True)
                written = render(root, "--write")
                self.assertEqual(written.returncode, 0, f"{label}: baseline write must succeed: {written.stderr}")
                self.assertEqual(verify(root, "--repo", ".").returncode, 0, f"{label}: baseline must verify")
                mutate()
                self.assertNotEqual(verify(root, "--repo", ".").returncode, 0, label)
                self.assertNotEqual(render(root, "--check").returncode, 0, label)


class Issue49BridgeInvariance(unittest.TestCase):
    def test_pin_changes_exactly_one_line_and_canonical_or_manifest_edits_change_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, content = git_repo(temporary)
            set_stage(root, "content")
            bridge = root / "hosts" / HOST_ID / f"{ORCHESTRATOR_ID}.md"
            self.assertEqual(render(root, "--write").returncode, 0)
            before_products = host_products(root)
            before = bridge.read_text(encoding="utf-8").splitlines()
            # Canonical edits: orchestrator body, worker template, a worker reference, a host reference,
            # and a platform manifest (the adapter reads no manifest: all three products stay identical).
            for relative, marker in (("templates/orchestrator/SKILL.md.tmpl", "\n\nCanonical policy sentence added for the invariance test.\n"),
                                     ("templates/SKILL.md.tmpl", "\n\nCanonical transport sentence added for the invariance test.\n"),
                                     ("templates/references/transport.md.tmpl", "\n\nReference sentence added for the invariance test.\n"),
                                     ("templates/orchestrator/references/grok-bot-host.md", "\n\nHost reference sentence added for the invariance test.\n")):
                path = root / relative
                path.write_text(path.read_text(encoding="utf-8") + marker, encoding="utf-8")
            manifest = root / "platforms" / "claude-code.yaml"
            manifest.write_text(re.sub(r'(?m)^runtime_name: ".*"$', 'runtime_name: "Renamed Runtime"', manifest.read_text(encoding="utf-8")), encoding="utf-8")
            self.assertEqual(render(root, "--write").returncode, 0)
            self.assertEqual(host_products(root), before_products, "canonical and manifest edits must not touch any host product")
            self.assertIn("Canonical policy sentence", (root / "skills" / ORCHESTRATOR_ID / "SKILL.md").read_text(encoding="utf-8"))
            self.assertIn("Renamed Runtime", (root / "skills" / "claude-code-kaola-project-runner" / "SKILL.md").read_text(encoding="utf-8"))
            # The pin gate demands a tree that differs from R only by the pin itself, so the canonical
            # experiments above are reverted (and the workers re-rendered) before pinning.
            git(root, "checkout", "-q", "--", ".")
            self.assertEqual(render(root, "--write").returncode, 0)
            self.assertEqual(git(root, "status", "--porcelain"), "")
            # Pin commit P: pinning the content commit changes exactly one line of the bridge.
            set_stage(root, "pinned", commit=content, label="pre-release UAT candidate; not a release")
            written = render(root, "--write")
            self.assertEqual(written.returncode, 0, written.stderr)
            after = bridge.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(before), len(after))
            changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
            self.assertEqual(len(changed), 1, f"expected exactly one changed line, got {changed}")
            self.assertIn(content, after[changed[0]])
            self.assertIn("pre-release UAT candidate; not a release", after[changed[0]])
            self.assertIn("none yet", before[changed[0]])
            self.assertEqual(verify(root, "--repo", ".", "--require-pinned").returncode, 0)
            self.assertEqual(render(root, "--check", "--require-pinned").returncode, 0)
            manifest_data = json.loads((root / "hosts" / HOST_ID / "bridge.json").read_text(encoding="utf-8"))
            self.assertEqual((manifest_data["stage"], manifest_data["accepted_commit"], manifest_data["saveable"]), ("pinned", content, True))
            # Re-pinning to another content commit again changes exactly one line.
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "pin")
            set_stage(root, "content")
            (root / "docs" / "README.md").write_text((root / "docs" / "README.md").read_text(encoding="utf-8") + "\nSecond content commit.\n", encoding="utf-8")
            self.assertEqual(render(root, "--write").returncode, 0)
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "content 2")
            second = git(root, "rev-parse", "HEAD")
            set_stage(root, "pinned", commit=second, label="second candidate")
            self.assertEqual(render(root, "--write").returncode, 0)
            again = bridge.read_text(encoding="utf-8").splitlines()
            changed = [i for i, (a, b) in enumerate(zip(after, again)) if a != b]
            self.assertEqual(len(changed), 1)
            self.assertIn(second, again[changed[0]])

    def test_renderer_refuses_a_non_40_hex_revision_or_over_budget_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = copy_repo(temporary)
            accepted = root / "templates" / HOST_ID / "accepted-revision.json"
            for bad in ("main", "v0.2.3", "ba3d14f", "G" * 40):
                set_stage(root, "pinned", commit=bad, label="candidate")
                result = render(root, "--check")
                self.assertNotEqual(result.returncode, 0, bad)
                self.assertIn("40-hex", result.stderr)
            set_stage(root, "pinned", commit="a" * 40)
            self.assertIn("exactly one of release", render(root, "--check").stderr)
            set_stage(root, "pinned", commit="a" * 40, label="x", release="v1.0.0")
            self.assertIn("exactly one of release", render(root, "--check").stderr)
            for masquerade in ("release v1.0.0", "Release candidate", "v1.2.3 candidate", "candidate for v0.3.0"):
                set_stage(root, "pinned", commit="a" * 40, label=masquerade)
                self.assertIn("must not masquerade as a release", render(root, "--check").stderr, masquerade)
            set_stage(root, "content", commit="a" * 40)
            self.assertIn("content stage carries no commit", render(root, "--check").stderr)
            accepted.write_text(json.dumps({"stage": "released"}) + "\n", encoding="utf-8")
            self.assertIn("stage must be one of", render(root, "--check").stderr)
            set_stage(root, "content")
            template = root / "templates" / HOST_ID / "bridge.md.tmpl"
            template.write_text(template.read_text(encoding="utf-8") + "\n" + ("padding " * 400) + "\n", encoding="utf-8")
            result = render(root, "--write")
            self.assertNotEqual(result.returncode, 0)
            self.assertRegex(result.stderr, r"budget: grok-bot/kaola-project-runner\.md is \d+ B > \d+ B \(bridge_bytes\)")


class Issue49PinModel(unittest.TestCase):
    """The pinned stage is proven against the Git checkout, by the renderer, the verifier, and here."""

    def check_findings(self, root: Path) -> str:
        result = render(root, "--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(verify(root, "--repo", ".").returncode, 0, "the verifier runs the same pin gate")
        return result.stderr

    def test_content_stage_is_not_saveable_and_require_pinned_refuses_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _ = git_repo(temporary)
            set_stage(root, "content")
            self.assertEqual(render(root, "--write").returncode, 0)
            check = render(root, "--check")
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("content stage, unpinned (not saveable)", check.stdout)
            self.assertEqual(verify(root, "--repo", ".").returncode, 0)
            gated = render(root, "--check", "--require-pinned")
            self.assertNotEqual(gated.returncode, 0)
            self.assertIn("--require-pinned demands a pinned", gated.stderr)
            self.assertNotEqual(verify(root, "--repo", ".", "--require-pinned").returncode, 0)
            self.assertNotEqual(verify(root, "--require-pinned").returncode, 0, "shape-only mode also refuses a content-stage bundle")

    def test_pin_gate_requires_existing_ancestor_complete_content_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, content = git_repo(temporary)
            # Not in this checkout.
            set_stage(root, "pinned", commit="f" * 40, label="candidate")
            self.assertIn("does not exist in this checkout", self.check_findings(root))
            # Present but missing the locator and a worker entry path.
            git(root, "rm", "-q", "scripts/kaola-locate.py", "skills/claude-code-kaola-project-runner/SKILL.md")
            set_stage(root, "content")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "incomplete")
            incomplete = git(root, "rev-parse", "HEAD")
            git(root, "checkout", "-q", content, "--", "scripts/kaola-locate.py", "skills/claude-code-kaola-project-runner/SKILL.md")
            set_stage(root, "pinned", commit=incomplete, label="candidate")
            stderr = self.check_findings(root)
            self.assertIn("lacks scripts/kaola-locate.py", stderr)
            self.assertIn("lacks skills/claude-code-kaola-project-runner/SKILL.md", stderr)
            # Not an ancestor of HEAD: a commit on an abandoned branch.
            git(root, "checkout", "-q", "-b", "side")
            set_stage(root, "content")
            (root / "docs" / "README.md").write_text("side\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "side")
            side = git(root, "rev-parse", "HEAD")
            git(root, "checkout", "-q", "-")
            git(root, "checkout", "-q", content, "--", "scripts/kaola-locate.py", "skills/claude-code-kaola-project-runner/SKILL.md")
            set_stage(root, "pinned", commit=side, label="candidate")
            self.assertIn("is not an ancestor of HEAD", self.check_findings(root))
            # The original content commit is an ancestor and complete: the gate passes and P can be committed.
            set_stage(root, "pinned", commit=content, label="pre-release UAT candidate")
            written = render(root, "--write")
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertIn(f"pinned at {content[:12]}, pin verified", written.stdout)
            self.assertEqual(render(root, "--check", "--require-pinned").returncode, 0)
            self.assertEqual(verify(root, "--repo", ".", "--require-pinned").returncode, 0)
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "pin")
            pin = git(root, "rev-parse", "HEAD")
            self.assertEqual(render(root, "--check", "--require-pinned").returncode, 0, "the pin still verifies from P itself")
            # A pin commit is not an honest target: pinning P (or any non-content-stage commit) is refused.
            set_stage(root, "pinned", commit=pin, label="candidate")
            self.assertIn("is not a content-stage commit", self.check_findings(root))
            # A named release must be a tag at the pinned commit.
            set_stage(root, "pinned", commit=content, release="v9.9.9")
            self.assertIn("release v9.9.9 is not a tag at", self.check_findings(root))
            git(root, "tag", "v9.9.9", pin)
            self.assertIn("release v9.9.9 is not a tag at", self.check_findings(root))
            git(root, "tag", "-d", "v9.9.9")
            git(root, "tag", "v9.9.9", content)
            self.assertEqual(render(root, "--write").returncode, 0)
            self.assertIn(f"(release v9.9.9).", (root / "hosts" / HOST_ID / f"{ORCHESTRATOR_ID}.md").read_text(encoding="utf-8"))
            self.assertEqual(verify(root, "--repo", ".", "--require-pinned").returncode, 0)

    def test_pinned_stage_cannot_be_verified_outside_a_git_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = copy_repo(temporary)
            set_stage(root, "pinned", commit="a" * 40, label="candidate")
            result = render(root, "--check")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot be verified", result.stderr)
            self.assertNotEqual(render(root, "--write").returncode, 0, "an unverifiable pin is never written")

    def test_pin_gate_enforces_the_p_delta_and_the_one_line_bridge_diff(self) -> None:
        """P may differ from R only by the accepted revision and the three generated products."""
        with tempfile.TemporaryDirectory() as temporary:
            root, content = git_repo(temporary)
            bundle = root / "hosts" / HOST_ID
            set_stage(root, "pinned", commit=content, label="candidate")
            self.assertEqual(render(root, "--write").returncode, 0)
            self.assertEqual(render(root, "--check", "--require-pinned").returncode, 0)
            self.assertEqual(sorted(line.split(None, 1)[1] for line in git(root, "status", "--porcelain").splitlines()),
                             sorted(["hosts/grok-bot/INSTALL.md", "hosts/grok-bot/bridge.json", f"hosts/grok-bot/{ORCHESTRATOR_ID}.md",
                                     "templates/grok-bot/accepted-revision.json"]))
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "pin")
            pin = git(root, "rev-parse", "HEAD")
            self.assertEqual(render(root, "--check", "--require-pinned").returncode, 0)
            # Any other tracked change in the tree under test is refused, before and after the pin commit.
            readme = root / "docs" / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nstray edit\n", encoding="utf-8")
            stderr = self.check_findings(root)
            self.assertIn("P may differ from", stderr)
            self.assertIn("found docs/README.md", stderr)
            self.assertNotEqual(render(root, "--write").returncode, 0, "an unverifiable pin is never written")
            git(root, "checkout", "-q", "--", "docs/README.md")
            self.assertEqual(render(root, "--check", "--require-pinned").returncode, 0)
            # A pair merged with an advanced main carries main's paths: refused.
            git(root, "checkout", "-q", "-b", "main-moved", content)
            (root / "docs" / "moved.md").write_text("main moved\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "main moved")
            git(root, "checkout", "-q", "-")
            git(root, "merge", "-q", "--no-edit", "main-moved")
            stderr = self.check_findings(root)
            self.assertIn("found docs/moved.md", stderr)
            git(root, "reset", "-q", "--hard", pin)
            # A rebase of the pair onto the moved main is refused the same way (the accepted R is unchanged).
            git(root, "rebase", "-q", "main-moved")
            stderr = self.check_findings(root)
            self.assertIn("found docs/moved.md", stderr)
            git(root, "reset", "-q", "--hard", pin)
            # A squash of R and P into one commit no longer has R as an ancestor.
            git(root, "checkout", "-q", "--orphan", "squashed")
            git(root, "commit", "-q", "-m", "squash")
            self.assertIn("is not an ancestor of HEAD", self.check_findings(root))
            git(root, "checkout", "-q", "-f", "master") if git(root, "branch", "--list", "master") else git(root, "checkout", "-q", "-f", "main")
            git(root, "reset", "-q", "--hard", pin)
            self.assertEqual(render(root, "--check", "--require-pinned").returncode, 0)
            # The bridge may differ from R's bridge by exactly the accepted-revision line: a content commit
            # whose committed bridge is stale (hand-edited) cannot be pinned.
            set_stage(root, "content")
            self.assertEqual(render(root, "--write").returncode, 0)
            bridge = bundle / f"{ORCHESTRATOR_ID}.md"
            bridge.write_text(bridge.read_text(encoding="utf-8") + "\nhand-edited line\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "content with a stale bridge")
            stale = git(root, "rev-parse", "HEAD")
            bridge.write_bytes(bridge.read_bytes().replace(b"\nhand-edited line\n", b""))
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "content repaired")
            set_stage(root, "pinned", commit=stale, label="candidate")
            stderr = self.check_findings(root)
            self.assertIn("exactly one line", stderr)

    def test_project_stage_is_consistent_with_its_own_checkout(self) -> None:
        accepted = json.loads(ACCEPTED_REVISION.read_text(encoding="utf-8"))
        check = render(PROJECT, "--check")
        self.assertEqual(check.returncode, 0, check.stderr)
        if accepted["stage"] == "pinned":
            self.assertEqual(render(PROJECT, "--check", "--require-pinned").returncode, 0)
            self.assertEqual(git(PROJECT, "merge-base", "--is-ancestor", accepted["commit"], "HEAD"), "")
            tree = git(PROJECT, "ls-tree", "-r", "--name-only", accepted["commit"]).splitlines()
            for path in ("scripts/kaola-locate.py", f"skills/{ORCHESTRATOR_ID}/SKILL.md", *(f"skills/{sid}/SKILL.md" for sid in WORKER_SKILL_IDS),
                         *(f"skills/{sid}/scripts/runtime-tmux.sh" for sid in WORKER_SKILL_IDS)):
                self.assertIn(path, tree, path)
            pinned = json.loads(git(PROJECT, "show", f"{accepted['commit']}:templates/grok-bot/accepted-revision.json"))
            self.assertEqual(pinned["stage"], "content", "the pinned commit is a content commit, never a self-pin")
            delta = set(git(PROJECT, "diff", "--name-only", accepted["commit"], "HEAD").splitlines())
            self.assertTrue(delta <= {"templates/grok-bot/accepted-revision.json", f"hosts/grok-bot/{ORCHESTRATOR_ID}.md",
                                      "hosts/grok-bot/bridge.json", "hosts/grok-bot/INSTALL.md"}, delta)
        else:
            self.assertIn("content stage, unpinned", check.stdout)


class Issue49LocatorAttestation(unittest.TestCase):
    def test_receipt_is_ok_bounded_and_credential_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary, origin_url="https://user:secret@github.com/KaolaBrother/kaola-project-runner.git")
            rc, registered = fx.register("--expect-revision", fx.revision)
            self.assertEqual(rc, 0, registered)
            rc, receipt = fx.via_link("--target", "local", "--expect-revision", fx.revision, "--project", str(fx.project),
                                      "--worker", "claude-code", "--session", "kaola-issue-49-no-such-session")
            self.assertEqual(rc, 0, receipt)
            self.assertEqual(receipt["result"], "ok")
            self.assertEqual(receipt["target"], "local")
            self.assertEqual(receipt["registration"]["path"], str(fx.registration))
            self.assertTrue(all(receipt["registration"][key] for key in ("present", "fingerprint_match", "target_match", "root_match", "revision_current")))
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
            stored = fx.registration.read_text(encoding="utf-8")
            for leak in ("secret", "user:", "@github", platform.node()):
                if leak:
                    self.assertNotIn(leak, stored, "the registration receipt is credential-free and names no host")

    def test_fails_closed_on_origin_revision_dirty_and_unknown_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            self.assertEqual(fx.register("--expect-revision", fx.revision)[0], 0)
            rc, receipt = fx.attest("--target", "local", "--expect-revision", "0" * 40)
            self.assertEqual(rc, 1)
            self.assertEqual(receipt["reasons"], ["revision-mismatch"])
            rc, receipt = fx.attest("--target", "local", "--worker", "bogus")
            self.assertEqual(receipt["reasons"], ["worker-unknown"])
            rc, receipt = fx.attest("--expect-revision", "abc")
            self.assertIn("expect-revision-not-40-hex", receipt["reasons"])
            rc, receipt = fx.attest("--project", str(fx.project))
            self.assertIn("target-required", receipt["reasons"])
            (fx.checkout / "scratch.txt").write_text("dirty\n", encoding="utf-8")
            rc, receipt = fx.attest("--target", "local")
            self.assertEqual(receipt["result"], "refused")
            self.assertEqual(receipt["reasons"], ["dirty"])
            (fx.checkout / "scratch.txt").unlink()
            git(fx.checkout, "remote", "set-url", "origin", "https://github.com/someone-else/kaola-project-runner.git")
            rc, receipt = fx.attest("--target", "local")
            self.assertIn("origin-mismatch", receipt["reasons"])
            self.assertNotIn("someone-else/kaola-project-runner.git", json.dumps(receipt).replace(receipt["root"]["origin"], ""))

    def test_paths_absent_on_the_executing_host_are_refused_and_the_declared_target_must_match_the_registration(self) -> None:
        """--target is echoed, never inferred: the script cannot tell a Mac from a cloud computer.

        What binds the declaration is the registration receipt: a target other than the
        registered one is refused, and a path that does not exist here is refused whatever
        target was declared.
        """
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            self.assertEqual(fx.register("--expect-revision", fx.revision)[0], 0)
            for declared, absent in (("local", "/workspace/consumer-project"), ("cloud", "/Users/owner/projects/consumer")):
                rc, receipt = fx.via_link("--target", declared, "--expect-revision", fx.revision, "--project", absent,
                                          "--worker", "claude-code", "--session", "s")
                self.assertEqual(receipt["result"], "refused")
                self.assertEqual(receipt["target"], declared, "the declaration is echoed as given")
                self.assertIn("project-not-on-this-host", receipt["reasons"])
                self.assertFalse(receipt["project"]["on_this_host"])
            self.assertIn("target-mismatch", receipt["reasons"], "cloud was declared but local was registered")
            # The same real path is accepted under the registered declaration only.
            rc, receipt = fx.via_link("--target", "local", "--expect-revision", fx.revision, "--project", str(fx.project))
            self.assertEqual(receipt["result"], "ok", receipt)
            rc, receipt = fx.via_link("--target", "cloud", "--expect-revision", fx.revision, "--project", str(fx.project))
            self.assertEqual(receipt["reasons"], ["target-mismatch"])
            self.assertFalse(receipt["registration"]["target_match"])
            # A relative path is never accepted as a project identity.
            rc, receipt = fx.via_link("--target", "local", "--project", "consumer project")
            self.assertIn("project-not-on-this-host", receipt["reasons"])
            # A non-git directory has no project identity.
            plain = fx.base / "plain"
            plain.mkdir()
            rc, receipt = fx.via_link("--target", "local", "--project", str(plain))
            self.assertIn("project-not-a-checkout", receipt["reasons"])

    def test_worker_script_must_live_under_the_same_canonical_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            script = fx.checkout / "skills" / "claude-code-kaola-project-runner" / "scripts" / "runtime-tmux.sh"
            outside = fx.base / "elsewhere.sh"
            outside.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            outside.chmod(0o755)
            self.assertEqual(fx.register("--expect-revision", fx.revision)[0], 0)
            script.unlink()
            script.symlink_to(outside)
            rc, receipt = fx.via_link("--target", "local", "--worker", "claude-code")
            self.assertIn("script-outside-root", receipt["reasons"])
            script.unlink()
            rc, receipt = fx.via_link("--target", "local", "--worker", "claude-code")
            self.assertIn("script-missing", receipt["reasons"])

    def test_register_links_the_locator_and_rediscovery_follows_a_moved_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            bin_dir = fx.bin
            rc, receipt = fx.register("--expect-revision", fx.revision)
            self.assertEqual(rc, 0, receipt)
            link = bin_dir / LOCATOR_COMMAND
            self.assertTrue(link.is_symlink())
            self.assertEqual(Path(os.readlink(link)), (fx.checkout / "scripts" / "kaola-locate.py").resolve())
            self.assertFalse(receipt["locator"]["replaced"])
            self.assertTrue(receipt["registration"]["changed"] and not receipt["registration"]["replaced"])
            self.assertEqual(json.loads(fx.registration.read_text(encoding="utf-8"))["root"], str(fx.checkout.resolve()))
            # The link is the whole locator: running it resolves the same ROOT.
            rc, via_link = fx.via_link("--target", "local", "--expect-revision", fx.revision)
            self.assertEqual(via_link["result"], "ok", via_link)
            self.assertEqual(Path(via_link["root"]["path"]), fx.checkout.resolve())
            # Path change = re-registration from the new location; no Skill changes.
            moved = fx.base / "moved checkout"
            shutil.move(str(fx.checkout), str(moved))
            stale = subprocess.run([sys.executable, str(link)], text=True, capture_output=True)
            self.assertNotEqual(stale.returncode, 0)
            completed = subprocess.run([sys.executable, str(moved / "scripts" / "kaola-locate.py"), "register", "--target", "local", "--bin-dir", str(bin_dir), "--expect-revision", fx.revision],
                                       text=True, capture_output=True, env=dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null"))
            receipt = json.loads(completed.stdout)
            self.assertEqual(receipt["result"], "ok", receipt)
            self.assertTrue(receipt["locator"]["replaced"] and receipt["registration"]["replaced"])
            self.assertEqual(Path(os.readlink(link)), (moved / "scripts" / "kaola-locate.py").resolve())
            self.assertEqual(json.loads(fx.registration.read_text(encoding="utf-8"))["root"], str(moved.resolve()))
            # A foreign link or file at the locator path is never replaced, and the receipt stays as it was.
            recorded = fx.registration.read_bytes()
            link.unlink()
            link.symlink_to(fx.base / "foreign")
            completed = subprocess.run([sys.executable, str(moved / "scripts" / "kaola-locate.py"), "register", "--target", "local", "--bin-dir", str(bin_dir), "--expect-revision", fx.revision],
                                       text=True, capture_output=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("foreign-locator-link", completed.stdout)
            self.assertEqual(Path(os.readlink(link)), fx.base / "foreign")
            self.assertEqual(fx.registration.read_bytes(), recorded)
            # register without --target is not a registration at all.
            completed = subprocess.run([sys.executable, str(moved / "scripts" / "kaola-locate.py"), "register", "--bin-dir", str(bin_dir)],
                                       text=True, capture_output=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("--target", completed.stderr)

    def test_register_validates_every_fact_before_touching_an_existing_locator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            bin_dir = fx.bin
            rc, receipt = fx.register("--expect-revision", fx.revision)
            self.assertEqual(rc, 0, receipt)
            self.assertTrue(receipt["locator"]["changed"])
            link = bin_dir / LOCATOR_COMMAND
            good = os.readlink(link)
            good_receipt = fx.registration.read_bytes()
            # A second checkout of the same origin must not take the link over while it is dirty,
            # at the wrong revision, or at a foreign origin; the good link stays exactly as it was.
            other = fx.base / "other checkout"
            git(fx.base, "clone", "-q", str(fx.bare), str(other))
            git(other, "checkout", "-q", "--detach", fx.revision)
            git(other, "remote", "set-url", "origin", "https://github.com/KaolaBrother/kaola-project-runner.git")
            def register_from(checkout: Path, *args: str) -> dict:
                completed = subprocess.run([sys.executable, str(checkout / "scripts" / "kaola-locate.py"), "register", "--target", "local", "--bin-dir", str(bin_dir), *args],
                                           text=True, capture_output=True, env=dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1"))
                self.assertNotEqual(completed.returncode, 0, completed.stdout)
                self.assertTrue(completed.stdout.strip(), completed.stderr)
                data = json.loads(completed.stdout)
                self.assertEqual(data["result"], "refused")
                self.assertFalse(data["locator"]["changed"] or data["registration"]["changed"])
                self.assertEqual(os.readlink(link), good, "a refused registration must leave the existing locator unchanged")
                self.assertEqual(fx.registration.read_bytes(), good_receipt, "a refused registration must leave the receipt unchanged")
                return data
            # The accepted revision is required at registration, so a registration can always go stale.
            self.assertEqual(register_from(other)["reasons"], ["expect-revision-required"])
            (other / "scratch.txt").write_text("dirty\n", encoding="utf-8")
            self.assertIn("dirty", register_from(other, "--expect-revision", fx.revision)["reasons"])
            (other / "scratch.txt").unlink()
            self.assertIn("revision-mismatch", register_from(other, "--expect-revision", "0" * 40)["reasons"])
            self.assertIn("expect-revision-not-40-hex", register_from(other, "--expect-revision", "abc")["reasons"])
            git(other, "remote", "set-url", "origin", "https://github.com/someone-else/kaola-project-runner.git")
            self.assertIn("origin-mismatch", register_from(other, "--expect-revision", fx.revision)["reasons"])
            git(other, "remote", "set-url", "origin", "github.com/KaolaBrother/kaola-project-runner")
            self.assertEqual(register_from(other, "--expect-revision", fx.revision)["reasons"], ["origin-form-unsupported"])
            # A clean, matching checkout may take over (re-registration), and only then do link and receipt change.
            git(other, "remote", "set-url", "origin", "https://github.com/KaolaBrother/kaola-project-runner.git")
            completed = subprocess.run([sys.executable, str(other / "scripts" / "kaola-locate.py"), "register", "--target", "local", "--bin-dir", str(bin_dir), "--expect-revision", fx.revision],
                                       text=True, capture_output=True, env=dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1"))
            data = json.loads(completed.stdout)
            self.assertEqual(data["result"], "ok", data)
            self.assertTrue(data["locator"]["changed"] and data["locator"]["replaced"])
            self.assertEqual(Path(os.readlink(link)), (other / "scripts" / "kaola-locate.py").resolve())
            self.assertEqual(json.loads(fx.registration.read_text(encoding="utf-8"))["root"], str(other.resolve()))
            # A dirty tree also blocks a first registration: nothing is linked or recorded at all.
            empty_bin = fx.base / "empty bin"
            (fx.checkout / "scratch.txt").write_text("dirty\n", encoding="utf-8")
            rc, receipt = fx.locate("register", "--target", "local", "--bin-dir", str(empty_bin), "--expect-revision", fx.revision)
            self.assertEqual(receipt["result"], "refused")
            self.assertIn("dirty", receipt["reasons"])
            self.assertFalse((empty_bin / LOCATOR_COMMAND).exists() or (empty_bin / LOCATOR_COMMAND).is_symlink())
            self.assertFalse((empty_bin / f".{LOCATOR_COMMAND}.json").exists())

    def test_session_field_reports_presence_only_and_docstring_says_so(self) -> None:
        docstring = normalize(LOCATOR.read_text(encoding="utf-8").split('"""', 2)[1])
        self.assertIn("presence on that server only: not proof that the session exists elsewhere, and never ownership, which the worker preflight proves", docstring)
        self.assertIn("as declared by the caller", docstring)
        self.assertIn("may include the user's home directory", docstring)
        self.assertIn("no content hashing is attempted", docstring)
        self.assertNotIn("exact owned session", docstring)
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            self.assertEqual(fx.register("--expect-revision", fx.revision)[0], 0)
            rc, receipt = fx.via_link("--target", "local", "--session", "kaola-issue-49-no-such-session")
            self.assertEqual(set(receipt["session"]), {"name", "present"}, "no ownership or existence claim in the receipt")

    def test_registration_receipt_is_durable_across_conversations_and_fails_closed_on_tampering(self) -> None:
        """A fresh process with no memory runs the link and the locator compares the receipt itself."""
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            rc, registered = fx.register("--expect-revision", fx.revision)
            self.assertEqual(rc, 0, registered)
            record = json.loads(fx.registration.read_text(encoding="utf-8"))
            self.assertEqual(set(record), {"schema", "root", "target", "host", "accepted_revision"})
            self.assertEqual(record["schema"], "kaola-project-runner-locator-registration/1")
            self.assertEqual((record["root"], record["target"], record["accepted_revision"]), (str(fx.checkout.resolve()), "local", fx.revision))
            self.assertEqual(set(record["host"]), {"kernel", "fingerprint"})
            self.assertEqual(len(record["host"]["fingerprint"]), 12)
            node = platform.node()
            if node:
                self.assertNotIn(node, fx.registration.read_text(encoding="utf-8"), "the hostname itself is never stored")
            # Fresh conversation: nothing but the link and the receipt on disk.
            rc, receipt = fx.via_link("--target", "local", "--expect-revision", fx.revision)
            self.assertEqual(receipt["result"], "ok", receipt)
            self.assertEqual(receipt["registration"]["accepted_revision"], fx.revision)
            self.assertTrue(receipt["registration"]["fingerprint_match"] and receipt["registration"]["target_match"])
            # A different declared target is refused by the receipt, not by any host classification.
            rc, receipt = fx.via_link("--target", "cloud", "--expect-revision", fx.revision)
            self.assertEqual(receipt["reasons"], ["target-mismatch"])
            # Tampering with each recorded fact is refused.
            original = fx.registration.read_text(encoding="utf-8")
            def tampered(**changes: object) -> dict:
                data = json.loads(original)
                data.update(changes)
                fx.registration.write_text(json.dumps(data) + "\n", encoding="utf-8")
                rc, receipt = fx.via_link("--target", "local", "--expect-revision", fx.revision)
                self.assertEqual(rc, 1, receipt)
                self.assertEqual(receipt["result"], "refused")
                return receipt
            self.assertEqual(tampered(host={"kernel": record["host"]["kernel"], "fingerprint": "0" * 12})["reasons"], ["host-fingerprint-mismatch"])
            self.assertEqual(tampered(host={"kernel": "Other", "fingerprint": record["host"]["fingerprint"]})["reasons"], ["host-fingerprint-mismatch"])
            self.assertEqual(tampered(target="cloud")["reasons"], ["target-mismatch"])
            self.assertEqual(tampered(root=str(fx.base / "elsewhere"))["reasons"], ["registration-root-mismatch"])
            self.assertEqual(tampered(accepted_revision="1" * 40)["reasons"], ["registration-stale"])
            self.assertEqual(tampered(accepted_revision=None)["reasons"], ["locator-registration-unreadable"], "a null accepted revision can never be current")
            self.assertEqual(tampered(schema="kaola-project-runner-locator-registration/0")["reasons"], ["locator-registration-unreadable"])
            fx.registration.write_text("{not json", encoding="utf-8")
            rc, receipt = fx.via_link("--target", "local")
            self.assertEqual(receipt["reasons"], ["locator-registration-unreadable"])
            # A missing receipt refuses any declared target; plain discovery still answers.
            fx.registration.unlink()
            rc, receipt = fx.via_link("--target", "local")
            self.assertEqual(receipt["reasons"], ["locator-not-registered"])
            rc, receipt = fx.via_link()
            self.assertEqual(receipt["result"], "ok", receipt)
            self.assertFalse(receipt["registration"]["present"])
            self.assertEqual(Path(receipt["root"]["path"]), fx.checkout.resolve())
            # A receipt that exists but mismatches refuses even a plain discovery call.
            fx.registration.write_text(original.replace(record["host"]["fingerprint"], "f" * 12), encoding="utf-8")
            rc, receipt = fx.via_link()
            self.assertEqual(receipt["reasons"], ["host-fingerprint-mismatch"])
            # Re-registration repairs it; changing R without re-registering is stale.
            fx.registration.write_text(original, encoding="utf-8")
            (fx.checkout / "next.txt").write_text("next\n", encoding="utf-8")
            git(fx.checkout, "add", "-A")
            git(fx.checkout, "commit", "-q", "-m", "next content commit")
            rc, receipt = fx.via_link("--target", "local")
            self.assertEqual(receipt["reasons"], ["registration-stale"])
            self.assertFalse(receipt["registration"]["revision_current"])
            rc, registered = fx.register("--expect-revision", git(fx.checkout, "rev-parse", "HEAD"))
            self.assertEqual(registered["result"], "ok", registered)
            self.assertTrue(registered["registration"]["replaced"])
            rc, receipt = fx.via_link("--target", "local")
            self.assertEqual(receipt["result"], "ok", receipt)

    def test_origin_is_accepted_only_in_explicit_https_ssh_or_scp_forms(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fx = LocatorFixture(temporary)
            accepted = ("https://github.com/KaolaBrother/kaola-project-runner.git",
                        "https://user:secret@github.com:443/KaolaBrother/kaola-project-runner/",
                        "ssh://git@github.com/KaolaBrother/kaola-project-runner.git",
                        "git@github.com:KaolaBrother/kaola-project-runner.git",
                        "github.com:KaolaBrother/kaola-project-runner")
            for url in accepted:
                git(fx.checkout, "remote", "set-url", "origin", url)
                rc, receipt = fx.locate()
                self.assertEqual(receipt["root"]["origin"], EXPECTED_ORIGIN, url)
                self.assertNotIn("origin-mismatch", receipt.get("reasons", []), url)
                self.assertNotIn("origin-form-unsupported", receipt.get("reasons", []), url)
                self.assertNotIn("secret", json.dumps(receipt))
            rejected = ("github.com/KaolaBrother/kaola-project-runner", "http://github.com/KaolaBrother/kaola-project-runner",
                        "git://github.com/KaolaBrother/kaola-project-runner", "file:///tmp/kaola-project-runner",
                        "/Users/owner/kaola-project-runner", "../kaola-project-runner", "https://github.com/KaolaBrother",
                        "https://user:secret@github.com/a/b/c",
                        # Malformed credential-bearing, query, and fragment forms are unsupported, never echoed.
                        "https://user:se@cret@github.com/KaolaBrother/kaola-project-runner.git",
                        "https://github.com/KaolaBrother/kaola-project-runner.git?token=secret",
                        "https://github.com/KaolaBrother/kaola-project-runner#secret",
                        "git@github.com:KaolaBrother/kaola-project-runner.git?secret=1",
                        "ssh://git@github.com/KaolaBrother/kaola-project-runner?ref=secret")
            for url in rejected:
                git(fx.checkout, "remote", "set-url", "origin", url)
                rc, receipt = fx.locate()
                self.assertEqual(rc, 1, url)
                self.assertIn("origin-form-unsupported", receipt["reasons"], url)
                self.assertIsNone(receipt["root"]["origin"], url)
                leak_check = dict(receipt, root={k: v for k, v in receipt["root"].items() if k != "expected_origin"})
                self.assertNotIn(url, json.dumps(leak_check), "the raw origin never leaks into the receipt")
                self.assertNotIn("secret", json.dumps(receipt))
                self.assertNotIn("cret@github", json.dumps(receipt), "no fragment of a malformed origin is echoed")
            git(fx.checkout, "remote", "set-url", "origin", "https://github.com/someone-else/kaola-project-runner.git")
            rc, receipt = fx.locate()
            self.assertEqual(receipt["reasons"], ["origin-mismatch"])

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
        self.assertIsNotNone(clause_present(reference, (r"`--target` is the Agent's declaration",)))
        self.assertIsNotNone(clause_present(reference, (r"host\.fingerprint.{0,80}recorded (?:at|when).{0,40}regist",)))
        self.assertIsNotNone(clause_present(reference, (r"presence only",)))
        self.assertIsNotNone(clause_present(reference, (r"may include the user's home",)))
        self.assertIsNotNone(clause_present(reference, (r"content commit R\*?\*?.{0,240}pin commit P",)))
        for overclaim in (r"rejects? cloud paths for a Local Computer dispatch", r"proves? (?:the )?physical host", r"no hostname, no user",
                          r"exact owned session(?: name)?[^.]{0,40}(?:proven|proves|attests)"):
            self.assertIsNone(re.search(overclaim, text + "\n" + reference, flags=re.IGNORECASE), overclaim)
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
        # The adapter's product functions take no manifest at all, so the declared input is the real one.
        self.assertRegex(renderer, r"(?m)^def bridge_values\(\) -> ")
        self.assertRegex(renderer, r"(?m)^def expected_grok_bot_host_files\(\) -> ")
        self.assertRegex(renderer, r"(?m)^def install_guide\(values: dict\[str, str\]\) -> ")
        adapter = renderer.split("# Host adapter: grok-bot", 1)[1].split("# Progressive-disclosure budgets", 1)[0]
        for leak in ("manifests[0]", "FIRST_WORKER", "runtime_name", "manifest[\"id\"]", "manifest['id']"):
            self.assertNotIn(leak, adapter, leak)
        self.assertNotIn("FIRST_WORKER", (GROK_BOT_TEMPLATES / "INSTALL.md.tmpl").read_text(encoding="utf-8"))
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
