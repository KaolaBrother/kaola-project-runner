#!/usr/bin/env python3
"""Issue #88 RED contract: the permission default is per platform, and the
OpenCode steering evidence carries its own version.

Two release-review defects on the frozen ``f39d940`` line, both prompt-level:

1. The generated main Skill's ``Defaults`` table said "Existing Runner default
   bypass start". Six platforms do apply an advertised ACP skip-all option
   (claude-code/codex/devin ``mode``, droid ``autonomy_level``, kimi-cli/zcode
   ``mode``), but cursor-cli and grok only carry a launch flag with
   ``acp_mode_config_id`` empty, and OpenCode's ACP surface has no skip-all of
   any kind. Issue #98 added a fourth member with the opposite safety posture:
   dsh advertises no skip-all because its ACP composition sends no permission
   request at all, so for dsh there is no gate to skip and no request to
   settle -- see ``DshHasNoApprovalGateAtAll`` below. A host reading that row as an all-platform guarantee stops
   expecting the permission request that ``test-issue-76-permission-wake.py``
   already models, and stops settling it with ``permit``. The correction states
   a possibility, not a certainty: a launch flag can still suppress the request,
   so "may arise" is what the evidence supports and "will arrive" is not.

2. ``platforms/opencode.yaml`` carried ``acp_verified_versions cli=1.18.29``
   while its ``steering_summary`` reported a ``-32601`` probe run on 1.18.17.
   Read together those assert a current-version result that was never measured.

The fix is wording and evidence marking only. This contract therefore pins the
*claims*, never a mechanism: no auto-approval, no new gate, no adapter change.
It must distinguish the old misleading sentence from the corrected one, so the
old bytes fail every assertion below and the corrected bytes pass.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
MAIN_SKILL = PROJECT / "skills" / "kaola-project-runner" / "SKILL.md"
MAIN_TMPL = PROJECT / "templates" / "orchestrator" / "SKILL.md.tmpl"
OPENCODE_MANIFEST = PROJECT / "platforms" / "opencode.yaml"
CURSOR_MANIFEST = PROJECT / "platforms" / "cursor-cli.yaml"
OPENCODE_STEERING = (
    PROJECT / "skills" / "opencode-kaola-project-runner" / "references" / "steering.md"
)
PLATFORMS = PROJECT / "platforms"
README = PROJECT / "README.md"
DSH_MANIFEST = PROJECT / "platforms" / "dsh.yaml"
DSH_ACP_REF = PROJECT / "skills" / "dsh-kaola-project-runner" / "references" / "acp.md"
OPENCODE_SKILL = PROJECT / "skills" / "opencode-kaola-project-runner" / "SKILL.md"
TMUX = PROJECT / "scripts" / "kaola-tmux.sh"
API_DOC = PROJECT / "docs" / "api.md"

# The exact sentence the release review rejected.
RETIRED_SENTENCE = "Existing Runner default bypass start"

# Platforms whose ACP surface advertises no skip-all option. Derived, not
# asserted from memory: see ``test_no_skip_all_platforms_are_still_the_derived_set``.
NO_ADVERTISED_ACP_SKIP_ALL = {"cursor-cli", "dsh", "grok", "opencode"}


def manifest_values(path: Path) -> dict[str, str]:
    """Flat ``key: "value"`` manifest reader, same shape the renderer expects."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r'^([a-z_]+):\s*"(.*)"\s*$', line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def flowed(text: str) -> str:
    """Collapse wrapping so a prose assertion pins the claim, not the line breaks."""
    return re.sub(r"\s+", " ", text)


def runtime_names_without_verified_skip_all() -> set[str]:
    """Derived from the manifests, never hardcoded: a platform has no verified ACP
    skip-all when it advertises no mode/autonomy config option for one."""
    names = set()
    for path in sorted(PLATFORMS.glob("*.yaml")):
        values = manifest_values(path)
        if not values.get("acp_mode_config_id"):
            names.add(values["runtime_name"])
    return names


def platforms_with_native_steering(value: str) -> set[str]:
    """Derived from the manifests: the one source of truth for who steers natively."""
    return {
        manifest_values(path)["id"]
        for path in sorted(PLATFORMS.glob("*.yaml"))
        if manifest_values(path)["native_steering"] == value
    }


