from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,tempfile,time,unittest
root=Path('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
out=Path('/tmp/kpr-i259-963-disposable-upgrade');out.mkdir(exist_ok=False)
scratch=Path(tempfile.mkdtemp(prefix='kpr-i259-963-copy-'));installed=scratch/'skills';installed.mkdir();trace=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
fixture=module('copy215',root/'tests/contract/test-issue-215-install-truthfulness.py')
for name in ['kaola-project-runner','kaola-delegator','codex-kaola-project-runner','droid-kaola-project-runner']:
 shutil.copytree(root/'skills'/name,installed/name)
 fixture.receipt_file(installed,name,['generic:'+str(installed)],fixture.tree_digest(installed/name))
tool=installed/'kaola-project-runner/scripts/kaola-dispatch.py'
t=module('existing259',root/'tests/contract/test-issue-259-record-contract.py');t.DISPATCH=tool
orig=t.run_dispatch
# Capture each real CLI call, its literal argv, output, and written file bytes.
def call(args,env=None):
 before={a:sha(a) for a in args if isinstance(a,str) and Path(a).is_file()};start=time.monotonic();r=orig(args,env);elapsed=time.monotonic()-start
 row={'argv':[t.PYTHON,str(tool),*args],'exit':r[0],'seconds':round(elapsed,6),'stdout_json':r[1],'before':before,'after':{a:sha(a) for a in before if Path(a).is_file()}}
 if '--file' in args:
  p=Path(args[args.index('--file')+1]);
  if p.is_file():row['stored_json']=json.loads(p.read_text())
 trace.append(row);return r
t.run_dispatch=call
start=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
 t.RecordContract('test_legacy_capacity_and_group_conflicts_stay_actionable_migration_repeats'),
 t.RecordContract('test_delegator_group_pause_expiry_and_resolved_relay_preserve_current_duties')]))
# Existing native timer contract, using copied candidate tool only.
repo=str(scratch/'timer-consumer');entry='/kaola-delegator';body=entry+'\n'+f"Kaola-Delegator inquiry: read {repo}/.kaola/delegator-heartbeat.json on target local and run the loaded Skill's standard inquiry."
for value in [body,None]:
 args=['state','timer','--repo',repo,'--target','local','--entry',entry]
 if value:args+=['--body',value]
 code,payload=call(args);assert code==0 and payload['result']==('match' if value else 'unavailable'),payload
refs=[installed/'kaola-delegator/references/inquiry-report.md',installed/'kaola-project-runner/references/heartbeat-skeleton.md',tool,installed/'kaola-project-runner/scripts/kaola-record-contract.py',installed/'kaola-project-runner/references/worker-profiles.md']
bindings=[{'copied':str(p),'candidate':str(root/'skills'/p.relative_to(installed)),'sha256':sha(p),'equal_candidate':p.read_bytes()==(root/'skills'/p.relative_to(installed)).read_bytes()} for p in refs]
assert all(row['equal_candidate'] for row in bindings)
shutil.rmtree(scratch)
receipt={'candidate':head,'result':'pass' if result.wasSuccessful() else 'fail','calls':len(trace),'seconds':round(time.monotonic()-start,6),'tool_bindings':bindings,'fixture':str(root/'tests/contract/test-issue-259-record-contract.py'),'fixture_sha256':sha(root/'tests/contract/test-issue-259-record-contract.py'),'catalog_source':str(root/'platforms'),'mapping':'existing259 fixture sources; disposable consumer roots and copied tool path only. Canonical source/catalog and grant intent unchanged. Legacy conflicts remain refused; no real Host judgments rewritten.','timer_body_sha256':hashlib.sha256(body.encode()).hexdigest(),'timer_entry_unchanged':True,'cleanup':{'scratch':str(scratch),'exists_after':scratch.exists()},'native_model':False,'live_install_or_consumer_write':False,'trace':trace}
(out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='trace'},ensure_ascii=False,indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
