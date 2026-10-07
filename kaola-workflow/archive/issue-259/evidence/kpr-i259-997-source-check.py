import ast, hashlib, subprocess
from pathlib import Path
root=Path('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259')
for argv in (['./scripts/render-skills.py','--check'], ['git','diff','--check']):
    print('COMMAND',repr(argv),flush=True)
    subprocess.run(argv,cwd=root,check=True)
for s in subprocess.check_output(['git','diff','--name-only'],cwd=root,text=True).splitlines():
    if s.endswith('.py'):ast.parse((root/s).read_bytes())
a=(root/'scripts/kaola-dispatch.py').read_bytes()
assert a==(root/'skills/kaola-project-runner/scripts/kaola-dispatch.py').read_bytes()
f=lambda b:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(b).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
old=f(subprocess.check_output(['git','show','5079042e:scripts/kaola-dispatch.py'],cwd=root));new=f(a)
assert sorted(k for k in old.keys()|new.keys() if old.get(k)!=new.get(k))==['host_view']
for p in ('scripts/kaola-record-contract.py','scripts/kaola-acp.py','scripts/kaola-acp-holder.py','scripts/kaola-launchd-broker.py','scripts/validate.sh','tests/contract/test-issue-266-launch-broker.py','tests/contract/test-issue-266-launch-broker-composed.py'):
    assert (root/p).read_bytes()==subprocess.check_output(['git','show','5079042e:'+p],cwd=root)
    print('UNCHANGED',p,hashlib.sha256((root/p).read_bytes()).hexdigest())
assert not subprocess.check_output(['git','diff','5079042e','--','AGENTS.md','templates/grok-golden','templates/budgets.json'],cwd=root)
print('PASS syntax, generated dispatch equality, only host_view changed; 266 auto lanes, production filtering and owner requirements unchanged')
