import ast,hashlib,json,re,shutil,subprocess
from pathlib import Path
r=Path('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259');main=r.parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=r)
def info(p):p=Path(p);return {'path':str(p),'sha256':sha(p.read_bytes())}
def blob(rev,p):
 q=subprocess.run(['git','show',rev+':'+p],cwd=r,capture_output=True);return q.stdout if q.returncode==0 else None
def methods(data):
 out={}
 for n in ast.parse(data).body:
  if isinstance(n,ast.ClassDef):
   for t in n.body:
    if isinstance(t,ast.FunctionDef) and t.name.startswith('test_'):out[n.name+'.'+t.name]=sha(ast.dump(t,include_attributes=False).encode())
 return out
mp=Path('/tmp/kpr-i259-host-compact-implementation-hashes-20261006.json');bp=Path('/tmp/kpr-i259-host-compact-implementation-delivery-binding-20261006.json');dp=Path('/tmp/kpr-i259-host-compact-implementation-delivery-20261006.md');sp=Path('/tmp/kpr-i259-six-requirement-answers-20261006.md')
m=json.loads(mp.read_text());b=json.loads(bp.read_text());prev=m['candidate'];assert prev=='469015649b72a6ef846ed608648f1e8f4ebf5d9d'
head=git('rev-parse','HEAD').decode().strip();assert head=='c33724048418fa75ff0ed2e7c356d50183fb702b';assert not git('status','--porcelain')
for p in [dp,sp,mp,bp]+[Path(m[k]['path']) for k in ('patch','authored_patch','refinement_patch')]:
 q=p.with_name(p.stem+'-469'+p.suffix);assert not q.exists();shutil.copy2(p,q);m['preserved_original_artifacts'].append({**info(q),'candidate':prev})
def rows(base):
 return [{'path':p,'kind':'generated' if p.startswith(('skills/','hosts/grok-bot/')) else 'authored','base_sha256':sha(blob(base,p)) if blob(base,p) is not None else None,'candidate_sha256':sha(blob(head,p)) if blob(head,p) is not None else None} for p in git('diff','--name-only',base,head).decode().splitlines()]
for key,base in [('files',m['base']),('refinement_files',m['refinement_base']),('repair_files',m['repair_base']),('last_commit_files',prev)]:m[key]=rows(base)
for key,field in [('refinement_counts','refinement_files'),('repair_counts','repair_files')]:m[key]={kind:sum(x['kind']==kind for x in m[field]) for kind in ('authored','generated')}
m['authored_count']=sum(x['kind']=='authored' for x in m['files']);m['generated_count']=sum(x['kind']=='generated' for x in m['files'])
for key,base,exclude in [('patch',m['base'],False),('authored_patch',m['base'],True),('refinement_patch',m['refinement_base'],False)]:
 argv=['diff','--binary',base,head]
 if exclude:argv+=['--','.',':(exclude)skills',':(exclude)hosts/grok-bot']
 p=Path(m[key]['path']);p.write_bytes(git(*argv));m[key]={**info(p),'bytes':p.stat().st_size}
new_names=['continuation-task-clearance','continuation-retirement-reconcile','continuation-retirement-final','continuation-original-retirement','continuation-source-final']
new=[]
for name in new_names:
 p=Path('/tmp/kpr-i259-997-'+name+'.json');d=json.loads(p.read_text());assert d['exit']==0;assert sha(Path(d['log']).read_bytes())==d['output_sha256']
 row={'receipt':str(p),'receipt_sha256':sha(p.read_bytes()),'candidate_binding':head,'measurement':d,'execution_context':'Precommit same-assignment continuation; original literal label is retained; executed source hashes establish the binding.'}
 row['sources_match_current']={p:sha((r/p).read_bytes())==h for p,h in d['source_sha256'].items()}
 row['reuse_at_current_candidate']='Historical clean469 clearance, replaced by extended final case' if name=='continuation-task-clearance' else 'Intermediate precommit shape, replaced by final source proof' if name=='continuation-retirement-reconcile' else 'Final affected proof; no live operation'
 new.append(row)
