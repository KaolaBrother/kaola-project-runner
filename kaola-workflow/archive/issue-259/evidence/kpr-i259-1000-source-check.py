import ast,hashlib,json,subprocess
from pathlib import Path
r=Path('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259')
run=lambda *a:subprocess.run(a,cwd=r,check=True,capture_output=True,text=True).stdout
print(run('./scripts/render-skills.py','--check').strip())
run('git','diff','--check')
for p in ('scripts/kaola-dispatch.py','tests/contract/test-issue-259-record-contract.py'): ast.parse((r/p).read_text())
def funcs(b): return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(b).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
old=funcs(run('git','show','469015649b72a6ef846ed608648f1e8f4ebf5d9d:scripts/kaola-dispatch.py'));now=funcs((r/'scripts/kaola-dispatch.py').read_bytes());changed=[k for k in old.keys()|now.keys() if old.get(k)!=now.get(k)]
assert sorted(changed)==['open_dispatch','retire_record'],changed
assert (r/'scripts/kaola-dispatch.py').read_bytes()==(r/'skills/kaola-project-runner/scripts/kaola-dispatch.py').read_bytes()
for p in ('AGENTS.md','templates/budgets.json','scripts/kaola-acp.py','scripts/kaola-acp-holder.py','scripts/kaola-launchd-broker.py','scripts/kaola-record-contract.py','tests/contract/test-issue-244-dispatch.py','tests/contract/test-droid-acp-contract.py','tests/contract/test-issue-266-launch-broker.py','tests/contract/test-issue-266-launch-broker-composed.py'):
 assert (r/p).read_bytes()==subprocess.check_output(['git','show','46901564:'+p],cwd=r),p
print(json.dumps({'result':'PASS','changed_product_functions':sorted(changed),'generated_dispatch_equal':True,'unchanged_boundaries':'469 launch/holder/broker/record schema/244/Droid/266/AGENTS/budgets','live_state_write':False}))
