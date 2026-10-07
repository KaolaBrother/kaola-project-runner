import argparse,hashlib,importlib.util,json
from pathlib import Path
root=Path('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259')
main=root.parents[2]
paths=[Path('/tmp/kpr-1000-retirement-gap-refusal.json'),Path('/tmp/kpr-1000-retirement-correlation/0-collect.json'),Path('/tmp/kpr-1000-sweep-list.json')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p):sha(p) for p in paths}
spec=importlib.util.spec_from_file_location('dispatch_retirement_proof',root/'scripts/kaola-dispatch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
args=argparse.Namespace(writer='host',id='qa-efficiency-research',file=str(main/'.kaola/heartbeat-prompt.json'),index=str(paths[1]),live=str(paths[2]))
task=json.loads(paths[0].read_text())['current']
problems=m.open_dispatch(task,args)
assert problems==[],problems
assert {r['item_id'] for r in args._reconciled_dispatch}=={'i259-test-rust-selection','i259-test-qa-boundaries'}
assert {str(p):sha(p) for p in paths}==before
print(json.dumps({'result':'PASS','operation':'open_dispatch read-only; not state retire','task_id':args.id,'source_sha256':before,'reconciled_dispatch':args._reconciled_dispatch,'state_write':False,'index_write':False,'limit':'Full atomic retirement is fixture-proven; Host owns live operation and current revision/cite/evidence. No other task or original unknown is accepted by this proof.'},indent=2))
