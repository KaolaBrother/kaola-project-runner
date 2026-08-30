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
export OBSERVATION_HELPER

usage() {
  cat <<'EOF'
Usage:
  kaola-tmux.sh PLATFORM preflight --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM start     --repo ABS_PATH --session NAME [--continue | --resume ID]
  kaola-tmux.sh PLATFORM observe   --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM status    --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM capture   --repo ABS_PATH --session NAME [--lines N]
  kaola-tmux.sh PLATFORM send      --repo ABS_PATH --session NAME --if-snapshot ID --require-empty-editor [--text TEXT]
  kaola-tmux.sh PLATFORM answer    --repo ABS_PATH --session NAME --decision-id ID --if-snapshot ID --replace-editor [--text TEXT]
  kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME --if-snapshot ID [--force]
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
[[ -f "$OBSERVATION_HELPER" && -f "$RELAY" && -f "$RELAY_CLIENT" ]] || die "relay control plane is incomplete"
# shellcheck source=/dev/null
source "$adapter_file"
[[ "${ADAPTER_ID:-}" == "$platform" ]] || die "adapter identity mismatch"
[[ "${ADAPTER_ANSWER_MODE:-}" =~ ^(unsupported|claude-clear-v1)$ ]] || die "adapter answer mode missing"

command_name="${1:-}"; [[ -n "$command_name" ]] || { usage; exit 2; }; shift
case "$command_name" in preflight|start|observe|status|capture|send|answer|stop) ;; *) die "unknown command: $command_name" ;; esac
repo="" session="" resume_id="" continue_mode=false force=false lines=120 text_value="" text_given=false
if_snapshot="" require_empty_editor=false decision_id="" replace_editor=false model=opus effort=high permission_mode=auto
model_given=false effort_given=false permission_mode_given=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) repo="$2"; shift 2 ;; --session) session="$2"; shift 2 ;; --resume) resume_id="$2"; shift 2 ;;
    --continue) continue_mode=true; shift ;; --force) force=true; shift ;; --lines) lines="$2"; shift 2 ;;
    --text) text_value="$2"; text_given=true; shift 2 ;; --if-snapshot) if_snapshot="$2"; shift 2 ;;
    --require-empty-editor) require_empty_editor=true; shift ;; --decision-id) decision_id="$2"; shift 2 ;;
    --replace-editor) replace_editor=true; shift ;; --model) model="$2"; model_given=true; shift 2 ;;
    --effort) effort="$2"; effort_given=true; shift 2 ;; --permission-mode) permission_mode="$2"; permission_mode_given=true; shift 2 ;;
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
if [[ "$platform" != claude-code && ( "$model_given" == true || "$effort_given" == true || "$permission_mode_given" == true ) ]]; then die "model, effort, and permission mode are Claude-only"; fi
if [[ "$command_name" != start && ( "$model_given" == true || "$effort_given" == true || "$permission_mode_given" == true ) ]]; then die "model, effort, and permission mode are start-only"; fi
[[ "$model" =~ ^[A-Za-z0-9._:-]+$ ]] || die "model contains unsupported characters"
case "$effort" in low|medium|high|xhigh|max) ;; *) die "unsupported Claude effort" ;; esac
case "$permission_mode" in acceptEdits|auto|bypassPermissions|manual|dontAsk|plan) ;; *) die "unsupported Claude permission mode" ;; esac

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

