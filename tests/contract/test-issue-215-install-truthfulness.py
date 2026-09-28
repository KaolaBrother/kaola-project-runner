#!/usr/bin/env python3
"""Issue #215: scoped installs, owned stale-Skill cleanup, skew refusal routes.

Offline and deterministic; no real CLI, login, or network. Covers:

* render-skills.py --verify-install: a root holding only kaola-project-runner
  is NOT a complete aligned install; an --expect scope verifies the named set
  only and reports itself filtered; receipt-owned obsolete names are
  inventoried; foreign paths are reported, never findings.
* install-local.sh: the pre-mutation render gate stops a stale checkout
  before any write; a filtered install reports its exact scope and fails
  nonzero when a requested payload does not land; obsolete owned copies are
  retired only while receipted, unmodified, and unreferenced -- modified,
  co-owned, foreign, and receipt-less paths stay.
* --bin-links: helper links report target/build/referrers separately from
  Skill alignment; a usable link to another checkout is kept and named
  "not upgraded" with its transition route.
* kaola-acp.py: the worker/main build-skew refusal route is owner-aware
  (--runtime NAME for a root a runtime owns, generic --skills-dir only where
  nothing owns it), prefers a complete-root refresh for stale siblings, and
  gates retry on mutation_status=not_started.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "scripts" / "render-skills.py"
INSTALLER = ROOT / "scripts" / "install-local.sh"
RECEIPT_DIR = ".kaola-install-receipts"
WORKER_NAMES = [f"{name}-kaola-project-runner" for name in (
    "claude-code", "codex", "cursor-cli", "devin", "droid", "dsh", "grok",
    "kimi-cli", "opencode", "zcode")]
MAIN_NAME = "kaola-project-runner"
EXTERNAL_NAME = "kaola-delegator"

CHECKS: list[str] = []


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run(argv: list[str], cwd: Path = ROOT, env: dict | None = None) -> subprocess.CompletedProcess:
    merged = dict(os.environ)
    if env:
        merged.update(env)
    return subprocess.run(argv, cwd=cwd, env=merged, capture_output=True, text=True)


def verify(root: Path, *extra: str) -> tuple[subprocess.CompletedProcess, dict]:
    proc = run([sys.executable, str(RENDERER), "--verify-install", str(root), *extra])
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    receipt = json.loads(lines[-1]) if lines else {}
    return proc, receipt


def receipt_file(root: Path, skill: str, referrers: list[str], digest: str = "x") -> None:
    receipts = root / RECEIPT_DIR
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / f"{skill}.json").write_text(json.dumps({
        "receipt": "kaola-project-runner-install/1",
        "skill": skill,
        "method": "copy",
        "source": str(ROOT),
        "content_sha256": digest,
        "referrers": referrers,
    }), encoding="utf-8")


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    entries = []
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        entries += [os.path.join(dirpath, n) for n in dirnames + filenames
                    if not n.endswith((".pyc", ".pyo"))]
    for entry in sorted(entries, key=lambda p: os.path.relpath(p, path)):
        rel = os.path.relpath(entry, path).replace(os.sep, "/")
        if os.path.islink(entry):
            digest.update(b"L" + rel.encode() + b"=" + os.readlink(entry).encode() + b"\n")
        elif os.path.isdir(entry):
            digest.update(b"D" + rel.encode() + b"\n")
        else:
            digest.update(b"F" + rel.encode() + b"=" + hashlib.sha256(
                Path(entry).read_bytes()).hexdigest().encode() + b"\n")
    return digest.hexdigest()


def copy_skill(root: Path, name: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    target = root / name
    shutil.copytree(ROOT / "skills" / name, target)
    return target


def shadow_home(tmp: Path) -> dict[str, str]:
    home = tmp / "home"
    home.mkdir(parents=True, exist_ok=True)
    return {"HOME": str(home)}


def test_verify_single_skill_root_is_not_complete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "skills"
        copy_skill(root, MAIN_NAME)
        proc, receipt = verify(root)
        check(proc.returncode == 1, "a one-Skill root must not verify aligned")
        check(receipt["result"] == "incomplete", f"result incomplete, got {receipt.get('result')}")
        check(receipt["scope"] == "complete", "scope complete")
        check(set(receipt["missing"]) == set(WORKER_NAMES),
              "every absent worker is a missing member of the expected set")
        check(receipt["root_complete"] is False, "root_complete false")
        check("not a complete aligned install" in proc.stderr, "stderr says not complete")


def test_verify_filtered_scope_names_selection() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "skills"
        copy_skill(root, MAIN_NAME)
        proc, receipt = verify(root, "--expect", MAIN_NAME)
        check(proc.returncode == 0, f"scoped verify of the present set passes: {proc.stderr}")
        check(receipt["scope"] == "filtered", "scope filtered")
        check(receipt["result"] == "aligned", "deliberate partial install stays valid")
        check(receipt["root_complete"] is False, "filtered root_complete false")
        check(set(receipt["unselected"]) == set(WORKER_NAMES + [EXTERNAL_NAME]),
              "unselected names the whole remaining catalog")
        check(all(state == "absent" for state in receipt["unselected"].values()),
              "unselected states are absent here")
        check("NOT a complete install" in proc.stderr, "stderr disclaims completeness")

        proc, receipt = verify(root, "--expect", "devin")
        check(proc.returncode == 1, "a filtered set that is absent is incomplete, not empty")
        check(receipt["result"] == "incomplete", "filtered absent set -> incomplete")
        check(receipt["missing"] == ["devin-kaola-project-runner"], "missing names the platform Skill")
        proc, receipt = verify(root, "--expect", "nonsense")
        check(proc.returncode == 2, "an unknown --expect token refuses (argparse error)")


def test_verify_obsolete_owned_and_foreign_inventory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "skills"
        shutil.copytree(ROOT / "skills", root)
        foreign = root / "my-own-skill"
        foreign.mkdir()
        (foreign / "SKILL.md").write_text("# mine\n", encoding="utf-8")
        proc, receipt = verify(root)
        check(proc.returncode == 0, f"full render verifies aligned: {proc.stderr}")
        check(receipt["unmanaged"] == ["my-own-skill"], "foreign path reported, not a finding")
        check(receipt["root_complete"] is True, "root_complete true for the full set")

        obsolete = root / "kaola-retired-worker"
        obsolete.mkdir()
        (obsolete / "SKILL.md").write_text("# retired\n", encoding="utf-8")
        receipt_file(root, "kaola-retired-worker", ["generic"])
        proc, receipt = verify(root)
        check(proc.returncode == 1, "receipt-owned obsolete copy makes the root incomplete")
        check(receipt["result"] == "incomplete", "obsolete owned -> incomplete")
        check(receipt["obsolete_owned"] == ["kaola-retired-worker"], "obsolete named")
        check("kaola-retired-worker" in proc.stderr, "stderr names the obsolete copy")

        shutil.rmtree(obsolete)
        proc, receipt = verify(root)
        check(proc.returncode == 0, "a stale receipt alone does not block alignment")
        check(receipt["stale_receipts"] == ["kaola-retired-worker"], "stale receipt inventoried")


def fixture_checkout(base: Path, render_ok: bool = True) -> Path:
    """A minimal install source: the installer, one Skill, and a render stub."""
    repo = base / "checkout"
    (repo / "scripts").mkdir(parents=True)
    (repo / "skills" / MAIN_NAME).mkdir(parents=True)
    (repo / "skills" / MAIN_NAME / "SKILL.md").write_text("# main\n", encoding="utf-8")
    (repo / "skills" / MAIN_NAME / ".generated-by-kaola-project-runner").write_text(
        "kaola-project-runner\n", encoding="utf-8")
    shutil.copy2(INSTALLER, repo / "scripts" / "install-local.sh")
    stub = repo / "scripts" / "render-skills.py"
    stub.write_text(
        "#!/usr/bin/env python3\nimport sys\n"
        + ("sys.exit(0)\n" if render_ok else
           "print('skills/devin-kaola-project-runner/SKILL.md is stale', file=sys.stderr)\n"
           "sys.exit(1)\n"),
        encoding="utf-8")
    stub.chmod(0o755)
    (repo / "scripts" / "install-local.sh").chmod(0o755)
    return repo


def test_installer_preflight_gate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        stale = fixture_checkout(tmp / "stale", render_ok=False)
        dest = tmp / "dest" / "skills"
        proc = run(["bash", str(stale / "scripts" / "install-local.sh"),
                    "--skills-dir", str(dest)], cwd=stale, env=shadow_home(tmp))
        check(proc.returncode == 1, "stale render refuses before mutation")
        check("render-skills.py --write" in proc.stderr, "refusal names the render remedy")
        check(not dest.exists(), "nothing was written to the destination")

        bare = tmp / "bare"
        (bare / "scripts").mkdir(parents=True)
        shutil.copy2(INSTALLER, bare / "scripts" / "install-local.sh")
        proc = run(["bash", str(bare / "scripts" / "install-local.sh"),
                    "--skills-dir", str(dest)], cwd=bare, env=shadow_home(tmp))
        check(proc.returncode == 1, "missing render tool refuses")
        check("cannot prove" in proc.stderr, "missing-renderer refusal names the reason")
        check(not dest.exists(), "still nothing written")


def test_installer_filtered_scope_and_repeat_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        dest = tmp / "dest" / "skills"
        env = shadow_home(tmp)
        proc = run(["bash", str(INSTALLER), "--skills-dir", str(dest),
                    "--platform", "devin", "--method", "copy"], cwd=ROOT, env=env)
        check(proc.returncode == 0, f"filtered install passes: {proc.stderr[-300:]}")
        check("scope: filtered" in proc.stdout, "filtered scope reported")
        check("selected: devin-kaola-project-runner" in proc.stdout,
              "selected payloads named")
        check("NOT a complete-root install" in proc.stdout, "never claimed complete")
        check("unselected:" in proc.stdout, "unselected siblings reported")
        proc, receipt = verify(dest)
        check(proc.returncode == 1, "bare verify of a filtered root is incomplete")
        check(receipt["result"] == "incomplete", "filtered root: incomplete")
        check(set(receipt["missing"]) == set(WORKER_NAMES) - {"devin-kaola-project-runner"},
              "missing = the nine unrequested workers")
        proc, receipt = verify(dest, "--expect",
                               "devin,kaola-project-runner,kaola-delegator")
        check(proc.returncode == 0 and receipt["scope"] == "filtered",
              "the exact installed scope verifies")

        dest_full = tmp / "dest-full" / "skills"
        proc = run(["bash", str(INSTALLER), "--skills-dir", str(dest_full),
                    "--method", "copy"], cwd=ROOT, env=env)
        check(proc.returncode == 0, f"complete install passes: {proc.stderr[-300:]}")
        check("scope: complete" in proc.stdout, "complete scope reported")
        check("12/12 requested Skills match" in proc.stdout, "every requested Skill verified")
        proc2 = run(["bash", str(INSTALLER), "--skills-dir", str(dest_full),
                     "--method", "copy"], cwd=ROOT, env=env)
        check(proc2.returncode == 0, "a second identical install is repeat-safe")
        proc3, receipt = verify(dest_full)
        check(proc3.returncode == 0 and receipt["root_complete"] is True,
              "the complete root verifies aligned")


def test_installer_obsolete_retirement() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        dest = tmp / "dest" / "skills"
        env = shadow_home(tmp)
        proc = run(["bash", str(INSTALLER), "--skills-dir", str(dest), "--method", "copy"],
                   cwd=ROOT, env=env)
        check(proc.returncode == 0, f"seed install: {proc.stderr[-200:]}")

        # 1. sole-owned unchanged obsolete copy -> retired
        old = dest / "kaola-retired-worker"
        shutil.copytree(ROOT / "skills" / MAIN_NAME, old)
        receipt_file(dest, "kaola-retired-worker", ["generic"], tree_digest(old))
        # 2. co-owned obsolete copy -> kept, this install's referrer withdrawn
        shared = dest / "kaola-old-shared"
        shutil.copytree(ROOT / "skills" / MAIN_NAME, shared)
        receipt_file(dest, "kaola-old-shared", ["dsh", "generic"], tree_digest(shared))
        # 3. modified obsolete copy -> kept, named
        edited = dest / "kaola-edited"
        shutil.copytree(ROOT / "skills" / MAIN_NAME, edited)
        digest = tree_digest(edited)
        (edited / "LOCAL.md").write_text("edit\n", encoding="utf-8")
        receipt_file(dest, "kaola-edited", ["generic"], digest)
        # 4. stale receipt with no directory -> receipt dropped
        receipt_file(dest, "kaola-ghost", ["generic"])
        # 5. foreign unreceipted path -> untouched
        foreign = dest / "not-ours"
        foreign.mkdir()
        (foreign / "SKILL.md").write_text("foreign\n", encoding="utf-8")

        proc = run(["bash", str(INSTALLER), "--skills-dir", str(dest), "--method", "copy"],
                   cwd=ROOT, env=env)
        check(proc.returncode == 0, f"install with obsolete inventory: {proc.stderr[-300:]}")
        check(not old.exists() and not (dest / RECEIPT_DIR / "kaola-retired-worker.json").exists(),
              "unchanged sole-owned obsolete copy retired with its receipt")
        check("retired obsolete owned copy" in proc.stdout, "retirement reported")
        check(shared.is_dir(), "co-owned obsolete copy kept")
        refs = json.loads((dest / RECEIPT_DIR / "kaola-old-shared.json").read_text())["referrers"]
        check(refs == ["dsh"], f"generic withdrawn, dsh kept: {refs}")
        check("still referenced by dsh" in proc.stdout, "co-owned keep reported")
        check(edited.is_dir() and (edited / "LOCAL.md").exists(),
              "modified obsolete copy preserved")
        check("bytes differ" in proc.stdout, "modified copy named with its reason")
        check(not (dest / RECEIPT_DIR / "kaola-ghost.json").exists(),
              "stale receipt for a missing copy dropped")
        check("dropped stale receipt" in proc.stdout, "stale-receipt drop reported")
        check((foreign / "SKILL.md").read_text() == "foreign\n",
              "foreign path preserved byte-for-byte")
        check("foreign path(s) preserved" in proc.stdout and "not-ours" in proc.stdout,
              "foreign path named")
        check("unresolved obsolete copies kept" in proc.stdout,
              "kept obsolete copies named in the verify block")


def test_installer_bin_links_helper_report() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        env = shadow_home(tmp)
        home = Path(env["HOME"])
        bin_dir = home / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        # A usable helper link on another accepted checkout (older build).
        other = tmp / "older-checkout"
        (other / "scripts").mkdir(parents=True)
        for name in ("kaola-acp.py", "kaola-acp-holder.py", "kaola-locate.py"):
            target = other / "scripts" / name
            target.write_bytes((ROOT / "scripts" / name).read_bytes() + b"\n# older\n")
            target.chmod(0o755)
            (bin_dir / name.replace("kaola-locate.py", "kaola-project-runner-locate")
             .replace(".py", "")).symlink_to(target)
        ledger = {
            "receipt": "kaola-project-runner-bin-links/1",
            "links": {name: {"target": str((bin_dir / name).resolve()),
                             "referrers": [{"runtime": "zcode",
                                            "checkout": str(other)}]}
                      for name in ("kaola-acp", "kaola-acp-holder",
                                   "kaola-project-runner-locate")},
        }
        (bin_dir / ".kaola-project-runner-bin-links.json").write_text(
            json.dumps(ledger), encoding="utf-8")
        dest = tmp / "dest" / "skills"
        proc = run(["bash", str(INSTALLER), "--skills-dir", str(dest),
                    "--platform", "devin", "--bin-links"], cwd=ROOT, env=env)
        check(proc.returncode == 0, f"install with kept helpers passes: {proc.stderr[-300:]}")
        check("helper not upgraded: " in proc.stdout, "older usable helper reported not upgraded")
        check("referrers:" in proc.stdout and "older-checkout" in proc.stdout,
              "helper referrers named")
        check("scope: filtered" in proc.stdout, "Skill alignment reported separately")
        check((bin_dir / "kaola-acp").resolve() == (other / "scripts" / "kaola-acp.py").resolve(),
              "the usable link was not retargeted")


def _skew_entry(root: Path, skill: str) -> dict:
    installed = root / skill / "scripts" / "kaola-acp.py"
    installed.parent.mkdir(parents=True, exist_ok=True)
    installed.write_text("# old\n", encoding="utf-8")
    return {"path": str(installed), "file": "kaola-acp.py",
            "installed": "aaaaaaaaaaaa", "expected": "bbbbbbbbbbbb"}


def test_refusal_route_owner_aware() -> None:
    acp = load(ROOT / "scripts" / "kaola-acp.py", "kaola_acp_215")
    old_home = os.environ.get("HOME")
    old_env = {key: os.environ.get(key) for key in
               ("DEVIN_CONFIG_DIR", "CODEX_HOME", "CLAUDE_CONFIG_DIR", "KIMI_CODE_HOME")}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            home = tmp / "home"
            home.mkdir()
            for key in old_env:
                os.environ.pop(key, None)
            os.environ["HOME"] = str(home)
            args = argparse.Namespace(platform="zcode", session="s215", model=None)
            devin_root = home / ".config" / "devin" / "skills"
            shared_root = home / ".agents" / "skills"
            foreign_root = tmp / "elsewhere" / "skills"

            # devin's own root -> --runtime devin, no --skills-dir.
            alignment = {"build": "bbbbbbbbbbbb", "roots": [], "unreadable_roots": [],
                         "skew": [_skew_entry(devin_root, "devin-kaola-project-runner")]}
            receipt = acp.worker_skill_skew_refusal(args, str(ROOT), alignment)
            detail = receipt["detail"]
            check(receipt["result"] == "refused" and
                  receipt["reason"] == "worker-skill-build-skew", "typed refusal kept")
            check(receipt["mutation_status"] == "not_started", "mutation_status not_started")
            check(f"--runtime devin --platform devin --no-orchestrator" in detail,
                  "native owner route, platform-scoped, workers only")
            check("--skills-dir" not in detail.split("generic")[0] or "--skills-dir install is" in detail,
                  "generic route never presented as the owner")
            check(f"--verify-install {devin_root} --expect devin" in detail,
                  "verify command checks the affected set")
            check("not_started" in detail, "retry gated on not_started")
            check("kaola-delegator" not in detail, "worker refusal never names the external Skill")
            check("Delegator or operator" in detail, "Host handoff keeps task and seat")

            # shared .agents root with a recorded dsh referrer -> --runtime dsh.
            (shared_root / RECEIPT_DIR).mkdir(parents=True)
            receipt_file(shared_root, "dsh-kaola-project-runner", ["dsh"])
            alignment = {"build": "bbbbbbbbbbbb", "roots": [], "unreadable_roots": [],
                         "skew": [_skew_entry(shared_root, "dsh-kaola-project-runner")]}
            detail = acp.worker_skill_skew_refusal(args, str(ROOT), alignment)["detail"]
            check("--runtime dsh" in detail, "shared root owned by its recorded referrer")
            check("--skills-dir" not in [part.split()[2] for part in detail.split(";")
                                         if "install-local.sh" in part][:1],
                  "owner route replaces the generic command")

            # unmapped root with two stale siblings -> complete-root refresh.
            alignment = {"build": "bbbbbbbbbbbb", "roots": [], "unreadable_roots": [],
                         "skew": [_skew_entry(foreign_root, "droid-kaola-project-runner"),
                                  _skew_entry(foreign_root, "dsh-kaola-project-runner")]}
            detail = acp.worker_skill_skew_refusal(args, str(ROOT), alignment)["detail"]
            check(f"--skills-dir {foreign_root} --no-orchestrator" in detail,
                  "stale siblings take the complete-root refresh (no --platform)")
            check(f"--verify-install {foreign_root}." in detail,
                  "complete refresh verifies the whole root, unfiltered")
            check("--platform" not in detail.split("install-local.sh")[1].split(";")[0],
                  "no single-platform flag on the complete refresh")

            # unmapped root, one stale platform -> the exact legacy route shape.
            alignment = {"build": "bbbbbbbbbbbb", "roots": [], "unreadable_roots": [],
                         "skew": [_skew_entry(foreign_root, "droid-kaola-project-runner")]}
            detail = acp.worker_skill_skew_refusal(args, str(ROOT), alignment)["detail"]
            check(f"--skills-dir {foreign_root} --platform droid --no-orchestrator" in detail,
                  "single stale platform keeps its --platform route")

            # a renamed copy has no installer route.
            alien = foreign_root / "renamed-skill" / "scripts" / "kaola-acp.py"
            alien.parent.mkdir(parents=True, exist_ok=True)
            alien.write_text("# alien\n", encoding="utf-8")
            alignment = {"build": "bbbbbbbbbbbb", "roots": [], "unreadable_roots": [],
                         "skew": [{"path": str(alien), "file": "kaola-acp.py",
                                   "installed": "aaa", "expected": "bbb"}]}
            detail = acp.worker_skill_skew_refusal(args, str(ROOT), alignment)["detail"]
            check("renamed copy no installer manages" in detail,
                  "renamed copies are owner-confirm, never scripted")

            # main-skill skew on an owned root: --runtime + orchestrator expect.
            main_copy = devin_root / MAIN_NAME
            (main_copy / "scripts").mkdir(parents=True, exist_ok=True)
            (main_copy / "scripts" / "x").write_text("", encoding="utf-8")
            alignment = {"build": "bbbbbbbbbbbb",
                         "skew": [{"path": str(main_copy), "file": "build",
                                   "installed": "aaa", "expected": "bbb"}]}
            receipt = acp.main_skill_skew_refusal(args, str(ROOT), alignment)
            detail = receipt["detail"]
            check(receipt["reason"] == "main-skill-build-skew", "main refusal reason kept")
            check("--runtime devin --platform zcode" in detail,
                  "main skew refreshes via the owner, Host platform scoped")
            check(f"--expect zcode,{MAIN_NAME}" in detail,
                  "main verify covers platform worker plus main Skill")
            check("kaola-delegator" in detail, "main route notes the delegator plan")
            check("never delete it by hand" in detail, "foreign-path guard kept")
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


TESTS = [
    test_verify_single_skill_root_is_not_complete,
    test_verify_filtered_scope_names_selection,
    test_verify_obsolete_owned_and_foreign_inventory,
    test_installer_preflight_gate,
    test_installer_filtered_scope_and_repeat_safe,
    test_installer_obsolete_retirement,
    test_installer_bin_links_helper_report,
    test_refusal_route_owner_aware,
]


def main() -> int:
    failures = 0
    for test in TESTS:
        before = len(CHECKS)
        try:
            test()
            print(f"PASS {test.__name__} ({len(CHECKS) - before} checks)")
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"test-issue-215-install-truthfulness: {len(TESTS) - failures}/{len(TESTS)} tests, "
          f"{len(CHECKS)} checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
