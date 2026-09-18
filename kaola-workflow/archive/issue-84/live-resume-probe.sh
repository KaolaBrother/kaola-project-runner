#!/usr/bin/env bash
# Issue #84 live acceptance: real ZCode 3.12.3, isolated ACP, native sess_* resume.
# Round 1 -> exact stop -> --resume sess_* -> round 2. Records real replies and
# the exact-stop residual. Never prints or copies a credential.
set -uo pipefail

WT=/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-84
EV=/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/kaola-workflow/issue-84/evidence/live
REPO=/tmp/i84-live-repo
SESSION=zcode-i84-live
RUN="$WT/scripts/kaola-tmux.sh"

export KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs
export KAOLA_ZCODE_NODE=/Applications/ZCode.app/Contents/MacOS/ZCode

mkdir -p "$EV"
step() { printf '\n===== %s =====\n' "$1"; }

# A holder never self-exits: guarantee the exact stop even on an early failure.
cleanup() { "$RUN" zcode stop --repo "$REPO" --session "$SESSION" --force >"$EV/99-cleanup-stop.json" 2>&1 || true; }
trap cleanup EXIT

step "00 preflight"
"$RUN" zcode preflight --repo "$REPO" --session "$SESSION" >"$EV/00-preflight.json" 2>&1
echo "exit=$?"

step "01 start (fresh native session)"
"$RUN" zcode start --repo "$REPO" --session "$SESSION" >"$EV/01-start.json" 2>&1
echo "exit=$?"

step "02 round 1 send"
"$RUN" zcode send --repo "$REPO" --session "$SESSION" \
  --text 'Reply with exactly one line: I84-ROUND-ONE. Then state which model you are.' \
  >"$EV/02-round1-send.json" 2>&1
echo "exit=$?"

step "03 observe (native id + model after round 1)"
"$RUN" zcode observe --repo "$REPO" --session "$SESSION" >"$EV/03-observe-round1.json" 2>&1
echo "exit=$?"

NATIVE=$(python3 -c '
import json,sys,re
raw=open(sys.argv[1],encoding="utf-8").read()
m=re.search(r"sess_[0-9a-fA-F-]{8,}",raw)
print(m.group(0) if m else "")
' "$EV/03-observe-round1.json")
echo "NATIVE_SESSION_ID=$NATIVE" | tee "$EV/04-native-session-id.txt"
[ -n "$NATIVE" ] || { echo "FAIL: no native sess_* id observed"; exit 1; }

step "05 exact stop of the holder"
"$RUN" zcode stop --repo "$REPO" --session "$SESSION" >"$EV/05-stop-exact.json" 2>&1
echo "exit=$?"

step "06 post-stop residual"
"$RUN" zcode status --repo "$REPO" --session "$SESSION" >"$EV/06-status-after-stop.json" 2>&1
echo "exit=$?"

step "07 resume the same native session"
"$RUN" zcode start --repo "$REPO" --session "$SESSION" --resume "$NATIVE" >"$EV/07-start-resume.json" 2>&1
echo "exit=$?"

step "08 round 2 send on the resumed session"
"$RUN" zcode send --repo "$REPO" --session "$SESSION" \
  --text 'Reply with exactly one line: I84-ROUND-TWO. Then state which model you are and repeat the one-line phrase you sent me first.' \
  >"$EV/08-round2-send.json" 2>&1
echo "exit=$?"

step "09 observe (native id + model after resume)"
"$RUN" zcode observe --repo "$REPO" --session "$SESSION" >"$EV/09-observe-round2.json" 2>&1
echo "exit=$?"

step "10 final exact stop + residual"
"$RUN" zcode stop --repo "$REPO" --session "$SESSION" >"$EV/10-stop-final.json" 2>&1
echo "exit=$?"
"$RUN" zcode status --repo "$REPO" --session "$SESSION" >"$EV/11-status-final.json" 2>&1
echo "exit=$?"

trap - EXIT
echo "LIVE PROBE COMPLETE"
