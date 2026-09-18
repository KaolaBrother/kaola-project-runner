# Issue #88 — state the permission default per platform and calibrate the OpenCode steering version evidence

Run facts: branch `workflow/issue-88`, worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-88`,
baseline `f39d940` (= origin/main at claim).

Scope guard (from the outer brief and the issue body): prompts / manifest evidence markers /
contract tests / renderer output only. No ACP adapter change, no scheduling or approval-mechanism
change, no new hard gate, no auto-approval. Do not start an OpenCode or Cursor live worker without
explicit outer authorization. Do not treat the OpenCode 1.18.17 measurement as a 1.18.29 result.
Do not claim OpenCode/Cursor ACP are fully bypassed.

Co-active constraint: `workflow/bundle-75` (Issue #75, not merged) edits the SAME Defaults
`Permissions` row in `templates/orchestrator/SKILL.md.tmpl`, and its rendered main Skill is
**17393 bytes against the 17408 budget (15 bytes headroom)**. This run must therefore be
byte-neutral-or-negative on the main Skill and must preserve #75's own wording of the second half
of that row.

---

## 1. Establish the per-platform permission-default evidence

item: Read every `platforms/*.yaml`, the adapters they name, and the Issue #22/#24/#76 contract
tests, and record for each of the nine platforms what the no-flag default start actually proves on
its default transport — proven skip-all, launch-flag-only, or no skip-all at all. This is the
traceability basis the acceptance asks for; it is measurement of what the repo already records, not
new live probing.
status: done
dispatched: self
result: DONE. Nine-platform posture on the DEFAULT transport (ACP), from `platforms/*.yaml`
+ `scripts/adapters/*.sh` + `tests/contract/test-issue-22-bypass-all-approvals.py`:

| platform | ACP skip-all mechanism | class |
|---|---|---|
| claude-code | `mode=bypassPermissions` after initialize (`acp_mode_config_id: mode`) | advertised option |
| codex | `mode=agent-full-access` (`acp_mode_config_id: mode`) | advertised option |
| devin | `mode=bypass` (`acp_mode_config_id: mode`) | advertised option |
| droid | `autonomy_level=auto-high`; default ACP session already auto-high | advertised option |
| kimi-cli | `mode=yolo` (`acp_mode_config_id: mode`) | advertised option |
| zcode | `mode=yolo` after initialize (`acp_mode_config_id: mode`) | advertised option |
| grok | `grok agent --always-approve stdio`; `acp_mode_config_id` EMPTY | launch flag only |
| cursor-cli | `cursor-agent --yolo acp`; `acp_mode_config_id` EMPTY, manifest says "configOptions.mode has no skip-all value" | launch flag only |
| opencode | NONE. `opencode acp` takes no skip argv, `acp_mode_config_id` EMPTY; PTY `--auto` via `--transport pty` is the only bypass | no skip-all |

Key corrections to the issue body's premise, both kept in the wording:
- The issue says "Cursor ACP 也无对应 bypass 配置". Precisely true about the CONFIG OPTION
  (`acp_mode_config_id: ""`), but the ACP process argv does carry `--yolo`
  (`acp_command: "cursor-agent --yolo acp"`, pinned by
  `test-issue-22-bypass-all-approvals.py::test_cursor_acp_command_includes_yolo`). So Cursor is
  "launch flag, no advertised option", NOT "no bypass at all". Grok sits in the same structural
  class.
- Only OpenCode has no ACP skip-all of any kind. `test-issue-22-bypass-all-approvals.py` docstring
  already states "OpenCode ACP has no skip argv and is not asserted as skipped".
- Pending permission is a real, already-modelled runtime event, not a hypothetical:
  `tests/contract/test-issue-76-permission-wake.py` makes `session/request_permission` a carrier
  event and `permit` the settle op. That is the existing mechanism the wording must point at, so
  no new mechanism is needed or added.
- `README.md:423` already says "OpenCode's default ACP path has no skip-permission launch flag";
  the main Skill was the surface out of step with it.

## 2. Rewrite the main Skill permission default as a per-platform, manifest-proven fact

item: In `templates/orchestrator/SKILL.md.tmpl` replace the Defaults `Permissions` row sentence
"Existing Runner default bypass start" with wording that binds the default to what the selected
platform's own manifest/worker Skill proves, and extend the existing OpenCode transport-fact
sentence so a platform whose ACP surface has no skip-all is reported and handled as a pending
permission rather than assumed auto-approved. Keep #75's half of the row untouched so the rebase is
a mechanical two-sided keep. Stay byte-neutral or negative on the rendered main Skill.
status: done
dispatched: self
result: DONE, with one measured constraint escalated rather than absorbed.
Row: `Existing Runner default bypass start.` -> `Each platform's own proven default, not one
global bypass.` (noun phrase, matching the other rows' style). Paragraph: the OpenCode-only
transport-fact sentence now reads `Where ACP advertises no skip-all (OpenCode none; Cursor's
`--yolo` is a launch flag), pending permission still arrives: settle it with `permit`, never force
PTY or invent a gate.` #75's half of the row (they drop the word "here") is untouched, so the
rebase is a mechanical two-sided keep.
BYTE-NEUTRAL WAS NOT ACHIEVABLE and the shortfall is reported, not hidden. Measured, not estimated:
- this branch alone: main Skill 16590 B / 17408 budget, `render --check` PASS.
- baseline f39d940: 16494 B. This run's delta: **+96 B** (first wording drafted at +134 B was
  tightened to +96 B specifically to shrink the collision).
- simulated semantic merge with `workflow/bundle-75` (built in /tmp from `git archive
  workflow/bundle-75` + these two template edits, no branch touched): **17489 B > 17408 B,
  `render-skills.py --check` FAILS by 81 B.**
The collision is structural, not a wording problem: main had 914 B of headroom and #75 consumes
899 B of it. `templates/budgets.json` says existing ceilings are not raised, and trimming #75's
content is not this run's call, so the residual 81 B is a cross-run decision for the outer.

## 3. Calibrate the OpenCode steering version evidence

item: In `platforms/opencode.yaml`, mark the `-32601` steering probe explicitly as the historical
1.18.17 measurement and state that the currently verified 1.18.29 has not been re-probed, so the
current-version capability is unknown rather than asserted. Do not change `native_steering`, which
is the measured capability, and do not invent a 1.18.29 result.
status: done
dispatched: self
result: DONE. `platforms/opencode.yaml` `steering_summary` now opens `Historical evidence, OpenCode
1.18.17:`, keeps the original `-32601` / no-`_meta` finding in past tense, then states that the
probe `is a 1.18.17 result, not a measurement of the `acp_verified_versions` 1.18.29 build; the
current version has not been re-probed, so treat its native-steering capability as unknown until a
live probe settles it`. It also notes the composite `--steer-mode interrupt` is unaffected and was
exercised live on 1.18.31 (archived #65 evidence), so "unknown" is not misread as "no steering of
any kind". `native_steering: "unsupported"` is UNCHANGED - the measured capability is not restated,
only its version provenance is marked. No live OpenCode probe was run; none was authorized.
Side finding, NOT changed: `acp_verified_versions: "cli=1.18.29"` while archived #65 evidence
records the live ACP PASS on 1.18.31. That is a separate possible staleness outside #88's scope and
is flagged rather than silently edited.

## 4. Contract test that separates the old misleading claim from the correct statement

item: Add a contract test that fails on the pre-change bytes and passes after: the generated main
Skill must not make an unqualified all-platform bypass claim, and the OpenCode steering evidence
must carry its own version and must not read as a statement about the manifest's currently verified
version. Prove RED on the baseline before GREEN.
status: done
dispatched: self
result: DONE. `tests/contract/test-issue-88-permission-defaults.py`, 15 tests in 4 classes, registered in
`scripts/validate.sh` (`python_suites_all` + lane `python_suites_a`).
RED PROOF: run against a pristine `git archive f39d940` extraction in /tmp/i88-baseline ->
**FAILED (failures=10)** of 15. The 10 that fail are exactly the new claims (retired sentence gone
on both template and generated Skill, per-platform row wording, no-skip-all case named, permit
route, Cursor flag vs option distinction, protective clauses kept in the new sentence, 1.18.17
marked historical, 1.18.29 named as uncovered, "unknown", calibrated steering reference). The 5
that already pass on the baseline are deliberate regression guards (existing row duties, no
auto-approval vocabulary, and the three manifest-fact guards) - they must pass on both sides.
GREEN: 15/15 OK on ad8b934.
Design notes: prose assertions run against a whitespace-collapsed copy (`flowed()`), so they pin the
claim and not the line wrapping - a later re-wrap will not fake a pass or a fail. The no-skip-all
platform set is DERIVED from the manifests (`acp_mode_config_id` empty ->
{cursor-cli, grok, opencode}) rather than hard-asserted, so if a platform gains an advertised
option the test fails and forces the wording to be revisited.

## 5. Render, validate, freeze

item: `./scripts/render-skills.py --write` then `--check` (budgets included), `./scripts/validate.sh`,
record exact outcomes, confirm the main Skill byte delta against the #75 headroom, freeze the
candidate SHA and produce the real diff plus raw validation output for the outer's ACCEPT.
status: done
dispatched: self
result: DONE. Frozen candidate **ad8b934** on `workflow/issue-88` (baseline f39d940, 9 files,
+285/-11).
- `./scripts/render-skills.py --check` -> **PASS** ("budgets OK"), exit 0.
- `./scripts/validate.sh` -> **exit 0**, zero FAIL/ERROR lines. Raw log:
  `kaola-workflow/issue-88/evidence/validate-ad8b934.log`. The new suite is the last python block
  in the replay (`Ran 15 tests ... OK`); the single "SKIPPED" string in the log is a test NAME
  inside test-issue-83's own output, not a skipped suite.
- Byte delta and the #75 collision: recorded in mission 2.
NOT DONE, by instruction: no Workflow finalize, no sink, no Issue close, no push. No live OpenCode
or Cursor worker was started. Release-wide smoke remains separate.


---

## Round 2 — outer review of ad8b934 (not accepted; four minimal corrections)

Frozen candidate is now **38a09e2**, rebased onto main **18db64b**. ad8b934 is superseded.

### 1. Over-absolute permission claim — FIXED
`pending permission still arrives` asserted a certainty the evidence does not support: Cursor's and
Grok's launch flags can still suppress most approvals. The main Skill now reads
`OpenCode has no ACP skip-all; permission may still arise: `permit` settles it, never force PTY or
add a gate.` OpenCode's absent ACP skip-all stays explicit, as asked; the Cursor parenthetical is
removed from the main Skill entirely rather than softened, which removes the over-claim at its
source and frees locked bytes. Test updated: `test_the_claim_is_possibility_not_certainty` now
requires `permission may still arise` AND rejects `pending permission still arrives`,
`permission always`, `every worker will request`.

### 2. 81 B budget overrun vs #75 — RESOLVED, semantics preserved
Compressed only #88's own two template sentences; budgets.json untouched, #75's worktree untouched.
- row: `Each platform's own proven default, not one global bypass.` -> `Per platform, not one
  global bypass.` (-22 B; the manifest-level "proven" traceability now lives in README and in the
  derived-set test, not in locked bytes)
- paragraph: dropped the Cursor parenthetical and shortened the tail (-69 B)
- **this run's main-Skill delta fell from +96 B to +5 B** (16494 -> 16499 B).
METHOD for the merged number, repeatable: `git archive workflow/bundle-75 | tar -x -C
/tmp/i88-merge-sim`, apply #88's two template edits to that tree only (leaving #75's own row tail
exactly as #75 wrote it), then `render-skills.py --write && --check` there. No branch is touched.
RESULT against bundle-75 at **6ac2d49** (it advanced from e2a8316 during round 1):
**17398 B / 17408 budget, `render --check` PASS, exit 0** -- 10 B spare. Was 17489 B / FAIL by 81 B.
For reference #75 alone at 6ac2d49 is 17393 B.

### 3. CHANGELOG / README length — TRIMMED
CHANGELOG entry 21 -> 13 lines; README block 8 -> 7 lines with the redundant lead-in dropped. Both
keep the necessary facts: the three-way platform split, OpenCode's absent ACP skip-all, the
historical 1.18.17 probe, and the un-measured current-version boundary. README now also carries the
per-platform split that left the main Skill, and two new tests pin it there so the traceability did
not simply evaporate.

### 4. Rebase + revalidation — DONE
Rebased onto **18db64b**. Two conflicts, both additive, both resolved by keeping BOTH sides:
`scripts/validate.sh` (#85's suite entry + #88's) and `CHANGELOG.md` (#85's entry kept above #88's).
Nothing from #85 was dropped or reworded.
- `./scripts/render-skills.py --check` -> **PASS**, exit 0.
- `./scripts/validate.sh` -> **exit 0**, zero FAIL/ERROR lines. Raw log:
  `kaola-workflow/issue-88/evidence/validate-38a09e2.log` (the ad8b934 log is removed; it described
  a superseded tree).
- targeted suite: RED re-proven on the NEW baseline 18db64b -> **FAILED (failures=12)** of 17;
  GREEN 17/17 on 38a09e2.
No other issue touched. No finalize, no sink, no Issue close, no push.


---

## Round 3 — outer review of 38a09e2 (not accepted; the unknown/unsupported contradiction)

Frozen candidate is now **aadb76a**, on main **18db64b**. 38a09e2 is superseded.

### The finding was correct and was mine
Round 2 marked the *summary* "unknown" but left `native_steering: "unsupported"`, so the generated
reference and every `steer` receipt kept asserting a proven absence. One fact, two answers.

### What already existed (so nothing new was built)
`unknown` was ALREADY first class on both sides: `render-skills.py:90` validates
`{supported, unsupported, unknown}`, and `kaola-acp.py` already branched on it to emit
`steer_outcome: unknown` and `steer-capability-unknown`, with the in-code comment "`unsupported` and
`unknown` are different answers and must not collapse". Only the human-readable wording contradicted
that. So this round changed claims, not mechanism.

### The four surfaces changed
1. `platforms/opencode.yaml`: `native_steering: "unsupported"` -> `"unknown"`. The 1.18.17 `-32601`
   result stays in `steering_summary` as history (pinned by
   `test_the_historical_unsupported_result_is_still_recorded`).
2. `scripts/render-skills.py`: new `STEERING_UNKNOWN` block, selected by a 3-way dict. The worker
   Skill now opens "No native mid-turn entry has been verified on OpenCode's ACP surface ... That is
   an unverified capability, not a proven absence". The composite paragraph is unchanged.
3. `scripts/kaola-acp.py`: the two refusal messages reword ONLY the unknown case and add "No probe
   has settled this version, so absence is not established." Error codes, outcomes,
   `available_steer_modes`, `mutation_status` and the no-auto-degrade refusal are untouched.
4. `docs/api.md`: "the other seven have no such entry" -> six, plus opencode as `unknown` with its
   version reason.

### Scope slip caught and fixed mid-round
My first cut used ONE shared phrase for both refusal paths, which silently changed grok's
`--steer-mode native` message from "has no" to "exposes no". That is a surface outside #88. Fixed:
each call site keeps its own `unsupported` wording byte-for-byte, and only the unknown case is
reworded. `test_unsupported_wording_is_byte_identical_to_the_baseline` now pins both sentences.

### Evidence
- Receipt sweep, real CLI, 9 platforms x 2 refusal paths = 18 receipts, baseline vs frozen tree:
  **only OpenCode's 2 rows differ; the other 16 are byte-identical.** Raw:
  `evidence/steer-receipts-18db64b.txt` and `evidence/steer-receipts-candidate.txt` (re-verified
  IDENTICAL against the frozen tree after the amend).
- `render-skills.py --check` -> PASS, exit 0. Note it first caught real staleness: editing
  `kaola-acp.py` requires a re-render because the Skills vendor a copy.
- `./scripts/validate.sh` -> **exit 0**, zero FAIL/ERROR. Log: `evidence/validate-aadb76a.log`.
- Targeted suite: RED on 18db64b **17 of 25 failing**, GREEN 25/25 on aadb76a. It drives the real
  CLI for the receipt claims rather than matching source text.
- `test-issue-65-steering.py` gained the matching third branch and stays green.
- Budgets unchanged: main Skill 16499 B / 17408; OpenCode worker 12090 B / 12288; merged with
  bundle-75 @ 6ac2d49 = **17398 B, --check PASS**.

No other issue touched. No finalize, sink, Issue close, or push.


---

## Round 4 — independent outer review of aadb76a (two doc/test corrections)

Frozen candidate is now **cf35882**, on main **18db64b**. aadb76a is superseded.

### (1) The no-skip-all rule was single-platform — FIXED as a GENERAL rule
aadb76a said "OpenCode has no ACP skip-all; permission may still arise". Cursor advertises no ACP
skip-all option and Grok carries only a launch flag, so naming one platform left two uncovered and
would go stale on the next manifest change. Main Skill now: `With no verified ACP skip-all,
permission may still arise: `permit` settles it, never force PTY or add a gate.` README carries the
roster and the existing flow by name: "On any platform with no verified ACP skip-all - Cursor, Grok
and OpenCode today - a permission request may still arise: it surfaces through the existing
`permission_required` carrier event and is settled with `permit`. Neither forcing PTY nor adding a
gate is the answer."
TRADEOFF, stated because it is the outer's call, not mine: naming the three platforms *inside* the
main Skill costs +33 B total, which renders 17431 B merged with #75 and FAILS the locked 17408
budget. The general rule costs +6 B (merged 17399, PASS). So the roster lives in README, which has
no budget, and the main Skill carries the rule that covers all three and any future platform. If
you want the names in the main Skill, that needs a byte decision against #75, not a wording tweak.
New checks: `test_the_rule_covers_any_platform_without_a_verified_skip_all` requires the general
sentence AND rejects `"<Runtime> has no ACP skip-all"` for every runtime in the DERIVED no-skip-all
set; `test_readme_names_every_platform_without_a_verified_skip_all` requires README to name each
one, also derived from `platforms/*.yaml`; `test_readme_routes_through_the_existing_flow_only` pins
`permission_required` -> `permit` and the no-PTY/no-gate clause.

### (2) docs/api.md hardcoded roster and counts — REMOVED
It pinned "Today `claude-code` ... and `codex` ... qualify. Six of the other seven have no such
entry". #81 may land ZCode native steering and #88 already moved opencode to `unknown`, so that
prose would contradict the manifests it claims to summarise. It now says to read the current roster
out of `platforms/*.yaml`, keeps `native_steering` / `steering_summary` named as the source of
truth, and keeps the OpenCode `unknown` case concrete with both versions (1.18.17 probe vs 1.18.29
verified). New class `ApiDocDefersToTheManifests`: no fixed count, no frozen "Today X and Y qualify"
roster (regex), must point at the manifest, and the OpenCode case must stay documented.

### Evidence
- Targeted suite: **RED on 18db64b 22 of 31**; and specifically for THIS round's two corrections,
  **RED on the prior candidate aadb76a, exactly 5 failing** -- the three api.md checks, the general
  rule, and the README flow check. GREEN 31/31 on cf35882.
- `render-skills.py --check` -> PASS, exit 0.
- `./scripts/validate.sh` -> **exit 0**, zero FAIL/ERROR, re-run on the final tree after a prose
  polish so the log matches the frozen bytes. Log: `evidence/validate-cf35882.log`.
- Diff check vs 18db64b, hand-edited sources only (generated `skills/` excluded): CHANGELOG,
  README, docs/api.md, platforms/opencode.yaml, scripts/kaola-acp.py, scripts/render-skills.py,
  scripts/validate.sh, templates/orchestrator/SKILL.md.tmpl, and the two test files. Nothing of
  #75's or #81's belongs to that set.
- BYTE BUDGET, final: main Skill **16500 B / 17408** (+6 B over 18db64b). OpenCode worker Skill
  **12090 B / 12288**. Merged with bundle-75 @ 6ac2d49: **17399 B, --check PASS** (9 B spare).
- DOCS final state: README carries the three-way platform split plus the roster and the
  `permission_required`/`permit` flow; docs/api.md defers to the manifests; CHANGELOG has one
  entry; the OpenCode worker Skill carries the unverified-not-absent steering wording.

### Standing caveat for the outer
The merged figure is against bundle-75 at 6ac2d49 and assumes #81 does not also grow the main
Skill. A later rebase onto a moved #75 or #81 invalidates this measurement and needs the merge
simulation and full validate re-run before release.

No other issue touched. No finalize, sink, Issue close, or push. Stopped for outer review.


---

## Round 5 — outer re-review of cf35882 (README native-steering roster residue)

Frozen candidate is now **e4d3d26**, still on **18db64b**. cf35882 is superseded.
NOT rebased, by instruction: #87 is serial-sinking main right now.

### The residue
Round 4 de-hardcoded `docs/api.md` but missed the same claim in `README.md` ~393: the native
example was labelled "(today Claude Code and Codex)" and the composite "Everywhere else". #81's
ZCode native steering would make both halves false.

### Fix
README now derives it: "Which platforms have a native mid-turn entry is read from `native_steering`
in `platforms/<id>.yaml` - `supported` means the entry exists, `unsupported` means it was
investigated and does not, and `unknown` means no probe has settled it. No roster is pinned here,
because that answer changes as surfaces are investigated." The two code examples stay, relabelled:
the native one as "on a platform whose manifest says native_steering: supported", the composite as
"works on every platform and is always chosen explicitly" - still opt-in, still never a fallback.
No runtime change; README and tests only this round.

### Focused regression, new class `ReadmeDefersToTheManifestsForNativeSteering`
- `test_no_frozen_native_steering_roster` rejects both retired phrasings.
- `test_it_names_the_manifest_field_as_the_source` requires the manifest field and all three of its
  values to be explained.
- `test_the_native_example_really_is_a_supported_platform` regex-extracts the platform id from the
  README example and asserts it is in the set DERIVED from `platforms/*.yaml` where
  `native_steering == supported`. So the example cannot rot silently: if that platform ever changes,
  the test fails and forces the example to move.
- `test_the_composite_stays_an_explicit_option` guards against the composite being described as
  automatic (no runtime expansion).

### Evidence
- Targeted suite: **RED on 18db64b 26 of 35**; for THIS round's residue specifically, **RED on
  cf35882, exactly the 4 new checks**; GREEN **35/35** on e4d3d26.
- `render-skills.py --check` -> PASS, exit 0.
- `./scripts/validate.sh` -> **exit 0**, zero FAIL/ERROR. Log: `evidence/validate-e4d3d26.log`.
- Diff check vs 18db64b, hand-edited sources only: CHANGELOG, README, docs/api.md,
  platforms/opencode.yaml, scripts/kaola-acp.py, scripts/render-skills.py, scripts/validate.sh,
  templates/orchestrator/SKILL.md.tmpl, tests/contract/test-issue-65-steering.py, and the #88 test.
  Nothing belonging to #75, #81, #86 or #87.
- BYTE BUDGET, final: main Skill **16500 B / 17408** (+6 B over 18db64b; unmoved this round since
  only README and tests changed). OpenCode worker Skill **12090 B / 12288**. Merged with bundle-75
  at **835cbc6** (it moved again from 6ac2d49): **17399 B, --check PASS**, 9 B spare.
- DOCS final state: README carries the permission three-way split, the no-verified-skip-all roster,
  the `permission_required`/`permit` flow, and a manifest-derived native-steering statement;
  docs/api.md defers to the manifests; the OpenCode worker Skill carries the
  unverified-not-absent steering wording; CHANGELOG has one entry.

### Integration caveats for the outer, all unverified from here
- The merged figure is against bundle-75 @ 835cbc6 and assumes #81 does not also grow the main
  Skill. Any later rebase onto a moved #75, #81 or the post-#87 main invalidates it.
- On rebase, re-run: the merge simulation, `render --check`, full `validate.sh`, and this suite.
  `scripts/validate.sh` and `CHANGELOG.md` conflict additively with sibling runs - keep BOTH sides,
  as was done for #85.
- Integration must keep #86/#87/#81 tests and both #75 and #88 semantics and budgets.

No other issue touched. No finalize, sink, Issue close, or push. Stopped for outer review.


---

## Round 6 — outer ACCEPT of e4d3d26, rebase onto post-#87 main

**Integration SHA: db6bc71** on `workflow/issue-88`, base **7d14782** (`chore: archive issue-87 [sink]`).

### Rebase
One conflict, exactly as the outer predicted: `scripts/validate.sh`, `test-issue-86-delegator-quota.py`
(HEAD) vs `test-issue-88-permission-defaults.py` (mine). Resolved additively, keeping BOTH.
CHANGELOG did NOT conflict this time and carries both the #87 and #88 entries.
PROOF the resolution dropped nothing: `diff` of my `scripts/validate.sh` against `7d14782`'s own
copy shows exactly two added lines, both `test-issue-88-permission-defaults.py`, nothing removed.
Registration audit: `python_suites_all` = 40 suites, lane_a 18 + lane_b 22 = 40, no suite missing
from a lane, no duplicate across lanes. `test-issue-87-*` does not exist on main - #87 ships no
dedicated suite file, so nothing of its coverage was dropped; `test-issue-86-delegator-quota.py`
stays registered twice and passes (46 checks).

### Verification on the integration tree
- `render-skills.py --write` -> re-render produced NO diff, so the committed generated output
  already matched the rebased sources.
- Byte budgets: main Skill **16500 / 17408 (+908 spare)**; largest worker `cursor-cli` **12136 /
  12288 (+152)**, `opencode` **12090 / 12288 (+198)**; largest reference
  `kaola-delegator/references/handoff.md` **8186 / 8192 (+6)** - unchanged by this run and already
  the known tight one.
- `render-skills.py --check` -> **PASS**, exit 0.
- Targeted suite **35/35 OK**; `test-issue-65-steering.py` **27/27 OK**;
  `test-issue-86-delegator-quota.py` **PASS (46 checks)**.
- `./scripts/validate.sh` -> **exit 0**, zero FAIL/ERROR, 30 suites replayed. Log:
  `evidence/validate-db6bc71-integration.log`.
- Source-only diff vs 7d14782 (generated `skills/` excluded): 10 files, +658/-23. Nothing belonging
  to #75, #81, #86 or #87.

No content conflict beyond the additive registration, and no budget overrun. Proceeding to
Workflow Finalize under the outer's explicit ACCEPT.
