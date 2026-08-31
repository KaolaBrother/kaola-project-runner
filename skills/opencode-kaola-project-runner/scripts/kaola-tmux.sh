#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
OWNER_KEY=KAOLA_PROJECT_RUNNER
PLATFORM_KEY=KAOLA_PROJECT_RUNNER_PLATFORM
REPO_KEY=KAOLA_PROJECT_RUNNER_REPO
RELAY_SOCKET_KEY=KAOLA_PROJECT_RUNNER_RELAY_SOCKET
RELAY_EPOCH_KEY=KAOLA_PROJECT_RUNNER_RELAY_EPOCH
OWNER_VALUE=1
LEGACY_OWNER_KEY=GROK_KAOLA_PROJECT_RUNNER
LEGACY_REPO_KEY=GROK_KAOLA_REPO
OBSERVATION_HELPER="$script_dir/kaola-observation.py"
RELAY="$script_dir/kaola-pane-relay.py"
RELAY_CLIENT="$script_dir/kaola-relay-client.py"
MODEL_POLICY_HELPER="$script_dir/kaola-model-policy.py"
MODEL_POLICY_KEY=KAOLA_PROJECT_RUNNER_MODEL_POLICY
export OBSERVATION_HELPER

usage() {
  cat <<'EOF'
Usage:
  kaola-tmux.sh PLATFORM preflight --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM start     --repo ABS_PATH --session NAME [--continue | --resume ID] [--model ID --effort LEVEL]
  kaola-tmux.sh PLATFORM observe   --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM status    --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM capture   --repo ABS_PATH --session NAME [--lines N]
  kaola-tmux.sh PLATFORM send      --repo ABS_PATH --session NAME [--if-snapshot ID] [--text TEXT]
  kaola-tmux.sh PLATFORM key       --repo ABS_PATH --session NAME [--if-snapshot ID] --key NAME
  kaola-tmux.sh PLATFORM answer    --repo ABS_PATH --session NAME [--decision-id ID] [--if-snapshot ID] --replace-editor [--text TEXT]
  kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME [--if-snapshot ID] [--force]
EOF
}

