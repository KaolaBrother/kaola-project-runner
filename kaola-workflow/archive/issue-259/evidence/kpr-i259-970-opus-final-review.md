# Final affected review: issue 259 candidate `2989c8cf`

Reviewer: Claude Code Opus Extra High, seat `claude-code/opus-xhigh`, session `claude-code-KPR-i259-final-2989-review`.
Date: 2026-10-06. Role: thinking and review only. This report is a review contribution. It is not Host acceptance, outer acceptance or release authority.

## 1. Conclusion

The candidate is **not ready** for the outer final integrated judgment.

- The seven-group contract is implemented, and the live Host adoption result is correct for this run.
- Four defects need a repair by the same owner (original259) before acceptance: D1, D2, D3 and D4.
- Five smaller defects (D5 to D9) each have a small correction. Three more (D10 to D12) are cleanup.
- Four statements in the six answers are false or too wide. One is stale. One is incomplete.
- The native limits in the delivery are accurate. They are limits, not hidden defects.
- No additional authority or value gap exists. I do not print the human decision marker.

The live Host record and the live Delegator record do not contain the inputs that trigger D1, D4 or D6. Those defects affect other consumers and future upgrades.

## 2. Exact candidate and identity

- Candidate: `2989c8cfe61db1f98902fa7759d2fbb55e382fcc`, branch `workflow/issue-259`, worktree `.kw/worktrees/issue-259`.
- The worktree was at this commit and clean at each of my checks. All probes ran before the worktree changed.
- I verified all line numbers below with `git show 2989c8cf:<path>`.
- After my last check, the writer started the 978 edit in the same worktree. I did not read those moving bytes as the candidate.
- Binding hashes match: delivery `d6b65753…`, six answers `54c030dd…`, and the three 266 files (`63cc4efb…`, `5c3b5515…`, `70440000…`).
- `scripts/kaola-dispatch.py` and `scripts/kaola-record-contract.py` are byte-equal to their generated copies.
- `templates/grok-golden/` and `templates/budgets.json` did not change from base `77d57fc0`.
- The canonical six requirements and the candidate `AGENTS.md` differ only in requirement 2. The candidate adds the 951 and 955 text.

## 3. Sources read

- Canonical `AGENTS.md` six requirements; owner corrections 951 and 955.
- Original return, delivery, six answers, binding, Host review 970.
- Affected diffs `13f0720c..2989c8cf` for contract, dispatch, ACP entry, launcher integration, templates, docs and tests.
- Live adoption receipts: legacy clear, migration write, current Host view, repeat plan, authority verification.
- Live Host record, live Delegator record, live dispatch index and the installed dispatch tool. All reads were read-only.
- Native limits report, Host review 929, original266 Host review 963, original266 final return, issue 266 body.
- Preserved intermediate findings of the writer.

## 4. Reviewer probes

I did not run test suites, inventories or native launches. I did not edit the repository, generated files or live records.

- I called candidate functions in memory with small legacy inputs.
- I ran `state migrate` and `delegator migrate` of the candidate tool on scratch files in a temporary directory. I removed that directory.
- The tool refused my scratch `--writer host` calls, because my session is an Elite seat. I did not go around that check. I called the same writer functions in memory.
- I loaded the installed dispatch tool in memory and gave it a copy of the live Host record.

Each probe result below has the label "probe".

## 5. Defects

### D1 (high). The Delegator migration silently removes a pause on a default Worker preset

- Path: `scripts/kaola-record-contract.py` lines 531 to 587 (check at 577, removal at 584). `scripts/kaola-dispatch.py` line 5635 runs the same migration on every Delegator update.
- Evidence (probe): a typed Delegator record had `worker_pool: [zcode/default, dsh/default]` and `paused: [zcode/default]`. `delegator migrate --write` returned exit 0 and `migrated`. The stored authorization then had no pause, no paused grant and no exclusion.
- The output said `authorization.paused -> current grants/exclusions`. That statement is false for this input.
- An ordinary `delegator update` has the same effect and does not report the removal, because line 5635 discards the removed list.
- Effect: a paused Worker preset becomes available without an owner decision. This is silent authority expansion. Owner group 6 forbids it.
- The Host branch refuses the equal case (lines 462 to 465). The two branches do not agree.
- Smallest correction: in the Delegator branch, add a blocker when a `paused` id is not in a grant row. Tell the Delegator to record a current exclusion or to relay a Host hold with its reason and its reopening route. Report the removed list in the update result.