# Preserve older source bindings and qualify their scope instead of rewriting results.
for c in m['checks']:
 c['reuse_at_current_candidate']=c.get('reuse_at_current_candidate','Original unchanged measured boundary only')+'; retirement functions changed in1000. No whole-function identity claim for affected task retirement. Final extended retirement case replaces affected proof.'
 if 'sources_match_current' in c:c['sources_match_current']={p:sha((r/p).read_bytes())==h for p,h in c['measurement'].get('source_sha256',{}).items()}
m['checks'].extend(new)
for key in ('candidate','parent','clean'):m[key]=head if key=='candidate' else prev if key=='parent' else True
m['commits']=git('log','--format=%H %P %s',m['base']+'..'+head).decode().splitlines()
m['repair_997']['historical_candidate']=prev
m['repair_997']['reuse_limit']='F1/F2/L1/L2 bytes unchanged. Current retirement projection is separately repaired and tested by1000.'
m['mixed_version_988']['candidate_retire_record_unchanged_from_2989']=False
m['mixed_version_988']['retirement_change']='1000 adds only source-bound accepted continuation reconciliation and transient command evidence; prior resolved alert removal is not replayed.'
# Bind exact current launch sources and every platform entry without launching anything.
shared=['scripts/kaola-acp.py','scripts/kaola-acp-holder.py','scripts/kaola-launchd-broker.py','scripts/kaola-tmux.sh','scripts/kaola-zcode-acp.py','scripts/kaola-quota.py','scripts/kaola-dispatch.py','scripts/kaola-record-contract.py','vendor/claude-code-acp/dist/index.js']
launch={p:sha((r/p).read_bytes()) for p in shared}
platform={p.stem:{s:sha((r/s).read_bytes()) for s in [str(p.relative_to(r)),'scripts/adapters/'+p.stem+'.sh','skills/'+p.stem+'-kaola-project-runner/scripts/runtime-tmux.sh','skills/'+p.stem+'-kaola-project-runner/scripts/kaola-tmux.sh','skills/'+p.stem+'-kaola-project-runner/scripts/kaola-acp.py']} for p in sorted((r/'platforms').glob('*.yaml'))}
original266=[info('/tmp/kpr-i266-entry/'+n) for n in ('launch-broker-test.json','launch-broker-composed.json','launch-broker-custody-probes.json','launch-broker-custody-composed.json')]
sourcepaths=['/tmp/kpr-i259-1000-owner-final-duties.txt','/tmp/kpr-i259-1000-current-retirement-gap.txt','/tmp/kpr-1000-host-review.md','/tmp/kpr-1000-retirement-gap-refusal.json','/tmp/kpr-1000-compact-gap-retire.json','/tmp/kpr-1000-sweep-list.json','/tmp/kpr-1000-retirement-correlation/sources.json','/tmp/kpr-i259-1000-retirement-proof.py','/tmp/kpr-i259-1000-source-check.py','/tmp/kpr-i259-continuation-run.py','/tmp/kpr-i266-grok-bot-entry-delivery-20261006.md','/tmp/kpr-i266-963-host-review.md','/tmp/kpr-i266-963-source-verification.json','/tmp/kpr-i262-host-closeout-verification.json']
for i in range(15):sourcepaths.extend(['/tmp/kpr-1000-retirement-correlation/'+str(i)+s+'.json' for s in ('','-collect')])
refs=[info(p) for p in sourcepaths]+original266
for x in refs:
 if x not in m['reference_bindings']:m['reference_bindings'].append(x)
