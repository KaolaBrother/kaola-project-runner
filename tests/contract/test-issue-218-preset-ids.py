#!/usr/bin/env python3
"""Issue #218: canonical `<runtime>/<tier>` preset IDs on the manifest-derived rows.

The catalog IDs are not a second registry: every surface that carries them derives
them from ``platforms/<id>.yaml`` through ``render-skills.py``'s ``preset_id``,
so a declaration change regenerates the rows instead of leaving a handwritten
mapping behind. This suite pins four things:

* the exact catalog: the README's generated region and the installed
  ``profile-catalog.md`` table carry the same 21 Preset ID cells in class
  grouping (Elite 13 / Worker 5 / Expert 3), each ID resolving to its
  manifest model name on the same row;
* the similar-name pairs the IDs exist to keep apart — ``cursor-cli/default``
  vs ``grok/default``, ``claude-code/default`` vs ``claude-code/sonnet`` — plus
  each platform Runner reference bullet tying tier word, preset ID, model name
  and native model ID together on one line;
* absent ``special_requirements`` means none: the guidance teaches
  owner-supplied-only deviations and omission by default, the Delegator/Host
  snapshot specs name seats by exact preset ID, and no generated example
  object carries the key;
* the ID is state notation only: no generated Skill or script grows a
  ``--preset-id`` flag or a second ID table.
"""

from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
PLATFORMS = PROJECT / "platforms"
SKILLS = PROJECT / "skills"
ORCHESTRATOR = SKILLS / "kaola-project-runner"
DELEGATOR = SKILLS / "kaola-delegator"
README = PROJECT / "README.md"

# Catalog render order (class, then manifest order). Issue #230 inserts
# ``claude-code/opus-xhigh`` after ``claude-code/default``. A declaration change
# regenerates these rows; this pin fails loudly instead of letting the catalog
# and the issue's grants drift apart.
ELITE = [
    "claude-code/default", "claude-code/opus-xhigh", "claude-code/sonnet", "codex/default", "cursor-cli/default",
    "cursor-cli/opus", "devin/opus-fusion", "droid/default", "droid/opus", "droid/core",
    "grok/default", "kimi-cli/default", "kimi-cli/kimi-k2-8",
]
WORKER = ["codex/luna", "devin/default", "dsh/default", "opencode/default", "zcode/default"]
EXPERT = ["claude-code/fable", "codex/astra", "devin/fable"]
EXPECTED_ORDER = ELITE + WORKER + EXPERT

ROW = re.compile(
    r"^\| (?P<class>\w+) \| (?P<runtime>[^|]+?) \| `(?P<tier>[^`]+)` \| "
    r"`(?P<preset>[a-z0-9-]+/[a-z0-9-]+)` \| (?P<model>[^|]+?) \| "
    r"(?P<parameters>[^|]+?) \| (?P<profile>[^|]+?) \|$"
)


def flat(text: str) -> str:
    """Whitespace-normalized text, so wrapped prose still matches a needle."""
    return " ".join(text.split())