load_session_identity() {
  STATE_PRESENT=false STATE_OWNED=false STATE_PLATFORM_MATCH=false STATE_REPO_MATCH=false STATE_TUI=false
  STATE_LEGACY_OWNERSHIP=false
  STATE_PANE_COUNT=0 STATE_PANE_ID="" STATE_PANE_PATH="" STATE_PANE_COMMAND="" STATE_PANE_TITLE="" STATE_PANE_DEAD="" STATE_PANE_PID="" STATE_PANE_PROCESS=""
  STATE_RELAY_PROCESS_MATCH=false STATE_PROCESS_MATCH=false STATE_PANE_INPUT_OFF=false STATE_PANE_WIDTH="" STATE_PANE_HEIGHT="" STATE_CURSOR_X="" STATE_CURSOR_Y=""
  STATE_CURSOR_FLAG=false STATE_ALTERNATE_ON=false STATE_HISTORY_SIZE="" STATE_HISTORY_BYTES="" STATE_CAPTURE_HISTORY="" STATE_ACTIVITY=unknown STATE_RUNTIME_SESSION_ID=""
  STATE_RELAY_SOCKET="" STATE_RELAY_EPOCH=""; session_exists || return 0; STATE_PRESENT=true
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
  local relay_json="$1" barrier_json="$2" result="${3:-observed}" frame cursor_frame cursor_logical_y process_json adapter_json child_pid ps_text temporary pane_facts_json
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
  KPR_FRAME_FILE="$temporary" KPR_PRESENT="$STATE_PRESENT" KPR_OWNED="$STATE_OWNED" KPR_PLATFORM_MATCH="$STATE_PLATFORM_MATCH" KPR_REPO_MATCH="$STATE_REPO_MATCH" KPR_PANE_COUNT="$STATE_PANE_COUNT" KPR_PANE_ID="$STATE_PANE_ID" KPR_PANE_DEAD="${STATE_PANE_DEAD:-0}" KPR_PANE_INPUT_OFF=false KPR_PANE_PATH="$STATE_PANE_PATH" KPR_PANE_PID="$STATE_PANE_PID" KPR_PANE_COMMAND="$STATE_PANE_COMMAND" KPR_PANE_TITLE="$STATE_PANE_TITLE" KPR_PANE_PROCESS="$STATE_PANE_PROCESS" KPR_RELAY_PROCESS_MATCH="$STATE_RELAY_PROCESS_MATCH" KPR_PROCESS_MATCH="$STATE_PROCESS_MATCH" KPR_TUI="$STATE_TUI" KPR_PANE_WIDTH="$STATE_PANE_WIDTH" KPR_PANE_HEIGHT="$STATE_PANE_HEIGHT" KPR_CURSOR_X="$STATE_CURSOR_X" KPR_CURSOR_Y="$STATE_CURSOR_Y" KPR_CURSOR_FLAG="$STATE_CURSOR_FLAG" KPR_ALTERNATE_ON="$STATE_ALTERNATE_ON" KPR_HISTORY_SIZE="$STATE_HISTORY_SIZE" KPR_HISTORY_BYTES="$STATE_HISTORY_BYTES" KPR_ADAPTER_JSON="$adapter_json" KPR_PROCESS_JSON="$process_json" KPR_RELAY_JSON="$relay_json" KPR_BARRIER_JSON="$barrier_json" KPR_RESULT="$result" KPR_PLATFORM="$platform" KPR_RUNTIME="$ADAPTER_DISPLAY_NAME" KPR_SESSION="$session" KPR_REPO="$repo" KPR_RUNTIME_SESSION_ID="$STATE_RUNTIME_SESSION_ID" "$PYTHON_BIN" "$OBSERVATION_HELPER" build
  rm -f "$temporary"
}

observe_managed() {
  local bootstrap child_fingerprint relay_pid quiesced lease state_reply relay_json barrier_json preliminary pane_revision resumed observation
  load_session_identity; if [[ -z "$STATE_RELAY_SOCKET" || -z "$STATE_RELAY_EPOCH" ]]; then build_sample null null observed; return; fi
  bootstrap="$(bootstrap_relay)" || { build_sample null null unstable; return; }; child_fingerprint="$(printf '%s' "$bootstrap" | json_value 'd["child_start_fingerprint"]')"; relay_pid="$(printf '%s' "$bootstrap" | json_value 'd["pid"]')"; [[ "$relay_pid" == "$STATE_PANE_PID" ]] || { build_sample null null unstable; return; }
  open_relay_channel "$STATE_RELAY_SOCKET" "$STATE_RELAY_EPOCH" "$child_fingerprint" "$relay_pid"; relay_line '{"operation":"quiesce"}' || { close_relay_channel; build_sample null null unstable; return; }; quiesced="$RELAY_REPLY"; [[ "$(printf '%s' "$quiesced" | json_value 'd["result"]')" == quiesced ]] || { close_relay_channel; build_sample null null unstable; return; }; lease="$(printf '%s' "$quiesced" | json_value 'd["lease_id"]')"
  relay_line '{"operation":"state"}'; state_reply="$RELAY_REPLY"; relay_json="$(printf '%s' "$state_reply" | json_value 'd["relay"]')"; barrier_json="$(printf '%s' "$state_reply" | json_value 'd.get("barrier")')"; [[ -n "$barrier_json" ]] || barrier_json=null; preliminary="$(build_sample "$relay_json" "$barrier_json")"; pane_revision="$(printf '%s' "$preliminary" | json_value 'd["pane_revision"]')"; current_frame_revision="$(printf '%s' "$preliminary" | frame_revision)"
  relay_line "{\"operation\":\"state\",\"pane_revision\":\"$pane_revision\",\"frame_revision\":\"$current_frame_revision\"}"; state_reply="$RELAY_REPLY"; relay_json="$(printf '%s' "$state_reply" | json_value 'd["relay"]')"; barrier_json="$(printf '%s' "$state_reply" | json_value 'd.get("barrier")')"; [[ -n "$barrier_json" ]] || barrier_json=null; observation="$(build_sample "$relay_json" "$barrier_json")"
  relay_line "{\"operation\":\"resume\",\"lease_id\":\"$lease\"}" || true; resumed="$RELAY_REPLY"; close_relay_channel; load_session_identity
  if [[ "$STATE_PANE_INPUT_OFF" == true || "$(printf '%s' "$resumed" | json_value 'd.get("result")' 2>/dev/null || true)" != resumed ]]; then OBS_VALUE="$observation" "$PYTHON_BIN" -c 'import json,os; d=json.loads(os.environ["OBS_VALUE"]); d["result"]="unstable"; d["guard_failures"]=sorted(set(d["guard_failures"]+["restoration-unconfirmed"])); print(json.dumps(d,ensure_ascii=False,sort_keys=True))'; else printf '%s\n' "$observation"; fi
}