continuation={'previous_candidate':prev,'owner_scope':info('/tmp/kpr-i259-1000-owner-final-duties.txt'),'retirement_scope':info('/tmp/kpr-i259-1000-current-retirement-gap.txt'),'host_disposition':info('/tmp/kpr-1000-host-review.md'),'product_functions_changed':['open_dispatch','retire_record'],'launch_source_sha256':launch,'platform_launch_source_sha256':platform,'original266_receipts':original266,'native_default_smoke':'UNVERIFIED per applicable platform/backend; Host allocates, executes and judges missing scope','original_correlation_sources':info('/tmp/kpr-1000-retirement-correlation/sources.json'),'actual_source_proof':'Read-only open_dispatch with original Host accepted task,0-collect and list198; Rust/ZCode initial refs reconcile without index mutation. Atomic tool removal is fixture-proven, not live-applied by this writer.','limits':['i264-compact-behavior holder-mismatch/unknown mutation does not qualify; exact original custody/reclaim or current duty reconciliation remains Host-owned','No missing/foreign/in-flight/unknown-effect bypass','Missing original refs require copied original receipts, not recreated index history','Host owns current cleanup;260 owner-approved keep-open; original259/263/264/265/266 integration and lifecycle remain current','Matching reader before migration; outer mapping stays outer-owned; no install'],'receipt_label_correction':'continuation-retirement-reconcile literal execution_worktree says clean469, but it ran with precommit retirement edits. Captured hashes prove those bytes. It is intermediate proof and is replaced by continuation-retirement-final. No receipt was rewritten.','render_limit':'Attempted lifecycle-state guidance addition made8633B >8192B. Both write/check refused the budget. Addition was removed; only existing docs/dispatch-collect.md was changed. The final renderer write/check pass; budget unchanged.','no_live_state_write':True,'no_index_write':True,'no_install':True,'no_ledger_write':True,'final_acceptance':'Fresh affected Opus Extra High and THIS outer personal integrated verdict pending before original lifecycle/authorized unused PATCH.'}
m['continuation_1000']=continuation
current259=methods((r/'tests/contract/test-issue-259-record-contract.py').read_bytes());old259=methods(blob(m['refinement_base'],'tests/contract/test-issue-259-record-contract.py'))
m['changed_tests']['tests/contract/test-issue-259-record-contract.py']={'changed_or_added':{k.split('.')[-1]:v for k,v in current259.items() if old259.get(k)!=v},'removed_or_renamed':sorted(k.split('.')[-1] for k in old259 if k not in current259),'helper_only_change':old259==current259}
u=m['unrun_cases_this_return']['test-issue-259-record-contract.py']
for case in ['RecordContract.test_retire_mirrors_original_verdict_without_hiding_open_dispatch','RecordContract.test_settled_task_and_retirement_leave_the_routine_view']:
 if case in u['not_executed_this_return']:u['not_executed_this_return'].remove(case)
 if case not in u['executed_this_return']:u['executed_this_return'].append(case)
