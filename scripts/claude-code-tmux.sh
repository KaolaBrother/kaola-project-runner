#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
OWNER_KEY="KAOLA_PROJECT_RUNNER"
PLATFORM_KEY="KAOLA_PROJECT_RUNNER_PLATFORM"
REPO_KEY="KAOLA_PROJECT_RUNNER_REPO"
OWNER_VALUE="1"
LEGACY_OWNER_KEY="GROK_KAOLA_PROJECT_RUNNER"
LEGACY_REPO_KEY="GROK_KAOLA_REPO"

usage() {
  cat <<'EOF'
Usage:
  kaola-tmux.sh PLATFORM preflight --repo ABS_PATH --session NAME
  kaola-tmux.sh claude-code start  --repo ABS_PATH --session NAME [--continue | --resume ID]
                                      [--model NAME] [--effort LEVEL]
                                      [--permission-mode MODE]
  kaola-tmux.sh PLATFORM status    --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM capture   --repo ABS_PATH --session NAME [--lines N]
  kaola-tmux.sh PLATFORM send      --repo ABS_PATH --session NAME [--text TEXT]
  kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME [--force]

This carrier accepts only PLATFORM=claude-code. Fresh launches default to
--model opus --effort high --permission-mode auto.
Without --text, send reads the prompt from stdin. --force kills only the exact owned session.
EOF
}

die() {
  printf 'kaola-tmux[%s]: %s\n' "${platform:-unknown}" "$*" >&2
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
    elif kind == "j":
        result[key] = json.loads(value)
    else:
        result[key] = value
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
PY
}

canonical_dir() {
  (cd "$1" 2>/dev/null && pwd -P)
}

platform="${1:-}"
[[ -n "$platform" ]] || { usage; exit 2; }
shift

case "$platform" in
  claude-code) ;;
  *) usage; die "unknown platform: $platform" ;;
esac

adapter_file="$script_dir/adapters/$platform.sh"
[[ -f "$adapter_file" ]] || die "adapter not installed: $adapter_file"
KAOLA_CLAUDE_PROFILE_REQUIRED=true
# shellcheck source=/dev/null
source "$adapter_file"
[[ "${ADAPTER_ID:-}" == "$platform" ]] || die "adapter identity mismatch"

command_name="${1:-}"
[[ -n "$command_name" ]] || { usage; exit 2; }
shift

case "$command_name" in
  preflight|start|status|capture|send|stop) ;;
  *) usage; die "unknown command: $command_name" ;;
esac

