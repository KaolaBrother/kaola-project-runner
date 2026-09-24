#!/usr/bin/env python3
"""Issue #133 contract: the Host reads the Workflow mission ledger read-only.

Checked here:

* the rendered ``issue-dispatch.md`` one-line ``{n,status}`` projection, run against
  a fixture ``<root>/kaola-workflow/.ledger/issue-7.jsonl``, prints ``1 / 3 [(3, 'blocked')]``;
* an absent ledger is ``unknown`` -- stated in the rendered rule, never reported as
  ``0 / 0``, and with no Markdown Mission List fallback;
* no generated surface or template still keeps a Mission List, and this repository
  ignores ``kaola-workflow/.ledger/``.

Not checked: the Workflow writer side (Kaola-Workflow#1089) and live Host progress UAT.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
ORCHESTRATOR = PROJECT / "skills" / "kaola-project-runner"
DISPATCH = ORCHESTRATOR / "references" / "issue-dispatch.md"
HOST_STARTUP = ORCHESTRATOR / "references" / "host-startup.md"
KEEPER = re.compile(r"mission[ -]list", re.IGNORECASE)


def projection_command() -> str:
    text = DISPATCH.read_text(encoding="utf-8")
    blocks = re.findall(r"```bash\n(.*?)\n```", text, re.DOTALL)
    commands = [b for b in blocks if ".ledger/issue-$N.jsonl" in b]
    assert len(commands) == 1, commands
    return commands[0]


def run_projection(root: Path, issue: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", projection_command()],
        env={"ROOT": str(root), "N": str(issue), "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
        capture_output=True,
        text=True,
        timeout=30,
    )


class LedgerProjection(unittest.TestCase):
    def test_projection_reads_done_over_total_and_flags_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "kaola-workflow" / ".ledger"
            ledger.mkdir(parents=True)
            rows = [
                {"n": 1, "name": "诊断", "details": "dispatched: self | result: /tmp/a.log", "status": "done"},
                {"n": 2, "name": "修夹具", "details": "dispatched: self → .kw/worktrees/issue-7", "status": "in-flight"},
                {"n": 3, "name": "门禁", "details": "", "status": "blocked"},
            ]
            (ledger / "issue-7.jsonl").write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
            )
            result = run_projection(Path(tmp), 7)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "1 / 3 [(3, 'blocked')]")

    def test_rule_states_path_writer_and_projection(self) -> None:
        text = re.sub(r"\s+", " ", DISPATCH.read_text(encoding="utf-8"))
        for needle in (
            "Path: `<canonical-root>/kaola-workflow/.ledger/issue-<N>.jsonl`.",
            "exists only in the main checkout, never in a child worktree",
            # Issue #157 (§1.2): the schema is the global Workflow contract's.
            "Schema (keys, statuses, sole writer): the global Workflow contract. The Runner never writes.",
            "progress = `done` lines / total lines; per-mission status by `n`",
            "`kaola-workflow/archive/<project>/mission-ledger.jsonl`",
        ):
            self.assertIn(needle, text)
        startup = HOST_STARTUP.read_text(encoding="utf-8")
        self.assertIn("| Workflow mission ledger `kaola-workflow/.ledger/issue-<N>.jsonl` |", startup)
        self.assertIn("the Runner only reads", startup)


class TerminalLedger(unittest.TestCase):
    """Owner revision (issuecomment-5770305093): an all-terminal ledger that is still
    present is read together with the forge issue state the Host already gates on."""

    RULES = {
        "OPEN": "Every line terminal (`done`/`failed`) with the forge issue OPEN: finalize/archive is in progress, keep waiting.",
        "CLOSED": "Every line terminal with the issue CLOSED, or the run already under `archive/`: the archive was forgotten - report it stuck and name its owner, neither `unknown` nor done.",
    }

    @staticmethod
    def verdict(projection: str, forge_state: str) -> str:
        """Apply the rendered rule to the one-liner's output; 'live' when not all terminal."""
        match = re.fullmatch(r"(\d+) / (\d+) (\[.*\])", projection)
        assert match, projection
        done, total = int(match.group(1)), int(match.group(2))
        flagged = re.findall(r"\((\d+), '(failed|blocked)'\)", match.group(3))
        failed = sum(1 for _, status in flagged if status == "failed")
        if total == 0 or done + failed != total:
            return "live"
        return "in-progress" if forge_state == "OPEN" else "stuck"

    def test_all_terminal_ledger_is_in_progress_when_open_and_stuck_when_closed(self) -> None:
        text = re.sub(r"\s+", " ", DISPATCH.read_text(encoding="utf-8"))
        for rule in self.RULES.values():
            self.assertIn(rule, text)
        self.assertIn("a vanished file means archive done", text)
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "kaola-workflow" / ".ledger"
            ledger.mkdir(parents=True)
            rows = [
                {"n": 1, "name": "a", "details": "", "status": "done"},
                {"n": 2, "name": "b", "details": "", "status": "failed"},
                {"n": 3, "name": "c", "details": "", "status": "done"},
            ]
            (ledger / "issue-7.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
            )
            terminal = run_projection(Path(tmp), 7)
            rows[2]["status"] = "in-flight"
            (ledger / "issue-7.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
            )
            live = run_projection(Path(tmp), 7)
        self.assertEqual(terminal.returncode, 0, terminal.stderr)
        self.assertEqual(terminal.stdout.strip(), "2 / 3 [(2, 'failed')]")
        self.assertEqual(self.verdict(terminal.stdout.strip(), "OPEN"), "in-progress")
        self.assertEqual(self.verdict(terminal.stdout.strip(), "CLOSED"), "stuck")
        self.assertEqual(self.verdict(live.stdout.strip(), "CLOSED"), "live")


class AbsentLedger(unittest.TestCase):
    def test_absent_ledger_is_unknown_with_no_fallback(self) -> None:
        text = re.sub(r"\s+", " ", DISPATCH.read_text(encoding="utf-8"))
        self.assertIn(
            "Absent file → no live Workflow run has recorded missions for this issue (`unknown`).", text
        )
        # Issue #157 (PR-R4): the consumer-display fallback list moved to docs.
        display = re.sub(r"\s+", " ", (PROJECT / "docs" / "issue-dispatch-display.md").read_text(encoding="utf-8"))
        self.assertIn("an absent ledger, or two active runs for one issue each fall back to unknown", display)
        self.assertNotIn("mission-list.md", text)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "kaola-workflow").mkdir()
            result = run_projection(Path(tmp), 7)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("/", result.stdout, "an absent ledger must never read as a progress count")


class NoMissionListKeeper(unittest.TestCase):
    def test_no_surface_keeps_a_mission_list(self) -> None:
        roots = [PROJECT / "skills", PROJECT / "hosts", PROJECT / "templates"]
        hits = []
        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or "grok-golden" in path.parts:
                    continue
                try:
                    body = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for number, line in enumerate(body.splitlines(), 1):
                    if KEEPER.search(line):
                        hits.append(f"{path.relative_to(PROJECT)}:{number}: {line.strip()}")
        self.assertEqual(hits, [])

    def test_repository_ignores_the_ledger_folder(self) -> None:
        result = subprocess.run(
            ["git", "-C", str(PROJECT), "check-ignore", "-q", "kaola-workflow/.ledger/issue-1.jsonl"],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
