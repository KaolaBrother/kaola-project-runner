# Final affected review: issue 259 candidate `5079042e`

Reviewer: Claude Code Opus Extra High, fresh context. Final affected reviewer for original259 with integrated 263, 264, 265 and 266.
Date: 2026-10-06. Role: thinking and review only.
This report is a review contribution. It is not Host acceptance, outer acceptance or release approval.

## 1. Conclusion

The candidate is **not ready as it is**. Two test-only repairs by the same owner are necessary. After these repairs, the candidate is ready for the outer final integrated judgment.

- Product source: the repairs for D1, D2, D4, D5, D6, D7, D8, D9 and D10 are correct.
- D3 is not complete. See F2.
- D11 has one side effect. See L1. D12 has one residue. See L2.
- F1: one case in the changed 244 suite cannot pass. I found this by source trace.
- F2: eight inventory suites still start mock sessions on the default launch path. One of them loses a fixture variable on that path.
- F1 and F2 need no product source change.
- The W1 to W5 repairs are correct in the cases that the owner named.
- The six answers are accurate. Three sentences need a small correction.
- The delivery states the native limits and the 266 limits correctly. They are limits, not hidden defects.
- I found no authority gap and no value gap. I do not print the human decision marker.

## 2. Exact candidate and identity

- Candidate: `5079042e12e17182897866a589e6b3a5d2248383`. Parent: `b7f5bc26`. Branch: `workflow/issue-259`. Worktree: `.kw/worktrees/issue-259`.
- The worktree was at this commit and clean at the start and at the end of my review.
- Refinement base: `2989c8cf`. Assignment base: `77d57fc0`.
- Diff `2989c8cf..5079042e`: 52 paths, 28 authored and 24 generated. I counted them.
- The last commit changes one test file (5 lines added, 5 lines removed). It changes no product file and no generated file.
- These hashes agree with the binding: delivery `90c1d7c4…`, six answers `7eaed728…`, manifest `2c8950af…`, 991 final receipt `a0a70d68…`, 991 logs `3ac1177a…` and `2db06cad…`.
- The 259 test file hash is `3730a42a…`. It is equal to the `source_sha256` in the 991 final receipt.
- `scripts/kaola-dispatch.py`, `scripts/kaola-record-contract.py` and `inquiry-report.md` are byte-equal to their generated copies.
- `templates/grok-golden/` and `templates/budgets.json` have no change from `77d57fc0`.
- The diff has no change in the holder, the ACP entry, the launch broker, the bridge, the quota catalog, the adapters or the platform manifests.
- The three 266 files have the same content as `cfa491dd`. Their file mode is 100755 now.
- The six numbered project items are byte-equal between `2989c8cf` and `5079042e`. I hashed the item block myself.
- `inquiry-report.md` is 7978 bytes. The budget is 8192 bytes.
- `git diff --check 2989c8cf..5079042e` is clean.
- The frozen 2989 tool hashes agree with `/tmp/kpr-985-frozen-tool-invocation.json`: dispatch `2db85d75…`, contract `ba2ce83f…`.

## 3. Sources read

- First review `/tmp/kpr-i259-970-opus-final-review.md` and Host disposition `/tmp/kpr-i259-982-host-opus-disposition.md`.
- Owner scope text `/tmp/kpr-i259-978-owner-scoped-section.md` and the candidate `AGENTS.md`.
- Full diff `2989c8cf..5079042e` of all authored paths. Diff `b7f5bc26..5079042e`.
- Current candidate source for each D item, with the adjacent code.
- Delivery, binding, manifest, six answers, original return, Host judgment 993, Host review 991.
- Receipts and logs: 991 (failed and passed), 982 (records, dispatch, reader, role, upgrade, routes, generated, fixture names), 988 (two).
- `/tmp/kpr-993-candidate-verification.json`, `/tmp/kpr-970-live-authority-adoption-verification.json`.
- `/tmp/kpr-988-maintenance-compatibility-disposition.md`, `/tmp/kpr-985-frozen-tool-invocation.json`, `/tmp/kpr-985-maintenance-returned-retire.json`.
- `/tmp/kpr-i264-native-boundary-limitations-20261006.md`, `/tmp/kpr-i264-882-host-proof.md`, `/tmp/kpr-i266-963-host-review.md`.
- `/tmp/kpr-i259-963-intermediate-findings.md` (writer findings).