repo=""
session=""
resume_id=""
continue_mode=false
force=false
lines=120
text_value=""
text_given=false
model="opus"
effort="high"
permission_mode="auto"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) [[ $# -ge 2 ]] || die "--repo needs a value"; repo="$2"; shift 2 ;;
    --session) [[ $# -ge 2 ]] || die "--session needs a value"; session="$2"; shift 2 ;;
    --resume) [[ $# -ge 2 ]] || die "--resume needs a value"; resume_id="$2"; shift 2 ;;
    --continue) continue_mode=true; shift ;;
    --force) force=true; shift ;;
    --lines) [[ $# -ge 2 ]] || die "--lines needs a value"; lines="$2"; shift 2 ;;
    --text) [[ $# -ge 2 ]] || die "--text needs a value"; text_value="$2"; text_given=true; shift 2 ;;
    --model) [[ $# -ge 2 ]] || die "--model needs a value"; model="$2"; shift 2 ;;
    --effort) [[ $# -ge 2 ]] || die "--effort needs a value"; effort="$2"; shift 2 ;;
    --permission-mode) [[ $# -ge 2 ]] || die "--permission-mode needs a value"; permission_mode="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

TMUX_BIN="$(resolve_tool "${TMUX_BIN:-tmux}")" || die "tmux executable not found"
PYTHON_BIN="$(resolve_tool "${PYTHON_BIN:-python3}")" || die "python3 executable not found"
PS_BIN="$(resolve_tool "${PS_BIN:-ps}")" || die "ps executable not found"
command -v git >/dev/null 2>&1 || die "git executable not found"
runtime_override="$(printenv "$ADAPTER_BIN_ENV" 2>/dev/null || true)"
RUNTIME_BIN="$(resolve_tool "${runtime_override:-$ADAPTER_DEFAULT_BIN}")" || \
  die "$ADAPTER_DISPLAY_NAME executable not found (override with $ADAPTER_BIN_ENV)"
RUNTIME_BIN_REAL="$("$PYTHON_BIN" - "$RUNTIME_BIN" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
)"

validate_common() {
  [[ -n "$repo" ]] || die "--repo is required"
  [[ "$repo" == /* ]] || die "--repo must be an absolute path"
  [[ -d "$repo" ]] || die "repository does not exist: $repo"
  repo="$(canonical_dir "$repo")" || die "cannot resolve repository: $repo"

  local git_root
  git_root="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || die "not a Git repository: $repo"
  git_root="$(canonical_dir "$git_root")" || die "cannot resolve Git root: $git_root"
  [[ "$git_root" == "$repo" ]] || die "--repo must name the Git root: $git_root"

  [[ -n "$session" ]] || die "--session is required"
  [[ "$session" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$ ]] || \
    die "session must match [A-Za-z0-9][A-Za-z0-9_.-]{0,79}"
}

validate_common
TMUX_SESSION_TARGET="=$session"

if [[ "$command_name" != start && ( "$model" != opus || "$effort" != high || "$permission_mode" != auto ) ]]; then
  die "model, effort, and permission mode are start-only options"
fi
[[ "$model" =~ ^[A-Za-z0-9._:-]+$ ]] || die "model contains unsupported characters"
case "$effort" in low|medium|high|xhigh|max) ;; *) die "unsupported Claude effort: $effort" ;; esac
case "$permission_mode" in
  acceptEdits|auto|bypassPermissions|manual|dontAsk|plan) ;;
  *) die "unsupported Claude permission mode: $permission_mode" ;;
esac

session_exists() {
  "$TMUX_BIN" has-session -t "$TMUX_SESSION_TARGET" 2>/dev/null
}

tmux_env_value() {
  local key="$1" line
  line="$("$TMUX_BIN" show-environment -t "$TMUX_SESSION_TARGET" "$key" 2>/dev/null || true)"
  [[ "$line" == "$key="* ]] || return 1
  printf '%s\n' "${line#*=}"
}

runtime_path_is_leading_argv() {
  local process_command="$1" expected_path="$2" after_argv0
  [[ -n "$process_command" && -n "$expected_path" ]] || return 1

  # Native executables expose the runtime path as argv[0]. Shebang launchers expose their
  # interpreter as argv[0] and the exact script path as argv[1]. A runtime path elsewhere in the
  # command line is only attacker-controlled argument text and is never process identity proof.
  if [[ "$process_command" == "$expected_path" || "$process_command" == "$expected_path "* ]]; then
    return 0
  fi
  [[ "$process_command" == *" "* ]] || return 1
  after_argv0="${process_command#* }"
  while [[ "$after_argv0" == " "* ]]; do after_argv0="${after_argv0# }"; done
  [[ "$after_argv0" == "$expected_path" || "$after_argv0" == "$expected_path "* ]]
}

runtime_process_matches() {
  local process_command="$1" pane_command="$2"
  runtime_path_is_leading_argv "$process_command" "$RUNTIME_BIN" && return 0
  if [[ "$RUNTIME_BIN_REAL" != "$RUNTIME_BIN" ]] && \
     runtime_path_is_leading_argv "$process_command" "$RUNTIME_BIN_REAL"; then
    return 0
  fi
  if type adapter_process_matches >/dev/null 2>&1; then
    adapter_process_matches "$process_command" "$pane_command"
    return $?
  fi
  return 1
}

load_session_state() {
  STATE_PRESENT=false
  STATE_OWNED=false
  STATE_PLATFORM_MATCH=false
  STATE_REPO_MATCH=false
  STATE_TUI=false
  STATE_LEGACY_OWNERSHIP=false
  STATE_ACTIVITY=unknown
  STATE_RUNTIME_SESSION_ID=""
  STATE_PANE_COUNT=0
  STATE_PANE_ID=""
  STATE_PANE_PATH=""
  STATE_PANE_COMMAND=""
  STATE_PANE_TITLE=""
  STATE_PANE_DEAD=""
  STATE_PANE_PID=""
  STATE_PANE_PROCESS=""
  STATE_PROCESS_MATCH=false
  STATE_CAPTURE=""

  session_exists || return 0
  STATE_PRESENT=true

  local pane_rows owner platform_marker repo_marker legacy_owner legacy_repo pane_real
  pane_rows="$("$TMUX_BIN" list-panes -t "$TMUX_SESSION_TARGET" \
    -F $'#{pane_id}\t#{pane_current_path}\t#{pane_current_command}\t#{pane_title}\t#{pane_dead}\t#{pane_pid}')"
  STATE_PANE_COUNT="$(printf '%s\n' "$pane_rows" | awk 'NF {count++} END {print count+0}')"
  if [[ "$STATE_PANE_COUNT" -eq 1 ]]; then
    IFS=$'\t' read -r STATE_PANE_ID STATE_PANE_PATH STATE_PANE_COMMAND STATE_PANE_TITLE \
      STATE_PANE_DEAD STATE_PANE_PID <<<"$pane_rows"
  fi

  owner="$(tmux_env_value "$OWNER_KEY" || true)"
  platform_marker="$(tmux_env_value "$PLATFORM_KEY" || true)"
  repo_marker="$(tmux_env_value "$REPO_KEY" || true)"
  if [[ "$owner" == "$OWNER_VALUE" ]]; then
    STATE_OWNED=true
    [[ "$platform_marker" == "$platform" ]] && STATE_PLATFORM_MATCH=true
  elif [[ "$platform" == grok ]]; then
    legacy_owner="$(tmux_env_value "$LEGACY_OWNER_KEY" || true)"
    legacy_repo="$(tmux_env_value "$LEGACY_REPO_KEY" || true)"
    if [[ "$legacy_owner" == "$OWNER_VALUE" && "$legacy_repo" == "$repo" ]]; then
      STATE_OWNED=true
      STATE_PLATFORM_MATCH=true
      STATE_LEGACY_OWNERSHIP=true
      repo_marker="$legacy_repo"
    fi
  fi

  if [[ "$STATE_PANE_COUNT" -eq 1 && -d "$STATE_PANE_PATH" ]]; then
    pane_real="$(canonical_dir "$STATE_PANE_PATH" || true)"
    [[ "$pane_real" == "$repo" && "$repo_marker" == "$repo" ]] && STATE_REPO_MATCH=true
  fi

  if [[ -n "$STATE_PANE_ID" ]]; then
    STATE_CAPTURE="$("$TMUX_BIN" capture-pane -p -t "$STATE_PANE_ID" -S -100 2>/dev/null || true)"
  fi
  if [[ "$STATE_PANE_COUNT" -eq 1 && "$STATE_PANE_DEAD" == "0" && -n "$STATE_PANE_PID" ]]; then
    STATE_PANE_PROCESS="$("$PS_BIN" -ww -p "$STATE_PANE_PID" -o command= 2>/dev/null || true)"
    if runtime_process_matches "$STATE_PANE_PROCESS" "$STATE_PANE_COMMAND"; then
      STATE_PROCESS_MATCH=true
    fi
  fi
  if [[ "$STATE_PROCESS_MATCH" == true ]] && \
     adapter_detect_tui "$STATE_PANE_TITLE" "$STATE_PANE_COMMAND" "$STATE_CAPTURE"; then
    STATE_TUI=true
  fi
  if [[ "$STATE_TUI" == true ]]; then
    STATE_ACTIVITY="$(adapter_detect_activity "$STATE_CAPTURE")"
    STATE_RUNTIME_SESSION_ID="$(adapter_extract_session_id "$STATE_CAPTURE" || true)"
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
      git -C "$repo" rev-list --left-right --count HEAD..."$GIT_UPSTREAM" 2>/dev/null || printf '%s\n' '-1 -1'
    )
  fi
}

emit_status() {
  local result="$1"
  load_git_state
  args=(
    "s:result:$result" "s:platform:$platform" "s:runtime:$ADAPTER_DISPLAY_NAME"
    "s:session:$session" "s:repo:$repo" "b:present:$STATE_PRESENT" "b:owned:$STATE_OWNED"
    "b:platform_match:$STATE_PLATFORM_MATCH" "b:repo_match:$STATE_REPO_MATCH"
    "b:tui_detected:$STATE_TUI" "b:legacy_ownership:$STATE_LEGACY_OWNERSHIP"
    "s:activity:$STATE_ACTIVITY" "s:runtime_session_id:$STATE_RUNTIME_SESSION_ID"
    "n:pane_count:$STATE_PANE_COUNT" "s:pane_id:$STATE_PANE_ID" "s:pane_path:$STATE_PANE_PATH"
    "s:pane_command:$STATE_PANE_COMMAND" "s:pane_title:$STATE_PANE_TITLE" "s:pane_pid:$STATE_PANE_PID"
    "s:pane_process:$STATE_PANE_PROCESS" "b:process_match:$STATE_PROCESS_MATCH"
    "s:git_branch:$GIT_BRANCH" "s:git_head:$GIT_HEAD" "b:git_clean:$GIT_CLEAN"
    "n:git_changed_count:$GIT_CHANGED_COUNT" "s:git_upstream:$GIT_UPSTREAM"
    "n:git_ahead:$GIT_AHEAD" "n:git_behind:$GIT_BEHIND"
  )
  if [[ "$platform" == grok ]]; then args+=("b:grok_tui:$STATE_TUI"); fi
  emit_json "${args[@]}"
}

require_owned_exact_tui() {
  load_session_state
  [[ "$STATE_PRESENT" == true ]] || { emit_status absent; exit 1; }
  [[ "$STATE_OWNED" == true ]] || { emit_status unowned; exit 1; }
  [[ "$STATE_PLATFORM_MATCH" == true ]] || { emit_status platform-mismatch; exit 1; }
  [[ "$STATE_REPO_MATCH" == true ]] || { emit_status repo-mismatch; exit 1; }
  [[ "$STATE_PANE_COUNT" -eq 1 ]] || { emit_status unexpected-pane-count; exit 1; }
  [[ "$STATE_TUI" == true ]] || { emit_status runtime-tui-not-detected; exit 1; }
}

case "$command_name" in
  preflight)
    adapter_preflight
    args=(
      "s:result:ready" "s:platform:$platform" "s:runtime:$ADAPTER_DISPLAY_NAME" \
      "s:runtime_version:$PREFLIGHT_VERSION" "s:runtime_binary:$RUNTIME_BIN" \
      "s:repo:$repo" "s:session:$session" "b:workflow_next:$PREFLIGHT_WORKFLOW_NEXT" \
      "b:kaola_workflow_finalize:$PREFLIGHT_FINALIZE" \
      "s:recurring_execution:$ADAPTER_RECURRING_EXECUTION" \
      "s:project_materialization:$PREFLIGHT_PROJECT_MATERIALIZATION" \
      "s:detail:$PREFLIGHT_DETAIL"
    )
    if [[ "$platform" == grok ]]; then
      args+=("s:grok_version:$PREFLIGHT_VERSION" "j:project_root:$PREFLIGHT_PROJECT_ROOT_JSON")
    fi
    emit_json "${args[@]}"
    ;;

  status)
    load_session_state
    [[ "$STATE_PRESENT" == true ]] && emit_status present || emit_status absent
    ;;

  start)
    [[ -z "$resume_id" || "$continue_mode" == false ]] || die "--resume and --continue are mutually exclusive"
    adapter_preflight
    load_session_state
    if [[ "$STATE_PRESENT" == true ]]; then
      if [[ "$STATE_OWNED" == true && "$STATE_PLATFORM_MATCH" == true && \
            "$STATE_REPO_MATCH" == true && "$STATE_TUI" == true ]]; then
        emit_status already-running
        exit 0
      fi
      emit_status existing-session-not-reusable
      exit 1
    fi

    # A platform may require one explicit, authority-owned point-of-use transaction before
    # launch. Preflight remains read-only; preparation runs only for a newly authorized exact
    # session and must finish before tmux is created so a refusal cannot leave an orphan session.
    if type adapter_prepare_launch >/dev/null 2>&1; then
      adapter_prepare_launch "$repo"
    fi

    "$TMUX_BIN" new-session -d -s "$session" -c "$repo"
    "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$OWNER_KEY" "$OWNER_VALUE"
    "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$PLATFORM_KEY" "$platform"
    "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$REPO_KEY" "$repo"
    if [[ "$platform" == grok ]]; then
      "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$LEGACY_OWNER_KEY" "$OWNER_VALUE"
      "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$LEGACY_REPO_KEY" "$repo"
    fi

    # Resolve tmux's stable pane identity after creation. Window and pane indexes
    # are user-configurable and cannot safely be assumed to be 0.0.
    load_session_state
    [[ "$STATE_PANE_COUNT" -eq 1 && -n "$STATE_PANE_ID" ]] || {
      emit_status unexpected-pane-count
      exit 1
    }

    adapter_build_launch "$repo" "$resume_id" "$continue_mode"
    launch="exec"
    for argument in "$RUNTIME_BIN" ${ADAPTER_LAUNCH_ARGS[@]+"${ADAPTER_LAUNCH_ARGS[@]}"}; do
      printf -v quoted '%q' "$argument"
      launch+=" $quoted"
    done
    "$TMUX_BIN" send-keys -t "$STATE_PANE_ID" -l "$launch"
    "$TMUX_BIN" send-keys -t "$STATE_PANE_ID" C-m

    if [[ "$platform" == grok ]]; then
      start_timeout="${KAOLA_START_TIMEOUT:-${GROK_START_TIMEOUT:-20}}"
    else
      start_timeout="${KAOLA_START_TIMEOUT:-20}"
    fi
    [[ "$start_timeout" =~ ^[0-9]+$ ]] || die "KAOLA_START_TIMEOUT must be an integer"
    for ((i=0; i<start_timeout; i++)); do
      sleep 1
      load_session_state
      if [[ "$STATE_PRESENT" != true ]]; then emit_status start-exited; exit 1; fi
      if [[ "$STATE_OWNED" == true && "$STATE_PLATFORM_MATCH" == true && \
            "$STATE_REPO_MATCH" == true && "$STATE_TUI" == true ]]; then
        emit_status started
        exit 0
      fi
    done
    emit_status start-pending
    exit 2
    ;;

  capture)
    [[ "$lines" =~ ^[1-9][0-9]*$ ]] || die "--lines must be a positive integer"
    [[ "$lines" -le 5000 ]] || die "--lines must be no greater than 5000"
    require_owned_exact_tui
    "$TMUX_BIN" capture-pane -p -t "$STATE_PANE_ID" -S "-$lines"
    ;;

  send)
    [[ -z "$resume_id" && "$continue_mode" == false && "$force" == false ]] || \
      die "send accepts neither resume nor stop options"
    require_owned_exact_tui
    [[ "$STATE_ACTIVITY" == idle ]] || { emit_status not-idle; exit 1; }
    if [[ "$text_given" == true ]]; then
      prompt="$text_value"
    else
      [[ ! -t 0 ]] || die "send needs --text or prompt data on stdin"
      prompt="$(</dev/stdin)"
    fi
    [[ -n "$prompt" ]] || die "prompt must not be empty"
    buffer_name="kaola-project-runner-${platform//[^A-Za-z0-9]/-}-$$"
    printf '%s' "$prompt" | "$TMUX_BIN" load-buffer -b "$buffer_name" -
    # Ask tmux to wrap the payload in terminal bracketed-paste markers when the target TUI
    # negotiated that mode. This keeps multiline prompts as one editor event instead of turning
    # embedded newlines into separate submitted/queued turns (observed in OpenCode).
    "$TMUX_BIN" paste-buffer -p -d -b "$buffer_name" -t "$STATE_PANE_ID"
    # Real bracketed-paste TUIs need a short event-loop turn before Enter; without it a large
    # prompt can remain as an unsubmitted "[Pasted: N lines]" chip.
    sleep 0.2
    "$TMUX_BIN" send-keys -t "$STATE_PANE_ID" C-m
    emit_json "s:result:sent" "s:platform:$platform" "s:session:$session" "s:repo:$repo"
    ;;

  stop)
    load_session_state
    if [[ "$STATE_PRESENT" != true ]]; then emit_status already-stopped; exit 0; fi
    [[ "$STATE_OWNED" == true ]] || { emit_status unowned; exit 1; }
    [[ "$STATE_PLATFORM_MATCH" == true ]] || { emit_status platform-mismatch; exit 1; }
    [[ "$STATE_REPO_MATCH" == true ]] || { emit_status repo-mismatch; exit 1; }
    [[ "$STATE_PANE_COUNT" -eq 1 ]] || { emit_status unexpected-pane-count; exit 1; }
    if [[ "$force" == true ]]; then
      "$TMUX_BIN" kill-session -t "$TMUX_SESSION_TARGET"
      STATE_PRESENT=false
      emit_status force-stopped
      exit 0
    fi
    [[ "$STATE_TUI" == true ]] || { emit_status runtime-tui-not-detected; exit 1; }
    [[ "$STATE_ACTIVITY" == idle ]] || { emit_status not-idle; exit 1; }
    "$TMUX_BIN" send-keys -t "$STATE_PANE_ID" -l "$ADAPTER_QUIT_TEXT"
    "$TMUX_BIN" send-keys -t "$STATE_PANE_ID" C-m
    for ((i=0; i<10; i++)); do
      sleep 1
      if ! session_exists; then STATE_PRESENT=false; emit_status stopped; exit 0; fi
    done
    load_session_state
    emit_status quit-pending
    exit 2
    ;;
esac
