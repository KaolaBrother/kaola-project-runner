#!/usr/bin/env python3
"""Issue #24 contract: keep OpenCode ACP without skip; permit settles each request.

Measurement found no OpenCode ACP skip-all. The ACP command stays
``opencode acp`` with no skip argv. Issue #130 retired the PTY transport, so
the former PTY ``--auto`` bypass is gone: there is no skip-all on any path and
every ``session/request_permission`` is settled by an explicit ``permit``. Do
not invent process-time auto-permit or inject ``OPENCODE_PERMISSION`` /
permission config as a fake skip.

Issue #112 re-measured the no-skip fact on OpenCode V2 ``2.0.11`` instead of
inheriting it: ``session/request_permission`` offers exactly ``allow_once``,
``allow_always`` and ``reject_once``, and ``session/new`` advertises only the
``model``/``effort``/``mode`` config options -- no skip-all in either place.
The same upgrade removed the ``--mini`` flag ("Unrecognized flag: --mini in
command opencode").

The Agent-facing surface is ``acp_quirks`` (manifest, rendered into the
generated ``references/acp.md``): it must state the no-skip-all fact and that
permit settles each request. README/CHANGELOG notes are not this contract.
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
    """The tmux entry's platform-mode table, if this build still has one.

    Issue #181 removed it: the per-platform default lives once, in
    ``kaola-acp.py``'s ``ACP_SKIP_MODE``. An empty string therefore means
    "nothing is forwarded by the shell", which is the no-skip outcome these
    tests assert for opencode.
    """
    match = re.search(
        r'case "\$platform" in(.*?)esac',
        runner,
        flags=re.DOTALL,
    )
    return match.group(1) if match is not None else ""


def skill_quirks_pointer(text: str) -> str | None:
    """Issue #65: the quirks string is no longer duplicated verbatim in the
    budgeted SKILL.md. The Skill names the on-demand reference that carries it;
    `test_generated_acp_reference_quirks_document_no_skip_all` checks the content
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

    def test_manifest_no_longer_declares_a_transport_choice(self) -> None:
        # Issue #130: ACP is the only transport; the manifest key is gone.
        self.assertNotIn("default_transport", parse_manifest(MANIFEST))

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


class Issue24LaunchSummaryStatesPermit(unittest.TestCase):
    """The platform reference launch summary states the ACP permission fact."""

    def test_launch_summary_states_no_skip_all_and_permit(self) -> None:
        summary = parse_manifest(MANIFEST)["launch_summary"]
        self.assertNotRegex(
            summary,
            r"--transport\s+pty",
            f"launch_summary must not offer the retired PTY transport: {summary!r}",
        )
        self.assertRegex(
            summary,
            r"ACP has no skip-all",
            f"launch_summary must state that ACP has no skip-all: {summary!r}",
        )
        self.assertRegex(
            summary,
            r"permit settles each request",
            f"launch_summary must state that permit settles each request: {summary!r}",
        )


class Issue24DocumentGeneratedAcpSurface(unittest.TestCase):
    """Generated Skill ACP surface must name the no-skip fact and permit."""

    def assert_documents_no_skip_all(self, quirks: str, label: str) -> None:
        text = (quirks or "").strip()
        self.assertTrue(
            text,
            f"{label} is empty; Agent-facing ACP quirks must document that "
            "OpenCode ACP has no skip-all and that permit settles each request",
        )
        self.assertRegex(
            text,
            r"no ACP skip-all|there is no skip-all",
            f"{label} must state the ACP no-skip-all fact: {text!r}",
        )
        self.assertRegex(
            text,
            r"permit settles each request",
            f"{label} must state that permit settles each request: {text!r}",
        )
        self.assertNotRegex(
            text,
            r"--transport\s+pty",
            f"{label} must not offer the retired PTY transport: {text!r}",
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

    def test_manifest_acp_quirks_documents_no_skip_all(self) -> None:
        quirks = parse_manifest(MANIFEST)["acp_quirks"]
        self.assert_documents_no_skip_all(quirks, "platforms/opencode.yaml acp_quirks")

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

    def test_generated_acp_reference_quirks_document_no_skip_all(self) -> None:
        body = ACP_REF.read_text(encoding="utf-8")
        quirks = acp_reference_quirks(body)
        self.assertIsNotNone(quirks, "generated references/acp.md missing Platform quirks")
        self.assert_documents_no_skip_all(quirks or "", "generated references/acp.md quirks")

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
        self.assert_documents_no_skip_all(
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