## 4. Method and limits of this review

- I ran no test, no suite, no inventory and no native launch.
- I changed no repository file, no generated file, no routine record and no outer state. I wrote only this report.
- I used read-only commands: `git` (diff, show, log), file reads, hash calculations and text searches.
- I parsed one test file as a syntax tree. I did not import it and did not run it.
- I read key names and grant rows of the two live routine records. I did not write them.
- "Source trace" below means: I followed the source lines. I did not run the code.
- The 982 and 988 receipts have no source hash. They ran before the repair commits. The manifest and the Host check of 264 hashes bind them to the candidate. I did not prove that binding myself. I use it as Host-verified evidence.

## 5. Concrete unresolved defects

### F1 (medium). One case in the changed 244 suite cannot pass

- Path: `tests/contract/test-issue-244-dispatch.py`, `DispatchEntry.test_authorization_keys_resources_and_launch_edges`, line 1405.
- Step 1, lines 1419 to 1424. The fixture `rows-auth.json` has the top-level key `classes`. The helper `project` (line 222) asserts exit code 0. `normalize_grants` raises on `classes` (`scripts/kaola-dispatch.py` lines 272 to 275). `command_project` then returns exit code 2.
- Step 2, lines 1426 to 1430. The fixture helper gets `paused=["zcode/default"]` and one `codex/default` grant. The helper calls `migrate_authorization_limits` and asserts an empty blocker list (lines 201 and 202). The Host branch adds an `authorization.paused` blocker for an id without a grant row (`scripts/kaola-record-contract.py` lines 473 to 476).
- Step 3, line 1434. The case expects the reason `paused` from a legacy `paused` list. The reader refuses that list (`scripts/kaola-dispatch.py` line 272).
- Evidence type: source trace. Each step is deterministic. The case has no skip marker.
- No receipt runs this case, at `2989c8cf` or at `5079042e`.
- The manifest lists this method in `changed_tests`, `changed_or_added`. This refinement changed lines 1407 and 1427 of the same method.
- Origin: the reader rule came with `be04bd09`. The helper assertion came with `ea1ee07f`. The two commits are in the 259 branch. The first review did not find this case.
- The product behavior is safe, because the tool refuses. The defect is a stale test.
- Effect: `./scripts/validate.sh --suite test-issue-244-dispatch.py` fails. The whole inventory fails. The release rule uses the inventory.
- Related fact: the manifest lists 32 changed methods in this file. Named receipts run 7 of them. The changed helper has 76 call sites. Each call site now gives an explicit count. Only this call site gives `paused`.
- Smallest correction:
  1. Step 1: expect the refusal, or remove `classes` from the fixture.
  2. Steps 2 and 3: use a grant row with `state: "paused"`, or keep only the exclusion assertion.
  3. Run this case.
  4. Then run the 244 file one time with `--suite`. The Host decides this step.

### F2 (medium, integration). The D3 repair does not include eight start suites

- The repair: `scripts/validate.sh` line 230 exports `KAOLA_LAUNCH_BACKEND=direct`. Lines 544 to 547 set the value for each suite. Sixteen fixtures keep or name the selector.
- The gap: these inventory suites call `kaola-acp.py start`, and their fixture environment removes the selector.