def render_module():
    spec = importlib.util.spec_from_file_location("render_skills_218", SCRIPTS / "render-skills.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifests():
    module = render_module()
    return [module.parse_manifest(path) for path in sorted(PLATFORMS.glob("*.yaml"))]


def catalog_rows(text: str) -> list[dict[str, str]]:
    rows = []
    for line in text.splitlines():
        match = ROW.match(line)
        if match:
            rows.append(match.groupdict())
    return rows


def catalog_ids(rows: list[dict[str, str]]) -> list[str]:
    return [row["preset"] for row in rows]


class PresetCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifests = manifests()
        cls.by_id = {
            f"{m['id']}/{tier}": (m, tier)
            for m in cls.manifests
            for tier in ["default", *render_module().named_tiers(m)]
        }
        cls.orchestrator_rows = catalog_rows(
            (ORCHESTRATOR / "references" / "profile-catalog.md").read_text(encoding="utf-8"))
        readme_region = re.search(
            r"<!-- KW-README-PRESETS-START -->.*?<!-- KW-README-PRESETS-END -->",
            README.read_text(encoding="utf-8"), re.DOTALL)
        assert readme_region is not None
        cls.readme_rows = catalog_rows(readme_region.group(0))

    def test_exact_catalog_ids_in_order(self) -> None:
        for label, rows in (("profile-catalog", self.orchestrator_rows),
                            ("README region", self.readme_rows)):
            self.assertEqual(catalog_ids(rows), EXPECTED_ORDER, label)
            self.assertEqual(len(set(catalog_ids(rows))), 21, label)

    def test_class_grouping_matches_issue(self) -> None:
        for rows in (self.orchestrator_rows, self.readme_rows):
            by_class = {klass: [r["preset"] for r in rows if r["class"] == klass]
                        for klass in ("Elite", "Worker", "Expert")}
            self.assertEqual(by_class["Elite"], ELITE)
            self.assertEqual(by_class["Worker"], WORKER)
            self.assertEqual(by_class["Expert"], EXPERT)

    def test_each_row_resolves_id_to_manifest_model_on_the_same_row(self) -> None:
        for rows in (self.orchestrator_rows, self.readme_rows):
            for row in rows:
                manifest, tier = self.by_id[row["preset"]]
                prefix = tier.replace("-", "_")
                self.assertEqual(
                    row["model"], manifest[f"{prefix}_model_name"], row["preset"])
                self.assertEqual(manifest["id"], row["preset"].split("/", 1)[0])
                self.assertEqual(tier, row["tier"])

    def test_similar_name_pairs_stay_distinct_rows(self) -> None:
        rows = {row["preset"]: row for row in self.orchestrator_rows}
        # Same marketing model name, different runtimes: only the ID keeps the
        # two seats apart.
        cursor, grok = rows["cursor-cli/default"], rows["grok/default"]
        self.assertEqual(cursor["model"], grok["model"])
        self.assertNotEqual(cursor["runtime"], grok["runtime"])
        self.assertNotEqual(cursor, grok)
        # Same runtime: default and opus-xhigh share the native alias ``opus``
        # and stay different preset IDs, efforts, and profiles.
        default = rows["claude-code/default"]
        extra = rows["claude-code/opus-xhigh"]
        sonnet = rows["claude-code/sonnet"]
        self.assertEqual(default["class"], "Elite")
        self.assertEqual(default["model"].strip(), "Opus 5.5")
        self.assertEqual(default["parameters"].strip(), "effort=high")
        self.assertEqual(
            default["profile"].strip(),
            "All-round execution worker, especially strong at complex execution work and UI and 3D visual implementation.")
        self.assertEqual(extra["class"], "Elite")
        self.assertEqual(extra["model"].strip(), "Opus 5.5")
        self.assertEqual(extra["model"].strip(), default["model"].strip())
        self.assertNotEqual(extra["parameters"].strip(), default["parameters"].strip())
        self.assertEqual(extra["parameters"].strip(), "effort=xhigh")
        self.assertEqual(
            extra["profile"].strip(),
            "Plans, designs, and reviews difficult, complex work and handles deep reasoning tasks, with particular strength in UI and 3D visual design and review; does not perform implementation.")
        default_manifest, _ = self.by_id["claude-code/default"]
        extra_manifest, _ = self.by_id["claude-code/opus-xhigh"]
        self.assertEqual(default_manifest["default_model_id"], "opus")
        self.assertEqual(extra_manifest["opus_xhigh_model_id"], "opus")
        self.assertNotEqual(default["preset"], extra["preset"])
        self.assertEqual(sonnet["class"], "Elite")
        self.assertEqual(sonnet["parameters"].strip(), "effort=high")
        self.assertEqual(
            sonnet["profile"].strip(),
            "All-round execution worker, well suited to well-scoped work, especially UI and 3D visual implementation.")
        self.assertEqual(rows["claude-code/fable"]["class"], "Expert")
        self.assertEqual(rows["claude-code/fable"]["parameters"].strip(), "effort=high")
        self.assertEqual(rows["cursor-cli/opus"]["class"], "Elite")
        self.assertEqual(rows["cursor-cli/opus"]["parameters"].strip(), "effort=high (encoded in model ID)")
        self.assertEqual(
            rows["cursor-cli/opus"]["profile"].strip(),
            "All-round execution worker, especially strong at complex execution work and UI and 3D visual implementation.")
        self.assertEqual(rows["droid/opus"]["class"], "Elite")
        self.assertEqual(rows["droid/opus"]["parameters"].strip(), "reasoning_effort=high")
        self.assertEqual(
            rows["droid/opus"]["profile"].strip(),
            "All-round execution worker, especially strong at complex execution work and UI and 3D visual implementation.")
        self.assertEqual(rows["devin/opus-fusion"]["class"], "Elite")
        self.assertEqual(rows["devin/opus-fusion"]["parameters"].strip(), "effort=high (encoded in model ID)")
        self.assertEqual(
            rows["devin/opus-fusion"]["profile"].strip(),
            "All-round execution worker, especially strong at complex execution work.")
        self.assertNotIn("UI", rows["devin/opus-fusion"]["profile"])
        self.assertNotIn("3D", rows["devin/opus-fusion"]["profile"])
        self.assertNotEqual(default["model"], sonnet["model"])

    def test_worker_pool_line_names_exact_ids(self) -> None:
        text = (ORCHESTRATOR / "references" / "worker-profiles.md").read_text(encoding="utf-8")
        self.assertIn(
            "The Worker pool is exactly: " + ", ".join(f"`{pid}`" for pid in WORKER) + ".",
            text)

    def test_platform_reference_bullets_tie_id_tier_name_native_id(self) -> None:
        for manifest in self.manifests:
            reference = (SKILLS / manifest["skill_name"] / "references" / "platform.md") \
                .read_text(encoding="utf-8")
            for tier in ["default", *render_module().named_tiers(manifest)]:
                prefix = tier.replace("-", "_")
                bullet = (f"- Runner {tier} preset `{manifest['id']}/{tier}` "
                          f"(`--tier {tier}`): **{manifest[f'{prefix}_model_name']}** — "
                          f"`{manifest[f'{prefix}_model_id']}`")
                self.assertIn(bullet, reference, manifest["id"])


class AuthorizationNotationTest(unittest.TestCase):
    """Seats by exact ID; absent special_requirements means none; no new flag."""

    def test_host_authorization_guidance_names_seats_by_exact_id(self) -> None:
        profiles = (ORCHESTRATOR / "references" / "worker-profiles.md").read_text(encoding="utf-8")
        self.assertIn("## Preset IDs in authorization", profiles)
        self.assertIn("named by its exact catalog Preset ID", profiles)
        self.assertIn("`<platform>/<tier>`", profiles)

    def test_delegator_snapshot_names_seats_by_exact_id(self) -> None:
        snapshot = (DELEGATOR / "references" / "snapshot.md").read_text(encoding="utf-8")
        self.assertIn("named by its exact catalog preset id", snapshot)
        self.assertIn("`<platform>/<tier>`", snapshot)
        self.assertIn("`cursor-cli/default` vs `grok/default`", snapshot)

    def test_handoff_example_uses_preset_id_entries(self) -> None:
        handoff = (DELEGATOR / "references" / "handoff.md").read_text(encoding="utf-8")
        self.assertIn("authorized_platforms=<preset_id:count, ...>", handoff)
        self.assertNotIn("authorized_platforms=<id:count, ...>", handoff)

    def test_special_requirements_only_when_owner_supplied(self) -> None:
        for path, needles in (
            (ORCHESTRATOR / "references" / "worker-profiles.md",
             ["only when the owner actually supplied", "omit by default"]),
            (ORCHESTRATOR / "references" / "profile-catalog.md",
             ["only when the owner actually supplied one;", "absent means none"]),
            (DELEGATOR / "references" / "snapshot.md",
             ["only when the owner actually supplied one (absent", "means none"]),
            (DELEGATOR / "references" / "host-platforms.md",
             ["absent `special_requirements` means none"]),
            (ORCHESTRATOR / "references" / "heartbeat-skeleton.md",
             ["仅当 owner 确实给出偏差时", "缺省即省略该键"]),
        ):
            text = flat(path.read_text(encoding="utf-8"))
            for needle in needles:
                self.assertIn(needle, text, f"{path.name}: {needle}")

    def test_heartbeat_example_object_has_no_special_requirements(self) -> None:
        """Absent key is the demonstrated default: the example carries none."""
        skeleton = (ORCHESTRATOR / "references" / "heartbeat-skeleton.md").read_text(encoding="utf-8")
        example = re.search(r"例：(\{.*\})", skeleton)
        self.assertIsNotNone(example)
        body = json.loads(example.group(1))
        self.assertNotIn("special_requirements", json.dumps(body))
        # The teaching sentence carries the two issue-named deviation shapes.
        self.assertIn('{"effort":"high"}', skeleton)
        self.assertIn('{"task_scope":"visual QA"}', skeleton)

    def test_heartbeat_authorization_names_seats_by_preset_id(self) -> None:
        skeleton = (ORCHESTRATOR / "references" / "heartbeat-skeleton.md").read_text(encoding="utf-8")
        self.assertIn("精确 preset id", skeleton)
        self.assertIn("<platform>/<tier>", skeleton)
        self.assertIn("claude-code/default", skeleton)
        self.assertNotIn("claude-code opus", skeleton)

    def test_heartbeat_example_rows_and_class_definitions(self) -> None:
        """#223 kept the three Class definitions once. #244 stops copying the
        profile roster into the routine example: grants keep exact preset ids."""
        skeleton = (ORCHESTRATOR / "references" / "heartbeat-skeleton.md").read_text(encoding="utf-8")
        self.assertNotIn("或其指针", skeleton)
        example = re.search(r"例：(\{.*\})", skeleton)
        self.assertIsNotNone(example)
        auth = json.loads(example.group(1))["authorization"]
        self.assertEqual(sorted(auth["classes"]), ["Elite", "Expert", "Worker"])
        for definition in auth["classes"].values():
            self.assertEqual(skeleton.count(definition), 1, definition)
        self.assertNotIn("rows", auth)
        self.assertIn("capability_summary", auth)
        # The tool derives the capability view. The stored example has only
        # current preset IDs and no handwritten capability text or roster.
        self.assertEqual(sorted(auth), ["capability_summary", "classes", "elite_cap", "grants"])
        self.assertEqual(sorted(auth["capability_summary"]), ["presets"])
        self.assertEqual(auth["capability_summary"]["presets"], ["droid/opus", "devin/default"])
        self.assertEqual([grant["id"] for grant in auth["grants"]],
                         auth["capability_summary"]["presets"])
        self.assertEqual(auth["elite_cap"], 4)
        self.assertEqual(auth["grants"][0]["count"], 2)
        self.assertEqual(auth["grants"][0]["shared_seat"], "droid")
        self.assertNotIn("computer_interaction", auth["capability_summary"])
        catalog = {}
        for line in (ORCHESTRATOR / "references" / "profile-catalog.md").read_text(encoding="utf-8").splitlines():
            match = ROW.match(line)
            if match:
                catalog[match["preset"]] = match["profile"]
        for grant in auth["grants"]:
            self.assertIn(grant["id"], catalog)
            self.assertEqual(grant["state"], "granted")
            self.assertNotIn("profile", grant)
            self.assertNotIn(catalog[grant["id"]], json.dumps(auth))

    def test_catalog_teaches_configured_not_running_caveat(self) -> None:
        catalog = flat((ORCHESTRATOR / "references" / "profile-catalog.md")
                       .read_text(encoding="utf-8"))
        self.assertIn("**configured preset**", catalog)
        self.assertIn("Droid's `auto` and Devin's ACP display", catalog)

    def test_no_new_cli_flag_or_second_id_table(self) -> None:
        """The ID is state notation: no --preset-id flag, no standalone ID table."""
        for path in sorted(SKILLS.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            text = path.read_bytes()
            self.assertNotIn(b"--preset-id", text, str(path))
        # The only Python definition of the ID is the manifest-derived helper.
        source = (SCRIPTS / "render-skills.py").read_text(encoding="utf-8")
        self.assertIn("def preset_id(", source)
        self.assertEqual(source.count("def preset_id("), 1)
        for name in ("preset-ids", "preset_ids", "preset-registry"):
            self.assertFalse(list(SCRIPTS.glob(f"*{name}*")), name)

    def test_sonnet_is_elite_without_a_preset_cap_or_pool_seat(self) -> None:
        """Issue #228: Sonnet is Elite at high. The five Workers stay exempt."""
        readme = README.read_text(encoding="utf-8")
        self.assertIn("| **Elite** | 13 |", readme)
        self.assertIn("| **Worker** | 5 |", readme)
        self.assertIn("| **Expert** | 3 |", readme)
        self.assertIn("no default seat and no preset-specific", readme)
        pool = (ORCHESTRATOR / "references" / "worker-profiles.md").read_text(encoding="utf-8")
        membership = pool.split("The Worker pool is exactly:", 1)[1].split(".", 1)[0]
        self.assertNotIn("claude-code/sonnet", membership)
        self.assertIn("`claude-code/opus-xhigh` plans, designs and reviews but does not implement", pool)
        self.assertNotIn("`claude-code/default` does not perform implementation", pool)
        skeleton = (ORCHESTRATOR / "references" / "heartbeat-skeleton.md").read_text(encoding="utf-8")
        example = json.loads(re.search(r"例：(\{.*\})", skeleton).group(1))
        self.assertNotIn("claude-code/sonnet", [row["id"] for row in example["authorization"]["grants"]])
        self.assertIn("五个池", skeleton)
        stale = (
            "six Worker", "Six Worker", "six-preset", "these six presets",
            "Disciplined implementation", "strongest in Worker Class",
            "preferred for the more complex and harder tasks",
        )
        surfaces = [
            ORCHESTRATOR / "references" / "worker-profiles.md",
            ORCHESTRATOR / "references" / "profile-catalog.md",
        ]
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            for needle in stale:
                self.assertNotIn(needle, text, f"{path}: {needle}")


if __name__ == "__main__":
    unittest.main()
