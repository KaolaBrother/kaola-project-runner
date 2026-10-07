import ast,hashlib,json,subprocess
from pathlib import Path
r=Path('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259');main=r.parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
def info(p):p=Path(p);return {'path':str(p),'sha256':sha(p.read_bytes())}
mp=Path('/tmp/kpr-i259-host-compact-implementation-hashes-20261006.json');bp=Path('/tmp/kpr-i259-host-compact-implementation-delivery-binding-20261006.json');dp=Path('/tmp/kpr-i259-host-compact-implementation-delivery-20261006.md');sp=Path('/tmp/kpr-i259-six-requirement-answers-20261006.md')
m=json.loads(mp.read_text());b=json.loads(bp.read_text())
t=dp.read_text().replace('The launch sources equal469; only dispatch retirement changed.', 'The transport launcher, holder and broker bytes equal469. The dispatch hash is current and includes the retirement repair.')
t=t.replace('A copied original index supplies only the relevant refs; no live index reconstruction or historical replay is needed.', 'A copied original index supplies only the relevant refs; no live index reconstruction or historical replay is needed. After retirement, use the current index for routine checks. The historical copy keeps its unknown correlation as original evidence; do not copy it into the current index. This route does not clear an unknown row already in the current index or settle its effects.')
old='python3 "$CANDIDATE/scripts/kaola-dispatch.py" state retire   --file "$PROJECT/.kaola/heartbeat-prompt.json" --writer host   --source "$ORIGINAL_HOST_RESULT_AND_CUSTODY" --kind tasks   --id qa-efficiency-research --expect-rev "$CURRENT_TASK_REV"   --evidence "$ORIGINAL_RESULT_AND_EXACT_RECLAIM" --cite "$RETRIEVABLE_CITE_JSON"   --index /tmp/kpr-1000-retirement-correlation/0-collect.json   --live "$FRESH_RUNNER_LIST_RECEIPT"'
args=['python3 "$CANDIDATE/scripts/kaola-dispatch.py" state retire','  --file "$PROJECT/.kaola/heartbeat-prompt.json" --writer host','  --source "$ORIGINAL_HOST_RESULT_AND_CUSTODY" --kind tasks','  --id qa-efficiency-research --expect-rev "$CURRENT_TASK_REV"','  --evidence "$ORIGINAL_RESULT_AND_EXACT_RECLAIM" --cite "$RETRIEVABLE_CITE_JSON"','  --index /tmp/kpr-1000-retirement-correlation/0-collect.json','  --live "$FRESH_RUNNER_LIST_RECEIPT"']
if old in t:t=t.replace(old,(' '+chr(92)+'\n').join(args))
dp.write_text(t)
# Bind source originals behind the supplied copied correlation mapping.
for p in json.loads(Path('/tmp/kpr-1000-retirement-correlation/sources.json').read_text()).values():
 row=info(p)
 if row not in m['reference_bindings']:m['reference_bindings'].append(row)
for p in ('/tmp/kpr-i259-1000-update-delivery.py','/tmp/kpr-i259-1000-final-bindings.py'):
 row=info(p)
 if row not in m['reference_bindings']:m['reference_bindings'].append(row)
m['continuation_1000']['current_index_limit']='Historical copied correlation is retained as evidence, not current state. Retirement does not clear an unknown row already in the current index or settle its effects.'
# Source/function and affected-case hashes bind precommit evidence to the clean commit.
functions={n.name:sha(ast.dump(n,include_attributes=False).encode()) for n in ast.parse((r/'scripts/kaola-dispatch.py').read_bytes()).body if isinstance(n,ast.FunctionDef)}
functions['host_changes']=next(sha(ast.dump(n,include_attributes=False).encode()) for n in ast.parse((r/'scripts/kaola-record-contract.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='host_changes')
m['continuation_1000']['binding_verification_correction']='First binding script lookup incorrectly searched the dispatch module for host_changes, which is an alias of RECORD.host_changes. It stopped before manifest/binding write. The corrected lookup reads the unchanged contract source. Product/test evidence was not affected.'
m['continuation_1000']['candidate_function_sha256']={k:functions[k] for k in ('open_dispatch','retire_record','mirror_task','open_seats','host_changes','host_view')}
methods={}
for n in ast.parse((r/'tests/contract/test-issue-259-record-contract.py').read_bytes()).body:
 if isinstance(n,ast.ClassDef):
  for x in n.body:
   if isinstance(x,ast.FunctionDef):methods[n.name+'.'+x.name]=sha(ast.dump(x,include_attributes=False).encode())
m['continuation_1000']['affected_case_sha256']={k:methods[k] for k in ('RecordContract.test_retire_mirrors_original_verdict_without_hiding_open_dispatch','RecordContract.test_settled_task_and_retirement_leave_the_routine_view')}
mp.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
b['delivery']=info(dp);b['manifest']=info(mp);b['continuation_1000']=m['continuation_1000'];bp.write_text(json.dumps(b,indent=2,ensure_ascii=False)+'\n')
for key in ('delivery','manifest','six_answers','patch','authored_patch','refinement_patch'):
 assert sha(Path(b[key]['path']).read_bytes())==b[key]['sha256'],key
body='1. '+sp.read_text().split('\n\n1. ',1)[1]
reported=dp.read_text().split('## Current six owner answers\n\n',1)[1].split('\n\n## Acceptance frontier',1)[0]
assert body.strip()==reported.strip();assert sha(body.encode())==b['six_answers']['body_sha256']
for name in ('files','refinement_files','repair_files','last_commit_files'):
 for row in m[name]:
  assert sha((r/row['path']).read_bytes())==row['candidate_sha256'],row['path']
  assert sha(subprocess.check_output(['git','show',m['candidate']+':'+row['path']],cwd=r))==row['candidate_sha256'],row['path']
for row in m['preserved_original_artifacts']+m['reference_bindings']:
 assert sha(Path(row['path']).read_bytes())==row['sha256'],row['path']
for row in m['checks']:
 assert sha(Path(row['receipt']).read_bytes())==row['receipt_sha256'],row['receipt']
 d=row['measurement'];p=d.get('log') or d.get('output')
 if p and d.get('output_sha256'):assert sha(Path(p).read_bytes())==d['output_sha256'],p
for p,h in m['continuation_1000']['launch_source_sha256'].items():assert sha((r/p).read_bytes())==h
for vals in m['continuation_1000']['platform_launch_source_sha256'].values():
 for p,h in vals.items():assert sha((r/p).read_bytes())==h
for row in m['checks'][-3:]:
 assert all(row['sources_match_current'].values()),row['receipt']
for p,field in [('kaola-workflow/issue-259/workflow-state.md','state_sha256'),('kaola-workflow/.ledger/issue-259.jsonl','ledger_sha256')]:assert sha((main/p).read_bytes())==m['claim'][field]
assert [json.loads(x)['status'] for x in (main/'kaola-workflow/.ledger/issue-259.jsonl').read_text().splitlines()]==['done']*4
assert not subprocess.check_output(['git','status','--porcelain'],cwd=r)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip()==m['candidate']
print(json.dumps({'result':'PASS','candidate':m['candidate'],'clean':True,'committed_paths':len(m['files']),'receipts':len(m['checks']),'original_claim_ledger_unchanged':True,'six_answers_equal_delivery':True,'delivery':info(dp),'six_answers':info(sp),'manifest':info(mp),'binding':info(bp),'no_live_state_index_write':True},indent=2))