| Suite | Line | Fixture environment | Note |
| --- | --- | --- | --- |
| `test-droid-acp-contract.py` | 72 | removes all `KAOLA_*` | gives `DROID_ACP_LOG` at line 74 |
| `test-issue-65-steering.py` | 85 | removes all `KAOLA_*` | mock parameters are in the argument list |
| `test-issue-65-host-contract.py` | 217 | removes all `KAOLA_*` | same |
| `test-issue-73-canonical-root.py` | 439 (also 125, 510) | removes all `KAOLA_*` | same |
| `test-issue-95-reader-exception.py` | 89 | removes all `KAOLA_*` | same |
| `test-issue-98-dsh-acp.py` | 324 (also 469, 545) | removes all `KAOLA_*` | runs the entry in `sandbox-exec` |
| `test-issue-165-path-drift.py` | 70 to 79 | isolated | same shape as 162 and 164 |
| `test-issue-123-shared-refs.py` | 129 to 137 | isolated | uses installed copies |

- `test-issue-247-codex-child.py` line 135 has the same filter. Its start refuses before a launch. It has no effect.
- Source of the default path: `scripts/kaola-acp.py` lines 4499 to 4510 give `auto` without the variable. `scripts/kaola-launchd-broker.py` lines 328 and 329 make `auto` equal to launchd on macOS.
- Source of the lost variable: the broker keeps named variables only (lines 64 to 74 and 172 to 181). `platforms/droid.yaml` line 43 has an empty allow-list. The direct path gives the full environment to the holder (`scripts/kaola-acp.py` line 567).
- Effect for the droid suite: `tests/contract/fake-droid-acp-agent.py` line 28 reads `DROID_ACP_LOG`. On the default path it gets no value and writes no log. The suite reads that log (lines 116 to 123) and uses its events at lines 278, 348 and 471. Those assertions cannot pass. This is the same defect class as the first D3 case. Evidence type: source trace.
- Effect for the other seven suites: their result on the default path is not measured. Each start makes a launchd job in the user domain from a test fixture.
- Writer record: `/tmp/kpr-i259-963-intermediate-findings.md` line 27. A 162 probe without the selector stopped at the 90.16 second limit. A long temporary root was also present, so the cause is not isolated.
- The delivery D3 row and its list of unrun suites do not name these suites. The `982-validate-routes` receipt proves the lane variable only. It does not prove that a fixture keeps it.
- Host disposition 982 says: shared validation mock fixtures use direct transport. These fixtures are mock fixtures.
- Smallest correction:
  1. Apply the same selector rule to the eight fixtures. Keep `KAOLA_LAUNCH_BACKEND=direct` in the filtered environments. Name `direct` in the two isolated environments.
  2. Keep the two 266 suites on `auto`.
  3. Run the droid suite (20 cases). Run one case for each other environment shape, or name the suites that did not run.
  4. Correct the D3 row, the unrun list and answer 5.

## 6. Small items (low)

**L1. The D11 repair removes the only unknown-availability statement from the Host view.**
- Path: `scripts/kaola-dispatch.py` line 3601. Text source: lines 518 to 535.
- `text` is `availability unknown: <ids>`. It repeats all presets only when no availability evidence exists. In other conditions it names a subset.
- The Host view `presets` list does not show availability. Owner group 3 says "Preserve unknown availability honestly" (`docs/dispatch-collect.md` line 275).
- The `project` output keeps the statement.
- Line 3599: `catalog_source` is the directory of the first manifest. That is the catalog root in the repository layout only. In the installed layout, ten manifests are in ten directories (lines 215 and 216). The digest includes all files.
- Correction: keep one short unknown marker in the Host view, and give the common parent directory. As an alternative, state this limit in the delivery.

**L2. D12 residue.** `README.md` line 299 says "outside the general worker cap".

**L3. Schema 1 limit removal write.** `scripts/kaola-dispatch.py` lines 4425 to 4433.
- The command reports `removed` and writes revision + 1 when the key is absent.
- Line 4426 writes the body with default separators. The snapshot writer uses the compact sorted form (line 3447). The body text becomes longer. The content is equal.

**L4. Two names for one list.** `delegator migrate` returns `dropped` (line 5642). `delegator update` returns `removed` (line 5701). The first 991 run failed on this difference.

