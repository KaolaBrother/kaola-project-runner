#!/usr/bin/env python3
"""Resume the same native ACP session after compaction; observe deferred hooks."""
import datetime,json,os,queue,subprocess,threading,time
from pathlib import Path
H=Path(__file__).resolve().parent
S=Path((H/'shadow-path.txt').read_text().strip())
sid=json.loads((H/'acp-summary.json').read_text())['session_id']
root='/Users/ylmacstudio/Workspace/kaola-project-runner'
env=os.environ.copy();env.update(HOME=str(S),CODEX_HOME=str(S/'.codex'),CODEX_PATH=str(S/'codex-trusted'),NO_BROWSER='1')
p=subprocess.Popen(['/Users/ylmacstudio/.npm/_npx/dbf52506fe4ebb57/node_modules/.bin/codex-acp'],cwd=root,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
q=queue.Queue(); f=(H/'acp-followup-transcript.jsonl').open('w'); e=(H/'adapter-followup-stderr.log').open('w')
def rec(d,m):f.write(json.dumps({'ts_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'direction':d,'message':m},ensure_ascii=False)+'\n');f.flush()
def reader():
 for line in p.stdout:
  try:m=json.loads(line)
  except ValueError:m={'unparsed':line.rstrip()}
  rec('in',m);q.put(m)
 q.put({'closed':True})
def errors():
 for line in p.stderr:e.write(line);e.flush()
threading.Thread(target=reader,daemon=True).start();threading.Thread(target=errors,daemon=True).start()
def send(i,method,params):
 m={'jsonrpc':'2.0','id':i,'method':method,'params':params};rec('out',m);p.stdin.write(json.dumps(m)+'\n');p.stdin.flush()
def wait(i,timeout):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  try:m=q.get(timeout=min(2,end-time.monotonic()))
  except queue.Empty:continue
  if m.get('id')==i:return m
  if m.get('closed'):raise RuntimeError('closed')
 raise TimeoutError(i)
sum={'session_id':sid,'method':'session/load, no session/new'}
try:
 send(1,'initialize',{'protocolVersion':1,'clientCapabilities':{'fs':{'readTextFile':False,'writeTextFile':False},'terminal':False}});sum['initialize']=wait(1,120)
 send(2,'session/load',{'sessionId':sid,'cwd':root,'mcpServers':[]});sum['load']=wait(2,120)
 send(3,'session/prompt',{'sessionId':sid,'prompt':[{'type':'text','text':'After the completed /compact measurement, reply DONE only. No tools or work.'}]});sum['followup_prompt']=wait(3,180)
 sum['result']='response_received'
except Exception as x:sum['result']='error';sum['error']=repr(x)
finally:
 p.stdin.close()
 try:p.wait(timeout=10)
 except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
 sum['adapter_exit']=p.returncode
 (H/'acp-followup-summary.json').write_text(json.dumps(sum,indent=2)+'\n')
 f.close();e.close()
print(json.dumps({k:sum.get(k) for k in ('result','error','adapter_exit')}))
