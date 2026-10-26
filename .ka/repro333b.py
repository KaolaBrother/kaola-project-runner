import json,os,subprocess,sys,tempfile
from pathlib import Path
REPO=Path('/Users/ylpromax5/Workspace/kaola-project-runner-dev');D=REPO/'scripts/kaola-dispatch.py'
env={k:v for k,v in os.environ.items() if not k.startswith('KAOLA_ACP_')}
sys.path.insert(0,str(REPO/'tests/contract'))
import importlib.util
spec=importlib.util.spec_from_file_location('t255',REPO/'tests/contract/test-issue-255-lifecycle-state.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

def case(status,extra):
  tmp=Path(tempfile.mkdtemp(prefix='repro333-'));repo=tmp/'consumer';(repo/'.kaola').mkdir(parents=True);(repo/'README.md').write_text('x\n')
  f=repo/'.kaola/heartbeat-prompt.json'
  def st(*a):
    p=subprocess.run([sys.executable,str(D),'state',*a],capture_output=True,text=True,env=env,timeout=60)
    try:o=json.loads(p.stdout)
    except Exception:o={'raw':p.stdout[-300:],'err':p.stderr[-300:]}
    return p.returncode,o
  st('init','--file',str(f),'--writer','host','--source','t1','--project',json.dumps({"code":"KT","goal":"ship"}),'--authorization',json.dumps(t.AUTH))
  st('update','--file',str(f),'--writer','host','--source','e','--kind','tasks','--id','i193','--set',json.dumps({"stage":"done","goal":"g","dispatch":["i193"],"verdict":{"value":"accepted"}}))
  idx=repo/'index.json';live=repo/'live.json'
  live.write_text(json.dumps({"schema":"kaola-acp-list/1","rows":[{"session":"zcode-KGIT-i193","state":"stopped"}]}))
  idx.write_text(json.dumps({"schema":"kaola-dispatch-index/1","repo":str(repo),"items":[dict({"item_id":"i193","status":status,"session":"zcode-KGIT-i193"},**extra)]}))
  c,o=st('retire','--file',str(f),'--writer','sideagent','--source','s','--kind','tasks','--id','i193','--expect-rev','1','--evidence','closed KGIT #193; archive; receipt','--cite',t.CITE,'--index',str(idx),'--live',str(live))
  print(status,extra,'-> exit',c,o.get('reason'),(o.get('detail') or '')[:170])
  import shutil;shutil.rmtree(tmp)
for status,extra in (('returned',{}),('unknown',{'reason':'event-range-unavailable'}),('unknown',{'reason':'fingerprint-differs'}),('unknown',{'reason':'no-last-prompt'})): case(status,extra)
