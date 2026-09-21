#!/usr/bin/env bash
# Issue #120 live probe, run by the dsh Host's own shell tool.
{
echo "== sandbox_check"; python3 /tmp/kpr120/sbcheck.py
echo "== ps"; /bin/ps -o pid= -p $$ >/dev/null 2>&1; echo "ps rc=$?"
echo "== env"; env | grep -E '^(HOME|DSH_|KAOLA_|TMPDIR|PATH)=' | sort
echo "== ppid chain"; p=$$; for i in 1 2 3 4 5 6; do ps -o pid=,ppid=,command= -p $p 2>&1 | cut -c1-200; p=$(ps -o ppid= -p $p 2>/dev/null | tr -d ' '); [ -z "$p" ] && break; done
echo "== worker start"; /Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-120/scripts/kaola-tmux.sh dsh start --repo /tmp/kpr120/repo --session dsh-KPR-i120-wdsh 2>&1 | tail -c 3000
echo; echo "== worker stderr.log"; cat /tmp/kpr120/records/dsh/dsh-KPR-i120-wdsh/*/stderr.log 2>&1 | head -30
echo "== worker stop"; /Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-120/scripts/kaola-tmux.sh dsh stop --force --repo /tmp/kpr120/repo --session dsh-KPR-i120-wdsh 2>&1 | tail -c 600
} > /tmp/kpr120/probe.out 2>&1
echo PROBE-DONE