### D2 (high). The named recovery for a blocked aggregate limit cannot run

- Path: `scripts/kaola-dispatch.py` line 4105 (section writer) and line 3542 (`legacy-format`). `scripts/kaola-record-contract.py` line 389 (recovery text). `docs/dispatch-collect.md` line 255.
- Evidence (probe), current schema: the record had a conflicting `elite_cap` and the usual previous-version keys (`classes`, `capability_summary`, `model_switches`, `paused`, `revoked`, repeated `shared_seat` rows). This is the shape of this run's own Host record before revision 952.
  - `state migrate` refused at `authorization.elite_cap` and named the authorization update with `null`.
  - The writer refused `{"elite_cap":null}`. It named `capability_summary`, `classes`, `model_switches`, `paused`, `revoked` and `grants`.
  - The writer refused a patch that set all legacy keys to `null`. It said "plan migration".
  - Each refusal sends the user to the other command. The only exit is a manual rewrite of all grants in one patch. No text names that exit.
- Evidence (source and probe), schema 1: `state update` refuses a schema 1 file with `run state migrate`. Migration refuses the limit. No tool step remains.
- Evidence (probe): the previous canonical skeleton example (`elite_cap: 4`, one grant without a count) is blocked at `authorization.elite_cap`.
- The live run did not meet this defect. The installed tool removed the limit at revision 952 and the project fields at revision 970.
- Smallest correction: let the Host authorization section writer apply `migrate_authorization_limits` to the merged section when the patch only removes legacy keys. The Delegator writer does this already. For a schema 1 file, name a step that can run, or state that no tool step exists.

### D3 (high for integration). The 266 default launch path is not carried into the existing ACP suites

- Path: `scripts/kaola-acp.py` line 4510 (default `auto`). `scripts/kaola-launchd-broker.py` line 329 (`auto` is launchd on macOS) and line 172 (environment filter). `tests/contract/test-progressive-disclosure.py` line 389.
- Evidence (source): each Runner `start` on macOS now goes through a per-user launchd job. The launcher keeps only named environment variables. It drops `MOCK_ACP_*`.
- Evidence (writer record): `/tmp/kpr-i259-963-intermediate-findings.md` records one failed case for this cause. The writer pinned that one fixture to `--launch-backend direct`.
- Evidence (source): 17 other unmodified suites start mock holders and pass `MOCK_ACP_*` variables. None sets a direct launch. No harness sets `KAOLA_LAUNCH_BACKEND`. Examples: `test-acp-contract.py`, `test-issue-162-upgrade-safety.py`, `test-issue-245-session-role.py`, `test-issue-64-receipt-bound.py`.
- Effect: on macOS these suites probably fail or assert less than before. Each run also creates launchd jobs in the user domain. I did not measure this, because a run would start service-manager jobs.
- The delivery names the unrun 244, 255 and 259 suites. It does not name these affected ACP suites.
- The owner authorized the shared launcher for Host and seats on all adapters. The default is in scope. The integration coverage is the gap.
- Smallest correction: set `KAOLA_LAUNCH_BACKEND=direct` one time in the shared suite environment of `scripts/validate.sh`. Keep the two 266 suites on their explicit backend. Then run the affected ACP suites with `--suite` and record the results.

### D4 (medium). The Host migration changes a revoked or excluded grant to paused