u['reason']+=' The two existing task-retirement cases also ran in1000, including the extended source-bound continuation and refusal assertions. Remaining cases are unrun; no full259 suite.'
# Keep six owner answers in their existing file and report body.
s=sp.read_text().replace(prev,head,1)
s=s.replace('Useful VRPAI/VRPCAD progress and reduced bookkeeping still require outer integrated judgment; correct fixture JSON is insufficient.', 'The1000 original Rust/ZCode copied receipts and accepted Host verdict pass the read-only retirement check. The extended existing case proves atomic task removal and all role views while the unknown index bytes remain equal. It refuses missing, foreign, live and unknown effects. Host owns actual cleanup of settled design/research and closed262; remaining integration/closeout stays on259/263/264/265/266, with owner-approved260 keep-open. The already-resolved maintenance warning is not replayed. Useful VRPAI/VRPCAD progress and reduced bookkeeping still require outer integrated judgment; correct fixture JSON is insufficient.')
s=s.replace('No universal recovery PASS is claimed.', 'Changed-default native ACP smoke per applicable platform/backend remains UNVERIFIED. Original266 launchd receipts use mock agents; earlier direct native proof does not cover auto. Host owns missing authorized smoke. The collected i264-compact-behavior holder-mismatch and unknown mutation still refuse the new narrow retirement route. No universal recovery PASS is claimed.')
s=s.replace('Broader Rust, Swift and Workflow research stays in its original scope.', 'The1000 current-only gap is repaired in the existing retirement operation and one extended case; no broad replay or audit. Final two-case proof takes1.515565s, the original-source read-only proof0.079254s and render/source checks0.359102s. Continuous improvement remains ordinary planning, review and QA; useful Worker research remains optional within authorization. Completed research stays in original evidence rather than routine state.')
s=s.replace('Candidate retirement and current selector functions and node guidance are unchanged from2989 and already describe no tombstones.', 'Current selector and node guidance remain unchanged from2989 and describe no tombstones. Candidate retirement adds the bounded1000 reconciliation of accepted continuations; the extended existing case and original-source read-only proof cover this change.')
s=s.replace('Pending owner mapping, final affected Opus/outer judgment and all-runtime installed adoption remain explicit limits.', 'Candidate tool adoption does not establish global installation. Outer-owned Delegator mapping waits for the safe accepted tool and remains with the outer; this writer did not write it. Pending owner mapping, fresh affected Opus/THIS outer personal judgment and all-runtime installed adoption remain explicit limits. Owner1000 duties are sourced in the existing delivery and manifest; the six project outcomes and this run-only outer appointment remain unchanged.')
sp.write_text(s);body='1. '+s.split('\n\n1. ',1)[1]
t=dp.read_text().replace(prev,head,1).replace('Parent: `5079042e12e17182897866a589e6b3a5d2248383`.','Parent: `'+prev+'`.',1)
t=t.replace('The changed Host projection needs affected review.', 'The changed Host projection and the minimal1000 retirement repair need affected review.')
t=t.replace('Production/generated source, all six project items and the scoped Delegator appointment are unchanged fromb7f5.', 'At the991 test-only return, production/generated source, all six project items and the scoped Delegator appointment were unchanged fromb7f5. The later997/1000 source repairs are bound separately.')
t=t.replace('Candidate retire_record and host_changes function bodies and node guidance match2989.', 'The candidate host_changes function body and node guidance match2989. The1000 retirement repair changes open_dispatch and retire_record; their former whole-function identity claim no longer applies.')
t=t.replace('Host owns retirement of this specific false warning.', 'The original Host985 receipt already proves retirement of this specific false warning. It has no current replay duty.')
t=t.replace('Only host_view changed in product source.', 'In the997 repair, only host_view changed in product source. The1000 retirement functions are bound separately below.')
t=t.replace('Original10 helper and7 composed checks plus the original native outside launch/preserve-worker evidence retain their measured scope.', 'Original10 helper and7 composed checks and the original OS-manager launch/preserve-worker receipts retain their measured scope with mock ACP agents. They do not prove native platform auto launch.')
t=t.replace('The new structure and validate-route checks do not replace native266 proof.', 'The structure and validate-route checks do not replace required native default-path smoke.')
t=t.replace('Required platform ACP start/observe/send/capture/stop release checks, pins, and Seats disposition remain pending at their binding boundary.', 'Required changed-default per-platform live ACP start/observe/send/capture/stop remains pending for final acceptance. Pins and Seats disposition also remain pending at their original boundary.')
start=t.index('The diff from 2989 has');end=t.index('\n\nAll path names',start)
c=m['refinement_counts'];rc=m['repair_counts'];last=m['last_commit_files']
t=t[:start]+f"The diff from2989 has{len(m['refinement_files'])} paths:{c['authored']} authored and{c['generated']} generated. The repair diff from03e0 has{len(m['repair_files'])} paths:{rc['authored']} authored and{rc['generated']} generated. This continuation commit changes{len(last)} paths:3 authored and11 generated. The full assignment diff has{len(m['files'])} paths:{m['authored_count']} authored and{m['generated_count']} generated. These are source path counts, not QA inventory counts."+t[end:]
start=t.index('patch: `');end=t.index('\n\nOriginal2989 delivery',start)
t=t[:start]+'\n\n'.join(f"{k}: `{m[k]['path']}`, SHA256 `{m[k]['sha256']}`, {m[k]['bytes']} bytes." for k in ('patch','authored_patch','refinement_patch'))+t[end:]
t=t.replace('The scope03e0 and 5079 delivery artifacts are also preserved.', 'The scope03e0,5079 and469 delivery artifacts are also preserved, including their patches, manifests and bindings.')
launch_section='''## Owner1000 delivery duties and changed-default smoke

Scope source: /tmp/kpr-i259-1000-owner-final-duties.txt and /tmp/kpr-1000-host-review.md. This continues the same original259 source assignment. Required live ACP smoke on the changed default launch path remains **UNVERIFIED** for each applicable platform/backend. Direct/mock receipts do not prove auto native launch. Host reconciles original266 evidence and owns allocation, start, observe, send, capture and exact stop for missing authorized scope. No worker was launched or controlled by this writer. Freeze of this candidate lets the Host test those unchanged launch bytes.

| Platform | Reusable original launch evidence | Native changed-default smoke |
| --- | --- | --- |
| codex | launch-broker-test.json:35 checks, codex label with mock ACP agent, actual macOS launchd mechanics | UNVERIFIED |
| claude-code | launch-broker-composed.json:22 checks, fake-claude Host/Worker, auto request, actual launchd/reparenting and preserve-worker stop | UNVERIFIED |
| opencode | custody-composed: explicit-selection refusal with mock input; no successful native launch | UNVERIFIED |
| cursor-cli | No original266 native default-path receipt established by this return | UNVERIFIED |
| devin | No original266 native default-path receipt established by this return | UNVERIFIED |
| droid | No original266 native default-path receipt established by this return | UNVERIFIED |
| dsh | Original finite native/direct compact proof retains its older boundary | UNVERIFIED |
| grok | No original266 native default-path receipt established by this return | UNVERIFIED |
| kimi-cli | No original266 native default-path receipt established by this return | UNVERIFIED |
| zcode | No original266 native default-path receipt established by this return | UNVERIFIED |

All four original receipts are under /tmp/kpr-i266-entry/. The custody-probes receipt has10 injected refusal/custody checks; custody-composed has7 child-record/refusal checks. Their exact hashes and source limits are in continuation_1000.original266_receipts. Host963 accepted source only at its measured boundary. The composed export root does not establish a full current-source hash at execution; unchanged-boundary reuse stays qualified. Linux systemd-user and other OS remain unverified. Auto requests select launchd on macOS; Linux can select systemd-user when available. Unsupported auto can truthfully degrade to direct. A recorded auto request alone is not the applied backend proof.

Exact launcher source hashes at this candidate:

| Source | SHA256 |
| --- | --- |
'''
for p,h in launch.items():launch_section+=f'| {p} | `{h}` |\n'
launch_section+='''
The manifest binds each of the ten platform manifests, adapters and generated runtime entry/launcher files under continuation_1000.platform_launch_source_sha256. These are candidate bytes, not installation proof. The launch sources equal469; only dispatch retirement changed.

Minimal Host-owned invocation shape, prepared only:

```bash
R="$CANDIDATE/skills/$PLATFORM-kaola-project-runner/scripts/runtime-tmux.sh"
"$R" start --repo "$PROJECT" --session "$SESSION" "${AUTHORIZED_START_ARGS[@]}"
"$R" observe --repo "$PROJECT" --session "$SESSION"
"$R" send --repo "$PROJECT" --session "$SESSION" --text "$TOKEN" --wait
"$R" capture --repo "$PROJECT" --session "$SESSION" --full
"$R" stop --repo "$PROJECT" --session "$SESSION" --expected-holder-instance-id "$HOLDER"
```

PROJECT is the Host-bound canonical root; SESSION is an exact allocated owned identity. Authorized selection/binary arguments come from existing grants and platform facts. To test the default, the Host omits --launch-backend and clears only an inherited KAOLA_LAUNCH_BACKEND in its controlled smoke environment. No mock KAOLA_ACP_COMMAND replaces the native runtime. The holder id comes from the original start receipt. Capture literal argv, full output, elapsed time, OS/CLI/adapter versions, candidate and entry hashes, applied selection, actual launch.backend/manager identity and any launch_backend_degraded flag. Preserve separate Runner session, holder, ACP id and native resume id. Verify the unique token reply and exact-stop residual/process facts. An incomplete, foreign or unknown effect needs source reconciliation before retry. This prepared shape creates no authority and was not run here.

Tool adoption is not global installation. Keep the matching reader BEFORE grouped-state migration. Host970/971 source-tool adoption and the measured old installed-node recipe remain scoped original evidence. The warning resolved by985 stays resolved. Outer-owned Delegator mapping waits for the safe accepted tool and remains outer-owned. This source writer did not install, write the outer record or replay maintenance.

'''
retire_section='''## Owner1000 current-only retirement repair and proof

Scope source: /tmp/kpr-i259-1000-current-retirement-gap.txt. Original source mapping is /tmp/kpr-1000-retirement-correlation/sources.json. The fifteen copied receipts and collect outputs remain unchanged and hash-bound. They show that the initial admission can differ from a completed same-assignment continuation. That difference alone does not reopen accepted research/design or closed262. The current index remains a correlation index, not a history ledger. No original collect result was promoted to accepted.

The minimal repair changes only open_dispatch and the transient retire command result. Existing Host task verdict, per-item dispositions, original copied dispatch evidence and exact reclaim establish the bounded path. The task must be done/accepted, with an explicit accepted disposition for each affected item. The row must link that task, root, platform, session and holder, be unknown/fingerprint-differs, and have a completed/stopped collect result under that same holder/root. Fresh live rows must prove the exact holder stopped. All other task seats still need normal stop proof. Missing, foreign, live, in-flight, unrelated unknown or unknown mutation refuses. The command emits reconciled_dispatch while the original unknown row remains byte-equal. No stored field, authority, history, tombstone or engine was added.

The original QA task and /tmp/kpr-1000-retirement-correlation/0-collect.json with /tmp/kpr-1000-sweep-list.json pass the read-only open_dispatch check for Rust and ZCode. Their Host verdict and per-item dispositions already existed in the original refusal receipt. This proof writes neither state nor index. The extended existing retirement case proves atomic removal from current storage/all three role views, unchanged unknown index bytes, and twelve meaningful refusal shapes. It preserves the original returned-index mirror assertions. The existing settled-task checkpoint case also passes. Full live retirement is still Host-owned.

Prepared supported operation for that original QA row, after Host reads its current revision and preserves original result/custody evidence:

```bash
python3 "$CANDIDATE/scripts/kaola-dispatch.py" state retire \
  --file "$PROJECT/.kaola/heartbeat-prompt.json" --writer host \
  --source "$ORIGINAL_HOST_RESULT_AND_CUSTODY" --kind tasks \
  --id qa-efficiency-research --expect-rev "$CURRENT_TASK_REV" \
  --evidence "$ORIGINAL_RESULT_AND_EXACT_RECLAIM" --cite "$RETRIEVABLE_CITE_JSON" \
  --index /tmp/kpr-1000-retirement-correlation/0-collect.json \
  --live "$FRESH_RUNNER_LIST_RECEIPT"
```

Use the original accepted disposition; do not strip refs. If a disposition is absent, the Host first records its source-based result judgment through existing state update, with CAS and without --index. A copied original index supplies only the relevant refs; no live index reconstruction or historical replay is needed. The Host must use a fresh exact list for the actual write. The original list198 is a measured snapshot, not future live availability.

Precise limit: i264-compact-behavior in7-collect.json is holder-mismatch, with unknown mutation and a different holder. It does not qualify. The Host must reconcile original custody and reclaim against the remaining current lifecycle duty; this writer does not accept that row or infer missing effects. A truly unresolved duty remains current. compact-gap-followup already used the normal route: /tmp/kpr-1000-compact-gap-retire.json proves revision999→1000 and current-row removal with original returned/stopped links. This operation is not replayed. Settled design/research and closed262 narratives leave routine state when their original result/custody and concrete closure duties are accounted. Preserve actual active integration/closeout on259/263/264/265/266 and the explicit owner-approved260 keep-open scope. No lifecycle was closed here.

Affected commands and results (same worktree; Bash5.3; existing90-second watchdog; direct isolated fixtures):

| Receipt | Scope | Seconds | Exit |
| --- | --- | --- | --- |
'''
for x in new:
 d=x['measurement'];retire_section+=f"| {d['name']} | {x['reuse_at_current_candidate']} | {d['seconds']:.6f} | {d['exit']} |\n"
