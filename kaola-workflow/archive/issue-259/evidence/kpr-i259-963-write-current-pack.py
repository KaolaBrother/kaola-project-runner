from pathlib import Path
import hashlib,json,subprocess
root=Path('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
manifest_path=Path('/tmp/kpr-i259-host-compact-implementation-hashes-20261006.json');manifest=json.loads(manifest_path.read_text());assert manifest['candidate']==head
copy=json.loads(Path('/tmp/kpr-i259-963-final-disposable-upgrade/receipt.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
six='''1. **Template fidelity.** The generated Host and Delegator entries keep their canonical native timer text. The Delegator user report alone must show the current Elite/Expert summary. Host seat access stays on demand. The final disposable managed copy selects the candidate reporting reference and executes its matching copied tool. The supplied canonical timer body returns match; absent readback returns unavailable. All copied reference/tool hashes match the candidate; render and generated checks pass within unchanged budgets. This is model-free tool/template evidence. Native timer API readback and native adoption of this changed report remain unverified. The accepted immutable055 full installed Skill Read/use remains valid for its unchanged native reload boundary.

2. **Structured, current and inspectable information.** The closed writers remove handled exceptions from stored current collections. All role views and injected bodies derive from them. There is no resolved flag, tombstone or alternative retrospective slot. Newer recovery inputs, active duties, pending owner relays and exact task/holder links stay current. Grant/group counts are the only seat count authority; aggregate limits, copied Class/capability lists and duplicate switch/pause lists leave the supported stored contract. The Delegator report derives shared counts, lifetimes, linked work and available/held/unknown capacity from authorization and verified dispatch/session facts. Missing Expert authorization says none. No second seat table is stored. Twenty named259 cases and five admission cases pass on their measured source routes. Final copied CLI cycles test repeated migration, stored JSON, current views, ambiguity refusal and pending duty/language retention. Current live Host/Delegator records were only read. Their owner migration and semantic adoption remain pending. Useful VRPAI/VRPCAD task advancement alongside this final contract, and final native use of the report, are not established by these fixtures.

3. **Host autonomy and Sideagent lifecycle.** A verified session-bound completed Host signal registers typed recovery input before native reload can skip maintenance. The existing safe boundary selects one bounded batch at unchanged business revision. Compatible/repeated inputs coalesce; worker compaction does not start a node. Checkpoint settlement binds the actual sent input, batch and node holder. Missing original sources and failed recipe/checkpoint/stop remain visible duties. The node prompt now states that applied means this node's authorized write/retirement; an unchanged Host record is retained with its next reader. It checkpoints once, returns partial results to Host, then ends. The checkpoint engine and native reload remain unchanged. Reused Host929 actual immutable055 Claude proof has completed41/42 → typed input43 before reload46, full installed Reads49/50 and use52, seven non-overlapping exact node stops, preserved newer input/decision and actual Host binding recovery. Current three binding cases pass. Corrected actual Codex initialize negotiation/structured signal and independent outer inquiry remain Host-owned and unverified. Controller requests are not additional native occurrences or independent inquiry proof.

4. **Recovery and informed autonomy.** Existing-row refusals name collection/id, current revision, removal operation and original evidence. An absent row is not recreated. Unresolved unclassified matters retain original evidence through the current decision/reconciliation route. Legacy count/switch/group ambiguity refuses writes and preserves bytes; it does not infer expanded authority. Unknown, held, reserved and idle-but-unreclaimed sessions are not free capacity. The original259 f888 task/session/holder and admission/status remain actionable despite the missing index row. Accepted266 launch custody is integrated from exact handed-over bytes. The seven current composed checks use real entry/manager paths with fake ACP clients and exact PIDs; they are model-free. Immediate holder-alive refusal reports unknown effects; later exact PID absence is a separate fact. Missing/foreign records do not prove reclamation, and cleanup is not stop. Existing safe retry and authentication/quota handling are preserved. No universal fault freedom, permanent runtime unsupportedness or all-platform native PASS is claimed.

5. **Continuous improvement.** The implementation reuses current resolution, dispatch projection, carrier boundaries and existing suites. It removes duplicate count/switch/pause/capability authority and copied routine requirements. Reference text was consolidated within existing byte budgets. The validate change adds only the two266 inventory names and preserves subset selection and the accepted Bash prerequisite repair. This return reuses accepted33 cases and unchanged055/DSH/native266 evidence. It runs named changed cases, two composed interfaces, copied-template/current-view calls and render/generated checks. No whole inventory or native matrix ran. Four additional old fixture expectations were corrected when inspection exposed affected failures; one real first-write migration repeat defect was fixed. Intermediate failures remain evidence. The existing Host improvement path still identifies coupling, defines the preserved outcome and affected boundary, compares minimal reuse/removal, resolves material scope choices and checks integrated interfaces. Broader Rust/Swift/Workflow research remains in its original scope; no new recurring audit or framework was added.

6. **Future upgrade continuity.** Version-matched readers derive Class/default model/effort from the selected catalog/template; explicit owner overrides remain input. Compatibility rows derive mechanically from grouped grants. Migration plans before writing, preserves active exclusions, paused grants/reopening duties, pending owner relays, original stop/handoff links and user language, and refuses conflicting or total-only authority with an executable owner recovery path. The affected existing255 v1 case first refuses copied project.rules without changing bytes, then uses the rule in the disposable AGENTS user section and stores one source pointer. Its first write omits an empty retirement collection; repeat returns current. The final disposable installed-template copy makes25 actual calls in1.825492s, with exit0 or expected ambiguity exit2, matching candidate tool/reference/catalog hashes and removed scratch. Repeated current migration is stable and does not fake a Host business revision. Existing v0.9.0/body-reader checks pass on their measured routes. This proves supported fixture/tool continuity, not installation on a live consumer or native use of all changed templates. Current owner judgments, incompatible legacy free text and complete all-runtime adoption remain pending with the Host.
'''
sixpath=Path('/tmp/kpr-i259-six-requirement-answers-20261006.md')
sixpath.write_text('# Current six owner answers — original259\n\nCandidate: `'+head+'`. These answers are a source return. Final affected Opus and outer acceptance remain pending.\n\n'+six)
rows=[]
for p in ['records','admission','checkpoint','receipt-boundary','final-generated']:
 d=json.loads(Path('/tmp/kpr-i259-963-'+p+'.json').read_text());rows.append('| '+p+' | '+d['candidate'][:8]+' | '+('20' if p=='records' else '5' if p=='admission' else '3' if p=='checkpoint' else '1' if p=='receipt-boundary' else 'render/generated lane')+' | '+str(d['seconds'])+'s | exit'+str(d['exit'])+' |')
parent_lines='\n'.join('- `'+x+'`' for x in manifest['commits'])
report=f'''# Original259 current source return — 2026-10-06

Clean candidate: `{head}` on `workflow/issue-259` in `{root}`. Parent: `{manifest['parent']}`. Original source base: `{manifest['base']}`. Host acceptance of this final integrated candidate is pending.

This return adopts the latest951 grant-count correction, the955 seven current-information groups, and accepted266 source at `cfa491dda33a1130746743ff15e10bdbbf11a324`. It preserves the accepted263/264/265 source, native reload, prior state/index and Bash prerequisite repairs. Earlier scoped Host939/945 acceptance applies to its measured candidates, not automatic final acceptance here. Historical reports remain evidence for their own candidates.

## Exact source and custody

{parent_lines}

The full binary patch is `/tmp/kpr-i259-host-compact-implementation.patch`, SHA256 `{manifest['patch']['sha256']}`, {manifest['patch']['bytes']}B. The authored-only patch is `/tmp/kpr-i259-host-compact-implementation-authored.patch`, SHA256 `{manifest['authored_patch']['sha256']}`. The hash manifest lists every changed source/generated path, base hash, candidate hash, parent, changed test body, reference size and original receipt binding. There are {manifest['authored_count']} authored and {manifest['generated_count']} generated changed paths. These are path counts, not a test inventory.

Generated payloads came from `./scripts/render-skills.py --write`. The final named generated lane includes render check and Skill validation. No generated file was hand-edited and no budget was raised. Frozen `templates/grok-golden/` is unchanged. The validate patch adds exactly two266 inventory entries; named-suite selection and prerequisites remain unchanged. AGENTS owner requirement2 adopts951/955; the other five owner requirements match13f.

Sole writer remains original259/f888: holder `f888667b7e6a5071753d218d0cc0484f`, session `codex-KPR-i259-host-compact-impl`, ACP `01a10ef7-cb78-70c0-8380-ec495356e431`, codex/default GPT-6.1 Sol/high/Fast off. Source custody stays here until Host accepts and exact-stops it. It is occupied/unreclaimed. No new claim, mission, reviewer, native model target, live index row or lifecycle was created.

Claim digest `{manifest['claim']['digest']}`; original state SHA256 `{manifest['claim']['state_sha256']}`; ledger SHA256 `{manifest['claim']['ledger_sha256']}`. All four DONE lines remain immutable. Recovery read installed Finalization only; no lifecycle command ran.

## Seven owner groups: implementation and remaining adoption

| Group | Source/writer/derived contract | Proof and owner boundary |
| --- | --- | --- |
| 1. Exact grant counts | `kaola-record-contract.py` rejects independent authorization caps. Admission removes aggregate/plan caps and derives only exact effective grant/shared counts. No sentinel cap or prose override. | Six granted Elite seats admit; third Droid and per-grant excess refuse. Redundant legacy limits migrate only with unchanged explicit grant authority; total-only/conflicting limits remain source-based owner recovery. This run cap4 was explicitly revoked at952, not restored. |
| 2. One switch authority | Grant/group owns choices and switch permission, with existing lifetime and restrictions. Choice membership alone is no switch permission. | Known consistent legacy switch rows map; false/conflicting/partial group intent refuses without writes. Owner free-text switch conditions must map to typed permission plus current restrictions/duty from originals. |
| 3. Derived capabilities | Existing dispatch/candidate projection derives grants, default Worker pool, exclusions, holds and verified availability. No stored capability copy. | Exclusion, paused/held and unknown propagation checked. Missing counts and unknown occupancy are withheld, not guessed available. Current live derived copies need Host-owned migration. |
| 4. Catalog defaults | Class/profile/default model/effort comes from a version-matched catalog/template. Only explicit owner overrides are stored. Partial roots can use existing `--platforms` exact catalog. | Catalog source/SHA is visible; fixture default/override checks pass. Mismatched or unavailable sources remain explicit unknowns. No full profile injection. |
| 5. Shared groups | One `preset_ids` group owns count/state/switch/lifetime/restrictions. Compatibility per-tier rows are generated. | Droid shared2 and Claude shared1 count once. Differing legacy rows and overlapping grouped rows refuse; per-choice restrictions stay intact. No second writable seat table. |
| 6. Current eligibility/duties | Handled rows leave stored applicable collections. Ended/revoked Expert eligibility leaves grants. Active Worker exclusions, paused/reopening duties, unresolved exact stop/handoff and pending owner relays remain. | Repeated create/update/resolve/retire and stored JSON/all-role view checks preserve newer inputs and unfinished duties. Expired Expert and source-backed settled relays are removed. Unknown originals stay visible. No history text outlet. |
| 7. Objective/source pointers | Closed project input holds concise goal and original requirements source. Owner requirements remain in AGENTS. Copied rules/adoption history is rejected rather than silently moved. | Existing255 legacy rule ambiguity refuses and preserves bytes. Supported source-backed migration retains the AGENTS rule and source pointer. Current Host/Delegator legacy content needs owner judgment before removal. |

Current authorization permits grok/default1, cursor-cli/default1, codex/default1, Droid choices default/opus/core in one shared count2, Claude choices default/opus-xhigh/sonnet in one shared count1: six possible Elite seats. These are authorized counts, not globally free seats. Missing Expert authorization is none. Host and Sideagent are separate; Worker pool authority is unchanged.

The concise summary is mandatory in the Delegator USER-FACING report only. It shows preset ids, counts, applicable Expert lifetime, working linked tasks, idle available capacity and held/unavailable/unknown separately. Idle-but-unreclaimed and reserved sessions are not automatically available. Both user view and on-demand Host dispatch access use the same current projection. There is no compulsory Host heartbeat section or injection, second seat list, copied Delegator occupancy, manual history, new registry or timer change.

## Current-only operations and actionable recovery

The existing resolve/clear/retire writer removes the handled row atomically; role views/body derive from stored state. Positive exception types and transition shapes are checked by tools. Agents judge semantic currentness against originals. Unknown is not resolved. A newer unrelated record/input and unfinished exact stop or handoff remains current. An absent handled row says do not create it; it does not ask for a retrospective note elsewhere.

Use the existing commands with the named actual file, row revision and original source/evidence. These are prepared owner operations, not live commands run by this source assignment:

```bash
python3 scripts/kaola-dispatch.py state migrate --file ACTUAL_HOST_FILE
python3 scripts/kaola-dispatch.py state update --file ACTUAL_HOST_FILE --writer host \\
  --source ORIGINAL_OWNER_DECISION --section authorization --expect-revision ACTUAL_FILE_REV \\
  --set '{{"elite_cap":null}}'
python3 scripts/kaola-dispatch.py state update --file ACTUAL_HOST_FILE --writer host \\
  --source ORIGINAL_OWNER_DECISION --section project --expect-revision ACTUAL_FILE_REV \\
  --set '{{"rules":null,"skill_adoption_source":null,"requirements_source":"AGENTS.md"}}'
python3 scripts/kaola-dispatch.py state retire --file ACTUAL_HOST_FILE --writer host \\
  --source ORIGINAL_HANDLED_FACT --kind alerts --id ACTUAL_ALERT_ID \\
  --expect-rev ACTUAL_ROW_REV --evidence ORIGINAL_HANDLED_EVIDENCE
python3 scripts/kaola-dispatch.py delegator migrate --file ACTUAL_DELEGATOR_FILE
python3 scripts/kaola-dispatch.py delegator update --file ACTUAL_DELEGATOR_FILE \\
  --expect-revision ACTUAL_FILE_REV --set '{{"watch":{{"ACTUAL_HANDLED_ID":null}}}}'
```

Do not replay the cap removal on this run: Host already removed it at952. Only clear an EXISTING handled row with its original evidence and fresh revision. Task retirement additionally needs the existing accepted cite and matching terminal dispatch/exact-holder stop, or an explicit current handoff. Unresolved unclassified matter keeps original evidence through the existing decision/reconciliation route until typed. Plan ambiguous migration, resolve original intent, then repeat `migrate --write`; a blocked plan leaves bytes unchanged. No blanket live JSON rewrite is proposed.

Read-only correlation at `/tmp/kpr-i259-963-current-source-correlation.json` captured Host revision969. Host authorization has no cap, but still has legacy Class/capability/switch/pause/revocation copies, and project rules/adoption fields. Owner next: adopt one typed grant/group authority from original current choices/counts, map known pause/switch/restrictions, retain active exclusions and exact stop duties, then remove proven duplicate fields through revision-bound updates. Source pointers must replace copied project content only after original owner intent is preserved in AGENTS or its proper current duty. The legacy Delegator has free-text switch conditions and project bags; migration must refuse ambiguous intent, not interpret them as permission.

The captured index has THREE in-flight rows: original DSH proof, original266 and original Devin Host proof. It omits f888. Original tasks/admission/status still bind f888; the missing row does not make its seat free. Exact start/status references are `/tmp/kpr-i259-862-compact-implementation-admission.json`, `/tmp/kpr-i259-929-status.json`, and Host945 correlation. Owner next: correlate known original stop receipts and current task/holder facts in the existing projection, adopt actual dispositions where due, and retain missing/unknown evidence as attention. No row is fabricated, prompt replayed or claim reconstructed. The precise historical cause of omitted rows is not proved by this read.

## Accepted266 integration

Exact accepted handoff is `cfa491dda33a1130746743ff15e10bdbbf11a324`. The three helper/test files match original963 SHA256 byte for byte. Overlap patches for ACP/tmux/renderer/validate were reconciled into current source, not copied over it. Guidance retains backend-dependent native-resume recovery and adds the outside-caller launch route. `auto` is the default; explicit backend and inherited route propagate through the supported entry. Holder/checkpoint/reload functions are unchanged from13f. Source verification and original final limits are bound in the manifest.

The existing one-shot per-user outside launcher retains argv/session identity and environment isolation. Failed startup handles `proc=None` and returns truthful effects. Missing record directory has actionable cleanup; matching unresolved native effects retain the attempt. Cleanup is not stop. Missing/foreign record outcomes are not advertised as exact reclamation. No detachment service, scheduler or transport redesign was added.

Fresh integrated composed calls: `--only config_refusal` has3 checks; `--only child_record` has4 checks. Both pass through real CLI/manager paths with fake ACP clients and recorded exact PID absence. Original accepted10 helper checks and7 composed checks, normal Host/seat/outside launch/preserve-worker evidence are reused at their original candidates. Linux user-systemd/other OS, GUI/TCC/Keychain, app quit/logout/reboot, quota and outer timer remain unmeasured. No all-platform native PASS is claimed.

## Affected checks, commands and reuse

| Receipt group | Measured source | Named cases | Time | Result |
| --- | --- | --- | --- | --- |
{chr(10).join(rows)}
| final affected fixture repair | final matching bytes, committed2989 | 3 existing244 + 1 existing255 | 3.200s + 0.216s test time | PASS |
| disposable installed-template copy | {head[:8]} | 25 actual CLI calls; 3 named cases + timer match/unavailable | 1.825492s | PASS; expected ambiguity exit2 |
| integrated266 interfaces | be04, unchanged launch bytes | 2 named cases / 7 checks | original receipts | PASS, model-free |

Each JSON receipt stores literal argv, candidate, result and output hash. Execute the named commands from this worktree. The four measured groups at2d7 are reused only for their unchanged routes;781 adds grouped legacy refusal and2989 adds first-write empty-collection removal, covered by the final copied migration cases and the affected255 case. Test fixture bodies changed where the old contract was superseded; their changed names are listed in the manifest. The unrun whole244/255/259 suites are not claimed PASS.

```bash
python3 /tmp/kpr-i259-963-final-disposable-upgrade.py
python3 tests/contract/test-issue-266-launch-broker-composed.py --only config_refusal --evidence-out /tmp/kpr-i259-266-integrated-config-refusal.json
python3 tests/contract/test-issue-266-launch-broker-composed.py --only child_record --evidence-out /tmp/kpr-i259-266-integrated-child-record.json
python3 tests/contract/test-issue-244-dispatch.py DispatchEntry.test_grant_state_cap_and_owner_precedence DispatchEntry.test_heartbeat_envelope_feeds_project_and_execute DispatchEntry.test_live_rows_use_status_selection_not_platform_class
python3 tests/contract/test-issue-255-lifecycle-state.py Migration.test_plan_then_write_preserves_duties_and_lists_unknowns
PATH=/Users/ylmacstudio/.local/share/bash-5.3.20/bin:$PATH /Users/ylmacstudio/.local/share/bash-5.3.20/bin/bash ./scripts/validate.sh --suite test-generated-skills.py
```

The copied-template receipt and trace are `/tmp/kpr-i259-963-final-disposable-upgrade/{{receipt,trace}}.json`; they record actual argv/stdout and before/after/stored JSON. The mapping changes disposable consumer root and copied tool path only. Existing215 copy receipts and existing259/255 fixtures are reused. Pending duties, active Worker exclusion, paused group/reopening duty, switch restrictions and Chinese user language remain. Conflicting count/switch/group authority refuses without writes. Repeated supported migration returns current with stable bytes; no fake Host revision is written. Copied reference/tool/catalog hashes match the candidate. Scratch `{copy['cleanup']['scratch']}` is removed. Native timer grammar remains canonical; no native timer API was called. The command above needs a fresh evidence destination if repeated; its receipt directory is already present.

Preserved intermediate failures and corrections are in `/tmp/kpr-i259-963-intermediate-findings.md`, including old cap/rule fixtures, genuine migration repeat edge, reference budgets, unsupported Bash invocation and canonical path fixture mismatch. They are not new missions and are not relabeled as native PASS. No timeout increase, budget raise, full inventory, unbounded experiment or new permanent prose test was used.

## Actual native proof and pending boundaries

Host929 independently accepted immutable055 Claude2.1.289 sonnet/high/Fast off: completed41/42 → typed43 before reload46; business revision stayed5. Full installed Runner17407B and platform10472B Reads49/50 plus use52 are bound to original hashes. Seven non-overlapping nodes exact-stopped; newer input2/decision@5 remained. Actual partial/recipe refusal led to Host binding repair and scoped recovery; final checkpoint `b-3364a45e5f1b`/`ce3718cd`/recovery4 verified with unavailable{{}}. Workflow originals are diagnostic fixtures; controller requests2–4 are not additional native occurrences. Original Devin helper is exact-stopped exit0/residual[] with no helper duty. This evidence proves its immutable mechanism, not native adoption of the final state/report changes.

Accepted DSH0.2.0-rc.2 uses original263 overlay/plugin seam `ctx.compaction.compactNow(agent,signal,commandId)` and actual native compaction/end/summary events. Its bounded finite compact/read-use is reused; native Skill reload stays independent. Background forwarding outside the finite route and all-runtime Host recovery remain unverified. Current foreign-session usage projection guard remains source/fixture-proved; no token-drop heuristic or nested-event speculation was added.

Codex adapter2.0.1 supports `clientCapabilities.session.compaction={{}}`; both candidate initialize paths supply it. A raw pre-fix initialize packet is missing. Real fallback completed facts remain; lack of structured detection does not prove no compaction or permanent unsupportedness. The corrected actual initialize request and supported structured completion are still unverified. Real independent outer inquiry and installed bridge emission remain unverified. Host929 consolidated limits are `/tmp/kpr-i264-native-boundary-limitations-20261006.md`; historical cap text there is not current authority.

Prepared exact commands and sources are in `/tmp/kpr-i259-963-prepared-live-step.md`, frozen at this candidate. Owner: Host. Next: source acceptance and exact-stop of f888, then receipt-bound allocation for missing proof only. Exact proposed resources: one disposable codex/default Host GPT-6.1 Sol/high/Fast off and one transient codex/luna Sideagent GPT-6 Luna/max/Fast off, concurrent two physical sessions. Worker-seat exemption is not service/resource authorization. This plan grants no diagnostic seat and starts no model. It requires actual initialize packet, session-bound completed event, typed input before reload, original current-source node reads/checkpoint/exact reclaim at unchanged business revision, and independent outer inquiry. If the bounded signal remains unseen, preserve uncertainty and actionable inquiry recovery. Do not repeat the accepted seven Claude nodes or DSH finite proof.

## Current six owner answers

{six}
## Acceptance frontier

The owner951/955 record → relay → AGENTS adoption → source/tool/render → named CLI proof → current report path is present in the existing references and this pack. Accepted266 source is integrated; original266 lifecycle remains Host-owned. These six answers replace the old34/bbf/helper narrative in the current report. Matching older055/DSH/cefc native and upgrade receipts remain separate evidence.

Pending: Host judgment of this exact candidate; final integrated affected Opus Extra High and outer personal verdict; actual native boundaries listed above if required by that judgment; pins/Seats release disposition and original259/263/264/265/266 lifecycle. No self-finalize, archive, sink, merge, release, installation, live consumer/state/index write or login occurred. Sole source custody stays with f888 until Host acceptance and exact stop.
'''
Path('/tmp/kpr-i259-host-compact-implementation-delivery-20261006.md').write_text(report)
# Keep one matching answer body; the binding below verifies this literal body.
manifest['current_six_answers']={'path':str(sixpath),'sha256':sha(sixpath),'body_sha256':hashlib.sha256(six.encode()).hexdigest()}
for path in ['/tmp/kpr-i259-963-final-disposable-upgrade.py','/tmp/kpr-i259-963-current-source-correlation.json','/tmp/kpr-i259-963-write-current-pack.py']:
 if path not in {x['path'] for x in manifest['reference_bindings']}:manifest['reference_bindings'].append({'path':path,'sha256':sha(path)})
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print(head)