- Path: `scripts/kaola-record-contract.py` lines 480 to 486.
- Evidence (probe): a schema 1 body had a grant with `state: revoked` and the same id in `paused`. `state migrate --write` stored `state: paused`. The same occurred for `state: excluded`.
- Effect: a paused grant stays authorized and can reopen. A revoked or excluded grant must not get that status without an owner decision.
- The accepted commit `13f0720c` removed such a revoked grant.
- Smallest correction: add a blocker for this state conflict. As an alternative, keep the stronger state and remove only the list entry.

### D5 (medium). A previous-version reader refuses the migrated record, and the update convention has no entry

- Path: `docs/conventions.md` lines 150 to 177. `scripts/kaola-dispatch.py` line 283.
- Evidence (probe): the installed dispatch tool refuses the live Host authorization with `each grant needs a string id`. That reader uses `state.authorization`. It does not use the generated rows in `body`.
- The refusal is safe, because it grants nothing. The message does not tell the user to update the Runner.
- The convention says: do not expose an incompatible format to an old reader. It also asks for source, target, migration time and incompatible-reader handling. The candidate did not add an entry for the grouped grants.
- The existing version 0.9.0 case uses `id` rows only. It does not cover a grouped grant or the issue 255 reader.
- Smallest correction: add one convention entry. State the order: install the new reader, then migrate. Name the refusal of the previous reader. Add the same limit to answer 6.

### D6 (medium-low). A revoked Worker preset loses its exclusion when the local catalog does not name it

- Path: `scripts/kaola-dispatch.py` lines 365 and 378.
- Evidence (probe): `revoked: [zcode/default]` became an exclusion. A revoked id that the catalog did not contain left no record.
- Effect: with a partial installation, a later installation of that platform restores default-pool authorization. The accepted commit kept the `revoked` list.
- Smallest correction: also keep the exclusion when the catalog does not name the Class of the id.

### D7 (medium-low). One owner-text restriction makes the full Delegator seat summary unknown

- Path: `scripts/kaola-dispatch.py` line 791.
- Evidence (probe): the Delegator contract accepts `special_requirements` as owner text. The seat summary copies it into a Host row. `normalize_grants` then refuses with `special_requirements must be an object`.
- Effect: the mandatory user report shows `unknown` for all seats. The accepted commit did not copy this field.
- Smallest correction: copy the field into the row only when it is an object.

### D8 (low-medium). The writer accepts one preset in two grant rows, and the reader then refuses all dispatch

- Path: `scripts/kaola-record-contract.py` line 777. `scripts/kaola-dispatch.py` line 286.
- Evidence (probe): a single row for `droid/opus` plus a group that contains `droid/opus` passed the writer and the migration. The reader returned `duplicate grant droid/opus`. The Host view said "plan migration", but migration reported no change.
- The delivery says that overlapping grouped rows refuse. That is true only when the rows have the same seat label.
- Smallest correction: add one check in `authorization_blockers` for a preset id in more than one row.

### D9 (low-medium). The Delegator grant `class` key gets a wrong recovery text

- Path: `scripts/kaola-record-contract.py` lines 663 and 664.
- Evidence (probe): the refusal says "rehome this fact from its source". Owner group 4 says that Class comes from the catalog. The correct action is removal.
- The live Delegator record has `class` on all five grants. The Host branch removes its `classes` copy mechanically (line 439).
- Smallest correction: remove a `class` value of `Elite`, `Expert` or `Worker` in the Delegator branch, or give a specific removal text.

### D10 (low). A record from `state init` is not current for `state migrate`

- Path: `scripts/kaola-dispatch.py` line 5288.
- Evidence (probe): after `state init`, the plan returned `planned` with `removed: []`. `--write` changed revision 1 to 2 only to delete an empty `retired` list.
- Smallest correction: do not create the empty list, or ignore it in the comparison.

### D11 (low). The routine Host view contains repeated and long derived text