**L5. Assertion coverage.** The Delegator branches of D4 (`scripts/kaola-record-contract.py` lines 587 to 589 and 608 to 610) and of D8 (lines 443 to 445, 680 to 682, 707) have no assertion. The source is correct. The Host branches have assertions (259 test lines 220 to 237).

**L6. Lifecycle notes. These are not candidate defects.**
- `AGENTS.md` line 142 has the status sentence "This review remains pending." It becomes false at acceptance. Retire or replace the run-scoped section at close-out.
- The 259 test line 965 reads commit `1acf4b12` with `git show`. The sink must keep that commit reachable. The current sink style does.
- The main checkout has an uncommitted `AGENTS.md` edit. The lifecycle merge must keep the owner text and take the two scoped sections.

L1, L3 and L4 change product bytes. If the owner does them now, the generated copies and the hash binding change. A later existing task is a valid alternative. The Host and the outer Delegator decide.

## 7. D and W resolution

| Id | Result | Candidate source | Evidence |
| --- | --- | --- | --- |
| D1 | Resolved | Contract lines 603 to 610. Ordinary update uses the same migration and reports `removed` (dispatch lines 5686 to 5701). | 991 final receipt: one case, exit 0, 0.802 s. Test lines 349 to 368. This run used candidate bytes. |
| D2 | Resolved | Null-only path: dispatch lines 4122 to 4131. Schema 1 path: lines 4413 to 4433. Command text: contract lines 389 to 403. | `982-final-records`. Test lines 208 to 218, 238 to 259, 261 to 292. |
| D3 | Partly resolved | `validate.sh` lines 230 and 544 to 547. Sixteen fixtures. | Route receipt and selected cases. See F2. |
| D4 | Resolved | Host: contract lines 493 to 496. Delegator: lines 587 to 589 and 608 to 610. | Host side: test lines 220 to 229. Delegator side: source only. |
| D5 | Resolved | `docs/conventions.md` lines 152 to 177. | Test lines 962 to 978. The limit is stated. |
| D6 | Resolved | Dispatch lines 368 and 381. | Test lines 550 to 555. |
| D7 | Resolved | Dispatch lines 794 to 796. | Test lines 672 to 680. |
| D8 | Resolved | Contract lines 624 to 640, with calls at 443 to 445, 620, 680 to 682, 707 and 786. | Host side: test lines 230 to 237. Delegator side: source only. |
| D9 | Resolved | Contract lines 566 to 568 and 720 to 723. | 991 final receipt. Test lines 369 to 374. |
| D10 | Resolved | Dispatch lines 3507 to 3513 and 5298 to 5299. | Test lines 1719 to 1722, strict `current`. |
| D11 | Resolved, with a side effect | Dispatch lines 3599 to 3601. | Test lines 176 to 178. See L1. |
| D12 | Resolved, with one residue | README, `dispatch-collect.md`, `quota-packages.md`, 244 helper. | See L2 and F1. |
| W1 | Resolved | The case runs the named recovery. | Test lines 208 to 218. |
| W2 | Resolved | Schema 1 fixtures have a limit, a Class copy and a grant without a count. | 255 `LEGACY_BODY`. 259 test lines 261 to 292. |
| W3 | Resolved | Strict `current`. | Test line 1721. |
| W4 | Resolved in the helper | The helper adds no count and removes no argument (244 lines 188 to 203). | Eight named 244 cases. See F1 for one stale call site. |
| W5 | Resolved | `count-unreadable` is asserted. | 259 test line 289. |

Notes on the product repairs:

- D1: an unmatched Worker pause now blocks `delegator migrate` and each `delegator update`. The record stays byte-equal. The two named routes can run: add the id to `exclusions`, or relay a Host hold and then remove the list with a sourced null patch.
- D2: a null-only patch on a current record now does the full authorization migration. It reports each removal. It stops at each ambiguous pause, switch or group.
- D6: an ended grant of an unknown Class now becomes an exclusion. A later grant of that preset also needs the exclusion to be removed. This is a visible, safe state.
- D9: the migration removes `class` when the value is `Elite`, `Expert` or `Worker`. It does not compare the value with the catalog. The receipt names each removal.

