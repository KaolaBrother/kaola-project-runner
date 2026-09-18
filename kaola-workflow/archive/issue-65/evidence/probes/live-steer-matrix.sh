#!/usr/bin/env bash
# Issue #65 round 3: prove the ACTUALLY USABLE steering path on one platform,
# live, through the generated Skill's own script.
#
#   MODE=native     -> steer --text ...
#   MODE=interrupt  -> steer --steer-mode interrupt --text ...
#
# The steering text asks for a codeword planted in the FIRST prompt, so a
# passing run also proves the same ACP session kept its context across the
# interruption. Owns only the exact session it starts, and stops it.
set -u
WT="/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-65"
EV="/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/kaola-workflow/issue-65/evidence/live-matrix"
PLATFORM="${1:?platform}"; MODE="${2:?native|interrupt}"
SESSION="${PLATFORM}-kaola-i65m"
R="$WT/skills/${PLATFORM}-kaola-project-runner/scripts/runtime-tmux.sh"
mkdir -p "$EV"
CODEWORD="TOPAZ-65"
P1="Remember this codeword for later: ${CODEWORD}. Now use your shell tool to run these commands ONE AT A TIME, each in its own separate tool call, never batched: \`sleep 5 && echo step-1\`, then \`sleep 5 && echo step-2\`, and so on up through step-10. Print a one-line comment after each. Do not stop early."
P2="Change of plan: stop the step loop and do not run any more shell commands. Reply with exactly one line: the codeword I gave you earlier, followed by -OK"
say(){ echo "=== $* ($(date +%T))"; }

say "start $PLATFORM"
"$R" start --repo "$WT" --session "$SESSION" >"$EV/$PLATFORM-1-start.json" 2>&1
python3 -c "import json;d=json.load(open('$EV/$PLATFORM-1-start.json'));print(' state',d.get('state'),'err',(d.get('error') or {}).get('code'))" || { head -c 300 "$EV/$PLATFORM-1-start.json"; exit 1; }

say "dispatch"
"$R" send --repo "$WT" --session "$SESSION" --no-wait --text "$P1" >"$EV/$PLATFORM-2-send.json" 2>&1
python3 -c "import json;d=json.load(open('$EV/$PLATFORM-2-send.json'));print(' outcome',d.get('outcome'),'cursor',d.get('dispatch_event_cursor'))"

say "wait for the turn to be genuinely working"
t0=$(date +%s)
while :; do
  "$R" observe --repo "$WT" --session "$SESSION" >"$EV/$PLATFORM-3-observe.json" 2>&1
  a=$(python3 -c "import json;d=json.load(open('$EV/$PLATFORM-3-observe.json'));print(d.get('turn_active'))" 2>/dev/null || echo unknown)
  el=$(( $(date +%s) - t0 ))
  [ "$a" != "True" ] && { echo "  turn ended early at ${el}s (active=$a)"; break; }
  [ "$el" -ge "${STEER_AFTER:-25}" ] && { echo "  steering at ${el}s, turn_active=True"; break; }
  sleep 3
done

say "steer (mode=$MODE)"
if [ "$MODE" = interrupt ]; then
  "$R" steer --repo "$WT" --session "$SESSION" --steer-mode interrupt --cancel-timeout "${CANCEL_TIMEOUT:-30}" --text "$P2" >"$EV/$PLATFORM-4-steer.json" 2>&1
else
  "$R" steer --repo "$WT" --session "$SESSION" --text "$P2" >"$EV/$PLATFORM-4-steer.json" 2>&1
fi
python3 -c "
import json;d=json.load(open('$EV/$PLATFORM-4-steer.json'))
keys=('steer_outcome','steer_mode','steer_consumed','steer_confirmation','interrupted','turn_was_active','cancelled_turn_stop_reason','side_effects_possible','cancelled_turn_request_id','new_turn_request_id','turn_request_id','turn_request_id_after','turn_request_id_preserved','steer_native_outcome')
print(json.dumps({k:d[k] for k in keys if k in d}, ensure_ascii=False))
e=d.get('error');  print(' error:', e.get('code') if e else None)"

say "wait for the steered turn"
"$R" wait --repo "$WT" --session "$SESSION" --timeout 300 >"$EV/$PLATFORM-5-wait.json" 2>&1
python3 -c "
import json;d=json.load(open('$EV/$PLATFORM-5-wait.json'))
t=(d.get('final_text') or '')
print(' outcome',d.get('outcome'),'stop',d.get('stop_reason'))
print(' CONTEXT_KEPT', 'TOPAZ-65' in t)
print(' final:',repr(t[-400:]))"

say stop
"$R" stop --repo "$WT" --session "$SESSION" >"$EV/$PLATFORM-6-stop.json" 2>&1
python3 -c "import json;d=json.load(open('$EV/$PLATFORM-6-stop.json'));print(' residual_pids',d.get('residual_pids'))"
say "done $PLATFORM"