- Path: `scripts/kaola-dispatch.py` lines 3591 to 3594.
- Evidence (live record): `capability.catalog_source` lists ten absolute file paths. `capability.text` repeats all 14 preset ids. The paths point into the candidate worktree.
- Owner correction 955 asks for concise current information on this surface.
- Smallest correction: show one catalog root and one digest. Omit `text` when it only repeats `presets`.

### D12 (low). Obsolete text and fixture arguments remain

- `templates/orchestrator/references/quota-packages.md` line 13: "The cap exemption is kept".
- `README.md` lines 390 to 392: "general worker concurrency cap".
- `docs/dispatch-collect.md` line 189: "This sentence adopts the latest owner951 correction".
- `tests/contract/test-issue-244-dispatch.py` line 194: the helper silently discards `elite_cap` and `worker_pool_cap`. 21 call sites still pass `elite_cap=`.
- Stale names: sub-test `worker-cap` (259, line 934) now asserts admission; `test_skeleton_example_sets_effective_cap`.

## 6. Weakened assertions

| Id | Location | Finding |
| --- | --- | --- |
| W1 | 259 suite, line 205 | "Actionable" is one word match on `original`. The case does not run the named recovery. See D2. |
| W2 | 255 suite, line 57 and `LEGACY_BODY` | The schema 1 fixture lost `elite_cap`, `classes` and the grant without a count. Two 259 schema 1 fixtures changed `{"elite_cap": 2}` to `{"grants": []}`. No schema 1 case has a legacy limit now. |
| W3 | 259 suite, line 1575 | The case accepts `planned` or `current`. Before, it required `current`. See D10. |
| W4 | 244 suite, line 194 | The helper adds `count: 1` and removes limits without a message. The cases pass through a different rule than their arguments show. |
| W5 | all suites | No case asserts `count-unreadable`. The delivery says that missing counts are withheld. |

The changes from `seat-cap` to `count` and from one free seat to two agree with owner correction 951. They are not weakened assertions.

## 7. Seven groups

| Group | Implementation | Result |
| --- | --- | --- |
| 1. Exact grant counts | Contract refuses the three limit keys. Admission uses grant and shared counts only. Plan `seat_cap` is refused. | Correct. Six seats admit and each excess refuses in the dry-run case. Recovery defect D2. |
| 2. One switch authority | `switch_authorized` reads the grant only. Migration refuses false, partial or unmatched switch intent. | Correct. |
| 3. Derived capabilities | `current_candidates` supplies `project` and the Host view. | Correct. The live derived list equals the former stored list. Defect D11. |
| 4. Catalog defaults | The Host view shows catalog Classes with source and digest. | Correct for the Host. Defect D9 for the Delegator. |
| 5. Shared groups | One `preset_ids` row owns count, state, switch and restrictions. `expanded_grants` makes the compatibility rows. | Correct for the measured cases. Defects D5 and D8. |
| 6. Current eligibility and duties | Ended grants leave. Worker revocations become exclusions. Paused state is on the grant. | Not correct in three cases: D1, D4 and D6. |
| 7. Objective and source pointers | Project keys are closed. `rules` and `skill_adoption_source` refuse. | Correct. The project removal runs with the candidate tool, because validation is per section. |

Note on group 1: the owner text names `elite_cap`, `total_cap` and an equivalent renamed field. The candidate also names `worker_pool_cap` in the owner section and removes the Worker pool ceiling. I think this agrees with the owner text. Migration never removes a numeric `worker_pool_cap` silently. The outer Delegator confirms the wording.

Note on group 4: migration removes `classes` by shape. It does not compare the sentence with the catalog. The plan names the path before the write.

## 8. Six owner answers

| Answer | Accuracy |
| --- | --- |
| 1. Template fidelity | True but incomplete. It does not state how drift is detected and corrected. The final copy measured the Delegator entry only. |
| 2. Current information | The contract statements are true. "Live records were only read" is stale after Host adoption at revisions 970 and 971. The answer correctly says that the VRPAI and VRPCAD criterion is not shown. |
| 3. Host autonomy and Sideagent | True. The numbers agree with Host review 929. The limits are stated. |
| 4. Recovery | "Does not infer expanded authority" is too wide. D1, D4 and D6 are cases without a refusal. |
| 5. Continuous improvement | True. It does not name the unrun ACP suites of D3 or the residue of D12. |
| 6. Upgrade continuity | "Executable owner recovery path" is false for D2. "Preserves paused grants" is false for D1. The version 0.9.0 statement is true but omits D5. |

