import json,os,subprocess,sys,tempfile
from pathlib import Path
REPO=Path('/Users/ylpromax5/Workspace/kaola-project-runner-dev')
D=REPO/'scripts/kaola-dispatch.py'
env={k:v for k,v in os.environ.items() if not k.startswith('KAOLA_ACP_')}
def run(preset,grant_kind):
    t=tempfile.mkdtemp(prefix='repro332-');repo=Path(t)/'consumer';(repo/'.kaola').mkdir(parents=True)
    auth={"grants":[{"id":preset,"state":"granted","count":1,"lifetime":"standing"}]}
    (repo/'auth.json').write_text(json.dumps(auth))
    az={"elite_grants":[{"count":1,"preset_ids":["claude-code/sonnet","claude-code/fable"],"state":"granted"}],
        "expert_task_grants":[{"count":1,"lifetime":"standing","preset_ids":[preset],"special_requirements":{preset:{"task_scope":"planning-design-review-only"}},"state":"granted"}]}
    (repo/'.kaola/delegator-heartbeat.json').write_text(json.dumps({"schema":"kaola-delegator-heartbeat/1","authorization":az}))
    (repo/'plan.json').write_text(json.dumps({"scope":"research","repo":str(repo.resolve()),"items":[{"item_id":"x","preset":preset,"session":"x","prompt":"review"}]}))
    (repo/'live.json').write_text(json.dumps({"rows":[]}))
    p=subprocess.run([sys.executable,str(D),'execute','--plan',str(repo/'plan.json'),'--authorization',str(repo/'auth.json'),'--platforms',str(REPO/'platforms'),'--live',str(repo/'live.json'),'--dry-run'],capture_output=True,text=True,env=env,timeout=60)
    o=json.loads(p.stdout);r=o['items'][0]
    return {k:r.get(k) for k in ('status','reason','evidence')}
for preset in ('claude-code/opus-xhigh','claude-code/fable','codex/astra'):
    print(preset, run(preset,'expert'))
