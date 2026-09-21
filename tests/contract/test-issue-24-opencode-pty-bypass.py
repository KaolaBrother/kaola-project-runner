#!/usr/bin/env python3
"""Issue #24 RED contract: keep OpenCode ACP without skip; document PTY --auto bypass.

Measurement found no OpenCode ACP skip-all. Default transport stays ACP
(``opencode acp`` with no skip argv). PTY ``--auto`` remains the bypass via
``--transport pty``. Do not invent process-time auto-permit or inject
``OPENCODE_PERMISSION`` / permission config as a fake skip.

Issue #112 re-measured the no-skip fact on OpenCode V2 ``2.0.11`` instead of
inheriting it: ``session/request_permission`` offers exactly ``allow_once``,
``allow_always`` and ``reject_once``, and ``session/new`` advertises only the
``model``/``effort``/``mode`` config options -- no skip-all in either place.
The same upgrade removed the ``--mini`` flag ("Unrecognized flag: --mini in
command opencode"), so the PTY bypass is now ``<repo> --auto``; ``--auto`` is
still a top-level V2 flag and is still the knob this contract protects.

The Agent-facing gap on this baseline is empty ``acp_quirks`` (generated Skill
says known quirks are blank). README/CHANGELOG/launch_summary notes are not
this contract.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import re
import subprocess
import unittest
from pathlib import Path
from unittest import mock


PROJECT = Path(__file__).resolve().parents[2]
ACP = PROJECT / "scripts" / "kaola-acp.py"
HOLDER = PROJECT / "scripts" / "kaola-acp-holder.py"
RUNNER = PROJECT / "scripts" / "kaola-tmux.sh"
OPENCODE_ADAPTER = PROJECT / "scripts" / "adapters" / "opencode.sh"
MANIFEST = PROJECT / "platforms" / "opencode.yaml"
SKILL = PROJECT / "skills" / "opencode-kaola-project-runner" / "SKILL.md"
ACP_REF = PROJECT / "skills" / "opencode-kaola-project-runner" / "references" / "acp.md"
SKILL_TMPL = PROJECT / "templates" / "SKILL.md.tmpl"
ACP_TMPL = PROJECT / "templates" / "references" / "acp.md.tmpl"
RENDERER = PROJECT / "scripts" / "render-skills.py"

SKIP_ARGV = (
    "--auto",
    "--yolo",
    "--dangerously-skip-permissions",
    "--always-approve",
    "--skip-permissions",
    "--yes",
)

START_SOURCES = (ACP, HOLDER, RUNNER, OPENCODE_ADAPTER)


def load_renderer():
    spec = importlib.util.spec_from_file_location("kaola_render_skills", RENDERER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_manifest(path: Path) -> dict[str, str]:
    return load_renderer().parse_manifest(path)


def acp_skip_mode(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "ACP_SKIP_MODE":
                value = ast.literal_eval(node.value)
                if not isinstance(value, dict):
                    raise AssertionError("ACP_SKIP_MODE is not a dict")
                return {str(key): str(val) for key, val in value.items()}
    raise AssertionError("ACP_SKIP_MODE assignment not found")


def acp_start_skip_case(runner: str) -> str:
    match = re.search(
        r'elif \[\[ "\$command_name" == start \]\]; then.*?case "\$platform" in(.*?)esac',
        runner,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError("ACP start skip-mode case not found in kaola-tmux.sh")
    return match.group(1)


def skill_quirks_pointer(text: str) -> str | None:
    """Issue #65: the quirks string is no longer duplicated verbatim in the
    budgeted SKILL.md. The Skill names the on-demand reference that carries it;
    `test_generated_acp_reference_quirks_document_pty_bypass` checks the content
    there, so the quirk is still documented by the generated Skill."""
    match = re.search(
        r"ACP quirks are in \[references/acp\.md\]\(references/acp\.md\)", text)
    return match.group(0) if match else None


def acp_reference_quirks(text: str) -> str | None:
    match = re.search(r"Platform quirks:\s*(.*)", text)
    if match is None:
        return None
    return match.group(1).strip().rstrip(".")


def class_method(tree: ast.AST, class_name: str, method_name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return item
    raise AssertionError(f"{class_name}.{method_name} not found")


def request_permission_if(func: ast.FunctionDef, source: str) -> ast.If:
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        test = ast.get_source_segment(source, node.test) or ""
        if "request_permission" in test:
            return node
    raise AssertionError("session/request_permission branch not found")


class Issue24KeepAcpWithoutSkip(unittest.TestCase):
    """Default OpenCode ACP stays ``opencode acp`` with no measured skip applied."""

    def test_acp_command_is_opencode_acp_without_skip_argv(self) -> None:
        command = parse_manifest(MANIFEST)["acp_command"]
        self.assertEqual(command, "opencode acp")
        for flag in SKIP_ARGV:
            self.assertNotIn(
                flag,
                command.split(),
                f"OpenCode ACP command must not carry skip argv {flag}: {command!r}",
            )

    def test_default_transport_remains_acp(self) -> None:
        self.assertEqual(parse_manifest(MANIFEST)["default_transport"], "acp")

    def test_acp_skip_mode_does_not_map_opencode(self) -> None:
        mapping = acp_skip_mode(ACP.read_text(encoding="utf-8"))
        self.assertNotIn(
            "opencode",
            mapping,
            "ACP_SKIP_MODE must not invent an OpenCode skip-all mode: "
            f"{mapping!r}",
        )

    def test_tmux_acp_start_does_not_forward_skip_mode_for_opencode(self) -> None:
        block = acp_start_skip_case(RUNNER.read_text(encoding="utf-8"))
        self.assertNotRegex(
            block,
            r"\bopencode\)",
            "default ACP start must not forward a skip --mode for opencode: "
            f"{block!r}",
        )


class Issue24PtyAutoBypass(unittest.TestCase):
    """PTY launch still supplies --auto as the documented bypass knob."""

    def test_opencode_pty_launch_still_passes_auto(self) -> None:
        body = OPENCODE_ADAPTER.read_text(encoding="utf-8")
        self.assertRegex(
            body,
            r"ADAPTER_LAUNCH_ARGS=\(\"\$launch_repo\" --auto\)",
            "PTY adapter must still launch the repo with --auto",
        )

    def test_opencode_pty_launch_drops_the_v1_only_flags(self) -> None:
        """Issue #112: V2 rejects each of these outright, so a surviving
        occurrence is a launch that aborts on 2.0.11, not a stale comment."""
        body = OPENCODE_ADAPTER.read_text(encoding="utf-8")
        launch = re.search(
            r"adapter_build_launch\(\) \{(.*?)^\}", body, flags=re.DOTALL | re.MULTILINE
        )
        self.assertIsNotNone(launch, "adapter_build_launch not found")
        args = re.findall(r"ADAPTER_LAUNCH_ARGS[+]?=\((.*?)\)", launch.group(1))
        self.assertTrue(args, "no ADAPTER_LAUNCH_ARGS assignment found")
        for argv in args:
            for flag in ("--mini", "--model", "--variant"):
                self.assertNotIn(
                    flag,
                    argv,
                    f"V2 rejects top-level {flag}; it must not reach the launch argv: {argv!r}",
                )

    def test_launch_summary_does_not_steer_default_start_onto_pty(self) -> None:
        summary = parse_manifest(MANIFEST)["launch_summary"]
        first = summary.split(".", 1)[0]
        self.assertNotRegex(
            first,
            r"--transport\s+pty",
            "Launch instruction must not lead with --transport pty; "
            "default_transport is still acp: "
            f"{first!r}",
        )
        self.assertRegex(
            summary,
            r"--transport\s+pty",
            f"launch_summary must still name --transport pty as the bypass: {summary!r}",
        )
        self.assertRegex(
            summary,
            r"--auto\b",
            f"launch_summary must still name PTY --auto: {summary!r}",
        )
        self.assertRegex(
            summary.lower(),
            r"default acp",
            "launch_summary must state that default ACP has no skip, "
            f"not only the PTY argv: {summary!r}",
        )


class Issue24DocumentGeneratedAcpSurface(unittest.TestCase):
    """Generated Skill ACP surface must name the no-skip fact and PTY bypass."""

    def assert_documents_pty_auto_bypass(self, quirks: str, label: str) -> None:
        text = (quirks or "").strip()
        self.assertTrue(
            text,
            f"{label} is empty; Agent-facing ACP quirks must document that "
            "OpenCode ACP has no skip-all and that PTY --auto via "
            "--transport pty is the bypass",
        )
        self.assertRegex(
            text,
            r"--auto\b",
            f"{label} must name PTY --auto as the bypass knob: {text!r}",
        )
        self.assertRegex(
            text,
            r"--transport\s+pty",
            f"{label} must name --transport pty as the bypass selector: {text!r}",
        )
        lowered = text.lower()
        self.assertRegex(
            lowered,
            r"\b(skip(?:-all)?|auto-approve|permission)\b",
            f"{label} must state the ACP skip/permission gap, not only PTY flags: "
            f"{text!r}",
        )
        self.assertNotRegex(
            text,
            r"opencode\s+acp\s+--(?:auto|yolo|dangerously-skip-permissions|always-approve)",
            f"{label} must not advertise skip argv on opencode acp: {text!r}",
        )

    def test_templates_still_interpolate_acp_quirks(self) -> None:
        # The quirks travel once, in the on-demand ACP reference; the worker
        # Skill points at it rather than carrying a second copy.
        self.assertNotIn("{{ACP_QUIRKS}}", SKILL_TMPL.read_text(encoding="utf-8"))
        self.assertIn("references/acp.md", SKILL_TMPL.read_text(encoding="utf-8"))
        self.assertIn("{{ACP_QUIRKS}}", ACP_TMPL.read_text(encoding="utf-8"))

    def test_manifest_acp_quirks_documents_pty_bypass(self) -> None:
        quirks = parse_manifest(MANIFEST)["acp_quirks"]
        self.assert_documents_pty_auto_bypass(quirks, "platforms/opencode.yaml acp_quirks")

    def test_generated_skill_points_at_the_quirks_reference(self) -> None:
        body = SKILL.read_text(encoding="utf-8")
        self.assertIsNotNone(
            skill_quirks_pointer(body),
            "generated SKILL.md must name the reference carrying this platform's quirks",
        )
        self.assertIn("`opencode acp`", body)
        self.assertNotRegex(
            body,
            r"opencode\s+acp\s+--(?:auto|yolo|dangerously-skip-permissions)",
        )

    def test_generated_acp_reference_quirks_document_pty_bypass(self) -> None:
        body = ACP_REF.read_text(encoding="utf-8")
        quirks = acp_reference_quirks(body)
        self.assertIsNotNone(quirks, "generated references/acp.md missing Platform quirks")
        self.assert_documents_pty_auto_bypass(quirks or "", "generated references/acp.md quirks")

    def test_renderer_copies_manifest_quirks_into_skill_templates(self) -> None:
        renderer = load_renderer()
        manifest = renderer.parse_manifest(MANIFEST)
        skill = renderer.render(
            SKILL_TMPL.read_text(encoding="utf-8"), manifest, SKILL_TMPL
        )
        acp = renderer.render(ACP_TMPL.read_text(encoding="utf-8"), manifest, ACP_TMPL)
        self.assertIsNotNone(
            skill_quirks_pointer(skill), "rendered SKILL.md.tmpl points at the quirks reference"
        )
        self.assert_documents_pty_auto_bypass(
            acp_reference_quirks(acp) or "",
            "rendered acp.md.tmpl quirks",
        )


class Issue24NoInventedSkipSubstitute(unittest.TestCase):
    """No process-time auto-permit and no OPENCODE_PERMISSION skip overlay."""

    def test_holder_does_not_auto_answer_request_permission(self) -> None:
        source = HOLDER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        func = class_method(tree, "Holder", "on_agent_request")
        branch = request_permission_if(func, source)
        block = ast.get_source_segment(source, branch) or ""
        self.assertIn("pending_permissions", block)
        self.assertNotIn(
            "send_message",
            block,
            "request_permission must stay pending for explicit permit, not auto-reply",
        )
        self.assertNotIn("op_permit", block)
        self.assertNotRegex(block, r"allow_always|allow_once")
        self.assertNotIn("opencode", block.lower())

    def test_start_sources_do_not_set_opencode_permission_env(self) -> None:
        for path in START_SOURCES:
            body = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "OPENCODE_PERMISSION",
                body,
                f"{path.relative_to(PROJECT)} must not set OPENCODE_PERMISSION "
                "as an ACP skip-all substitute",
            )

    def test_opencode_adapter_model_env_does_not_inject_permission(self) -> None:
        body = OPENCODE_ADAPTER.read_text(encoding="utf-8")
        self.assertNotRegex(
            body,
            r'["\']permission["\']',
            "adapter start must not mutate permission config as a fake skip",
        )
        snippet = re.search(
            r"adapter_prepare_model_environment\(\) \{(.*?)(?:^adapter_|\Z)",
            body,
            flags=re.DOTALL | re.MULTILINE,
        )
        self.assertIsNotNone(snippet, "adapter_prepare_model_environment not found")
        model_env = snippet.group(1) if snippet else ""
        self.assertNotIn("permission", model_env.lower())


PROXY = "http://proxy.invalid:3128"

# (case env, expected child additions). One table drives both implementations.
LOOPBACK_CASES = (
    ({}, {}),
    ({"NO_PROXY": "corp.example"}, {}),
    ({"HTTP_PROXY": PROXY},
     {"NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}),
    ({"https_proxy": PROXY, "NO_PROXY": "corp.example"},
     {"NO_PROXY": "corp.example,127.0.0.1,localhost"}),
    ({"HTTP_PROXY": PROXY, "NO_PROXY": "corp.example, localhost"},
     {"NO_PROXY": "corp.example, localhost,127.0.0.1"}),
    ({"HTTP_PROXY": PROXY, "NO_PROXY": "a,", "no_proxy": "b"},
     {"NO_PROXY": "a,127.0.0.1,localhost", "no_proxy": "b,127.0.0.1,localhost"}),
    ({"HTTPS_PROXY": PROXY, "no_proxy": "127.0.0.1,localhost"}, {}),
    ({"HTTP_PROXY": PROXY, "NO_PROXY": "*"}, {}),
)

BASH_LOOPBACK = (
    'source "$1"; opencode_loopback_env; '
    'for kv in ${OPENCODE_LOOPBACK_ENV[@]+"${OPENCODE_LOOPBACK_ENV[@]}"}; do printf "%s\\n" "$kv"; done'
)


def load_acp():
    spec = importlib.util.spec_from_file_location("kaola_acp_issue_112", ACP)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def bash_loopback(case: dict[str, str]) -> dict[str, str]:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), **case}
    out = subprocess.run(
        ["bash", "-c", BASH_LOOPBACK, "bash", str(OPENCODE_ADAPTER)],
        env=env, capture_output=True, text=True, check=True,
    ).stdout
    return dict(line.split("=", 1) for line in out.splitlines() if line)


class Issue112LoopbackProxyBypass(unittest.TestCase):
    """Issue #112: OpenCode V2 reaches its own server over loopback HTTP, so a
    forward proxy without a loopback NO_PROXY entry breaks every ACP session
    method (live-measured ClientError) and hangs the PTY TUI. The opencode
    child, and only the child, gets the missing loopback entries appended."""

    def test_acp_rule_matches_the_case_table(self) -> None:
        module = load_acp()
        for case, expected in LOOPBACK_CASES:
            with self.subTest(case=case):
                self.assertEqual(module.loopback_no_proxy(dict(case)), expected)

    def test_pty_rule_is_the_same_rule(self) -> None:
        for case, expected in LOOPBACK_CASES:
            with self.subTest(case=case):
                self.assertEqual(bash_loopback(case), expected)

    def test_acp_child_env_gets_it_and_the_runner_env_does_not(self) -> None:
        module = load_acp()
        args = argparse.Namespace(platform="opencode", manifest={})
        with mock.patch.dict(os.environ, {"HTTP_PROXY": PROXY}, clear=True):
            env = module.agent_environment(args)
            self.assertEqual(env["NO_PROXY"], "127.0.0.1,localhost")
            self.assertEqual(env["no_proxy"], "127.0.0.1,localhost")
            self.assertEqual(env["HTTP_PROXY"], PROXY, "the proxy itself is left alone")
            self.assertEqual(dict(os.environ), {"HTTP_PROXY": PROXY},
                             "the Runner's own environment must not be modified")

    def test_acp_injection_is_scoped_to_opencode(self) -> None:
        module = load_acp()
        with mock.patch.dict(os.environ, {"HTTP_PROXY": PROXY}, clear=True):
            env = module.agent_environment(argparse.Namespace(platform="codex", manifest={}))
        self.assertNotIn("NO_PROXY", env)
        self.assertNotIn("no_proxy", env)

    def test_no_forward_proxy_leaves_the_acp_child_untouched(self) -> None:
        module = load_acp()
        with mock.patch.dict(os.environ, {"NO_PROXY": "corp.example"}, clear=True):
            env = module.agent_environment(argparse.Namespace(platform="opencode", manifest={}))
        self.assertEqual(env, {"NO_PROXY": "corp.example"})

    def test_pty_child_env_carries_it_with_and_without_a_model(self) -> None:
        script = (
            'source "$1"; RESOLVED_MODEL_ID="$2"; RESOLVED_MODEL_EFFORT=""; PYTHON_BIN=python3; '
            'adapter_prepare_model_environment; '
            'for kv in ${ADAPTER_MODEL_ENV[@]+"${ADAPTER_MODEL_ENV[@]}"}; do printf "%s\\n" "${kv%%=*}"; done'
        )
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HTTP_PROXY": PROXY}
        for model, names in (("", ["NO_PROXY", "no_proxy"]),
                             ("zhipuai-coding-plan/glm-5.3",
                              ["NO_PROXY", "no_proxy", "OPENCODE_CONFIG_CONTENT"])):
            with self.subTest(model=model):
                out = subprocess.run(
                    ["bash", "-c", script, "bash", str(OPENCODE_ADAPTER), model],
                    env=env, capture_output=True, text=True, check=True,
                ).stdout.split()
                self.assertEqual(out, names)

    def test_preflight_reports_what_the_child_sees(self) -> None:
        script = (
            'source "$1"; repo=/nonexistent; RUNTIME_BIN=/usr/bin/true; adapter_preflight; '
            'printf "%s\\n" "${PREFLIGHT_DETAIL##*loopback=}"'
        )
        for case, state in (({}, "direct"),
                            ({"HTTP_PROXY": PROXY}, "ensured"),
                            ({"HTTP_PROXY": PROXY, "NO_PROXY": "127.0.0.1,localhost"}, "excluded")):
            with self.subTest(case=case):
                env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                       "HOME": "/nonexistent", **case}
                out = subprocess.run(
                    ["bash", "-c", script, "bash", str(OPENCODE_ADAPTER)],
                    env=env, capture_output=True, text=True, check=True,
                ).stdout.strip()
                self.assertEqual(out, state)


if __name__ == "__main__":
    unittest.main()
