#!/usr/bin/env python3
import datetime, json, os, subprocess, sys
from pathlib import Path
raw=sys.stdin.read()
record={"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"matcher":"compact","raw_stdin":raw,"parsed_stdin":None}
try: record["parsed_stdin"]=json.loads(raw)
except ValueError: pass
with open('/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-149/kaola-workflow/issue-149/evidence/measurement/hook-firings-control.jsonl',"a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False)+"\n")
proc=subprocess.run([sys.executable,'/tmp/kpr149-shadow.KPvJNs/.codex/kaola-project-runner/hooks/kaola-codex-compact-hook.py',"user-emit"],input=raw,text=True,capture_output=True)
sys.stdout.write(proc.stdout)
sys.stderr.write(proc.stderr)
sys.exit(proc.returncode)
