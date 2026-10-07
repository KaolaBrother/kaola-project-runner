import hashlib, json, os, subprocess, sys, time
from pathlib import Path
root=Path('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259')
name=sys.argv[1]; argv=sys.argv[2:]
log=Path('/tmp/kpr-i259-997-'+name+'.log'); receipt=log.with_suffix('.json')
assert not log.exists() and not receipt.exists(), name
sha=lambda b:hashlib.sha256(b).hexdigest()
sources=sorted(set(['scripts/kaola-dispatch.py','scripts/kaola-record-contract.py','scripts/kaola-acp.py','scripts/kaola-acp-holder.py','scripts/kaola-launchd-broker.py','scripts/validate.sh','scripts/validate-watchdog.sh']+[p for p in argv if p.endswith('.py') and (root/p).is_file()]+[str(p.relative_to(root)) for p in (root/'platforms').glob('*.yaml')]))
hashes={p:sha((root/p).read_bytes()) for p in sources}
env={k:v for k,v in os.environ.items() if not k.startswith('KAOLA_')};env.update(TMPDIR='/tmp',KAOLA_LAUNCH_BACKEND='direct',PATH='/Users/ylmacstudio/.local/share/bash-5.3.20/bin:'+env.get('PATH',''))
wrapped=argv if './scripts/validate.sh' in argv else ['/Users/ylmacstudio/.local/share/bash-5.3.20/bin/bash',str(root/'scripts/validate-watchdog.sh'),'--label','i259-997-'+name,'--budget','90','--receipt-dir','/tmp/kpr-i259-997-watchdog','--',*argv]
t0=time.monotonic()
with log.open('w') as out:
 proc=subprocess.run(wrapped,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT)
seconds=time.monotonic()-t0
assert all(sha((root/p).read_bytes())==h for p,h in hashes.items())
d={'name':'997-'+name,'argv':argv,'wrapped_argv':wrapped,'cwd':str(root),'env':{'TMPDIR':'/tmp','KAOLA_LAUNCH_BACKEND':'direct','KAOLA_inherited':'scrubbed','PATH_prefix':'/Users/ylmacstudio/.local/share/bash-5.3.20/bin'},'execution_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'execution_worktree':'scoped F1/F2/L1/L2 repairs before commit','exit':proc.returncode,'seconds':seconds,'log':str(log),'output_sha256':sha(log.read_bytes()),'source_sha256':hashes}
receipt.write_text(json.dumps(d,indent=2)+'\n')
print(log.read_text());print(json.dumps({'receipt':str(receipt),'exit':proc.returncode,'seconds':seconds}))
sys.exit(proc.returncode)
