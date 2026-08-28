#!/usr/bin/env bash
set -euo pipefail

OWNER_KEY="GROK_KAOLA_PROJECT_RUNNER"
REPO_KEY="GROK_KAOLA_REPO"
OWNER_VALUE="1"

usage() {
  cat <<'EOF'
Usage:
  grok-tmux.sh preflight --repo ABS_PATH --session NAME
  grok-tmux.sh start     --repo ABS_PATH --session NAME [--continue | --resume ID]
  grok-tmux.sh status    --repo ABS_PATH --session NAME
  grok-tmux.sh capture   --repo ABS_PATH --session NAME [--lines N]
  grok-tmux.sh send      --repo ABS_PATH --session NAME [--text TEXT]
  grok-tmux.sh stop      --repo ABS_PATH --session NAME [--force]

Without --text, send reads the prompt from stdin. --force kills only the exact owned session.
EOF
}

die() {
  printf 'grok-tmux: %s\n' "$*" >&2
  exit 1
}

resolve_tool() {
  local candidate="$1"
  if [[ "$candidate" == */* ]]; then
    [[ -x "$candidate" ]] || return 1
    printf '%s\n' "$candidate"
  else
    command -v "$candidate"
  fi
}

emit_json() {
  "$PYTHON_BIN" - "$@" <<'PY'
import json
import sys

result = {}
for raw in sys.argv[1:]:
    kind, key, value = raw.split(":", 2)
    if kind == "b":
        result[key] = value == "true"
    elif kind == "n":
        result[key] = int(value)
    else:
        result[key] = value
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
PY
}

canonical_dir() {
  (cd "$1" 2>/dev/null && pwd -P)
}

validate_common() {
  [[ -n "$repo" ]] || die "--repo is required"
  [[ "$repo" == /* ]] || die "--repo must be an absolute path"
  [[ -d "$repo" ]] || die "repository does not exist: $repo"
  repo="$(canonical_dir "$repo")" || die "cannot resolve repository: $repo"

  local git_root
  git_root="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || \
    die "not a Git repository: $repo"
  git_root="$(canonical_dir "$git_root")" || die "cannot resolve Git root: $git_root"
  [[ "$git_root" == "$repo" ]] || die "--repo must name the Git root: $git_root"

  [[ -n "$session" ]] || die "--session is required"
  [[ "$session" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$ ]] || \
    die "session must match [A-Za-z0-9][A-Za-z0-9_.-]{0,79}"
}

inspect_workflow_skills() {
  local inspect_json
  inspect_json="$(cd "$repo" && "$GROK_BIN" inspect --json)" || \
    die "grok inspect --json failed"
  INSPECT_JSON="$inspect_json" "$PYTHON_BIN" <<'PY'
import json
import os
import sys

try:
    payload = json.loads(os.environ["INSPECT_JSON"])
except Exception as exc:
    print(f"invalid grok inspect JSON: {exc}", file=sys.stderr)
    raise SystemExit(2)

skills = {item.get("name") for item in payload.get("skills", [])}
required = {"workflow-next", "kaola-workflow-finalize"}
missing = sorted(required - skills)
if missing:
    print("missing Grok skills: " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(3)

print(json.dumps({
    "grok_version": payload.get("grokVersion", "unknown"),
    "project_root": payload.get("projectRoot"),
    "workflow_next": True,
    "kaola_workflow_finalize": True,
}, ensure_ascii=False, sort_keys=True))
PY
}

session_exists() {
  "$TMUX_BIN" has-session -t "$TMUX_SESSION_TARGET" 2>/dev/null
}

tmux_env_value() {
  local key="$1"
  local line
  line="$("$TMUX_BIN" show-environment -t "$TMUX_SESSION_TARGET" "$key" 2>/dev/null || true)"
  [[ "$line" == "$key="* ]] || return 1
  printf '%s\n' "${line#*=}"
}

load_session_state() {
  STATE_PRESENT=false
  STATE_OWNED=false
  STATE_REPO_MATCH=false
  STATE_TUI=false
  STATE_ACTIVITY=unknown
  STATE_PANE_COUNT=0
  STATE_PANE_PATH=""
  STATE_PANE_COMMAND=""
  STATE_PANE_TITLE=""
  STATE_PANE_DEAD=""
  STATE_PANE_PID=""
  STATE_CAPTURE=""

  session_exists || return 0
  STATE_PRESENT=true

  local pane_rows owner repo_marker tail_sample
  pane_rows="$("$TMUX_BIN" list-panes -t "$TMUX_SESSION_TARGET" \
    -F $'#{pane_current_path}\t#{pane_current_command}\t#{pane_title}\t#{pane_dead}\t#{pane_pid}')"
  STATE_PANE_COUNT="$(printf '%s\n' "$pane_rows" | awk 'NF {count++} END {print count+0}')"
  if [[ "$STATE_PANE_COUNT" -eq 1 ]]; then
    IFS=$'\t' read -r STATE_PANE_PATH STATE_PANE_COMMAND STATE_PANE_TITLE \
      STATE_PANE_DEAD STATE_PANE_PID <<<"$pane_rows"
  fi

  owner="$(tmux_env_value "$OWNER_KEY" || true)"
  repo_marker="$(tmux_env_value "$REPO_KEY" || true)"
  if [[ "$owner" == "$OWNER_VALUE" ]]; then
    STATE_OWNED=true
  fi

  if [[ "$STATE_PANE_COUNT" -eq 1 && -d "$STATE_PANE_PATH" ]]; then
    local pane_real
    pane_real="$(canonical_dir "$STATE_PANE_PATH" || true)"
    if [[ "$pane_real" == "$repo" && "$repo_marker" == "$repo" ]]; then
      STATE_REPO_MATCH=true
    fi
  fi

  STATE_CAPTURE="$("$TMUX_BIN" capture-pane -p -t "$TMUX_PANE_TARGET" -S -80 2>/dev/null || true)"
  if [[ "$STATE_PANE_COUNT" -eq 1 && "$STATE_PANE_TITLE" == "grok" && \
        "$STATE_PANE_DEAD" == "0" ]]; then
    STATE_TUI=true
  fi

  tail_sample="$(printf '%s\n' "$STATE_CAPTURE" | tail -n 14)"
  if printf '%s\n' "$tail_sample" | grep -Eq \
      'Waiting for response|Press Esc to interrupt|Running tool|Working…|Thinking…|esc to cancel'; then
    STATE_ACTIVITY=busy
  elif [[ "$STATE_TUI" == true ]] && printf '%s\n' "$tail_sample" | grep -q '^❯'; then
    STATE_ACTIVITY=idle
  fi
}

load_git_state() {
  GIT_BRANCH="$(git -C "$repo" branch --show-current 2>/dev/null || true)"
  [[ -n "$GIT_BRANCH" ]] || GIT_BRANCH="DETACHED"
  GIT_HEAD="$(git -C "$repo" rev-parse --short=12 HEAD 2>/dev/null || true)"
  [[ -n "$GIT_HEAD" ]] || GIT_HEAD="UNBORN"
  GIT_CHANGED_COUNT="$(git -C "$repo" status --porcelain=v1 2>/dev/null | awk 'END {print NR+0}')"
  GIT_CLEAN=true
  [[ "$GIT_CHANGED_COUNT" -eq 0 ]] || GIT_CLEAN=false
  GIT_UPSTREAM="$(git -C "$repo" rev-parse --abbrev-ref '@{u}' 2>/dev/null || true)"
  GIT_AHEAD=-1
  GIT_BEHIND=-1
  if [[ -n "$GIT_UPSTREAM" ]]; then
    read -r GIT_AHEAD GIT_BEHIND < <(
      git -C "$repo" rev-list --left-right --count HEAD..."$GIT_UPSTREAM" 2>/dev/null || \
        printf '%s\n' '-1 -1'
    )
  fi
}

emit_status() {
  load_git_state
  emit_json \
    "s:result:$1" \
    "s:session:$session" \
    "s:repo:$repo" \
    "b:present:$STATE_PRESENT" \
    "b:owned:$STATE_OWNED" \
    "b:repo_match:$STATE_REPO_MATCH" \
    "b:grok_tui:$STATE_TUI" \
    "s:activity:$STATE_ACTIVITY" \
    "n:pane_count:$STATE_PANE_COUNT" \
    "s:pane_path:$STATE_PANE_PATH" \
    "s:pane_command:$STATE_PANE_COMMAND" \
    "s:pane_title:$STATE_PANE_TITLE" \
    "s:pane_pid:$STATE_PANE_PID" \
    "s:git_branch:$GIT_BRANCH" \
    "s:git_head:$GIT_HEAD" \
    "b:git_clean:$GIT_CLEAN" \
    "n:git_changed_count:$GIT_CHANGED_COUNT" \
    "s:git_upstream:$GIT_UPSTREAM" \
    "n:git_ahead:$GIT_AHEAD" \
    "n:git_behind:$GIT_BEHIND"
}

require_owned_exact_tui() {
  load_session_state
  [[ "$STATE_PRESENT" == true ]] || { emit_status "absent"; exit 1; }
  [[ "$STATE_OWNED" == true ]] || { emit_status "unowned"; exit 1; }
  [[ "$STATE_REPO_MATCH" == true ]] || { emit_status "repo-mismatch"; exit 1; }
  [[ "$STATE_PANE_COUNT" -eq 1 ]] || { emit_status "unexpected-pane-count"; exit 1; }
  [[ "$STATE_TUI" == true ]] || { emit_status "grok-tui-not-detected"; exit 1; }
}

command_name="${1:-}"
[[ -n "$command_name" ]] || { usage; exit 2; }
shift

repo=""
session=""
resume_id=""
continue_mode=false
force=false
lines=120
text_value=""
text_given=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) [[ $# -ge 2 ]] || die "--repo needs a value"; repo="$2"; shift 2 ;;
    --session) [[ $# -ge 2 ]] || die "--session needs a value"; session="$2"; shift 2 ;;
    --resume) [[ $# -ge 2 ]] || die "--resume needs a value"; resume_id="$2"; shift 2 ;;
    --continue) continue_mode=true; shift ;;
    --force) force=true; shift ;;
    --lines) [[ $# -ge 2 ]] || die "--lines needs a value"; lines="$2"; shift 2 ;;
    --text) [[ $# -ge 2 ]] || die "--text needs a value"; text_value="$2"; text_given=true; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

case "$command_name" in
  preflight|start|status|capture|send|stop) ;;
  *) usage; die "unknown command: $command_name" ;;
esac

TMUX_BIN="$(resolve_tool "${TMUX_BIN:-tmux}")" || die "tmux executable not found"
GROK_BIN="$(resolve_tool "${GROK_BIN:-grok}")" || die "grok executable not found"
PYTHON_BIN="$(resolve_tool "${PYTHON_BIN:-python3}")" || die "python3 executable not found"
command -v git >/dev/null 2>&1 || die "git executable not found"

validate_common
TMUX_SESSION_TARGET="=$session"
TMUX_PANE_TARGET="=$session:0.0"

case "$command_name" in
  preflight)
    workflow_json="$(inspect_workflow_skills)" || exit $?
    WORKFLOW_JSON="$workflow_json" REPO_VALUE="$repo" SESSION_VALUE="$session" \
      "$PYTHON_BIN" <<'PY'
import json
import os

payload = json.loads(os.environ["WORKFLOW_JSON"])
payload.update({
    "result": "ready",
    "repo": os.environ["REPO_VALUE"],
    "session": os.environ["SESSION_VALUE"],
})
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
PY
    ;;

  status)
    load_session_state
    if [[ "$STATE_PRESENT" == true ]]; then
      emit_status "present"
    else
      emit_status "absent"
    fi
    ;;

  start)
    [[ -z "$resume_id" || "$continue_mode" == false ]] || \
      die "--resume and --continue are mutually exclusive"
    inspect_workflow_skills >/dev/null
    load_session_state
    if [[ "$STATE_PRESENT" == true ]]; then
      if [[ "$STATE_OWNED" == true && "$STATE_REPO_MATCH" == true && "$STATE_TUI" == true ]]; then
        emit_status "already-running"
        exit 0
      fi
      emit_status "existing-session-not-reusable"
      exit 1
    fi

    "$TMUX_BIN" new-session -d -s "$session" -c "$repo"
    "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$OWNER_KEY" "$OWNER_VALUE"
    "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$REPO_KEY" "$repo"

    printf -v grok_q '%q' "$GROK_BIN"
    printf -v repo_q '%q' "$repo"
    launch="exec $grok_q --cwd $repo_q --minimal"
    if [[ -n "$resume_id" ]]; then
      printf -v resume_q '%q' "$resume_id"
      launch+=" --resume $resume_q"
    elif [[ "$continue_mode" == true ]]; then
      launch+=" --continue"
    fi
    "$TMUX_BIN" send-keys -t "$TMUX_PANE_TARGET" -l "$launch"
    "$TMUX_BIN" send-keys -t "$TMUX_PANE_TARGET" C-m

    start_timeout="${GROK_START_TIMEOUT:-20}"
    [[ "$start_timeout" =~ ^[0-9]+$ ]] || die "GROK_START_TIMEOUT must be an integer"
    for ((i=0; i<start_timeout; i++)); do
      sleep 1
      load_session_state
      if [[ "$STATE_PRESENT" != true ]]; then
        emit_status "start-exited"
        exit 1
      fi
      if [[ "$STATE_OWNED" == true && "$STATE_REPO_MATCH" == true && "$STATE_TUI" == true ]]; then
        emit_status "started"
        exit 0
      fi
    done
    emit_status "start-pending"
    exit 2
    ;;

  capture)
    [[ "$lines" =~ ^[1-9][0-9]*$ ]] || die "--lines must be a positive integer"
    [[ "$lines" -le 5000 ]] || die "--lines must be no greater than 5000"
    require_owned_exact_tui
    "$TMUX_BIN" capture-pane -p -t "$TMUX_PANE_TARGET" -S "-$lines"
    ;;

  send)
    [[ -z "$resume_id" && "$continue_mode" == false && "$force" == false ]] || \
      die "send accepts neither resume nor stop options"
    require_owned_exact_tui
    [[ "$STATE_ACTIVITY" == idle ]] || { emit_status "not-idle"; exit 1; }

    if [[ "$text_given" == true ]]; then
      prompt="$text_value"
    else
      [[ ! -t 0 ]] || die "send needs --text or prompt data on stdin"
      prompt="$(</dev/stdin)"
    fi
    [[ -n "$prompt" ]] || die "prompt must not be empty"

    buffer_name="grok-kaola-project-runner-$$"
    printf '%s' "$prompt" | "$TMUX_BIN" load-buffer -b "$buffer_name" -
    "$TMUX_BIN" paste-buffer -d -b "$buffer_name" -t "$TMUX_PANE_TARGET"
    "$TMUX_BIN" send-keys -t "$TMUX_PANE_TARGET" C-m
    emit_json "s:result:sent" "s:session:$session" "s:repo:$repo"
    ;;

  stop)
    load_session_state
    if [[ "$STATE_PRESENT" != true ]]; then
      emit_status "already-stopped"
      exit 0
    fi
    [[ "$STATE_OWNED" == true ]] || { emit_status "unowned"; exit 1; }
    [[ "$STATE_REPO_MATCH" == true ]] || { emit_status "repo-mismatch"; exit 1; }
    [[ "$STATE_PANE_COUNT" -eq 1 ]] || { emit_status "unexpected-pane-count"; exit 1; }

    if [[ "$force" == true ]]; then
      "$TMUX_BIN" kill-session -t "$TMUX_SESSION_TARGET"
      STATE_PRESENT=false
      emit_status "force-stopped"
      exit 0
    fi

    [[ "$STATE_TUI" == true ]] || { emit_status "grok-tui-not-detected"; exit 1; }
    [[ "$STATE_ACTIVITY" == idle ]] || { emit_status "not-idle"; exit 1; }
    "$TMUX_BIN" send-keys -t "$TMUX_PANE_TARGET" -l '/quit'
    "$TMUX_BIN" send-keys -t "$TMUX_PANE_TARGET" C-m
    for ((i=0; i<10; i++)); do
      sleep 1
      if ! session_exists; then
        STATE_PRESENT=false
        emit_status "stopped"
        exit 0
      fi
    done
    load_session_state
    emit_status "quit-pending"
    exit 2
    ;;
esac