## 8. Scoped requirement reader and report (owner 978)

- Reader: `requirement_scope` and `requirement_lines`, dispatch lines 3631 to 3680. Heading names: lines 112 to 115.
- Output: `user_requirements.project` and `user_requirements.delegator`. `missing` appears only when no region exists.
- A legacy heading and the legacy marker region stay project-scoped.
- The only consumer is `delegator_view` (line 3705). The Host and Sideagent views have no requirement text. A 255 case asserts this.
- The tool stores no copy. A 255 case asserts byte-equal state.
- Template: `inquiry-report.md` lines 75 to 86. It lists the two scopes separately. An empty scope says "none". It gives the role rule for each scope.
- `AGENTS.md`: project section at line 123, Delegator section at line 138. The six items are unchanged.
- The completion paragraph stays in the project section. The appointment moved to the Delegator section. It applies to this run and to this outer Delegator. It keeps the conditional release dependency. It gives no duty to an ordinary Delegator, no seat and no model grant.
- Source trace on the candidate `AGENTS.md`: the project array gets the heading, the source line, the six items and the completion paragraph. The Delegator array gets the heading, the source line and the appointment paragraph.
- Limit: the Delegator scope has one English heading name. A different heading name is not read as a Delegator requirement.
- Evidence: `982-final-reader`, 5 cases, exit 0, 2.362 s.
- Result: correct.

## 9. Seven groups

| Group | Result |
| --- | --- |
| 1. Exact grant counts | Correct. The limit recovery can now run (D2). |
| 2. One switch authority | Correct. No change in this refinement. |
| 3. Derived capabilities | Correct. See L1 for the Host view. |
| 4. Catalog defaults | Correct for the Host and for the Delegator (D9). |
| 5. Shared groups | Correct. Duplicate presets refuse in the writers and in the migration (D8). The reader order is in the convention (D5). |
| 6. Current eligibility and duties | Correct now. D1, D4 and D6 are repaired. |
| 7. Objective and source pointers | Correct. No change in this refinement. |

- Admission: the diff does not change the admission code.
- Projection: the diff changes the Host capability view (D11) and the Delegator seat projection (D7) only.
- Writer: the diff changes the authorization section writer (D2) and the Delegator update result (D1).
- Migration: the diff changes `migrate_authorization_limits` and `empty_state` only.

## 10. Six owner answers

| Answer | Accuracy |
| --- | --- |
| 1. Template fidelity | Accurate. It now states detection, correction and the no-readback condition. Correction: the five cases ran before the commit. Say "bound to this candidate by hash". |
| 2. Current information | Accurate. Nine different 259 cases have a run. It says correctly that the VRPAI and VRPCAD criterion needs the outer judgment. |
| 3. Host autonomy and Sideagent | Accurate. The three retirement cases agree with the receipts. The limits are stated. |
| 4. Recovery | Accurate after the D2 repair. Each named refusal and recovery has a source branch and a case. |
| 5. Continuous improvement | Two corrections. "Shared validation uses direct mock transport" is not true for eight suites (F2). "Omits repeated text" is true only without availability evidence (L1). It must also name F1 after the repair. |
| 6. Upgrade continuity | Accurate. The reader order, the previous reader refusal and the three tool hashes agree with the sources. |

The delivery D3 row needs the same correction as answer 5.

## 11. Evidence binding

- The D1 and D9 block is now in the body of an executable case (259 test lines 349 to 374). No `return` comes before it.
- The first 991 run failed at line 373 with `KeyError: 'removed'`. The pause assertions passed before that line. The failed receipt and log are kept.
- The final 991 run shows one case and `OK`. Its product bytes are equal to the candidate, because the last commit changes one test file only.
- The delivery says correctly that the old `982-final-records` pass did not run the old block.
- The other 982 and 988 receipts keep their original scope. See section 4 for the binding limit.
- Reuse of the native proof and the 266 proof is valid at its original scope. Those source paths have no change in this refinement.

