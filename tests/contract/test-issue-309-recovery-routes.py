#!/usr/bin/env python3
"""Issue #309: every audited refusal code has a recovery route or a self-route.

The table is scripts/kaola-recovery-routes.py. This test enumerates the codes
from the audited sources and requires the refusal text to carry route,
self_route, or a non-empty recovery. It does not launch a seat.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROUTES_PATH = REPO / "scripts" / "kaola-recovery-routes.py"
AUDITED = (
    "scripts/kaola-launchd-broker.py",
    "scripts/kaola-acp-holder.py",
    "scripts/kaola-acp.py",
    "scripts/kaola-dispatch.py",
    "scripts/kaola-locate.py",
)
CODE = re.compile(r"^[a-z][a-z0-9-]{1,80}$")
SHORT = {"dirty", "stopping", "conflict", "timeout", "connection"}
CALLS = {
    "BrokerError", "fail", "StateRefusal", "_webhook_refusal", "view_error",
    "follow_error_line", "offer_error", "emit_error",
}
APPEND = {"reasons", "mismatches", "unknown", "gaps", "reported", "blocking", "unknown_sources"}
SHELL_EXPLICIT = ("canonical-root-invalid", "canonical-root-mismatch", "runner-python-missing")


def _ok(value: object) -> bool:
    return isinstance(value, str) and bool(CODE.match(value)) and ("-" in value or value in SHORT)


def _consts(node: ast.AST | None) -> list[str]:
    found: list[str] = []
    if node is None:
        return found
    if isinstance(node, ast.Constant) and _ok(node.value):
        found.append(node.value)
    elif isinstance(node, (ast.IfExp, ast.BoolOp, ast.UnaryOp)):
        for child in ast.iter_child_nodes(node):
            found.extend(_consts(child))
    elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for elt in node.elts:
            found.extend(_consts(elt))
    return found


def extracted_python() -> set[str]:
    found: set[str] = set()
    for rel in AUDITED:
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = None
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in CALLS and node.args:
                    found.update(_consts(node.args[0]))
                if (isinstance(node.func, ast.Attribute) and node.func.attr == "append"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in APPEND and node.args):
                    found.update(_consts(node.args[0]))
                if isinstance(node.func, ast.Attribute) and node.func.attr == "update":
                    for kw in node.keywords:
                        if kw.arg == "reason":
                            found.update(_consts(kw.value))
                for kw in node.keywords:
                    if kw.arg in {"reason", "skip_reason", "code"}:
                        found.update(_consts(kw.value))
            elif isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value in {
                        "code", "reason", "skip_reason", "reasons",
                    }:
                        found.update(_consts(value))
            elif isinstance(node, ast.Assign):
                names = [target.id for target in node.targets if isinstance(target, ast.Name)]
                if any(item in {"reasons", "mismatches"} or item.endswith("_CODES") or "ERROR" in item
                       for item in names):
                    found.update(_consts(node.value))
            elif isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
                if len(node.value.elts) >= 2:
                    found.update(_consts(node.value.elts[1]))
    return found


def load_routes():
    spec = importlib.util.spec_from_file_location("kaola_recovery_routes", ROUTES_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {ROUTES_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecoveryRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.routes = load_routes()

    def test_every_extracted_code_has_a_route(self) -> None:
        table = self.routes.ROUTES
        missing = sorted(extracted_python() - set(table))
        self.assertEqual(missing, [], "audited source codes missing from ROUTES")
        for code, entry in table.items():
            self.assertRegex(code, CODE)
            self.assertEqual(len(entry), 2, code)
            kind, text = entry
            self.assertIn(kind, {"route", "self-route"}, code)
            self.assertTrue(text.strip(), code)
            self.assertNotIn("\n", text, code)

    def test_stamp_attaches_the_table_text(self) -> None:
        stamp = self.routes.stamp
        for code, (kind, text) in self.routes.ROUTES.items():
            payload = stamp({"result": "refused", "reason": code})
            field = "route" if kind == "route" else "self_route"
            self.assertEqual(payload.get(field), text, code)
            self.assertNotIn("self_route" if field == "route" else "route", payload, code)

    def test_stamp_keeps_recovery_and_skips_success(self) -> None:
        stamp = self.routes.stamp
        kept = stamp({"result": "refused", "reason": "conflict", "recovery": "keep me"})
        self.assertEqual(kept["recovery"], "keep me")
        self.assertNotIn("route", kept)
        self.assertNotIn("self_route", kept)
        skipped = stamp({"result": "skipped", "skip_reason": "duplicate", "error": "duplicate"})
        self.assertEqual(set(skipped), {"result", "skip_reason", "error"})
        ok = stamp({"result": "ok", "reason": "already-recovered"})
        self.assertEqual(set(ok), {"result", "reason"})
        failed = stamp({"result": "failed", "error": "timeout", "reason": "holder_lost"})
        self.assertIn("Do not retry a final receipt", failed["route"])
        self.assertNotIn("holder_lost", failed["route"])
        duplicate = stamp({"result": "refused", "reason": "duplicate"})
        self.assertIn("route", duplicate)

    def test_oversized_attest_keeps_a_route(self) -> None:
        huge = {
            "schema": "kaola-project-runner-locator/1",
            "result": "refused",
            "reasons": ["dirty"] * 400,
            "detail": "x" * 5000,
        }
        fitted = self.routes.fit_locate(huge, 4096)
        self.assertEqual(fitted["result"], "refused")
        self.assertTrue(fitted.get("reasons"))
        self.assertTrue(fitted.get("route") or fitted.get("self_route"))
        import json
        self.assertLessEqual(len(json.dumps(fitted, sort_keys=True).encode()), 4096)

    def test_shell_and_install_texts_match_the_table(self) -> None:
        table = self.routes.ROUTES
        install = (REPO / "scripts" / "install-local.sh").read_text(encoding="utf-8")
        tmux = (REPO / "scripts" / "kaola-tmux.sh").read_text(encoding="utf-8")
        install_codes = set(re.findall(r"refuse\s+[0-9]+\s+([a-z0-9-]+)", install))
        tmux_codes = set(re.findall(r"s:reason:([a-z0-9-]+)", tmux))
        tmux_codes.update(re.findall(r'"code"\s*:\s*"([a-z0-9-]+)"', tmux))
        tmux_codes.update(SHELL_EXPLICIT)
        self.assertTrue(install_codes)
        self.assertTrue(tmux_codes)
        for code in install_codes:
            self.assertIn(code, table, code)
            self.assertIn(table[code][1], install, code)
        for code in tmux_codes:
            self.assertIn(code, table, code)
            self.assertIn(table[code][1], tmux, code)
        self.assertNotIn("<<", install)
        self.assertNotIn("<<<", install)
        self.assertNotIn("<<", tmux)
        self.assertNotIn("<<<", tmux)

    def test_dynamic_capture_codes_and_webhook_tuple(self) -> None:
        dispatch = (REPO / "scripts" / "kaola-dispatch.py").read_text(encoding="utf-8")
        self.assertIn('"status-" +', dispatch)
        self.assertIn('"capture-" +', dispatch)
        self.assertIn("status-unreadable", self.routes.ROUTES)
        self.assertIn("capture-unreadable", self.routes.ROUTES)
        acp = (REPO / "scripts" / "kaola-acp.py").read_text(encoding="utf-8")
        for code in (
            "timeout", "connection", "http-status", "redirect-refused", "config-mode",
            "invalid-config", "invalid-payload", "not-enabled", "not-configured", "duplicate",
        ):
            self.assertIn(f'"{code}"', acp)
            self.assertIn(code, self.routes.ROUTES)
        verify = (REPO / "scripts" / "kaola-grok-bot-verify.py").read_text(encoding="utf-8")
        self.assertIn(self.routes.ROUTES["verify-finding"][1], verify)

    def test_broker_dead_end_is_gone_and_holder_is_not_stamped(self) -> None:
        broker = (REPO / "scripts" / "kaola-launchd-broker.py").read_text(encoding="utf-8")
        self.assertNotIn("reconcile it", broker)
        # After the #308 composition the broker carries #308's richer route
        # (exact-stop -> this broker's reconcile mode -> retry start --resume)
        # wherever it applies; the generic phrasing was the pre-#308 form.
        self.assertIn("reconcile mode, then retry start --resume", broker)
        self.assertIn("def _emit", broker)
        holder = (REPO / "scripts" / "kaola-acp-holder.py").read_text(encoding="utf-8")
        self.assertNotIn("kaola-recovery-routes", holder)
        for name in ("kaola-acp.py", "kaola-dispatch.py", "kaola-locate.py"):
            text = (REPO / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("_load_recovery_routes", text, name)
        render = (REPO / "scripts" / "render-skills.py").read_text(encoding="utf-8")
        self.assertIn('result["scripts/kaola-recovery-routes.py"]', render)
        self.assertIn(
            '(shared_root / "kaola-recovery-routes.py", "scripts/kaola-recovery-routes.py")',
            render,
        )

    def test_host_restart_docs_and_registry(self) -> None:
        restart = (REPO / "templates" / "kaola-delegator" / "references" / "host-restart.md").read_text(encoding="utf-8")
        for needle in (
            "start",
            "without `--resume`",
            'capture --repo "$PROJECT" --session "$HOST" --lines 200',
            "list --repo",
            "--include-dead",
            "delegator view",
            "Exact-stop",
            "does not auto-reap",
            "Never re-claim, re-dispatch, or redo",
            "existing_host",
            "status --repo",
        ):
            self.assertIn(needle, restart, needle)
        handoff = (REPO / "templates" / "kaola-delegator" / "references" / "handoff.md.tmpl").read_text(encoding="utf-8")
        self.assertIn("host-restart.md", handoff)
        self.assertIn("On proven failure", handoff)
        api = (REPO / "docs" / "api.md").read_text(encoding="utf-8")
        self.assertIn("## Recovery routes (Issue #309)", api)
        self.assertIn("scripts/kaola-recovery-routes.py", api)
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = changelog.split("## 0.9.9", 1)[0]
        self.assertIn("Seats: restart not required", unreleased)
        self.assertNotIn("Seats: restart required", unreleased)
        self.assertIn("Issue #309", unreleased)
        validate = (REPO / "scripts" / "validate.sh").read_text(encoding="utf-8")
        self.assertEqual(validate.count('"test-issue-309-recovery-routes.py"'), 2)
        route = self.routes.ROUTES["job-occupied"]
        self.assertEqual(route[0], "route")
        self.assertIn("Exact-stop", route[1])
        self.assertIn("fresh Host", route[1])
        self.assertIn("does not auto-reap", route[1])
        self.assertIn("capture --lines 200", route[1])
        self.assertIn("delegator view", route[1])


if __name__ == "__main__":
    unittest.main()
