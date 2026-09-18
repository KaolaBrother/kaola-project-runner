#!/usr/bin/env bash
# Issue #65 live acceptance: drive one exact owned ACP session through the real
# Runner and prove a native mid-turn steer. Owns only the session it starts.
set -u
WT="/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-65"
EV="/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/kaola-workflow/issue-65/evidence/live"
R="$WT/scripts/kaola-tmux.sh"
PLATFORM="${1:?platform}"; SESSION="${2:?session}"
LONG='Use your shell tool to run these commands ONE AT A TIME, each in its own separate tool call, never batched: `sleep 4 && echo step-1`, then `sleep 4 && echo step-2`, and so on up through step-12. Print a one-line comment after each. Do not stop early, do not combine them.'
STEER='STOP. Abandon the step loop immediately. Do not run any more shell commands. Reply with exactly one line: STEERED-OK-65'
mkdir -p "$EV"
say(){ echo "=== $* ($(date +%T))"; }
say start; "$R" "$PLATFORM" start --repo "$WT" --session "$SESSION" >"$EV/$PLATFORM-1-start.json" 2>&1; echo "exit=$?"
python3 -c "import json;d=json.load(open('$EV/$PLATFORM-1-start.json'));print(' state',d.get('state'),'acp_session_id',d.get('acp_session_id'),'error',d.get('error'))" 2>/dev/null || head -c 400 "$EV/$PLATFORM-1-start.json"
say send-no-wait; "$R" "$PLATFORM" send --repo "$WT" --session "$SESSION" --no-wait --text "$LONG" >"$EV/$PLATFORM-2-send.json" 2>&1; echo "exit=$?"
python3 -c "import json;d=json.load(open('$EV/$PLATFORM-2-send.json'));print(' outcome',d.get('outcome'),'mutation_status',d.get('mutation_status'),'error',d.get('error'))" 2>/dev/null || head -c 400 "$EV/$PLATFORM-2-send.json"
say wait-then-steer
# Steer EARLY, while the turn is demonstrably still running: poll the holder's
# own turn_active and fire once the agent has been working for STEER_AFTER s.
STEER_AFTER="${STEER_AFTER:-20}"
t0=$(date +%s)
while :; do
  "$R" "$PLATFORM" observe --repo "$WT" --session "$SESSION" >"$EV/$PLATFORM-3-observe.json" 2>&1
  a=$(python3 -c "import json;d=json.load(open('$EV/$PLATFORM-3-observe.json'));print(d.get('turn_active'))" 2>/dev/null || echo unknown)
  el=$(( $(date +%s) - t0 ))
  echo "  poll t=${el}s turn_active=$a"
  [ "$a" != "True" ] && { echo "  turn already ended before the steer"; break; }
  [ "$el" -ge "$STEER_AFTER" ] && break
  sleep 2
done
say steer; "$R" "$PLATFORM" steer --repo "$WT" --session "$SESSION" --text "$STEER" >"$EV/$PLATFORM-4-steer.json" 2>&1; echo "exit=$?"
cat "$EV/$PLATFORM-4-steer.json"
say wait-turn-end; "$R" "$PLATFORM" wait --repo "$WT" --session "$SESSION" --timeout 240 >"$EV/$PLATFORM-5-wait.json" 2>&1; echo "exit=$?"
python3 -c "import json;d=json.load(open('$EV/$PLATFORM-5-wait.json'));print(' outcome',d.get('outcome'),'stop_reason',d.get('stop_reason'),'final_text',repr((d.get('final_text') or '')[-300:]))" 2>/dev/null || head -c 600 "$EV/$PLATFORM-5-wait.json"
say capture; "$R" "$PLATFORM" capture --repo "$WT" --session "$SESSION" --lines 200 >"$EV/$PLATFORM-6-capture.json" 2>&1
say stop; "$R" "$PLATFORM" stop --repo "$WT" --session "$SESSION" >"$EV/$PLATFORM-7-stop.json" 2>&1; echo "exit=$?"
python3 -c "import json;d=json.load(open('$EV/$PLATFORM-7-stop.json'));print(' outcome',d.get('outcome'),'residual_pids',d.get('residual_pids'))" 2>/dev/null || head -c 400 "$EV/$PLATFORM-7-stop.json"
say done