## 12. Compatibility, update convention and mixed versions (988)

- The convention gives the order: install the matching reader, then migrate. It names the refusal of the previous reader and the recovery.
- A case runs the previous reader `1acf4b12` on a grouped record. That reader refuses. The matching reader reads the same bytes.
- Retirement keeps no stored row. The command receipt carries the outcome. A case asserts no `retired` row and no maintenance input from the retirement.
- The 985 receipt shows revision 984 to 985, Host revision 736, outcome `resolved`. The frozen tool hash is the 2989 Git object.
- `retire_record`, `host_changes` and the node guidance have no change from `2989c8cf`.
- The convention says: an empty later batch proves only its range. I do not treat the earlier partial checkpoint as settled by a node. The Host resolved that alert from the original receipts.
- Not measured: an installed old node recipe that reads a newer record. That recipe can give the same false warning again until its update. The convention gives the recovery.
- I ask for no history in the current state.

## 13. Explicit limits: accepted or not measured (these are not defects)

- Native use of the changed report. Native timer readback.
- Corrected Codex initialize request and structured completion signal.
- Independent outer inquiry and installed bridge emission.
- Host outcome 3 on runtimes other than the accepted Claude route (immutable 055).
- DSH background forwarding outside the finite route.
- Droid and Cursor native boundary: not reached, not failed, not unsupported.
- Launcher on Linux and other systems. GUI, TCC and Keychain. App quit, logout and restart.
- Live ACP smoke for each platform through the default launch path. The release rule requires it.
- Installation and installed activation. The Host 970 and 971 adoption used candidate source at `2989c8cf` without installation.
- Full 244, 255 and 259 suites and the named ACP suites did not run on this candidate.
- Requirement 2 owner criterion: useful task progress beside maintained state for the VRPAI and VRPCAD cases. The outer Delegator judges this.
- Outer legacy mapping of the Delegator record. The outer Delegator owns it.

## 14. Live facts (read-only)

- Host record: current schema, revision 996. Grants: grok 1, cursor 1, codex 1, one Droid group with count 2, one Claude group with count 1. No aggregate limit key.
- The `opus-xhigh` restriction is stored for that choice. Switch permission is on the two groups only.
- Host record size: 80737 bytes. Stored body: 27256 bytes. Fifteen tasks. No holds, alerts, decisions or unverified rows. No `retired` key.
- Delegator record: no schema. No `paused` list and no `revoked` list, so D1 does not apply to it.
- Its five grants have `class: "Elite"`. The candidate migration removes these copies and names each removal.
- Two groups have a text switch condition. The candidate tool refuses each `delegator update` until the outer Delegator maps these two values from the owner source. I did not judge that mapping.

## 15. Required repair and next step

Owner: the original259 assignment. The Host holds source custody now. Reviewer of the repair: the Host, then the outer Delegator.

1. Repair F1 (one 244 case). Run that case.
2. Repair F2 (eight fixtures). Run the droid suite and the selected cases. Name each suite that does not run.
3. Correct the delivery D3 row, the unrun list, answer 1 and answer 5. Update the binding and the manifest.
4. L2 and L5 can go in the same test and document edit. L1, L3 and L4 need a decision, because they change product bytes.
5. F1 and F2 change test files only. If the product bytes stay equal, this product source review stays valid. Only the changed test paths need a new check.
6. Recommendation: run the 244 file one time with `--suite` after the repair. The demonstrated stale case is the reason, not the number of cases.

After steps 1 to 3, the candidate is ready for the outer final integrated judgment.

These duties stay open and are not in this review: final affected QA, the outer verdict, the original lifecycles and cleanup for 259, 263, 264, 265 and 266, pins, the Seats statement and the conditional next unused PATCH.

I stop work after this report. I do not control workers.
