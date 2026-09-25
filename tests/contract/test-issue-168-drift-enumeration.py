#!/usr/bin/env python3
"""Issue #179: one constant holds the ``reported_drift`` vocabulary.

``seat_freshness`` is driven for real (no stub) over recorded-path fixtures,
and every value it emits must be a member of ``REPORTED_DRIFT_VALUES``. The
prose surfaces name the ``reported_drift`` field instead of listing values, so
this also guards against re-enumeration - a list in prose could drift from the
constant, which is the problem #168 tried to patch with a hard-coded list.
"""

from __future__ import annotations

import ast
import importlib.util
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"

# The prose surfaces that describe ``reported_drift``. Each must name the field
# and must not spell out its values.
SURFACES = (
    PROJECT / "docs" / "api.md",
    PROJECT / "templates" / "references" / "acp.md.tmpl",
    PROJECT / "templates" / "orchestrator" / "references" / "zcode-host-dispatch.md.tmpl",
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DriftVocabularyTests(unittest.TestCase):
    def test_the_constant_is_the_only_emitted_vocabulary(self) -> None:
        """Every value the real ``seat_freshness`` emits is a member.

        Two fixtures drive every reported branch: an unrecorded build with a
        changed CLI file, a recorded path that no longer resolves, and changed
        restart-required bytes of an exempt checkout; then no recorded
        revision against a locator pin. Together they reach every member, and
        the exercised set is derived from the constant rather than restated.
        """
        acp = load_module(CLI, "acp179")
        self.assertIsInstance(acp.REPORTED_DRIFT_VALUES, tuple)
        self.assertEqual(len(set(acp.REPORTED_DRIFT_VALUES)),
                         len(acp.REPORTED_DRIFT_VALUES),
                         acp.REPORTED_DRIFT_VALUES)
        # The locator registration pin, isolated from this machine's own.
        acp.registration_pin = lambda: "a" * 40
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "checkout" / "scripts"
            tree.mkdir(parents=True)

            def recorded(name: str) -> dict:
                return {"path": str(tree / name), "sha256": "0" * 64}

            for name in ("kaola-acp.py", "kaola-acp-holder.py"):
                (tree / name).write_bytes(b"changed on disk\n")
            facts = {
                # No runner_build: build-unrecorded.
                "accepted_revision": "b" * 40,
                "baseline_exempt": True,
                "script_paths": {
                    "kaola-acp.py": recorded("kaola-acp.py"),
                    "kaola-acp-holder.py": recorded("kaola-acp-holder.py"),
                    "kaola-tmux.sh": recorded("gone/kaola-tmux.sh"),
                },
            }
            fresh = acp.seat_freshness(facts)
            # A pin with no recorded revision is the other half of the pin
            # branch, so revision-unrecorded is reached too.
            unrevisioned = acp.seat_freshness({
                "runner_build": "c" * 12,
                "script_paths": {},
            })
        emitted = set(fresh["reported_drift"]) | set(unrevisioned["reported_drift"])
        self.assertLessEqual(emitted, set(acp.REPORTED_DRIFT_VALUES), fresh)
        # The fixtures really did exercise the whole vocabulary, not an empty
        # list - and this is the constant, not a second hard-coded copy.
        self.assertEqual(emitted, set(acp.REPORTED_DRIFT_VALUES),
                         (fresh["reported_drift"], unrevisioned["reported_drift"]))
        # The values #179 removed are not in the constant.
        self.assertNotIn("install-root-mismatch", acp.REPORTED_DRIFT_VALUES)
        self.assertNotIn("quota-drift", acp.REPORTED_DRIFT_VALUES)

    def test_every_append_in_seat_freshness_uses_the_constant(self) -> None:
        """A source guard: no new literal can bypass the constant.

        The real behavioral proof is the test above. This keeps a future
        ``reported.append("new-value")`` from being added beside the constant
        instead of inside it.
        """
        acp = load_module(CLI, "acp179src")
        tree = ast.parse(CLI.read_text(encoding="utf-8"))
        function = next(
            (node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef) and node.name == "seat_freshness"),
            None)
        self.assertIsNotNone(function, "seat_freshness not found")
        literals: set[str] = set()
        appends = 0
        for node in ast.walk(function):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "append"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "reported"):
                continue
            appends += 1
            # Every string constant anywhere in the appended expression -
            # this is what catches the ternary that carries two values.
            for inner in ast.walk(node):
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                    literals.add(inner.value)
        self.assertGreaterEqual(appends, 4, "no reported.append calls found")
        self.assertLessEqual(literals, set(acp.REPORTED_DRIFT_VALUES),
                             sorted(literals - set(acp.REPORTED_DRIFT_VALUES)))

    def test_prose_surfaces_name_the_field_without_listing_values(self) -> None:
        """No surface may enumerate values beside the constant."""
        acp = load_module(CLI, "acp179prose")
        for surface in SURFACES:
            text = surface.read_text(encoding="utf-8")
            self.assertIn("reported_drift", text, surface)
            for value in acp.REPORTED_DRIFT_VALUES:
                self.assertNotIn(value, text,
                                 f"{surface} enumerates {value!r}; name the "
                                 "reported_drift field instead")

    def test_the_removed_vocabulary_is_not_described_anywhere(self) -> None:
        for surface in SURFACES + (
            PROJECT / "scripts" / "kaola-acp.py",
            PROJECT / "templates" / "orchestrator" / "references" / "host-startup.md.tmpl",
        ):
            text = surface.read_text(encoding="utf-8")
            self.assertNotIn("install-root-mismatch", text, surface)
            self.assertNotIn("quota-drift", text, surface)

    def test_every_holder_sibling_module_is_restart_required(self) -> None:
        """A holder-loaded sibling cannot drift into the report-only bucket.

        The holder imports ``SIBLING_MODULES`` at startup and never re-imports
        them, so a running seat only picks up their new bytes by restarting.
        """
        acp = load_module(CLI, "acp179sib")
        holder = load_module(PROJECT / "scripts" / "kaola-acp-holder.py", "holder179")
        self.assertTrue(holder.SIBLING_MODULES, "no sibling modules to check")
        for name in holder.SIBLING_MODULES:
            self.assertTrue(acp._restart_required_name(name),
                            f"{name} is holder-loaded but not restart-required")


if __name__ == "__main__":
    unittest.main()