emit_status() { local observation status; observation="$(observe_managed)"; status="$(printf '%s' "$observation" | "$PYTHON_BIN" "$OBSERVATION_HELPER" status-view)"; load_session_identity; STATUS_JSON="$status" STATUS_RESULT="$1" STATUS_LEGACY="$STATE_LEGACY_OWNERSHIP" "$PYTHON_BIN" -c 'import json,os; d=json.loads(os.environ["STATUS_JSON"]); d["result"]=os.environ["STATUS_RESULT"]; d.update({"legacy_ownership":os.environ["STATUS_LEGACY"]=="true"} if d.get("platform")=="grok" else {}); print(json.dumps(d,ensure_ascii=False,sort_keys=True))'; }
emit_refusal() { emit_json "n:schema_version:2" "s:result:$1" "s:action:${2:-$command_name}" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot" "b:mutation_performed:false" "b:restored:true"; }
emit_prepared_refusal() { emit_json "n:schema_version:2" "s:result:refused" "s:reason:$1" "s:action:$2" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot" "b:mutation_performed:false" "b:restored:true"; }
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
frame_revision() { "$PYTHON_BIN" -c 'import hashlib,json,sys; d=json.load(sys.stdin); h=d["hard_evidence"]; keys=("pane_id","pane_dead","pane_width","pane_height","cursor_x","cursor_y","cursor_flag","alternate_on"); v={"raw_current_frame":d["raw_current_frame"],"hard_evidence":{k:h.get(k) for k in keys}}; print("sha256:"+hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest())'; }
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
tracked_descendants_gone() {
  TRACKED_DESCENDANTS_JSON="$1" "$PYTHON_BIN" - <<'PY'
import hashlib
import json
import os
import subprocess

for tracked in json.loads(os.environ["TRACKED_DESCENDANTS_JSON"]):
    pid = int(tracked["pid"])
    result = subprocess.run(
        ["ps", "-ww", "-p", str(pid), "-o", "lstart=", "-o", "command="],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        continue
    # Read the two fields independently so the fingerprint exactly matches
    # the relay's process_fingerprint().
    started = subprocess.run(
        ["ps", "-p", str(pid), "-o", "lstart="], capture_output=True, text=True
    ).stdout.strip()
    command = subprocess.run(
        ["ps", "-ww", "-p", str(pid), "-o", "command="], capture_output=True, text=True
    ).stdout.strip()
    material = f"{pid}\0{started}\0{command}".encode()
    fingerprint = "sha256:" + hashlib.sha256(material).hexdigest()
    if fingerprint == tracked["start_fingerprint"]:
        raise SystemExit(1)
PY
}
guard_result() { OBS_JSON="$1" ACTION="$2" "$PYTHON_BIN" - <<'PY'
import json,os
d=json.loads(os.environ["OBS_JSON"]); a=os.environ["ACTION"]
tests=[(d["result"]!="observed","observation-unstable"),(not d["relay"]["managed"],"relay-required"),((d.get("later_output_barrier") or {}).get("state") in {"pending","output-seen"},"awaiting-later-output"),(d["editor_state"]=="unknown","editor-unknown"),(a!="answer" and d["editor_state"]=="nonempty","editor-nonempty"),(a!="answer" and d["structured_decision_marker"] is not None,"structured-decision-present"),(d["visible_shell_count"] is None,"visible-shell-unknown"),((d["visible_shell_count"] or 0)>0,"visible-shell-active"),(d["visible_agent_count"] is None,"visible-agent-unknown"),((d["visible_agent_count"] or 0)>0,"visible-agent-active"),(d["native_approval"]["state"]=="unknown","native-approval-unknown"),(d["native_approval"]["state"]=="present","native-approval-present")]
print(next((n for failed,n in tests if failed),"ok"))
PY
}
prepared_surface_result() { OBS_JSON="$1" EXPECTED_FP="${2:-}" ALLOW_EMPTY="${3:-false}" "$PYTHON_BIN" - <<'PY'
import json, os
d=json.loads(os.environ["OBS_JSON"]); h=d["hard_evidence"]
expected=os.environ.get("EXPECTED_FP", "")
allow_empty=os.environ.get("ALLOW_EMPTY") == "true"
tests=[
 (d["result"]!="observed", "prepared-observation-unstable"),
 (not d["relay"]["managed"], "prepared-relay-missing"),
 (not h["owned"] or not h["platform_match"] or not h["repo_match"] or h["pane_count"]!=1, "prepared-identity-changed"),
 (not h["relay_process_match"] or not h["process_match"] or not h["tui_detected"], "prepared-runtime-changed"),
 (d["native_approval"]["state"]!="absent", "prepared-native-approval"),
 (d["structured_decision_marker"] is not None, "prepared-structured-decision"),
 (d["visible_shell_count"] is None or d["visible_agent_count"] is None, "prepared-visible-work-unknown"),
 ((d["visible_shell_count"] or 0)>0 or (d["visible_agent_count"] or 0)>0, "prepared-visible-work-active"),
 (d["editor_state"]=="unknown" or (not allow_empty and d["editor_state"]!="nonempty"), "prepared-editor-unproven"),
 (bool(expected) and d["editor_fingerprint"]!=expected, "prepared-editor-mismatch"),
]
print(next((name for failed,name in tests if failed), "ok"))
PY
}
prepared_answer_surface_result() { OBS_JSON="$1" EXPECTED_DECISION="$2" EXPECTED_FP="$3" "$PYTHON_BIN" - <<'PY'
import json, os
d=json.loads(os.environ["OBS_JSON"]); h=d["hard_evidence"]
decision=d.get("structured_decision_marker") or {}
tests=[
 (d["result"]!="observed", "prepared-observation-unstable"),
 (not d["relay"]["managed"], "prepared-relay-missing"),
 (not h["owned"] or not h["platform_match"] or not h["repo_match"] or h["pane_count"]!=1, "prepared-identity-changed"),
 (not h["relay_process_match"] or not h["process_match"] or not h["tui_detected"], "prepared-runtime-changed"),
 (d["native_approval"]["state"]!="absent", "prepared-native-approval"),
 (decision.get("decision_id")!=os.environ["EXPECTED_DECISION"], "prepared-decision-changed"),
 (d["visible_shell_count"] is None or d["visible_agent_count"] is None, "prepared-visible-work-unknown"),
 ((d["visible_shell_count"] or 0)>0 or (d["visible_agent_count"] or 0)>0, "prepared-visible-work-active"),
 (d["editor_state"]!="nonempty", "prepared-editor-unproven"),
 (d["editor_fingerprint"]!=os.environ["EXPECTED_FP"], "prepared-editor-mismatch"),
]
print(next((name for failed,name in tests if failed), "ok"))
PY
}

MUTATION_LOCK="kaola-project-runner:${platform}:${session}" MUTATION_LOCKED=false TX_LEASE=""
unlock_mutation() { if [[ "$MUTATION_LOCKED" == true ]]; then "$TMUX_BIN" wait-for -U "$MUTATION_LOCK" 2>/dev/null || true; MUTATION_LOCKED=false; fi; }
trap 'close_relay_channel; unlock_mutation' EXIT HUP INT TERM
lock_mutation() { "$TMUX_BIN" wait-for -L "$MUTATION_LOCK"; MUTATION_LOCKED=true; }
renew_transaction() {
  relay_line "{\"operation\":\"renew\",\"lease_id\":\"$TX_LEASE\"}" || { REFUSAL=lease-renewal-failed; return 1; }
  [[ "$(printf '%s' "$RELAY_REPLY" | json_value 'd["result"]')" == renewed ]] || { REFUSAL=lease-renewal-failed; return 1; }
}
prepare_transaction() {
  local bootstrap relay_pid state_reply barrier_json preliminary pane_revision
  lock_mutation; load_session_identity; [[ "$STATE_PRESENT" == true ]] || { REFUSAL=absent; return 1; }; [[ "$STATE_OWNED" == true ]] || { REFUSAL=unowned; return 1; }; [[ "$STATE_PLATFORM_MATCH" == true ]] || { REFUSAL=platform-mismatch; return 1; }; [[ "$STATE_PANE_COUNT" -eq 1 ]] || { REFUSAL=unexpected-pane-count; return 1; }; [[ "$STATE_REPO_MATCH" == true ]] || { REFUSAL=repo-mismatch; return 1; }; [[ -n "$STATE_RELAY_SOCKET" && -n "$STATE_RELAY_EPOCH" ]] || { REFUSAL=relay-required; return 1; }
  bootstrap="$(bootstrap_relay)" || { REFUSAL=relay-attestation-failed; return 1; }; TX_CHILD_FP="$(printf '%s' "$bootstrap" | json_value 'd["child_start_fingerprint"]')"; relay_pid="$(printf '%s' "$bootstrap" | json_value 'd["pid"]')"; [[ "$relay_pid" == "$STATE_PANE_PID" ]] || { REFUSAL=relay-attestation-failed; return 1; }
  open_relay_channel "$STATE_RELAY_SOCKET" "$STATE_RELAY_EPOCH" "$TX_CHILD_FP" "$relay_pid"; relay_line '{"operation":"quiesce"}' || { REFUSAL=quiesce-failed; return 1; }; [[ "$(printf '%s' "$RELAY_REPLY" | json_value 'd["result"]')" == quiesced ]] || { REFUSAL=quiesce-failed; return 1; }; TX_LEASE="$(printf '%s' "$RELAY_REPLY" | json_value 'd["lease_id"]')"
  relay_line '{"operation":"state"}'; state_reply="$RELAY_REPLY"; TX_RELAY="$(printf '%s' "$state_reply" | json_value 'd["relay"]')"; barrier_json="$(printf '%s' "$state_reply" | json_value 'd.get("barrier")')"; [[ -n "$barrier_json" ]] || barrier_json=null; renew_transaction || return 1; preliminary="$(build_sample "$TX_RELAY" "$barrier_json")"; renew_transaction || return 1; pane_revision="$(printf '%s' "$preliminary" | json_value 'd["pane_revision"]')"; current_frame_revision="$(printf '%s' "$preliminary" | frame_revision)"; relay_line "{\"operation\":\"state\",\"pane_revision\":\"$pane_revision\",\"frame_revision\":\"$current_frame_revision\"}"; state_reply="$RELAY_REPLY"; TX_RELAY="$(printf '%s' "$state_reply" | json_value 'd["relay"]')"; barrier_json="$(printf '%s' "$state_reply" | json_value 'd.get("barrier")')"; [[ -n "$barrier_json" ]] || barrier_json=null; renew_transaction || return 1; TX_OBSERVATION="$(build_sample "$TX_RELAY" "$barrier_json")"; renew_transaction || return 1; [[ "$(printf '%s' "$TX_OBSERVATION" | json_value 'd["snapshot_id"]')" == "$if_snapshot" ]] || { REFUSAL=stale-snapshot; return 1; }
}
restore_transaction() { if [[ -n "$TX_LEASE" ]]; then relay_line "{\"operation\":\"resume\",\"lease_id\":\"$TX_LEASE\"}" 2>/dev/null || true; fi; close_relay_channel; unlock_mutation; TX_LEASE=""; }

case "$command_name" in
  preflight) adapter_preflight; args=("s:result:ready" "s:platform:$platform" "s:runtime:$ADAPTER_DISPLAY_NAME" "s:runtime_version:$PREFLIGHT_VERSION" "s:runtime_binary:$RUNTIME_BIN" "s:repo:$repo" "s:session:$session" "b:workflow_next:$PREFLIGHT_WORKFLOW_NEXT" "b:kaola_workflow_finalize:$PREFLIGHT_FINALIZE" "s:recurring_execution:$ADAPTER_RECURRING_EXECUTION" "s:project_materialization:$PREFLIGHT_PROJECT_MATERIALIZATION" "s:detail:$PREFLIGHT_DETAIL"); if [[ "$platform" == grok ]]; then args+=("s:grok_version:$PREFLIGHT_VERSION" "j:project_root:$PREFLIGHT_PROJECT_ROOT_JSON"); fi; emit_json "${args[@]}" ;;
  observe) observe_managed ;;
  status) load_session_identity; if [[ "$STATE_PRESENT" == true ]]; then emit_status present; else emit_status absent; fi ;;
  capture) [[ "$lines" =~ ^[1-9][0-9]*$ && "$lines" -le 5000 ]] || die "--lines must be 1..5000"; load_session_identity; [[ "$STATE_PRESENT" == true && "$STATE_OWNED" == true && "$STATE_PLATFORM_MATCH" == true && "$STATE_REPO_MATCH" == true && -n "$STATE_PANE_ID" ]] || { emit_refusal identity-mismatch capture; exit 1; }; "$TMUX_BIN" capture-pane -p -t "$STATE_PANE_ID" -S "-$lines" ;;
  start)
    [[ -z "$resume_id" || "$continue_mode" == false ]] || die "--resume and --continue are mutually exclusive"; adapter_preflight; load_session_identity
    if [[ "$STATE_PRESENT" == true ]]; then if [[ "$STATE_OWNED" == true && "$STATE_PLATFORM_MATCH" == true && "$STATE_REPO_MATCH" == true && -n "$STATE_RELAY_SOCKET" ]]; then emit_status already-running; exit 0; fi; emit_status existing-session-not-reusable; exit 1; fi
    type adapter_prepare_launch >/dev/null 2>&1 && adapter_prepare_launch "$repo"; session_env_args=(); while IFS='=' read -r name value; do case "$name" in CLAUDE_*|GROK_*|OPENCODE_*|KIMI_*|CURSOR_*|FAKE_*) session_env_args+=(-e "$name=$value") ;; esac; done < <(env)
    if (( ${#session_env_args[@]} > 0 )); then
      "$TMUX_BIN" new-session -d -s "$session" -c "$repo" "${session_env_args[@]}" || { emit_status existing-session-not-reusable; exit 1; }
    else
      "$TMUX_BIN" new-session -d -s "$session" -c "$repo" || { emit_status existing-session-not-reusable; exit 1; }
    fi
    "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$OWNER_KEY" 1; "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$PLATFORM_KEY" "$platform"; "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$REPO_KEY" "$repo"; if [[ "$platform" == grok ]]; then "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$LEGACY_OWNER_KEY" 1; "$TMUX_BIN" set-environment -t "$TMUX_SESSION_TARGET" "$LEGACY_REPO_KEY" "$repo"; fi
    load_session_identity; adapter_build_launch "$repo" "$resume_id" "$continue_mode"; launch=exec; for argument in "$PYTHON_BIN" "$RELAY" --tmux-bin "$TMUX_BIN" --session "$session" --pane-id "$STATE_PANE_ID" --repo "$repo" --runtime-path "$RUNTIME_BIN" --exact-process-title "${ADAPTER_CHILD_PROCESS_TITLE_EXACT:-}" -- ${ADAPTER_LAUNCH_ARGS[@]+"${ADAPTER_LAUNCH_ARGS[@]}"}; do printf -v quoted '%q' "$argument"; launch+=" $quoted"; done; "$TMUX_BIN" send-keys -t "$STATE_PANE_ID" -l "$launch"; "$TMUX_BIN" send-keys -t "$STATE_PANE_ID" C-m
    start_timeout="${KAOLA_START_TIMEOUT:-${GROK_START_TIMEOUT:-20}}"; [[ "$start_timeout" =~ ^[0-9]+$ ]] || die "KAOLA_START_TIMEOUT must be integer"; start_deadline=$((SECONDS + start_timeout)); while (( SECONDS < start_deadline )); do sleep 0.1; load_session_identity; [[ "$STATE_PRESENT" == true ]] || { emit_status start-exited; exit 1; }; if [[ -n "$STATE_RELAY_SOCKET" ]]; then observation="$(observe_managed)"; if [[ "$(printf '%s' "$observation" | json_value 'd["result"]')" == observed && "$(printf '%s' "$observation" | json_value 'd["hard_evidence"]["tui_detected"]')" == true ]]; then STATUS_JSON="$(printf '%s' "$observation" | "$PYTHON_BIN" "$OBSERVATION_HELPER" status-view)" "$PYTHON_BIN" -c 'import json,os; d=json.loads(os.environ["STATUS_JSON"]); d["result"]="started"; print(json.dumps(d,ensure_ascii=False,sort_keys=True))'; exit 0; fi; fi; done; emit_status start-pending; exit 2
    ;;
  answer)
    [[ "$ADAPTER_ANSWER_MODE" == claude-clear-v1 ]] || { emit_refusal answer-unsupported answer; exit 1; }; [[ -n "$if_snapshot" ]] || { emit_refusal snapshot-required answer; exit 1; }; [[ -n "$decision_id" ]] || { emit_refusal decision-id-required answer; exit 1; }; [[ "$replace_editor" == true ]] || { emit_refusal replace-editor-required answer; exit 1; }; load_payload; validate_payload_controls || { emit_prepared_refusal unsafe-terminal-control answer; exit 1; }
    if ! prepare_transaction; then restore_transaction; emit_refusal "$REFUSAL" answer; exit 1; fi; guard="$(guard_result "$TX_OBSERVATION" answer)"; [[ "$guard" == ok ]] || { restore_transaction; emit_refusal "$guard" answer; exit 1; }; current_decision="$(printf '%s' "$TX_OBSERVATION" | json_value '(d.get("structured_decision_marker") or {}).get("decision_id")')"; [[ "$current_decision" == "$decision_id" ]] || { restore_transaction; emit_refusal decision-mismatch answer; exit 1; }
    if payload_needs_bracketed_paste && [[ "$(printf '%s' "$TX_RELAY" | json_value 'd.get("bracketed_paste",False)')" != true ]]; then restore_transaction; emit_prepared_refusal bracketed-paste-required answer; exit 1; fi
    editor_fp="$(printf '%s' "$TX_OBSERVATION" | json_value 'd["editor_fingerprint"]')"; answer_fp="$(fingerprint_payload)"; hex="$(payload_hex)"; relay_line "{\"operation\":\"prepare-input\",\"lease_id\":\"$TX_LEASE\",\"clear_editor\":true,\"payload_hex\":\"$hex\"}"; [[ "$(printf '%s' "$RELAY_REPLY" | json_value 'd["result"]')" == prepared ]] || { debug_relay_reply; restore_transaction; emit_refusal action-prepare-uncertain answer; exit 1; }
    prepared_relay="$(printf '%s' "$RELAY_REPLY" | json_value 'd["relay"]')"; prepared_payload_fp="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("prepared_payload_fingerprint")')"; prepared_clear="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("prepared_clear_editor",False)')"; [[ "$prepared_payload_fp" == "$answer_fp" && "$prepared_clear" == true ]] || { restore_transaction; emit_refusal prepared-payload-attestation-mismatch answer; exit 1; }; renew_transaction || { restore_transaction; emit_refusal "$REFUSAL" answer; exit 1; }; prepared_observation="$(build_sample "$prepared_relay" null)"; renew_transaction || { restore_transaction; emit_refusal "$REFUSAL" answer; exit 1; }; prepared_revision="$(printf '%s' "$prepared_observation" | json_value 'd["pane_revision"]')"; prepared_frame_revision="$(printf '%s' "$prepared_observation" | frame_revision)"; prepared_guard="$(prepared_answer_surface_result "$prepared_observation" "$decision_id" "$answer_fp")"; [[ "$prepared_guard" == ok ]] || { restore_transaction; emit_prepared_refusal "$prepared_guard" answer; exit 1; }; submitted_offset="$(printf '%s' "$prepared_relay" | json_value 'd["child_output_offset"]')"; output_digest="$(printf '%s' "$prepared_relay" | json_value 'd["child_output_digest"]')"; receipt_fields="$(emit_json "n:schema_version:2" "s:action:answer" "s:platform:$platform" "s:session:$session" "s:repo:$PUBLIC_REPO" "s:decision_id:$decision_id" "s:replaced_editor_fingerprint:$editor_fp" "s:answer_fingerprint:$answer_fp" "s:based_on_snapshot:$if_snapshot" "s:relay_epoch:$STATE_RELAY_EPOCH" "s:child_start_fingerprint:$TX_CHILD_FP" "s:prepared_pane_revision:$prepared_revision" "n:submitted_output_offset:$submitted_offset" "s:child_output_digest:$output_digest")"; receipt="$(printf '%s' "$receipt_fields" | "$PYTHON_BIN" "$OBSERVATION_HELPER" receipt)"; renew_transaction || { restore_transaction; emit_refusal "$REFUSAL" answer; exit 1; }; relay_line "{\"operation\":\"submit\",\"lease_id\":\"$TX_LEASE\",\"receipt_id\":\"$receipt\",\"prepared_pane_revision\":\"$prepared_revision\",\"prepared_frame_revision\":\"$prepared_frame_revision\"}"; [[ "$(printf '%s' "$RELAY_REPLY" | json_value 'd["result"]')" == submitted ]] || { close_relay_channel; unlock_mutation; emit_refusal action-submit-uncertain answer; exit 1; }; close_relay_channel; unlock_mutation; emit_json "n:schema_version:2" "s:result:answer-sent" "s:action:answer" "s:platform:$platform" "s:session:$session" "s:repo:$PUBLIC_REPO" "s:decision_id:$decision_id" "s:based_on_snapshot:$if_snapshot" "s:later_output_barrier:pending" "s:receipt_id:$receipt" "s:prepared_pane_revision:$prepared_revision" "s:relay_epoch:$STATE_RELAY_EPOCH" "s:child_start_fingerprint:$TX_CHILD_FP" "s:replaced_editor_fingerprint:$editor_fp" "s:answer_fingerprint:$answer_fp"
    ;;
  send)
    [[ -n "$if_snapshot" ]] || { emit_refusal snapshot-required send; exit 1; }; [[ "$require_empty_editor" == true ]] || { emit_refusal empty-editor-guard-required send; exit 1; }; load_payload; validate_payload_controls || { emit_prepared_refusal unsafe-terminal-control send; exit 1; }; if ! prepare_transaction; then restore_transaction; emit_refusal "$REFUSAL" send; exit 1; fi; guard="$(guard_result "$TX_OBSERVATION" send)"; [[ "$guard" == ok ]] || { restore_transaction; emit_refusal "$guard" send; exit 1; }; if payload_needs_bracketed_paste && [[ "$(printf '%s' "$TX_RELAY" | json_value 'd.get("bracketed_paste",False)')" != true ]]; then restore_transaction; emit_prepared_refusal bracketed-paste-required send; exit 1; fi; send_fp="$(fingerprint_payload)"; hex="$(payload_hex)"; relay_line "{\"operation\":\"prepare-input\",\"lease_id\":\"$TX_LEASE\",\"payload_hex\":\"$hex\"}"; [[ "$(printf '%s' "$RELAY_REPLY" | json_value 'd["result"]')" == prepared ]] || { debug_relay_reply; restore_transaction; emit_refusal action-prepare-uncertain send; exit 1; }; prepared_relay="$(printf '%s' "$RELAY_REPLY" | json_value 'd["relay"]')"; prepared_payload_fp="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("prepared_payload_fingerprint")')"; [[ "$prepared_payload_fp" == "$send_fp" ]] || { restore_transaction; emit_refusal prepared-payload-attestation-mismatch send; exit 1; }; renew_transaction || { restore_transaction; emit_refusal "$REFUSAL" send; exit 1; }; prepared_observation="$(build_sample "$prepared_relay" null)"; renew_transaction || { restore_transaction; emit_refusal "$REFUSAL" send; exit 1; }; prepared_guard="$(prepared_surface_result "$prepared_observation" "$send_fp")"; [[ "$prepared_guard" == ok ]] || { restore_transaction; emit_prepared_refusal "$prepared_guard" send; exit 1; }; relay_line "{\"operation\":\"submit\",\"lease_id\":\"$TX_LEASE\"}" ; [[ "$(printf '%s' "$RELAY_REPLY" | json_value 'd["result"]')" == submitted ]] || { debug_relay_reply; close_relay_channel; unlock_mutation; emit_refusal action-submit-uncertain send; exit 1; }; close_relay_channel; unlock_mutation; emit_json "n:schema_version:2" "s:result:sent" "s:action:send" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot"
    ;;
  stop)
    load_session_identity; if [[ "$STATE_PRESENT" != true ]]; then emit_status already-stopped; exit 0; fi; [[ -n "$if_snapshot" ]] || { emit_refusal snapshot-required stop; exit 1; }; if ! prepare_transaction; then restore_transaction; emit_refusal "$REFUSAL" stop; exit 1; fi
    if [[ "$force" == true ]]; then
      terminal_child_pid="$(printf '%s' "$TX_RELAY" | json_value 'd.get("child_pid")')"
      terminal_child_pgid="$(printf '%s' "$TX_RELAY" | json_value 'd.get("child_pgid")')"
      terminal_socket="$(printf '%s' "$TX_RELAY" | json_value 'd.get("socket_path")')"
      terminal_epoch="$(printf '%s' "$TX_RELAY" | json_value 'd.get("epoch")')"
      relay_line "{\"operation\":\"containment\",\"lease_id\":\"$TX_LEASE\"}" || { restore_transaction; emit_refusal containment-uncertain force-stop; exit 1; }
      [[ "$(printf '%s' "$RELAY_REPLY" | json_value 'd["result"]')" == containment ]] || { restore_transaction; emit_refusal containment-uncertain force-stop; exit 1; }
      terminal_tracked="$(printf '%s' "$RELAY_REPLY" | json_value 'd.get("tracked_descendants",[])')"
      terminate_reply=false
      if relay_line "{\"operation\":\"terminate\",\"lease_id\":\"$TX_LEASE\"}"; then
        terminate_result="$(printf '%s' "$RELAY_REPLY" | json_value 'd["result"]')"
        [[ "$terminate_result" == terminating ]] || {
          [[ "${KAOLA_RUNNER_DEBUG:-0}" == 1 ]] && printf 'kaola-tmux[%s]: terminate reply=%s\n' "$platform" "$terminate_result" >&2
          restore_transaction; emit_refusal termination-uncertain force-stop; exit 1;
        }
        terminate_reply=true
      elif [[ "${KAOLA_RUNNER_DEBUG:-0}" == 1 ]]; then
        printf 'kaola-tmux[%s]: terminate reply transport closed; reconciling terminal facts\n' "$platform" >&2
      fi
      # The exact child may exit quickly enough to close the relay transport
      # before its `terminating` frame reaches the controller.  Force-stop is
      # already authorized by the fresh identity-bound snapshot, so reconcile
      # that transport loss against terminal facts instead of calling a
      # successful shutdown uncertain.
      TX_LEASE=""; close_relay_channel
      if session_exists; then "$TMUX_BIN" kill-session -t "$TMUX_SESSION_TARGET" || true; fi
      terminal_absent=false
      for _ in {1..100}; do
        session_gone=true child_gone=true group_gone=true socket_gone=true
        session_exists && session_gone=false
        if [[ "$terminal_child_pid" =~ ^[0-9]+$ ]] && "$PS_BIN" -p "$terminal_child_pid" -o pid= 2>/dev/null | grep -q '[0-9]'; then child_gone=false; fi
        if [[ "$terminal_child_pgid" =~ ^[0-9]+$ ]] && "$PS_BIN" -axo pgid= 2>/dev/null | awk -v pgid="$terminal_child_pgid" '$1 == pgid { found=1 } END { exit !found }'; then group_gone=false; fi
        if [[ "$session_gone" == true && "$child_gone" == true && "$group_gone" == true && -n "$terminal_socket" && -e "$terminal_socket" ]]; then cleanup_terminal_socket "$terminal_socket" "$terminal_epoch" || true; fi
        [[ -z "$terminal_socket" || ! -e "$terminal_socket" ]] || socket_gone=false
        tracked_gone=true; tracked_descendants_gone "$terminal_tracked" || tracked_gone=false
        if [[ "$session_gone" == true && "$child_gone" == true && "$group_gone" == true && "$tracked_gone" == true && "$socket_gone" == true ]]; then terminal_absent=true; break; fi
        sleep 0.05
      done
      if [[ "$terminal_absent" != true ]]; then
        if [[ "${KAOLA_RUNNER_DEBUG:-0}" == 1 ]]; then
          printf 'kaola-tmux[%s]: terminal absence unproven session=%s child=%s group=%s tracked=%s socket=%s\n' \
            "$platform" "$session_gone" "$child_gone" "$group_gone" "$tracked_gone" "$socket_gone" >&2
        fi
        unlock_mutation; emit_refusal termination-uncertain force-stop; exit 1
      fi
      unlock_mutation
      emit_json "n:schema_version:2" "s:result:stopped" "s:action:force-stop" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot" "b:terminate_reply_received:$terminate_reply" 'j:final_state:{"session_present":false,"child_running":false,"child_group_running":false,"socket_present":false,"pane_input_off":null}'
      exit 0
    fi
    guard="$(guard_result "$TX_OBSERVATION" stop)"; [[ "$guard" == ok ]] || { restore_transaction; emit_refusal "$guard" stop; exit 1; }; PAYLOAD="$ADAPTER_QUIT_TEXT"; quit_fp="$(fingerprint_payload)"; hex="$(payload_hex)"; relay_line "{\"operation\":\"prepare-input\",\"lease_id\":\"$TX_LEASE\",\"payload_hex\":\"$hex\"}"; [[ "$(printf '%s' "$RELAY_REPLY" | json_value 'd["result"]')" == prepared ]] || { restore_transaction; emit_refusal action-prepare-uncertain stop; exit 1; }; prepared_relay="$(printf '%s' "$RELAY_REPLY" | json_value 'd["relay"]')"; renew_transaction || { restore_transaction; emit_refusal "$REFUSAL" stop; exit 1; }; prepared_observation="$(build_sample "$prepared_relay" null)"; renew_transaction || { restore_transaction; emit_refusal "$REFUSAL" stop; exit 1; }; prepared_guard="$(prepared_surface_result "$prepared_observation" "$quit_fp")"; [[ "$prepared_guard" == ok ]] || { restore_transaction; emit_prepared_refusal "$prepared_guard" stop; exit 1; }; relay_line "{\"operation\":\"submit\",\"lease_id\":\"$TX_LEASE\"}" || { close_relay_channel; unlock_mutation; emit_refusal action-submit-uncertain stop; exit 1; }; close_relay_channel; unlock_mutation; for _ in {1..100}; do session_exists || { emit_json "n:schema_version:2" "s:result:stopped" "s:action:stop" "s:platform:$platform" "s:session:$session" "s:repo:$repo" "s:based_on_snapshot:$if_snapshot"; exit 0; }; sleep 0.1; done; emit_json "n:schema_version:2" "s:result:quit-pending" "s:action:stop" "s:platform:$platform" "s:session:$session" "s:repo:$repo"; exit 2
    ;;
esac