die() { printf 'kaola-tmux[%s]: %s\n' "${platform:-unknown}" "$*" >&2; exit 1; }
resolve_tool() { if [[ "$1" == */* ]]; then [[ -x "$1" ]] || return 1; printf '%s\n' "$1"; else command -v "$1"; fi; }
canonical_dir() { (cd "$1" 2>/dev/null && pwd -P); }
json_value() { local expression="$1"; JSON_INPUT="$(cat)" "$PYTHON_BIN" -c 'import json,os,sys; d=json.loads(os.environ["JSON_INPUT"]); v=eval(sys.argv[1], {"d":d}); print(json.dumps(v,separators=(",",":")) if isinstance(v,(dict,list,bool)) else ("" if v is None else str(v)))' "$expression"; }
emit_json() {
  "$PYTHON_BIN" - "$@" <<'PY'
import json,sys
d={}
for raw in sys.argv[1:]:
    kind,key,value=raw.split(":",2)
    d[key]=(value=="true") if kind=="b" else int(value) if kind=="n" else json.loads(value) if kind=="j" else value
print(json.dumps(d,ensure_ascii=False,sort_keys=True))
PY
}

platform="${1:-}"; [[ -n "$platform" ]] || { usage; exit 2; }; shift
case "$platform" in grok|claude-code|opencode|kimi-cli|cursor-cli) ;; *) die "unknown platform: $platform" ;; esac
adapter_file="$script_dir/adapters/$platform.sh"; [[ -f "$adapter_file" ]] || die "adapter not installed"
[[ -f "$OBSERVATION_HELPER" && -f "$RELAY" && -f "$RELAY_CLIENT" && -f "$MODEL_POLICY_HELPER" ]] || die "relay control plane is incomplete"
# shellcheck source=/dev/null
source "$adapter_file"
[[ "${ADAPTER_ID:-}" == "$platform" ]] || die "adapter identity mismatch"
[[ "${ADAPTER_ANSWER_MODE:-}" =~ ^(unsupported|claude-clear-v1)$ ]] || die "adapter answer mode missing"

command_name="${1:-}"; [[ -n "$command_name" ]] || { usage; exit 2; }; shift
case "$command_name" in preflight|start|observe|status|capture|send|key|answer|stop) ;; *) die "unknown command: $command_name" ;; esac
repo="" session="" resume_id="" continue_mode=false force=false lines=120 text_value="" text_given=false
if_snapshot="" require_empty_editor=false decision_id="" replace_editor=false model="" effort="" permission_mode=auto
model_given=false effort_given=false permission_mode_given=false key_name=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) repo="$2"; shift 2 ;; --session) session="$2"; shift 2 ;; --resume) resume_id="$2"; shift 2 ;;
    --continue) continue_mode=true; shift ;; --force) force=true; shift ;; --lines) lines="$2"; shift 2 ;;
    --text) text_value="$2"; text_given=true; shift 2 ;; --if-snapshot) if_snapshot="$2"; shift 2 ;;
    --require-empty-editor) require_empty_editor=true; shift ;; --decision-id) decision_id="$2"; shift 2 ;;
    --replace-editor) replace_editor=true; shift ;; --model) model="$2"; model_given=true; shift 2 ;;
    --effort) effort="$2"; effort_given=true; shift 2 ;; --permission-mode) permission_mode="$2"; permission_mode_given=true; shift 2 ;;
    --key) key_name="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
done

TMUX_BIN="$(resolve_tool "${TMUX_BIN:-tmux}")" || die "tmux executable not found"
PYTHON_BIN="$(resolve_tool "${PYTHON_BIN:-python3}")" || die "python3 executable not found"
PS_BIN="$(resolve_tool "${PS_BIN:-ps}")" || die "ps executable not found"
runtime_override="$(printenv "$ADAPTER_BIN_ENV" 2>/dev/null || true)"
RUNTIME_BIN="$(resolve_tool "${runtime_override:-$ADAPTER_DEFAULT_BIN}")" || die "$ADAPTER_DISPLAY_NAME executable not found (override with $ADAPTER_BIN_ENV)"
RUNTIME_BIN_REAL="$("$PYTHON_BIN" -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$RUNTIME_BIN")"
[[ "$repo" == /* && -d "$repo" ]] || die "--repo must be an existing absolute path"
PUBLIC_REPO="$repo"
repo="$(canonical_dir "$repo")"; git_root="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || die "not a Git repository: $repo"
git_root="$(canonical_dir "$git_root")"; [[ "$git_root" == "$repo" ]] || die "--repo must name the Git root: $git_root"
[[ "$session" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$ ]] || die "invalid session name"
TMUX_SESSION_TARGET="=$session"
if [[ "$platform" != claude-code && "$permission_mode_given" == true ]]; then die "permission mode is Claude-only"; fi
if [[ "$command_name" != start && ( "$model_given" == true || "$effort_given" == true || "$permission_mode_given" == true ) ]]; then die "model, effort, and permission mode are start-only"; fi
MODEL_VALUE="$model" "$PYTHON_BIN" - <<'PY' || die "model contains unsupported terminal controls"
import os
value = os.environ.get("MODEL_VALUE", "")
raise SystemExit(1 if any(ord(ch) < 32 or ord(ch) == 127 for ch in value) else 0)
PY
if [[ -n "$effort" ]]; then case "$effort" in low|medium|high|xhigh|max) ;; *) die "unsupported effort" ;; esac; fi
case "$permission_mode" in acceptEdits|auto|bypassPermissions|manual|dontAsk|plan) ;; *) die "unsupported Claude permission mode" ;; esac
if [[ -n "$key_name" && "$command_name" != key ]]; then die "--key is only valid with key"; fi
if [[ "$command_name" == key ]]; then
  case "$key_name" in up|down|left|right|enter|escape|tab|backtab|space) ;; *) die "--key must be one of up,down,left,right,enter,escape,tab,backtab,space" ;; esac
fi

session_exists() { "$TMUX_BIN" has-session -t "$TMUX_SESSION_TARGET" 2>/dev/null; }
tmux_env_value() { local line; line="$("$TMUX_BIN" show-environment -t "$TMUX_SESSION_TARGET" "$1" 2>/dev/null || true)"; [[ "$line" == "$1="* ]] || return 1; printf '%s\n' "${line#*=}"; }
path_leads_command() {
  local command="$1" expected="$2" after_argv0
  [[ -n "$command" && -n "$expected" ]] || return 1
  [[ "$command" == "$expected" || "$command" == "$expected "* ]] && return 0
  [[ "$command" == *" "* ]] || return 1
  after_argv0="${command#* }"
  while [[ "$after_argv0" == " "* ]]; do after_argv0="${after_argv0# }"; done
  [[ "$after_argv0" == "$expected" || "$after_argv0" == "$expected "* ]]
}
runtime_process_matches() { path_leads_command "$1" "$RUNTIME_BIN" && return 0; [[ "$RUNTIME_BIN_REAL" != "$RUNTIME_BIN" ]] && path_leads_command "$1" "$RUNTIME_BIN_REAL" && return 0; type adapter_process_matches >/dev/null 2>&1 && adapter_process_matches "$1" "$2"; }

MODEL_POLICY_JSON="" RESOLVED_MODEL_ID="" RESOLVED_MODEL_EFFORT="" MODEL_HAS_EFFORT=false MODEL_HAS_VARIANT=false
resolve_model_policy() {
  local source requested candidate chosen_effort
  if [[ "$model_given" == true ]]; then source=user requested="$model" candidate="$model"; else source=runner-default requested="$ADAPTER_DEFAULT_MODEL_NAME" candidate="$ADAPTER_DEFAULT_MODEL_ID"; fi
  if [[ "$effort_given" == true ]]; then chosen_effort="$effort"; else chosen_effort="$ADAPTER_DEFAULT_MODEL_EFFORT"; fi
  MODEL_POLICY_JSON="$("$PYTHON_BIN" "$MODEL_POLICY_HELPER" resolve --platform "$platform" --runtime-bin "$RUNTIME_BIN" --repo "$repo" --source "$source" --requested-name "$requested" --candidate-id "$candidate" --effort "$chosen_effort" --fast "$ADAPTER_DEFAULT_MODEL_FAST")"
  RESOLVED_MODEL_ID="$(printf '%s' "$MODEL_POLICY_JSON" | json_value 'd.get("resolved_runtime_model_id")')"
  RESOLVED_MODEL_EFFORT="$(printf '%s' "$MODEL_POLICY_JSON" | json_value 'd.get("resolved_parameters",{}).get("effort")')"
  [[ "$(printf '%s' "$MODEL_POLICY_JSON" | json_value 'd.get("model_evidence_provenance",{}).get("resolution",{}).get("supported_options",[])')" == *'--effort'* ]] && MODEL_HAS_EFFORT=true
  [[ "$(printf '%s' "$MODEL_POLICY_JSON" | json_value 'd.get("model_evidence_provenance",{}).get("resolution",{}).get("supported_options",[])')" == *'--variant'* ]] && MODEL_HAS_VARIANT=true
  [[ -n "$RESOLVED_MODEL_ID" ]]
}

load_session_identity() {
  STATE_PRESENT=false STATE_OWNED=false STATE_PLATFORM_MATCH=false STATE_REPO_MATCH=false STATE_TUI=false
  STATE_LEGACY_OWNERSHIP=false
  STATE_PANE_COUNT=0 STATE_PANE_ID="" STATE_PANE_PATH="" STATE_PANE_COMMAND="" STATE_PANE_TITLE="" STATE_PANE_DEAD="" STATE_PANE_PID="" STATE_PANE_PROCESS=""
  STATE_RELAY_PROCESS_MATCH=false STATE_PROCESS_MATCH=false STATE_PANE_INPUT_OFF=false STATE_PANE_WIDTH="" STATE_PANE_HEIGHT="" STATE_CURSOR_X="" STATE_CURSOR_Y=""
  STATE_CURSOR_FLAG=false STATE_ALTERNATE_ON=false STATE_HISTORY_SIZE="" STATE_HISTORY_BYTES="" STATE_CAPTURE_HISTORY="" STATE_ACTIVITY=unknown STATE_RUNTIME_SESSION_ID=""
  STATE_RELAY_SOCKET="" STATE_RELAY_EPOCH="" STATE_MODEL_POLICY_JSON=""; session_exists || return 0; STATE_PRESENT=true
  local panes owner platform_marker repo_marker value pane_real legacy_owner legacy_repo
  panes="$("$TMUX_BIN" list-panes -t "$TMUX_SESSION_TARGET" -F '#{pane_id}')"; STATE_PANE_COUNT="$(printf '%s\n' "$panes" | awk 'NF{n++}END{print n+0}')"
  if [[ "$STATE_PANE_COUNT" -eq 1 ]]; then
    STATE_PANE_ID="$(printf '%s\n' "$panes" | awk 'NF{print;exit}')"
    read -r STATE_PANE_PATH STATE_PANE_COMMAND STATE_PANE_DEAD STATE_PANE_PID STATE_PANE_WIDTH STATE_PANE_HEIGHT STATE_CURSOR_X STATE_CURSOR_Y STATE_HISTORY_SIZE STATE_HISTORY_BYTES <<EOF
$("$TMUX_BIN" display-message -p -t "$STATE_PANE_ID" '#{pane_current_path} #{pane_current_command} #{pane_dead} #{pane_pid} #{pane_width} #{pane_height} #{cursor_x} #{cursor_y} #{history_size} #{history_bytes}')
EOF
    STATE_PANE_TITLE="$("$TMUX_BIN" display-message -p -t "$STATE_PANE_ID" '#{pane_title}')"; value="$("$TMUX_BIN" display-message -p -t "$STATE_PANE_ID" '#{pane_input_off}')"; [[ "$value" == 1 ]] && STATE_PANE_INPUT_OFF=true
    value="$("$TMUX_BIN" display-message -p -t "$STATE_PANE_ID" '#{cursor_flag}')"; [[ "$value" == 1 ]] && STATE_CURSOR_FLAG=true; value="$("$TMUX_BIN" display-message -p -t "$STATE_PANE_ID" '#{alternate_on}')"; [[ "$value" == 1 ]] && STATE_ALTERNATE_ON=true
    STATE_CAPTURE_HISTORY="$("$TMUX_BIN" capture-pane -p -t "$STATE_PANE_ID" -S -100 2>/dev/null || true)"; STATE_PANE_PROCESS="$("$PS_BIN" -ww -p "$STATE_PANE_PID" -o command= 2>/dev/null || true)"
  fi
  owner="$(tmux_env_value "$OWNER_KEY" || true)"; platform_marker="$(tmux_env_value "$PLATFORM_KEY" || true)"; repo_marker="$(tmux_env_value "$REPO_KEY" || true)"
  if [[ "$owner" == 1 ]]; then STATE_OWNED=true; [[ "$platform_marker" == "$platform" ]] && STATE_PLATFORM_MATCH=true
  elif [[ "$platform" == grok ]]; then legacy_owner="$(tmux_env_value "$LEGACY_OWNER_KEY" || true)"; legacy_repo="$(tmux_env_value "$LEGACY_REPO_KEY" || true)"; [[ "$legacy_owner" == 1 && "$legacy_repo" == "$repo" ]] && STATE_OWNED=true STATE_PLATFORM_MATCH=true STATE_LEGACY_OWNERSHIP=true repo_marker="$legacy_repo"; fi
  if [[ -d "$STATE_PANE_PATH" ]]; then pane_real="$(canonical_dir "$STATE_PANE_PATH" || true)"; [[ "$pane_real" == "$repo" && "$repo_marker" == "$repo" ]] && STATE_REPO_MATCH=true; fi
  STATE_RELAY_SOCKET="$(tmux_env_value "$RELAY_SOCKET_KEY" || true)"; STATE_RELAY_EPOCH="$(tmux_env_value "$RELAY_EPOCH_KEY" || true)"
  STATE_MODEL_POLICY_JSON="$(tmux_env_value "$MODEL_POLICY_KEY" || true)"
  if [[ -n "$STATE_RELAY_SOCKET" && -n "$STATE_RELAY_EPOCH" ]]; then path_leads_command "$STATE_PANE_PROCESS" "$RELAY" && STATE_RELAY_PROCESS_MATCH=true; if [[ -n "${CURRENT_RELAY_JSON:-}" ]]; then STATE_PROCESS_MATCH="$(printf '%s' "$CURRENT_RELAY_JSON" | json_value 'd.get("child_process_match",False)')"; fi
  else runtime_process_matches "$STATE_PANE_PROCESS" "$STATE_PANE_COMMAND" && STATE_PROCESS_MATCH=true; fi
  if [[ "$STATE_PROCESS_MATCH" == true ]] && adapter_detect_tui "$STATE_PANE_TITLE" "$STATE_PANE_COMMAND" "$STATE_CAPTURE_HISTORY"; then STATE_TUI=true; STATE_ACTIVITY="$(adapter_activity_hint "$STATE_CAPTURE_HISTORY")"; STATE_RUNTIME_SESSION_ID="$(adapter_extract_session_id "$STATE_CAPTURE_HISTORY" || true)"; fi
}

RELAY_DIR="" RELAY_CLIENT_PID="" RELAY_REPLY="" RELAY_CHANNEL_OPEN=false
close_relay_channel() { if [[ "$RELAY_CHANNEL_OPEN" == true ]]; then { exec 8>&-; } 2>/dev/null || true; { exec 9<&-; } 2>/dev/null || true; RELAY_CHANNEL_OPEN=false; fi; if [[ -n "$RELAY_CLIENT_PID" ]]; then wait "$RELAY_CLIENT_PID" 2>/dev/null || true; RELAY_CLIENT_PID=""; fi; if [[ -n "$RELAY_DIR" && -d "$RELAY_DIR" ]]; then rm -rf "$RELAY_DIR"; RELAY_DIR=""; fi; }
open_relay_channel() { RELAY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/kpr-channel.XXXXXX")"; mkfifo "$RELAY_DIR/request" "$RELAY_DIR/reply"; "$PYTHON_BIN" "$RELAY_CLIENT" --serve --socket "$1" --epoch "$2" --child-fingerprint "$3" --relay-pid "$4" <"$RELAY_DIR/request" >"$RELAY_DIR/reply" 2>"$RELAY_DIR/error" & RELAY_CLIENT_PID=$!; exec 8>"$RELAY_DIR/request"; exec 9<"$RELAY_DIR/reply"; RELAY_CHANNEL_OPEN=true; }
relay_line() { printf '%s\n' "$1" >&8; IFS= read -r RELAY_REPLY <&9 || { [[ -f "$RELAY_DIR/error" ]] && cat "$RELAY_DIR/error" >&2; return 1; }; }
debug_relay_reply() {
  [[ "${KAOLA_RUNNER_DEBUG:-0}" == 1 ]] || return 0
  local result detail
  result="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("result")' 2>/dev/null || true)"
  detail="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("detail")' 2>/dev/null || true)"
  printf 'kaola-tmux[%s]: relay result=%s detail=%s\n' "$platform" "${result:-unavailable}" "${detail:-none}" >&2
}

bootstrap_relay() {
  "$PYTHON_BIN" - "$STATE_RELAY_SOCKET" "$STATE_RELAY_EPOCH" "$script_dir/kaola-relay-protocol.py" <<'PY'
import importlib.util,json,secrets,socket,sys
spec=importlib.util.spec_from_file_location("kpr_protocol_boot",sys.argv[3]); p=importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.settimeout(5.0); s.connect(sys.argv[1]); h={"protocol_version":1,"request_id":secrets.token_hex(16),"relay_epoch":sys.argv[2],"operation":"bootstrap-hello","expected_child_fingerprint":""}; p.send_frame(s,h); r,_=p.recv_frame(s); s.close(); print(json.dumps(r,sort_keys=True))
PY
}

build_sample() {
  local relay_json="$1" barrier_json="$2" result="${3:-observed}" frame cursor_frame cursor_logical_y process_json adapter_json child_pid ps_text temporary pane_facts_json model_json
  if [[ -n "$relay_json" && "$relay_json" != null ]]; then
    CURRENT_RELAY_JSON="$relay_json"
  else
    CURRENT_RELAY_JSON=""
  fi
  load_session_identity; frame=""; cursor_frame=""; cursor_logical_y=0
  if [[ "$STATE_PRESENT" == true && -n "$STATE_PANE_ID" ]]; then
    frame="$("$TMUX_BIN" capture-pane -p -N -J -t "$STATE_PANE_ID" 2>/dev/null || true)"
    cursor_frame="$("$TMUX_BIN" capture-pane -p -N -J -S 0 -E "${STATE_CURSOR_Y:-0}" -t "$STATE_PANE_ID" 2>/dev/null || true)"
    cursor_logical_y="$(CURSOR_FRAME="$cursor_frame" "$PYTHON_BIN" -c 'import os; print(max(0,len(os.environ["CURSOR_FRAME"].splitlines())-1))')"
  fi
  pane_facts_json="$(emit_json "n:cursor_x:${STATE_CURSOR_X:-0}" "n:cursor_y:${STATE_CURSOR_Y:-0}" "n:cursor_logical_y:$cursor_logical_y")"
  if [[ "$STATE_TUI" == true ]]; then adapter_json="$(adapter_observe_frame "$frame" "$pane_facts_json")"; else adapter_json='{"editor_state":"unknown","editor_fingerprint":null,"visible_shell_count":null,"visible_agent_count":null,"native_approval":{"state":"unknown","kind":null,"fingerprint":null},"structured_decision_marker":null,"activity_hint":"unknown"}'; fi
  process_json=null; child_pid=""
  if [[ -n "$CURRENT_RELAY_JSON" ]]; then
    child_pid="$(printf '%s' "$CURRENT_RELAY_JSON" | json_value 'd.get("child_pid")' 2>/dev/null || true)"
  fi
  [[ "$child_pid" =~ ^[0-9]+$ ]] || child_pid="$STATE_PANE_PID"
  if [[ -n "$child_pid" ]]; then ps_text="$("$PS_BIN" -axo pid=,ppid=,state=,comm=,command= 2>/dev/null || true)"; process_json="$(printf '%s\n' "$ps_text" | "$PYTHON_BIN" "$OBSERVATION_HELPER" process-tree "$child_pid" 2>/dev/null || printf null)"; fi
  temporary="$(mktemp "${TMPDIR:-/tmp}/kpr-frame.XXXXXX")"; printf '%s' "$frame" >"$temporary"
  if [[ -n "$STATE_MODEL_POLICY_JSON" ]]; then
    model_json="$("$PYTHON_BIN" "$MODEL_POLICY_HELPER" verify --platform "$platform" --policy-json "$STATE_MODEL_POLICY_JSON" --frame-file "$temporary")"
    [[ "$STATE_PRESENT" == true ]] && "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$MODEL_POLICY_KEY" "$model_json"
  else
    model_json='{}'
  fi
  KPR_FRAME_FILE="$temporary" KPR_PRESENT="$STATE_PRESENT" KPR_OWNED="$STATE_OWNED" KPR_PLATFORM_MATCH="$STATE_PLATFORM_MATCH" KPR_REPO_MATCH="$STATE_REPO_MATCH" KPR_PANE_COUNT="$STATE_PANE_COUNT" KPR_PANE_ID="$STATE_PANE_ID" KPR_PANE_DEAD="${STATE_PANE_DEAD:-0}" KPR_PANE_INPUT_OFF=false KPR_PANE_PATH="$STATE_PANE_PATH" KPR_PANE_PID="$STATE_PANE_PID" KPR_PANE_COMMAND="$STATE_PANE_COMMAND" KPR_PANE_TITLE="$STATE_PANE_TITLE" KPR_PANE_PROCESS="$STATE_PANE_PROCESS" KPR_RELAY_PROCESS_MATCH="$STATE_RELAY_PROCESS_MATCH" KPR_PROCESS_MATCH="$STATE_PROCESS_MATCH" KPR_TUI="$STATE_TUI" KPR_PANE_WIDTH="$STATE_PANE_WIDTH" KPR_PANE_HEIGHT="$STATE_PANE_HEIGHT" KPR_CURSOR_X="$STATE_CURSOR_X" KPR_CURSOR_Y="$STATE_CURSOR_Y" KPR_CURSOR_FLAG="$STATE_CURSOR_FLAG" KPR_ALTERNATE_ON="$STATE_ALTERNATE_ON" KPR_HISTORY_SIZE="$STATE_HISTORY_SIZE" KPR_HISTORY_BYTES="$STATE_HISTORY_BYTES" KPR_ADAPTER_JSON="$adapter_json" KPR_PROCESS_JSON="$process_json" KPR_RELAY_JSON="$relay_json" KPR_BARRIER_JSON="$barrier_json" KPR_RESULT="$result" KPR_PLATFORM="$platform" KPR_RUNTIME="$ADAPTER_DISPLAY_NAME" KPR_SESSION="$session" KPR_REPO="$repo" KPR_RUNTIME_SESSION_ID="$STATE_RUNTIME_SESSION_ID" KPR_MODEL_JSON="$model_json" "$PYTHON_BIN" "$OBSERVATION_HELPER" build
  rm -f "$temporary"
}

observe_managed() {
  local bootstrap child_fingerprint relay_pid state_reply relay_json barrier_json
  load_session_identity; if [[ -z "$STATE_RELAY_SOCKET" || -z "$STATE_RELAY_EPOCH" ]]; then build_sample null null observed; return; fi
  bootstrap="$(bootstrap_relay)" || { build_sample null null unstable; return; }; child_fingerprint="$(printf '%s' "$bootstrap" | json_value 'd["child_start_fingerprint"]')"; relay_pid="$(printf '%s' "$bootstrap" | json_value 'd["pid"]')"; [[ "$relay_pid" == "$STATE_PANE_PID" ]] || { build_sample null null unstable; return; }
  open_relay_channel "$STATE_RELAY_SOCKET" "$STATE_RELAY_EPOCH" "$child_fingerprint" "$relay_pid"
  relay_line '{"operation":"state"}' || { close_relay_channel; build_sample null null unstable; return; }
  state_reply="$RELAY_REPLY"
  close_relay_channel
  [[ "$(printf '%s' "$state_reply" | json_value 'd.get("result")' 2>/dev/null || true)" == state ]] || { build_sample null null unstable; return; }
  relay_json="$(printf '%s' "$state_reply" | json_value 'd["relay"]')"
  barrier_json="$(printf '%s' "$state_reply" | json_value 'd.get("barrier")')"
  [[ -n "$barrier_json" ]] || barrier_json=null
  build_sample "$relay_json" "$barrier_json"
}

emit_status() { local observation status; observation="$(observe_managed)"; status="$(printf '%s' "$observation" | "$PYTHON_BIN" "$OBSERVATION_HELPER" status-view)"; load_session_identity; STATUS_JSON="$status" STATUS_RESULT="$1" STATUS_LEGACY="$STATE_LEGACY_OWNERSHIP" "$PYTHON_BIN" -c 'import json,os; d=json.loads(os.environ["STATUS_JSON"]); d["result"]=os.environ["STATUS_RESULT"]; d.update({"legacy_ownership":os.environ["STATUS_LEGACY"]=="true"} if d.get("platform")=="grok" else {}); print(json.dumps(d,ensure_ascii=False,sort_keys=True))'; }
emit_refusal() { emit_json "n:schema_version:2" "s:result:$1" "s:action:${2:-$command_name}" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot" "b:mutation_performed:false"; }
emit_transport_result() {
  local mutation_field
  case "$3" in
    true|false) mutation_field="b:mutation_performed:$3" ;;
    *) mutation_field="j:mutation_performed:null" ;;
  esac
  emit_json "n:schema_version:2" "s:result:$1" "s:action:$2" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot" "$mutation_field"
}
emit_transport_refusal() {
  emit_json "n:schema_version:2" "s:result:refused" "s:reason:$1" "s:action:$2" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot" "b:mutation_performed:false"
}
emit_existing_session_not_reusable() {
  local relay_endpoint_present=false
  [[ -n "$STATE_RELAY_SOCKET" && -n "$STATE_RELAY_EPOCH" ]] && relay_endpoint_present=true
  emit_json "n:schema_version:2" "s:result:existing-session-not-reusable" "s:action:start" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "b:mutation_performed:false" "b:owned:$STATE_OWNED" "b:platform_match:$STATE_PLATFORM_MATCH" "b:repo_match:$STATE_REPO_MATCH" "n:pane_count:$STATE_PANE_COUNT" "b:relay_process_match:$STATE_RELAY_PROCESS_MATCH" "b:relay_endpoint_present:$relay_endpoint_present"
}
load_payload() { if [[ "$text_given" == true ]]; then PAYLOAD="$text_value"; else [[ ! -t 0 ]] || die "$command_name needs --text or stdin"; PAYLOAD="$(</dev/stdin)"; fi; [[ -n "$PAYLOAD" ]] || die "prompt must not be empty"; }
validate_payload_controls() {
  PAYLOAD_VALUE="$PAYLOAD" "$PYTHON_BIN" - <<'PY'
import os

payload = os.environ["PAYLOAD_VALUE"]
for character in payload:
    codepoint = ord(character)
    if codepoint in (0x09, 0x0A):
        continue
    if (
        codepoint < 0x20
        or codepoint == 0x7F
        or 0x80 <= codepoint <= 0x9F
        or 0xDC80 <= codepoint <= 0xDCFF
    ):
        raise SystemExit(1)
PY
}
payload_needs_bracketed_paste() { [[ "$PAYLOAD" == *$'\n'* || "$PAYLOAD" == *$'\t'* ]]; }
payload_hex() { printf '%s' "$PAYLOAD" | "$PYTHON_BIN" -c 'import sys; print(sys.stdin.buffer.read().hex())'; }
fingerprint_payload() { printf '%s' "$PAYLOAD" | "$PYTHON_BIN" -c 'import hashlib,sys; print("sha256:"+hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'; }
cleanup_terminal_socket() {
  "$PYTHON_BIN" - "$1" "$2" <<'PY'
import os, pathlib, socket, stat, sys, tempfile
path = pathlib.Path(sys.argv[1])
epoch = sys.argv[2]
expected = pathlib.Path(tempfile.gettempdir()) / f"kpr-{os.getuid()}" / f"{epoch}.sock"
if path != expected or not epoch:
    raise SystemExit(1)
try:
    info = path.lstat()
except FileNotFoundError:
    raise SystemExit(0)
if path.is_symlink() or not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
    raise SystemExit(1)
path.unlink()
PY
}
DIRECT_CHILD_FP="" DIRECT_RELAY=""
open_transport_channel() {
  local bootstrap relay_pid state_reply
  load_session_identity
  [[ "$STATE_PRESENT" == true ]] || { REFUSAL=absent; return 1; }
  [[ "$STATE_OWNED" == true ]] || { REFUSAL=unowned; return 1; }
  [[ "$STATE_PLATFORM_MATCH" == true ]] || { REFUSAL=platform-mismatch; return 1; }
  [[ "$STATE_PANE_COUNT" -eq 1 ]] || { REFUSAL=unexpected-pane-count; return 1; }
  [[ "$STATE_REPO_MATCH" == true ]] || { REFUSAL=repo-mismatch; return 1; }
  [[ "$STATE_RELAY_PROCESS_MATCH" == true && -n "$STATE_RELAY_SOCKET" && -n "$STATE_RELAY_EPOCH" ]] || { REFUSAL=relay-required; return 1; }
  bootstrap="$(bootstrap_relay)" || { REFUSAL=relay-attestation-failed; return 1; }
  DIRECT_CHILD_FP="$(printf '%s' "$bootstrap" | json_value 'd.get("child_start_fingerprint")')"
  relay_pid="$(printf '%s' "$bootstrap" | json_value 'd.get("pid")')"
  [[ "$relay_pid" == "$STATE_PANE_PID" && "$DIRECT_CHILD_FP" =~ ^sha256:[0-9a-f]{64}$ ]] || { REFUSAL=relay-attestation-failed; return 1; }
  open_relay_channel "$STATE_RELAY_SOCKET" "$STATE_RELAY_EPOCH" "$DIRECT_CHILD_FP" "$relay_pid"
  relay_line '{"operation":"state"}' || { close_relay_channel; REFUSAL=relay-unavailable; return 1; }
  state_reply="$RELAY_REPLY"
  [[ "$(printf '%s' "$state_reply" | json_value 'd.get("result")' 2>/dev/null || true)" == state ]] || { close_relay_channel; REFUSAL=relay-unavailable; return 1; }
  [[ "$(printf '%s' "$state_reply" | json_value 'd.get("direct_input",False)' 2>/dev/null || true)" == true ]] || { close_relay_channel; REFUSAL=relay-upgrade-required; return 1; }
  DIRECT_RELAY="$(printf '%s' "$state_reply" | json_value 'd.get("relay")')"
  [[ "$(printf '%s' "$DIRECT_RELAY" | json_value 'd.get("managed",False)' 2>/dev/null || true)" == true ]] || { close_relay_channel; REFUSAL=relay-attestation-failed; return 1; }
  [[ "$(printf '%s' "$DIRECT_RELAY" | json_value 'd.get("child_process_match",False)' 2>/dev/null || true)" == true ]] || { close_relay_channel; REFUSAL=process-mismatch; return 1; }
}
trap 'close_relay_channel' EXIT HUP INT TERM

# Force stop is intentionally small: prove the exact owned tmux identity,
# end that one session, and report what remains. The relay owns its child
# lifecycle; the runner does not classify or sweep unrelated processes.
force_stop_exact() {
  local relay_pid terminal_socket terminal_epoch session_present relay_running socket_present result
  load_session_identity
  if [[ "$STATE_PRESENT" != true ]]; then emit_status already-stopped; return 0; fi
  if [[ "$STATE_OWNED" != true ]]; then emit_refusal unowned force-stop; return 1; fi
  if [[ "$STATE_PLATFORM_MATCH" != true ]]; then emit_refusal platform-mismatch force-stop; return 1; fi
  if [[ "$STATE_PANE_COUNT" -ne 1 ]]; then emit_refusal unexpected-pane-count force-stop; return 1; fi
  if [[ "$STATE_REPO_MATCH" != true ]]; then emit_refusal repo-mismatch force-stop; return 1; fi
  if [[ "$STATE_RELAY_PROCESS_MATCH" != true || ! "$STATE_PANE_PID" =~ ^[0-9]+$ ]]; then
    emit_refusal relay-attestation-failed force-stop
    return 1
  fi

  relay_pid="$STATE_PANE_PID"
  terminal_socket="$STATE_RELAY_SOCKET"
  terminal_epoch="$STATE_RELAY_EPOCH"
  "$TMUX_BIN" kill-session -t "$TMUX_SESSION_TARGET" >/dev/null 2>&1 || true

  for _ in {1..20}; do
    if ! session_exists; then
      if ! "$PS_BIN" -p "$relay_pid" -o pid= 2>/dev/null | awk 'NF{found=1} END{exit !found}'; then
        break
      fi
    fi
    sleep 0.05
  done

  session_present=false
  session_exists && session_present=true
  relay_running=false
  "$PS_BIN" -p "$relay_pid" -o pid= 2>/dev/null | awk 'NF{found=1} END{exit !found}' && relay_running=true

  if [[ "$session_present" == false && "$relay_running" == false && -n "$terminal_socket" && -n "$terminal_epoch" ]]; then
    cleanup_terminal_socket "$terminal_socket" "$terminal_epoch" >/dev/null 2>&1 || true
  fi
  socket_present=false
  [[ -n "$terminal_socket" && -e "$terminal_socket" ]] && socket_present=true

  result=stopped
  if [[ "$session_present" == true || "$relay_running" == true || "$socket_present" == true ]]; then
    result=termination-uncertain
  fi
  emit_json \
    "n:schema_version:2" \
    "s:result:$result" \
    "s:action:force-stop" \
    "s:platform:$platform" \
    "s:session:$session" \
    "s:repo:$repo" \
    "s:based_on_snapshot:$if_snapshot" \
    "b:mutation_performed:true" \
    "j:final_state:{\"session_present\":$session_present,\"relay_running\":$relay_running,\"child_running\":null,\"child_group_running\":null,\"socket_present\":$socket_present,\"pane_input_off\":null}" \
    "s:escaped_descendants:unknown"
  [[ "$result" == stopped ]]
}

case "$command_name" in
  preflight)
    adapter_preflight; resolve_model_policy || true
    base_json="$(emit_json "s:result:ready" "s:platform:$platform" "s:runtime:$ADAPTER_DISPLAY_NAME" "s:runtime_version:$PREFLIGHT_VERSION" "s:runtime_binary:$RUNTIME_BIN" "s:repo:$repo" "s:session:$session" "b:workflow_next:$PREFLIGHT_WORKFLOW_NEXT" "b:kaola_workflow_finalize:$PREFLIGHT_FINALIZE" "s:recurring_execution:$ADAPTER_RECURRING_EXECUTION" "s:project_materialization:$PREFLIGHT_PROJECT_MATERIALIZATION" "s:detail:$PREFLIGHT_DETAIL")"
    BASE_JSON="$base_json" POLICY_JSON="$MODEL_POLICY_JSON" GROK_VERSION="$PREFLIGHT_VERSION" GROK_ROOT="${PREFLIGHT_PROJECT_ROOT_JSON:-null}" "$PYTHON_BIN" - "$platform" <<'PY'
import json,os,sys
d=json.loads(os.environ["BASE_JSON"]); d.update(json.loads(os.environ["POLICY_JSON"]))
if sys.argv[1] == "grok": d.update(grok_version=os.environ["GROK_VERSION"], project_root=json.loads(os.environ["GROK_ROOT"]))
print(json.dumps(d,ensure_ascii=False,sort_keys=True))
PY
    ;;
  observe) observe_managed ;;
  status) load_session_identity; if [[ "$STATE_PRESENT" == true ]]; then emit_status present; else emit_status absent; fi ;;
  capture) [[ "$lines" =~ ^[1-9][0-9]*$ && "$lines" -le 5000 ]] || die "--lines must be 1..5000"; load_session_identity; [[ "$STATE_PRESENT" == true && "$STATE_OWNED" == true && "$STATE_PLATFORM_MATCH" == true && "$STATE_REPO_MATCH" == true && "$STATE_PANE_COUNT" -eq 1 && -n "$STATE_PANE_ID" ]] || { emit_refusal identity-mismatch capture; exit 1; }; "$TMUX_BIN" capture-pane -p -t "$STATE_PANE_ID" -S "-$lines" ;;
  start)
    [[ -z "$resume_id" || "$continue_mode" == false ]] || die "--resume and --continue are mutually exclusive"
    adapter_preflight
    # Catalog probes are evidence only. The adapter always receives the
    # declared exact model literal from resolve_model_policy.
    resolve_model_policy || true
    load_session_identity
    if [[ "$STATE_PRESENT" == true ]]; then
      if [[ "$STATE_OWNED" == true && "$STATE_PLATFORM_MATCH" == true && "$STATE_REPO_MATCH" == true && "$STATE_PANE_COUNT" -eq 1 && "$STATE_RELAY_PROCESS_MATCH" == true && -n "$STATE_RELAY_SOCKET" && -n "$STATE_RELAY_EPOCH" ]]; then
        existing_bootstrap="$(bootstrap_relay 2>/dev/null || true)"
        existing_relay_pid="$(printf '%s' "$existing_bootstrap" | json_value 'd.get("pid")' 2>/dev/null || true)"
        existing_child_fp="$(printf '%s' "$existing_bootstrap" | json_value 'd.get("child_start_fingerprint")' 2>/dev/null || true)"
        if [[ "$existing_relay_pid" == "$STATE_PANE_PID" && "$existing_child_fp" =~ ^sha256:[0-9a-f]{64}$ ]]; then
          emit_status already-running
          exit 0
        fi
      fi
      # A present endpoint that cannot complete same-epoch bootstrap is not a
      # reusable live session. Leave it intact; explicit --force owns recovery.
      emit_existing_session_not_reusable
      exit 1
    fi
    adapter_prepare_model_environment
    session_env_args=(); while IFS='=' read -r name value; do case "$name" in CLAUDE_*|GROK_*|OPENCODE_*|KIMI_*|CURSOR_*|FAKE_*) session_env_args+=(-e "$name=$value") ;; esac; done < <(env)
    set +u
    for value in "${ADAPTER_MODEL_ENV[@]}"; do session_env_args+=(-e "$value"); done
    set -u
    if (( ${#session_env_args[@]} > 0 )); then
      "$TMUX_BIN" new-session -d -s "$session" -c "$repo" "${session_env_args[@]}" || { emit_status existing-session-not-reusable; exit 1; }
    else
      "$TMUX_BIN" new-session -d -s "$session" -c "$repo" || { emit_status existing-session-not-reusable; exit 1; }
    fi
    "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$OWNER_KEY" 1; "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$PLATFORM_KEY" "$platform"; "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$REPO_KEY" "$repo"; "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$MODEL_POLICY_KEY" "$MODEL_POLICY_JSON"; if [[ "$platform" == grok ]]; then "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$LEGACY_OWNER_KEY" 1; "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$LEGACY_REPO_KEY" "$repo"; fi
    load_session_identity; adapter_build_launch "$repo" "$resume_id" "$continue_mode"; launch=exec; for argument in "$PYTHON_BIN" "$RELAY" --tmux-bin "$TMUX_BIN" --session "$session" --pane-id "$STATE_PANE_ID" --repo "$repo" --runtime-path "$RUNTIME_BIN" --exact-process-title "${ADAPTER_CHILD_PROCESS_TITLE_EXACT:-}" -- ${ADAPTER_LAUNCH_ARGS[@]+"${ADAPTER_LAUNCH_ARGS[@]}"}; do printf -v quoted '%q' "$argument"; launch+=" $quoted"; done; "$TMUX_BIN" send-keys -t "$STATE_PANE_ID" -l "$launch"; "$TMUX_BIN" send-keys -t "$STATE_PANE_ID" C-m
    start_timeout="${KAOLA_START_TIMEOUT:-${GROK_START_TIMEOUT:-20}}"; [[ "$start_timeout" =~ ^[0-9]+$ ]] || die "KAOLA_START_TIMEOUT must be integer"; start_deadline=$((SECONDS + start_timeout)); while (( SECONDS < start_deadline )); do sleep 0.1; load_session_identity; [[ "$STATE_PRESENT" == true ]] || { emit_status start-exited; exit 1; }; if [[ -n "$STATE_RELAY_SOCKET" ]]; then observation="$(observe_managed)"; if [[ "$(printf '%s' "$observation" | json_value 'd.get("relay",{}).get("managed",False)')" == true ]]; then STATUS_JSON="$(printf '%s' "$observation" | "$PYTHON_BIN" "$OBSERVATION_HELPER" status-view)" "$PYTHON_BIN" -c 'import json,os; d=json.loads(os.environ["STATUS_JSON"]); d["result"]="started"; print(json.dumps(d,ensure_ascii=False,sort_keys=True))'; exit 0; fi; fi; done; emit_status start-pending; exit 2
    ;;
  answer)
    [[ "$ADAPTER_ANSWER_MODE" == claude-clear-v1 ]] || { emit_transport_result answer-unsupported answer false; exit 1; }
    [[ "$replace_editor" == true ]] || { emit_transport_result replace-editor-required answer false; exit 1; }
    load_payload
    validate_payload_controls || { emit_transport_refusal unsafe-terminal-control answer; exit 1; }
    if ! open_transport_channel; then emit_transport_result "$REFUSAL" answer false; exit 1; fi
    if payload_needs_bracketed_paste && [[ "$(printf '%s' "$DIRECT_RELAY" | json_value 'd.get("bracketed_paste",False)')" != true ]]; then close_relay_channel; emit_transport_refusal bracketed-paste-required answer; exit 1; fi
    answer_fp="$(fingerprint_payload)"; hex="$(payload_hex)"
    relay_line "{\"operation\":\"send-input\",\"clear_editor\":true,\"payload_hex\":\"$hex\"}" || { close_relay_channel; emit_transport_result transport-uncertain answer unknown; exit 1; }
    relay_result="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("result")' 2>/dev/null || true)"
    [[ "$relay_result" == input-sent ]] || { debug_relay_reply; close_relay_channel; emit_transport_result "${relay_result:-transport-failed}" answer false; exit 1; }
    payload_fp="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("payload_fingerprint")')"; clear_editor="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("clear_editor",False)')"
    [[ "$payload_fp" == "$answer_fp" && "$clear_editor" == true ]] || { close_relay_channel; emit_transport_result payload-attestation-mismatch answer true; exit 1; }
    close_relay_channel
    emit_json "n:schema_version:2" "s:result:answer-sent" "s:action:answer" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:decision_id:$decision_id" "s:based_on_snapshot:$if_snapshot" "b:mutation_performed:true" "s:payload_fingerprint:$payload_fp" "b:clear_editor:true"
    ;;
  send)
    load_payload
    validate_payload_controls || { emit_transport_refusal unsafe-terminal-control send; exit 1; }
    if ! open_transport_channel; then emit_transport_result "$REFUSAL" send false; exit 1; fi
    if payload_needs_bracketed_paste && [[ "$(printf '%s' "$DIRECT_RELAY" | json_value 'd.get("bracketed_paste",False)')" != true ]]; then close_relay_channel; emit_transport_refusal bracketed-paste-required send; exit 1; fi
    send_fp="$(fingerprint_payload)"; hex="$(payload_hex)"
    relay_line "{\"operation\":\"send-input\",\"payload_hex\":\"$hex\"}" || { close_relay_channel; emit_transport_result transport-uncertain send unknown; exit 1; }
    relay_result="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("result")' 2>/dev/null || true)"
    [[ "$relay_result" == input-sent ]] || { debug_relay_reply; close_relay_channel; emit_transport_result "${relay_result:-transport-failed}" send false; exit 1; }
    payload_fp="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("payload_fingerprint")')"
    [[ "$payload_fp" == "$send_fp" ]] || { close_relay_channel; emit_transport_result payload-attestation-mismatch send true; exit 1; }
    close_relay_channel
    emit_json "n:schema_version:2" "s:result:sent" "s:action:send" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot" "b:mutation_performed:true" "s:payload_fingerprint:$payload_fp"
    ;;
  key)
    if ! open_transport_channel; then emit_transport_result "$REFUSAL" key false; exit 1; fi
    case "$key_name" in
      up) key_hex=1b5b41 ;; down) key_hex=1b5b42 ;; right) key_hex=1b5b43 ;; left) key_hex=1b5b44 ;;
      enter) key_hex=0d ;; escape) key_hex=1b ;; tab) key_hex=09 ;; backtab) key_hex=1b5b5a ;; space) key_hex=20 ;;
    esac
    expected_key_fp="$(printf '%s' "$key_hex" | "$PYTHON_BIN" -c 'import hashlib,sys; print("sha256:"+hashlib.sha256(bytes.fromhex(sys.stdin.read())).hexdigest())')"
    relay_line "{\"operation\":\"send-control\",\"payload_hex\":\"$key_hex\"}" || { close_relay_channel; emit_transport_result transport-uncertain key unknown; exit 1; }
    [[ "$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("result")')" == control-sent ]] || { relay_result="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("result")' 2>/dev/null || true)"; debug_relay_reply; close_relay_channel; emit_transport_result "${relay_result:-transport-failed}" key false; exit 1; }
    key_fp="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("payload_fingerprint")')"
    [[ "$key_fp" == "$expected_key_fp" ]] || { close_relay_channel; emit_transport_result key-attestation-mismatch key true; exit 1; }
    close_relay_channel
    emit_json "n:schema_version:2" "s:result:key-sent" "s:action:key" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:key:$key_name" "s:based_on_snapshot:$if_snapshot" "b:mutation_performed:true" "s:payload_fingerprint:$key_fp"
    ;;
  stop)
    load_session_identity
    if [[ "$STATE_PRESENT" != true ]]; then emit_status already-stopped; exit 0; fi
    if [[ "$force" == true ]]; then
      force_stop_exact
      exit $?
    fi
    if ! open_transport_channel; then emit_transport_result "$REFUSAL" stop false; exit 1; fi
    PAYLOAD="$ADAPTER_QUIT_TEXT"; quit_fp="$(fingerprint_payload)"; hex="$(payload_hex)"
    relay_line "{\"operation\":\"send-input\",\"payload_hex\":\"$hex\"}" || { close_relay_channel; emit_transport_result transport-uncertain stop unknown; exit 1; }
    relay_result="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("result")' 2>/dev/null || true)"
    [[ "$relay_result" == input-sent ]] || { debug_relay_reply; close_relay_channel; emit_transport_result "${relay_result:-transport-failed}" stop false; exit 1; }
    payload_fp="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("payload_fingerprint")')"
    [[ "$payload_fp" == "$quit_fp" ]] || { close_relay_channel; emit_transport_result payload-attestation-mismatch stop true; exit 1; }
    close_relay_channel
    for _ in {1..100}; do session_exists || { emit_json "n:schema_version:2" "s:result:stopped" "s:action:stop" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot" "b:mutation_performed:true" "s:payload_fingerprint:$payload_fp"; exit 0; }; sleep 0.1; done
    emit_json "n:schema_version:2" "s:result:quit-pending" "s:action:stop" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot" "b:mutation_performed:true" "s:payload_fingerprint:$payload_fp"; exit 2
    ;;
esac