def permissions_row(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("| Permissions |"):
            return line
    raise AssertionError("Defaults table has no Permissions row")


class MainSkillStatesAPerPlatformDefault(unittest.TestCase):
    """The main Skill must not promise one bypass for all ten platforms."""

    def test_retired_all_platform_bypass_sentence_is_gone(self) -> None:
        for label, path in (("generated main Skill", MAIN_SKILL), ("orchestrator template", MAIN_TMPL)):
            with self.subTest(surface=label):
                self.assertNotIn(
                    RETIRED_SENTENCE,
                    path.read_text(encoding="utf-8"),
                    f"{label} still promises {RETIRED_SENTENCE!r}, which reads as an "
                    "all-platform guarantee; OpenCode ACP has no skip-all at all",
                )

    def test_permissions_row_binds_the_default_to_the_platform(self) -> None:
        row = permissions_row(MAIN_SKILL.read_text(encoding="utf-8"))
        self.assertRegex(
            row,
            r"(?i)per[- ]platform",
            f"Permissions row must source the default from the platform: {row!r}",
        )
        self.assertRegex(
            row,
            r"not one global bypass",
            f"Permissions row must deny a global bypass reading: {row!r}",
        )

    def test_permissions_row_keeps_its_existing_duties(self) -> None:
        """The correction must not drop what the row already promised."""
        row = permissions_row(MAIN_SKILL.read_text(encoding="utf-8"))
        self.assertIn("Honor explicit permission-mode overrides.", row)
        self.assertIn("within authorized scope", row)


class MainSkillHandlesTheNoSkipAllCase(unittest.TestCase):
    """OpenCode advertises no skip-all, so a request may still arise -- may, not will."""

    def test_the_rule_covers_any_platform_without_a_verified_skip_all(self) -> None:
        """Cursor advertises no ACP skip-all option and Grok carries only a launch
        flag, exactly like OpenCode's case. A rule naming one platform leaves the
        other two uncovered, and would go stale the moment a manifest changes."""
        text = flowed(MAIN_SKILL.read_text(encoding="utf-8"))
        self.assertIn(
            "With no verified ACP skip-all",
            text,
            "main Skill must state a general rule, not a single-platform fact",
        )
        for runtime in runtime_names_without_verified_skip_all():
            self.assertNotIn(
                f"{runtime} has no ACP skip-all",
                text,
                f"main Skill must not single out {runtime}: the rule covers every "
                "platform with no verified ACP skip-all",
            )

    def test_the_claim_is_possibility_not_certainty(self) -> None:
        """Cursor's and Grok's launch flags do suppress approvals. OpenCode is certain
        to have no skip-all and even there a request is not guaranteed; dsh is certain
        to have no gate at all, which the README carries per-platform."""
        text = flowed(MAIN_SKILL.read_text(encoding="utf-8"))
        self.assertIn(
            "permission may still arise",
            text,
            "main Skill must state the possibility, not a certainty",
        )
        for overclaim in (
            "pending permission still arrives",
            "permission always",
            "every worker will request",
        ):
            self.assertNotIn(
                overclaim,
                text,
                f"main Skill must not assert {overclaim!r}: a launch flag can still "
                "suppress the request, so certainty is not measured",
            )

    def test_main_skill_routes_it_to_the_existing_permit_op(self) -> None:
        """Handling, not auto-approval: ``permit`` already exists (Issue #76)."""
        text = flowed(MAIN_SKILL.read_text(encoding="utf-8"))
        self.assertIn(
            "`permit` settles it",
            text,
            "main Skill must route the possible request to the existing permit op",
        )

    def test_main_skill_keeps_the_protective_clauses(self) -> None:
        text = flowed(MAIN_SKILL.read_text(encoding="utf-8"))
        self.assertIn("Bypass is not broader authorization.", text)
        self.assertIn(
            "never force PTY or add a gate",
            text,
            "the correction must keep the do-not-force-PTY / do-not-add-a-gate rule",
        )

    def test_main_skill_claims_no_automatic_approval(self) -> None:
        text = flowed(MAIN_SKILL.read_text(encoding="utf-8"))
        for banned in ("auto-approve", "auto-approval", "automatically approve"):
            self.assertNotIn(
                banned,
                text,
                f"main Skill must not introduce {banned!r}: Issue #88 adds no approval mechanism",
            )


class ReadmeCarriesThePerPlatformSplit(unittest.TestCase):
    """The three-way split is traceable in README, so the main Skill need not spend
    its locked byte budget naming every platform."""

    def test_readme_states_the_three_classes(self) -> None:
        text = flowed(README.read_text(encoding="utf-8"))
        self.assertIn(
            "the default is per platform, not one guarantee across all ten",
            text,
            "README must deny the all-platform reading",
        )
        self.assertIn(
            "apply an advertised ACP skip-all option at start",
            text,
            "README must name the platforms that do apply an advertised option",
        )
        self.assertIn(
            "Cursor and Grok carry only a launch flag",
            text,
            "README must keep Cursor and Grok as launch-flag-only, not as 'no bypass'",
        )
        self.assertIn(
            "OpenCode's default ACP path has none at all",
            text,
            "README must keep OpenCode as the platform with no ACP skip-all",
        )

    def test_readme_states_the_possibility_not_a_certainty(self) -> None:
        text = flowed(README.read_text(encoding="utf-8"))
        self.assertIn("a permission request may still arise", text)

    def test_readme_names_every_platform_without_a_verified_skip_all(self) -> None:
        """The main Skill carries the general rule; README carries the roster, and
        the roster is derived from the manifests so it cannot drift silently."""
        text = flowed(README.read_text(encoding="utf-8"))
        for runtime in runtime_names_without_verified_skip_all():
            self.assertIn(
                runtime,
                text,
                f"README must name {runtime} among the platforms with no verified "
                "ACP skip-all",
            )

    def test_readme_routes_through_the_existing_flow_only(self) -> None:
        """The existing permission_required -> permit path, and nothing new."""
        text = flowed(README.read_text(encoding="utf-8"))
        self.assertIn("`permission_required` carrier event", text)
        self.assertIn("settled with `permit`", text)
        self.assertIn("Neither forcing PTY nor adding a gate", text)


class PlatformFactsStayTheSingleSource(unittest.TestCase):
    """Per-platform traceability: the manifests the wording defers to must hold."""

    def test_no_skip_all_platforms_are_still_the_derived_set(self) -> None:
        derived = set()
        for path in sorted(PLATFORMS.glob("*.yaml")):
            values = manifest_values(path)
            if not values.get("acp_mode_config_id"):
                derived.add(values["id"])
        self.assertEqual(
            derived,
            NO_ADVERTISED_ACP_SKIP_ALL,
            "the set of platforms with no advertised ACP skip-all option changed; "
            "the main Skill wording names cursor-cli and opencode explicitly and "
            "must be revisited with the manifests",
        )

    def test_opencode_still_has_no_acp_skip_all(self) -> None:
        values = manifest_values(OPENCODE_MANIFEST)
        self.assertEqual(values["acp_command"], "opencode acp")
        self.assertIn("no ACP skip-all", values["acp_quirks"])

    def test_cursor_acp_still_carries_the_yolo_launch_flag(self) -> None:
        values = manifest_values(CURSOR_MANIFEST)
        self.assertEqual(values["acp_command"], "cursor-agent --yolo acp")
        self.assertEqual(
            values["acp_mode_config_id"],
            "",
            "Cursor advertises no ACP skip-all option; only the launch flag exists",
        )


class OpenCodeSteeringEvidenceIsVersioned(unittest.TestCase):
    """1.18.17 is history; 1.18.29 was never probed and must read as unknown."""

    def test_summary_marks_the_probe_as_historical(self) -> None:
        summary = manifest_values(OPENCODE_MANIFEST)["steering_summary"]
        self.assertIn("1.18.17", summary, "the probe must keep the version it ran on")
        self.assertRegex(
            summary,
            r"[Hh]istorical evidence",
            f"the 1.18.17 probe must be marked historical: {summary!r}",
        )

    def test_summary_refuses_to_speak_for_the_verified_version(self) -> None:
        values = manifest_values(OPENCODE_MANIFEST)
        summary = values["steering_summary"]
        self.assertIn(
            "1.18.29",
            summary,
            "the summary must name the currently verified version it does NOT cover",
        )
        self.assertIn("cli=1.18.29", values["acp_verified_versions"])
        self.assertRegex(
            summary,
            r"not a measurement of",
            f"the summary must deny that 1.18.17 measured 1.18.29: {summary!r}",
        )
        self.assertRegex(
            summary,
            r"unknown",
            f"the un-probed current version must read as unknown: {summary!r}",
        )

    def test_generated_steering_reference_carries_the_calibration(self) -> None:
        text = OPENCODE_STEERING.read_text(encoding="utf-8")
        for needle in ("1.18.17", "1.18.29", "unknown"):
            self.assertIn(
                needle,
                text,
                f"generated OpenCode steering reference lost {needle!r}",
            )


class OpenCodeCurrentCapabilityIsUnknownEverywhere(unittest.TestCase):
    """The review's finding: marking the summary "unknown" while the manifest still
    said ``unsupported`` left the reference and every steer receipt asserting a
    proven absence. The three surfaces must now agree.

    Scope guard: this changes what the Runner *claims*, never what it *does*. The
    refusal, the error codes, ``available_steer_modes`` and the no-auto-degrade
    rule are asserted unchanged below, and no probe engine is added.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls._tmp.name) / "repo"
        cls.repo.mkdir()
        for argv in (["init", "-q", "."], ["commit", "-q", "--allow-empty", "-m", "x"]):
            subprocess.run(["git", *argv], cwd=cls.repo, check=True,
                           capture_output=True, env={**os.environ,
                                                     "GIT_AUTHOR_NAME": "t",
                                                     "GIT_AUTHOR_EMAIL": "t@t",
                                                     "GIT_COMMITTER_NAME": "t",
                                                     "GIT_COMMITTER_EMAIL": "t@t"})

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def steer(self, platform: str, *extra: str) -> dict:
        """Real CLI, no holder and no session: these paths refuse before any I/O."""
        env = {k: v for k, v in os.environ.items()
               if k != "KAOLA_PROJECT_RUNNER_CANONICAL_REPO"}
        result = subprocess.run(
            ["bash", str(TMUX), platform, "steer", "--repo", str(self.repo),
             "--session", f"{platform}-kaola-i88unk", "--text", "hi", *extra],
            capture_output=True, text=True, env=env, timeout=60)
        return json.loads(result.stdout)

    def test_manifest_current_capability_is_unknown(self) -> None:
        self.assertEqual(
            manifest_values(OPENCODE_MANIFEST)["native_steering"],
            "unknown",
            "the 1.18.17 probe does not measure the verified 1.18.29 build, so the "
            "current capability is unknown, not unsupported",
        )

    def test_the_historical_unsupported_result_is_still_recorded(self) -> None:
        """Marking the current state unknown must not erase what 1.18.17 measured."""
        summary = manifest_values(OPENCODE_MANIFEST)["steering_summary"]
        self.assertIn("1.18.17", summary)
        self.assertIn("-32601", summary)
        self.assertRegex(summary, r"[Hh]istorical evidence")

    def test_generated_worker_skill_claims_no_proven_absence(self) -> None:
        body = OPENCODE_SKILL.read_text(encoding="utf-8")
        self.assertIn(
            "No native mid-turn entry has been verified",
            body,
            "an unknown surface must read as unverified",
        )
        self.assertNotIn(
            "exposes no native mid-turn entry",
            body,
            "an unknown surface must not be described as a proven absence",
        )

    def test_generated_worker_skill_keeps_the_explicit_composite(self) -> None:
        """No auto-degrade, no invented native tool: the composite stays opt-in."""
        body = OPENCODE_SKILL.read_text(encoding="utf-8")
        self.assertIn("--steer-mode interrupt", body)
        self.assertIn("never injection", body)
        self.assertIn("refuses and writes nothing", body)
        self.assertEqual(manifest_values(OPENCODE_MANIFEST)["acp_steer_method"], "")

    def test_generated_reference_reports_unknown(self) -> None:
        self.assertIn("unknown", OPENCODE_STEERING.read_text(encoding="utf-8"))

    def test_cli_bare_steer_refuses_without_claiming_a_proven_absence(self) -> None:
        receipt = self.steer("opencode")
        self.assertEqual(receipt["steer_outcome"], "unknown")
        self.assertEqual(receipt["native_steering"], "unknown")
        self.assertEqual(receipt["error"]["code"], "steer-mode-required")
        message = receipt["error"]["message"]
        self.assertIn("has no verified native mid-turn steering entry", message)
        self.assertNotIn("exposes no native mid-turn steering entry", message)
        self.assertIn("absence is not established", message)
        # behaviour is untouched: still a refusal, still opt-in, still no writes
        self.assertEqual(receipt["available_steer_modes"], ["interrupt"])
        self.assertEqual(receipt["mutation_status"], "not_started")
        self.assertIs(receipt["mutation_performed"], False)
        self.assertIs(receipt["steer_consumed"], False)

    def test_cli_explicit_native_reports_capability_unknown(self) -> None:
        receipt = self.steer("opencode", "--steer-mode", "native")
        self.assertEqual(receipt["steer_outcome"], "unknown")
        self.assertEqual(receipt["error"]["code"], "steer-capability-unknown")
        message = receipt["error"]["message"]
        self.assertIn("has no verified native mid-turn steering entry", message)
        self.assertIn("absence is not established", message)
        self.assertEqual(receipt["available_steer_modes"], ["interrupt"])
        self.assertEqual(receipt["mutation_status"], "not_started")

    def test_a_genuinely_unsupported_platform_still_says_so(self) -> None:
        """`unknown` must not leak onto platforms that really were measured."""
        receipt = self.steer("grok", "--steer-mode", "native")
        self.assertEqual(receipt["steer_outcome"], "unsupported")
        self.assertEqual(receipt["error"]["code"], "steer-unsupported")
        message = receipt["error"]["message"]
        self.assertIn("has no native mid-turn steering entry", message)
        self.assertNotIn("verified", message)
        self.assertNotIn("absence is not established", message)

    def test_unsupported_wording_is_byte_identical_to_the_baseline(self) -> None:
        """Issue #88 reworded only the `unknown` case. A platform that really was
        measured keeps each path's original sentence, so no unrelated receipt moved."""
        bare = self.steer("grok")["error"]["message"]
        self.assertIn("grok exposes no native mid-turn steering entry on its ACP surface", bare)
        native = self.steer("grok", "--steer-mode", "native")["error"]["message"]
        self.assertIn("grok has no native mid-turn steering entry on the ACP channel", native)


class ReadmeDefersToTheManifestsForNativeSteering(unittest.TestCase):
    """README pinned "today Claude Code and Codex" for the native entry and
    "Everywhere else" for the composite. Issue #81 may add ZCode native steering,
    which would make both halves false. The page must derive the answer instead."""

    def test_no_frozen_native_steering_roster(self) -> None:
        text = flowed(README.read_text(encoding="utf-8"))
        for frozen in (
            "today Claude Code and Codex",
            "Everywhere else, the composite",
        ):
            self.assertNotIn(
                frozen,
                text,
                f"README must not pin {frozen!r}: which platforms steer natively "
                "changes as surfaces are investigated",
            )

    def test_it_names_the_manifest_field_as_the_source(self) -> None:
        text = flowed(README.read_text(encoding="utf-8"))
        self.assertIn("`native_steering` in `platforms/<id>.yaml`", text)
        self.assertIn("No roster is pinned here", text)
        for value in ("supported", "unsupported", "unknown"):
            self.assertIn(
                f"`{value}`",
                text,
                f"README must explain the {value!r} manifest value it tells the reader to read",
            )

    def test_the_native_example_really_is_a_supported_platform(self) -> None:
        """An example must still be true. If its platform ever stops steering
        natively, this fails and forces the example to move rather than rot."""
        text = README.read_text(encoding="utf-8")
        match = re.search(
            r"native_steering: supported\.\n\./scripts/kaola-tmux\.sh (\S+) steer", text)
        self.assertIsNotNone(match, "README native steer example not found")
        self.assertIn(
            match.group(1),
            platforms_with_native_steering("supported"),
            f"README shows {match.group(1)!r} as the native-steering example, but its "
            "manifest does not say native_steering: supported",
        )

    def test_the_composite_stays_an_explicit_option(self) -> None:
        """No runtime expansion: the composite is still opt-in, never a fallback."""
        text = flowed(README.read_text(encoding="utf-8"))
        self.assertIn("The composite works on every platform and is always chosen explicitly", text)
        self.assertIn("--steer-mode interrupt", text)


class ApiDocDefersToTheManifests(unittest.TestCase):
    """docs/api.md pinned "claude-code and codex qualify, six of the other seven
    have no such entry". Issue #81 may land ZCode native steering, and #88 already
    moved opencode to `unknown`, so a hand-maintained roster on this page goes
    stale and contradicts the manifests it claims to summarise."""

    def test_no_fixed_count_of_steering_platforms(self) -> None:
        text = flowed(API_DOC.read_text(encoding="utf-8"))
        for frozen in (
            "Six of the other seven",
            "the other seven have no such entry",
            "the other six have no such entry",
        ):
            self.assertNotIn(
                frozen,
                text,
                f"docs/api.md must not pin {frozen!r}: the count changes as surfaces "
                "are investigated",
            )

    def test_no_frozen_native_steering_roster(self) -> None:
        """No "today X and Y qualify" list that a manifest change would falsify."""
        text = flowed(API_DOC.read_text(encoding="utf-8"))
        self.assertNotRegex(
            text,
            r"Today\s+`claude-code`.{0,400}?and\s+`codex`.{0,200}?qualify",
            "docs/api.md must not freeze the native-steering roster in prose",
        )

    def test_it_points_at_the_manifest_instead(self) -> None:
        text = flowed(API_DOC.read_text(encoding="utf-8"))
        self.assertIn("The manifest is the single source of truth", text)
        self.assertIn("Read the current roster out of `platforms/*.yaml`", text)
        self.assertIn("no count or list is pinned here", text)
        for key in ("native_steering", "steering_summary"):
            self.assertIn(key, text, f"docs/api.md must name {key} as the source")

    def test_opencode_unknown_stays_documented_with_its_versions(self) -> None:
        """The one case #88 established is still concrete, not generalised away."""
        text = flowed(API_DOC.read_text(encoding="utf-8"))
        self.assertIn("1.18.17", text)
        self.assertIn("1.18.29", text)
        self.assertIn("steer-capability-unknown", text)
        self.assertIn("instead of a proven absence", text)


class DshHasNoApprovalGateAtAll(unittest.TestCase):
    """Issue #98. dsh is in ``NO_ADVERTISED_ACP_SKIP_ALL`` for the opposite reason to
    the other three, and that difference is safety-relevant: OpenCode, Cursor and Grok
    still ask, dsh never does. Measured twice over raw ACP and once through the Runner:
    two tool-using turns, including a bash write to an absolute path *outside* the
    session workspace, produced zero ``session/request_permission`` calls and both
    writes landed.

    Without this class the wording is unguarded: the roster check above is satisfied by
    the word "dsh" appearing anywhere in README, so softening the paragraph into
    OpenCode's weaker "no skip-all" shape keeps the suite green. These assertions pin
    the claim itself on every surface that carries it.
    """

    #: The distinguishing claim, in the three places a reader meets it.
    SURFACES = (
        ("platforms/dsh.yaml", DSH_MANIFEST),
        ("generated dsh references/acp.md", DSH_ACP_REF),
        ("README.md", README),
    )

    def test_every_surface_states_that_no_permission_request_is_sent(self) -> None:
        for label, path in self.SURFACES:
            with self.subTest(surface=label):
                text = flowed(path.read_text(encoding="utf-8"))
                self.assertRegex(
                    text,
                    r"(?:never sends? (?:a )?(?:`?session/request_permission`?|permission request)"
                    r"|sends no `?session/request_permission`? at all)",
                    f"{label} must state that dsh never sends a permission request",
                )

    def test_every_surface_states_there_is_no_gate_to_skip(self) -> None:
        for label, path in self.SURFACES:
            with self.subTest(surface=label):
                text = flowed(path.read_text(encoding="utf-8"))
                self.assertIn(
                    "no approval gate to skip",
                    text,
                    f"{label} must say there is no approval gate to skip, not merely "
                    "that no skip-all option is advertised",
                )

    def test_readme_keeps_the_measured_outside_workspace_write(self) -> None:
        """The fact that makes the default consequential, not a technicality."""
        text = flowed(README.read_text(encoding="utf-8"))
        self.assertIn("outside the session workspace", text)

    def test_the_operator_brief_carries_it_before_first_dispatch(self) -> None:
        """It is useless 370 lines away from the dsh subsection an operator reads."""
        text = README.read_text(encoding="utf-8")
        start = text.index("dsh is driven through its shipped automation-only ACP profile")
        brief = flowed(text[start:start + 1600])
        self.assertIn(
            "no approval gate to skip",
            brief,
            "the dsh operator brief must carry the no-gate fact itself; a reader who "
            "stops after the pre-dispatch facts must not miss it",
        )

    def test_dsh_is_never_described_with_opencodes_weaker_shape(self) -> None:
        """"No ACP skip-all" is OpenCode's fact and understates dsh's."""
        for label, path in self.SURFACES:
            with self.subTest(surface=label):
                text = flowed(path.read_text(encoding="utf-8"))
                for sentence in re.split(r"(?<=[.;]) ", text):
                    if "dsh" not in sentence.lower():
                        continue
                    self.assertNotRegex(
                        sentence,
                        r"dsh[^.;]*\bno (?:ACP )?skip-all\b",
                        f"{label} describes dsh with OpenCode's weaker shape: "
                        f"{sentence!r}",
                    )

    def test_the_manifest_advertises_no_mode_option_to_match(self) -> None:
        values = manifest_values(DSH_MANIFEST)
        self.assertEqual(values["acp_mode_config_id"], "")
        self.assertEqual(values["acp_command"], "dsh --profile acp")


if __name__ == "__main__":
    unittest.main()