The delivery table also says that overlapping grouped rows refuse. See D8.

## 9. Explicit unverified limits

These are stated limits. I found no hidden defect behind them and I did not turn them into a pass or a fail.

- Native use of the changed report and native timer readback.
- Corrected Codex initialize request and structured completion signal.
- Independent outer inquiry and installed bridge emission.
- Host outcome 3 on runtimes other than the accepted Claude route.
- DSH background forwarding outside the finite route.
- Droid and Cursor native boundary: not reached, not failed, not unsupported.
- Launcher on Linux and other systems; GUI, TCC and Keychain under a service-manager start; app quit, logout and reboot.
- Per-platform live ACP smoke through the new default launch path. Project policy requires this before a release.
- Requirement 2 owner criterion: useful task advancement beside maintained state on the VRPAI and VRPCAD cases. The outer Delegator must judge this gap.

## 10. Current live adoption

- The stored Host authorization holds grok 1, cursor 1, codex 1, one Droid group with count 2 and one Claude group with count 1. The total is six. No aggregate limit exists.
- The `opus-xhigh` restriction "thinking and review only" is stored for that choice. Switch permission is on the two groups only.
- Tasks, maintenance sequence and the five protected paths agree with the Host verification.
- The live Delegator record has no schema. The candidate reads it as a migration observation and keeps Host authorization. Its free-text switch conditions and its `class` keys need owner-sourced mapping by the Delegator.
- The live Host body at revision 977 came from the candidate tool in the worktree. The installed tool cannot admit from this record (D5).
- A file `/tmp/kpr-970-derived-review-authorization.json` holds expanded rows. I did not find which tool admitted my dispatch.
- Live checkpoint `b-1ab76cb3b4b4` is not verified. It returned two Host changes to the Host. This is a current Host duty. I did not judge it.
- The main checkout has an uncommitted `AGENTS.md` edit with the six requirements. The lifecycle merge must keep that owner text.

## 11. Pending owner refinement 978

- The owner issued one narrow refinement: project and Delegator special requirements as two scoped sections.
- I read `/tmp/kpr-i259-978-owner-scoped-section.md`. Its SHA-256 is `44522468…606ae7`. The quoted hash `73f24c5a…` is different. I did not compare it with the authoritative body.
- This refinement is **pending affected source acceptance**. Candidate `2989c8cf` does not contain it. I did not review a design or an implementation for it.
- The findings in this report apply to immutable `2989c8cf`. A later commit needs its own affected check of each finding.
- The six substantive project outcomes stay shared. The personal final audit and the joint Opus review are an appointment of this outer Delegator for this run only.

## 12. Required repair and next step

Owner: original259, same assignment. Reviewer of the repair: Host, then the affected Opus and outer review.

1. Repair D1, D2, D3 and D4.
2. Apply the small corrections D5 to D9. D10 to D12 are optional cleanup in the same edit.
3. Make W1 and W2 real: run the named recovery in the existing case, and keep one schema 1 fixture with a legacy limit.
4. Run the affected named cases and the affected ACP suites of D3. Do not run the full inventory only for this repair.
5. Correct answers 1, 2, 4 and 6 and the group 5 row. Add D5 to the stated limits.
6. Reference files are 3 to 7 bytes below the 8192-byte budget. A text correction needs consolidation, not a larger budget.
7. Until D1 is repaired, do not run candidate `delegator migrate` or `delegator update` on a record that pauses a default Worker preset.

Final lifecycle, pins, the Seats statement and the PATCH stay pending. They are not in this review.