retire_section+='\nLiteral final commands:\n\n```text\n'
for x in new[-3:]:retire_section+=json.dumps(x['measurement']['argv'])+'\n'
retire_section+='''```

The receipts preserve literal wrapped argv, output/log hashes, elapsed time, execution base and product/test source bindings. Tests ran before commit. The final captured bytes match this clean candidate. The intermediate retirement-reconcile receipt mistakenly says clean469 in its literal context label; its source hashes show precommit edits. That label is corrected here, and the final receipt supersedes it. No original receipt was rewritten. One attempted guidance addition exceeded lifecycle-state's8192B budget at8633B; renderer write/check refused. The addition was removed. Existing docs/dispatch-collect.md contains the minimal guidance. Final write/check and budgets pass; no budget was raised or generated file hand-edited.

No full259,244,Droid,266 or inventory rerun was needed for this narrow retirement change. Prior F1/F2/L1/L2 test methods and launch boundaries are unchanged. Retain their valid PASS at the stated scope. The two affected retirement cases replace current task-retirement proof. Earlier whole-function retirement identity statements are withdrawn; prior alert/maintenance original outcomes remain source-bound evidence, not a replay requirement. Exact unrun case names and reasons stay in unrun_cases_this_return. No native run, live state/index mutation or installation occurred.

'''
t=t.replace('## Current six owner answers',launch_section+retire_section+'## Current six owner answers',1)
start=t.index('## Current six owner answers');end=t.index('## Acceptance frontier',start)
t=t[:start]+'## Current six owner answers\n\n'+body.strip()+'\n\n'+t[end:]
t=t.replace('Review993 → Host997 → this same source assignment → F1/F2/L1/L2 repairs → focused checks → this report is the current return path.', 'Review993 → Host997 → F1/F2/L1/L2 → Host1000/owner duties → bounded current-only retirement repair → affected proof → these corrected six answers is the same return path.')
t=t.replace('Pending: fresh affected Claude Code Opus Extra High review at the exact candidate;', 'Pending: required changed-default live ACP smoke for each applicable platform/backend, owned by Host; fresh affected Claude Code Opus Extra High conclusion at the exact candidate;')
t=t.replace("this run's outer personal integrated judgment;", "THIS run's outer personal final verdict before original lifecycle and authorized unused PATCH;")
dp.write_text(t)
m['current_six_answers']={**info(sp),'body_sha256':sha(body.encode())}
mp.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
b.update(candidate=head,parent=prev,clean=True,delivery=info(dp),six_answers=m['current_six_answers'],manifest=info(mp),mixed_version_988=m['mixed_version_988'],continuation_1000=continuation,pending='Required per-platform/backend changed-default live ACP smoke; fresh affected Opus Extra High conclusion and THIS outer personal verdict; Host current-only cleanup and original259/263/264/265/266 lifecycle before authorized unused PATCH;260 keep-open; reader-first/outer mapping/install/native limits.')
for k in ('patch','authored_patch','refinement_patch'):b[k]=m[k]
b['native_proof']='No native launch/control by this writer. Original266 OS-manager receipts use mock agents, not native auto smoke. Original925/926/929 direct/finite native boundaries retain their limits; required changed-default live smoke remains UNVERIFIED.'
b['changed_path_count']=len(m['files']);b['refinement_path_count']=len(m['refinement_files']);b['repair_path_count']=len(m['repair_files'])
b['checks'] += [{'receipt':x['receipt'],'sha256':x['receipt_sha256'],'exit':x['measurement']['exit'],'seconds':x['measurement']['seconds'],'reuse_limit':x['reuse_at_current_candidate']} for x in new]
b['repair_997']=m['repair_997']
bp.write_text(json.dumps(b,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'candidate':head,'delivery':info(dp),'six_answers':info(sp),'binding':info(bp),'paths':len(m['files']),'state_write':False},indent=2))
