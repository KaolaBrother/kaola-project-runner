#!/usr/bin/env python3
"""One shadow Codex ACP session, one requested /compact, with raw ACP receipts."""
import datetime, json, os, queue, subprocess, sys, threading, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
SHADOW=Path((HERE/'shadow-path.txt').read_text().strip())
ADAPTER=Path('/Users/ylmacstudio/.npm/_npx/dbf52506fe4ebb57/node_modules/.bin/codex-acp')
ROOT=Path('/Users/ylmacstudio/Workspace/kaola-project-runner')
ENV=os.environ.copy()
ENV.update(HOME=str(SHADOW), CODEX_HOME=str(SHADOW/'.codex'), CODEX_PATH=str(SHADOW/'codex-trusted'), NO_BROWSER='1')
q=queue.Queue()
proc=subprocess.Popen([str(ADAPTER)],cwd=str(ROOT),env=ENV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
log=(HERE/'acp-transcript.jsonl').open('w',encoding='utf8')
err=(HERE/'adapter-stderr.log').open('w',encoding='utf8')
def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def record(direction,message):
    log.write(json.dumps({'ts_utc':stamp(),'direction':direction,'message':message},ensure_ascii=False)+'\n');log.flush()
def readout():
    for line in proc.stdout:
        try: message=json.loads(line)
        except ValueError: message={'unparsed':line.rstrip()}
        record('in',message);q.put(message)
    q.put({'closed':True})
def readerr():
    for line in proc.stderr: err.write(line);err.flush()
threading.Thread(target=readout,daemon=True).start()
threading.Thread(target=readerr,daemon=True).start()
def send(method,params,id):
    msg={'jsonrpc':'2.0','id':id,'method':method,'params':params}
    record('out',msg);proc.stdin.write(json.dumps(msg)+'\n');proc.stdin.flush()
def wait(id,timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try: msg=q.get(timeout=min(2,deadline-time.monotonic()))
        except queue.Empty: continue
        if msg.get('id')==id:return msg
        if 'method' in msg and 'id' in msg:
            response={'jsonrpc':'2.0','id':msg['id'],'error':{'code':-32601,'message':'measurement client does not support this request'}}
            record('out',response);proc.stdin.write(json.dumps(response)+'\n');proc.stdin.flush()
        if msg.get('closed'):raise RuntimeError('adapter stdout closed')
    raise TimeoutError(f'ACP response {id} after {timeout}s')
summary={'started_utc':stamp(),'pid':proc.pid,'adapter':str(ADAPTER),'codex_path':ENV['CODEX_PATH'],'shadow':str(SHADOW)}
try:
    send('initialize',{'protocolVersion':1,'clientCapabilities':{'fs':{'readTextFile':False,'writeTextFile':False},'terminal':False}},1)
    init=wait(1,120);summary['initialize']=init
    if 'error' in init:raise RuntimeError('initialize error')
    send('session/new',{'cwd':str(ROOT),'mcpServers':[]},2)
    new=wait(2,120);summary['session_new']=new
    if 'error' in new:raise RuntimeError('session/new error')
    sid=new['result']['sessionId'];summary['session_id']=sid
    send('session/prompt',{'sessionId':sid,'prompt':[{'type':'text','text':'$kaola-project-runner\nThis is a temporary ACP Host hook measurement for issue #149. Read the installed Project Runner skill as the entry requires, then reply READY. Do not start or contact workers, change files, or touch the forge.'}]},3)
    first=wait(3,180);summary['first_prompt']=first
    if 'error' in first:raise RuntimeError('first prompt error')
    send('session/prompt',{'sessionId':sid,'prompt':[{'type':'text','text':'/compact'}]},4)
    compact=wait(4,240);summary['compact_prompt']=compact
    if 'error' in compact:raise RuntimeError('compact prompt error')
    summary['result']='compact_response_received'
except Exception as exc:
    summary['result']='error';summary['error']=repr(exc)
finally:
    summary['ended_utc']=stamp()
    (HERE/'acp-summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    try:proc.stdin.close()
    except Exception:pass
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    summary['adapter_exit']=proc.returncode
    (HERE/'acp-summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    log.close();err.close()
print(json.dumps({k:summary.get(k) for k in ('result','error','session_id','adapter_exit')},ensure_ascii=False))
sys.exit(0 if summary.get('result')=='compact_response_received' else 1)
