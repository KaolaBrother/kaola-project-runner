#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
MODEL_POLICY_HELPER="$script_dir/kaola-model-policy.py"
ACP_CLI="$script_dir/kaola-acp.py"

# Issue #78: this file must contain no here-document and no here-string. Bash writes
# any heredoc body up to HEREDOC_PIPESIZE (4096) into a pipe from the forked child
# *before* exec, so that one process holds both ends and nothing drains it. macOS hands
# out 512-byte pipes once system-wide pipe KVA is under pressure - measured on the dev
# Mac: capacity 65536 idle, 512 at 150 held pipes - so any body over 512 bytes blocks in
# write() forever. The stuck process has not exec'd yet, so it wears this script's argv,
# has no children, and survives the SIGKILL a caller's timeout aims at its parent. That
# is what hung the Issue #73 refusal cases (emit_json, 883 bytes) under load. Feed Python
# with -c and read with a process substitution instead; both are pipe-free or drained by
# a separate writer. tests/contract/test-issue-78-heredoc-deadlock.py enforces this.
usage() {
  printf '%s\n' 'Usage:
  kaola-tmux.sh PLATFORM preflight --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM start     --repo ABS_PATH --session NAME [--continue | --resume ID] [--tier default|upgrade|PLATFORM_TIER] [--model ID --effort LEVEL] [--fast on|off]
  kaola-tmux.sh PLATFORM observe   --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM status    --repo ABS_PATH --session NAME
  kaola-tmux.sh PLATFORM capture   --repo ABS_PATH --session NAME [--lines N] [--full]
  kaola-tmux.sh PLATFORM send      --repo ABS_PATH --session NAME [--if-snapshot ID] [--text TEXT]
  kaola-tmux.sh PLATFORM steer     --repo ABS_PATH --session NAME --text TEXT [--steer-mode native|interrupt] [--cancel-timeout SECONDS]
  kaola-tmux.sh PLATFORM key       --repo ABS_PATH --session NAME [--if-snapshot ID] --key NAME
  kaola-tmux.sh PLATFORM answer    --repo ABS_PATH --session NAME [--decision-id ID] [--if-snapshot ID] --replace-editor [--text TEXT]
  kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME [--if-snapshot ID] [--force]
  kaola-tmux.sh PLATFORM drain-restart --repo ABS_PATH --session NAME (--continue | --resume ID) [--timeout SECONDS]
Transport is ACP only (Issue #130); a request for the pty transport is refused (transport-pty-retired).'
}

die() { printf 'kaola-tmux[%s]: %s\n' "${platform:-unknown}" "$*" >&2; exit 1; }
resolve_tool() { if [[ "$1" == */* ]]; then [[ -x "$1" ]] || return 1; printf '%s\n' "$1"; else command -v "$1"; fi; }
canonical_dir() { (cd "$1" 2>/dev/null && pwd -P); }
json_value() { local expression="$1"; JSON_INPUT="$(cat)" "$PYTHON_BIN" -c 'import json,os,sys; d=json.loads(os.environ["JSON_INPUT"]); v=eval(sys.argv[1], {"d":d}); print(json.dumps(v,separators=(",",":")) if isinstance(v,(dict,list,bool)) else ("" if v is None else str(v)))' "$expression"; }
emit_json() {
  "$PYTHON_BIN" -c 'import json,os,sys
d={}
for raw in sys.argv[1:]:
    kind,key,value=raw.split(":",2)
    d[key]=(value=="true") if kind=="b" else int(value) if kind=="n" else json.loads(value) if kind=="j" else value
if d.get("schema_version") == 3 and os.environ.get("KPR_CANONICAL_REPO") and "canonical_repo" not in d:
    d["canonical_repo"]=os.environ["KPR_CANONICAL_REPO"]
if d.get("schema_version") == 3 and d.get("platform") and "transport" not in d:
    d["transport"]={"selected":"acp"}
if "mutation_performed" in d and "mutation_status" not in d:
    d["mutation_status"]="completed" if d["mutation_performed"] is True else "not_started" if d["mutation_performed"] is False else "unknown"
print(json.dumps(d,ensure_ascii=False,sort_keys=True))' "$@"
}

# KPR_CANONICAL_REPO is this invocation's own channel to emit_json and kaola-acp.py;
# a value inherited from a parent Runner (a Host-dispatched seat) is not a binding.
unset KPR_CANONICAL_REPO
platform="${1:-}"; [[ -n "$platform" ]] || { usage; exit 2; }; shift
case "$platform" in grok|claude-code|opencode|kimi-cli|cursor-cli|devin|codex|zcode|droid|dsh) ;; *) die "unknown platform: $platform" ;; esac
adapter_file="$script_dir/adapters/$platform.sh"; [[ -f "$adapter_file" ]] || die "adapter not installed"
[[ -f "$MODEL_POLICY_HELPER" && -f "$ACP_CLI" ]] || die "ACP transport is not installed"
# shellcheck source=/dev/null
source "$adapter_file"
[[ "${ADAPTER_ID:-}" == "$platform" ]] || die "adapter identity mismatch"
[[ "${ADAPTER_ANSWER_MODE:-}" =~ ^(unsupported|claude-clear-v1)$ ]] || die "adapter answer mode missing"

command_name="${1:-}"; [[ -n "$command_name" ]] || { usage; exit 2; }; shift
if [[ "$command_name" == view ]]; then
  printf '%s\n' '{"error":{"code":"view-unsupported","message":"view is not a Runner command; use kaola-acp"},"schema":"kaola-acp-view/1"}'
  exit 1
fi
if [[ "$command_name" == follow ]]; then
  printf '%s\n' '{"error":{"code":"follow-unsupported","message":"follow is not a Runner command; use kaola-acp"},"kind":"error"}'
  exit 1
fi
case "$command_name" in preflight|start|observe|status|capture|send|steer|wait|permit|cancel|key|answer|stop|drain-restart) ;; *) die "unknown command: $command_name" ;; esac
repo="" session="" resume_id="" continue_mode=false force=false lines=120 text_value="" text_given=false
if_snapshot="" require_empty_editor=false decision_id="" replace_editor=false model="" effort="" permission_mode=auto
model_given=false effort_given=false permission_mode_given=false key_name="" transport="" transport_given=false
tier="" tier_given=false fast="off" fast_given=false
acp_wait=true timeout="" request_id="" option="" capture_tools=false capture_since="" capture_full=false capture_inline=false
expected_holder_instance_id="" expected_holder_instance_id_given=false steer_mode="" cancel_timeout=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) repo="$2"; shift 2 ;; --session) session="$2"; shift 2 ;; --resume) resume_id="$2"; shift 2 ;;
    --continue) continue_mode=true; shift ;; --force) force=true; shift ;; --lines) lines="$2"; shift 2 ;;
    --text) text_value="$2"; text_given=true; shift 2 ;; --if-snapshot) if_snapshot="$2"; shift 2 ;;
    --require-empty-editor) require_empty_editor=true; shift ;; --decision-id) decision_id="$2"; shift 2 ;;
    --replace-editor) replace_editor=true; shift ;; --model) model="$2"; model_given=true; shift 2 ;;
    --effort) effort="$2"; effort_given=true; shift 2 ;; --tier) tier="$2"; tier_given=true; shift 2 ;;
    --fast) fast="$2"; fast_given=true; shift 2 ;; --permission-mode) permission_mode="$2"; permission_mode_given=true; shift 2 ;;
    --transport) transport="$2"; transport_given=true; shift 2 ;; --key) key_name="$2"; shift 2 ;;
    --steer-mode) steer_mode="$2"; shift 2 ;; --cancel-timeout) cancel_timeout="$2"; shift 2 ;;
    --wait) acp_wait=true; shift ;; --no-wait) acp_wait=false; shift ;; --timeout) timeout="$2"; shift 2 ;;
    --request-id) request_id="$2"; shift 2 ;; --option) option="$2"; shift 2 ;; --tools) capture_tools=true; shift ;;
    --expected-holder-instance-id) expected_holder_instance_id="$2"; expected_holder_instance_id_given=true; shift 2 ;;
    --since) capture_since="$2"; shift 2 ;; --full) capture_full=true; shift ;; --inline) capture_inline=true; shift ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
done

if [[ ( -n "$steer_mode" || -n "$cancel_timeout" ) && "$command_name" != steer ]]; then
  die "--steer-mode and --cancel-timeout are steer-only"
fi
PYTHON_BIN="$(resolve_tool "${PYTHON_BIN:-python3}")" || die "python3 executable not found"

# Issue #130 (owner ruling 2026-09-22): PTY is retired and the Runner is ACP-only.
# A request for the pty transport on any command is refused here, from the arguments
# alone, before a manifest, Git, the canonical-root binding (#73), or the
# dispatcher (#104) is consulted, and before any process, session, or record
# exists. --transport acp stays accepted as a no-op.
if [[ "$transport_given" == true && "$transport" == pty ]]; then
  emit_json "n:schema_version:3" "s:result:refused" "s:reason:transport-pty-retired" \
    "s:action:$command_name" "s:platform:$platform" "s:session:$session" "s:repo:$repo" \
    "s:detail:PTY transport is retired (Issue #130); this Runner is ACP-only. Re-run without --transport (or with --transport acp)." \
    "b:mutation_performed:false" "j:transport:{\"requested\":\"pty\",\"supported\":[\"acp\"]}"
  exit 1
fi
[[ "$transport_given" != true || "$transport" == acp ]] || die "--transport must be acp"

# Issue #73: a Project Runner Orchestrator binds one human-selected canonical
# project root once, and every worker it dispatches afterwards uses that root.
# The binding is explicit: without KAOLA_PROJECT_RUNNER_CANONICAL_REPO this is an
# ordinary standalone invocation and nothing here applies. With it, an omitted
# --repo is completed from the bound root, and a new `start` must name exactly
# that root - a linked worktree of the same repository is a different Git
# top-level and is refused here, before any process, holder, or record
# exists. An already-located session keeps its own --repo for close-out, so
# legacy worktree-rooted work can still be observed and exactly stopped. This
# guards against accidental dispatch drift; it is not protection against a
# hostile controlling host, and it is not a second Workflow classifier.
refuse_canonical_root() {
  local reason="$1" requested="$2" bound="$3"
  emit_json "n:schema_version:3" "s:result:refused" "s:reason:$reason" \
    "s:action:$command_name" "s:platform:$platform" "s:session:$session" \
    "s:repo:$requested" "s:canonical_repo:$bound" "b:mutation_performed:false"
  exit 1
}
canonical_binding="${KAOLA_PROJECT_RUNNER_CANONICAL_REPO:-}"
if [[ -n "$canonical_binding" && ( -z "$repo" || "$command_name" == start ) ]]; then
  canonical_repo=""
  if [[ "$canonical_binding" == /* && -d "$canonical_binding" ]]; then
    canonical_repo="$(canonical_dir "$canonical_binding" || true)"
    if [[ -n "$canonical_repo" ]]; then
      canonical_root="$(git -C "$canonical_repo" rev-parse --show-toplevel 2>/dev/null || true)"
      canonical_root="$([[ -n "$canonical_root" ]] && canonical_dir "$canonical_root" || true)"
      [[ "$canonical_root" == "$canonical_repo" ]] || canonical_repo=""
    fi
  fi
  [[ -n "$canonical_repo" ]] || refuse_canonical_root canonical-root-invalid "$repo" "$canonical_binding"
  if [[ -z "$repo" ]]; then
    repo="$canonical_repo"
  else
    requested_repo="$(canonical_dir "$repo" || true)"
    [[ -n "$requested_repo" ]] || requested_repo="$repo"
    [[ "$requested_repo" == "$canonical_repo" ]] \
      || refuse_canonical_root canonical-root-mismatch "$requested_repo" "$canonical_repo"
    repo="$canonical_repo"
  fi
  # The receipt reports the bound root it passed through as one bounded fact.
  export KPR_CANONICAL_REPO="$canonical_repo"
fi

# Issue #104: the dispatcher's PTY refusal (heartbeat-host-pty-unsupported) is
# absorbed by the unconditional transport-pty-retired refusal above.
if [[ "$command_name" != preflight && ! "$session" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$ ]]; then
  die "invalid or missing --session name"
fi
acp_args=("$PYTHON_BIN" "$ACP_CLI" "$platform" "$command_name" --repo "$repo")
[[ -n "$session" ]] && acp_args+=(--session "$session")
[[ -n "$resume_id" ]] && acp_args+=(--resume "$resume_id")
[[ "$continue_mode" == true ]] && acp_args+=(--continue)
[[ "$force" == true ]] && acp_args+=(--force)
[[ "$text_given" == true ]] && acp_args+=(--text "$text_value")
[[ ( "$command_name" == send || "$command_name" == steer ) && "$text_given" == false ]] && acp_args+=(--stdin)
[[ "$acp_wait" == false ]] && acp_args+=(--no-wait)
[[ -n "$timeout" ]] && acp_args+=(--timeout "$timeout")
[[ -n "$steer_mode" ]] && acp_args+=(--steer-mode "$steer_mode")
[[ -n "$cancel_timeout" ]] && acp_args+=(--cancel-timeout "$cancel_timeout")
[[ -n "$request_id" ]] && acp_args+=(--request-id "$request_id")
[[ -n "$option" ]] && acp_args+=(--option "$option")
[[ "$expected_holder_instance_id_given" == true ]] && acp_args+=(--expected-holder-instance-id "$expected_holder_instance_id")
[[ "$capture_tools" == true ]] && acp_args+=(--tools)
[[ -n "$capture_since" ]] && acp_args+=(--since "$capture_since")
[[ "$capture_full" == true ]] && acp_args+=(--full)
[[ "$capture_inline" == true ]] && acp_args+=(--inline)
if [[ "$command_name" == start || "$command_name" == preflight || "$command_name" == drain-restart ]]; then
  # Selection inputs pass through raw; kaola-acp.py resolves presets,
  # explicit overrides, resume preservation, and Fast itself through the
  # shared model-policy helper. drain-restart carries the same flags; omitted
  # ones are filled from the seat's recorded start selection. Do not inject
  # the platform default --mode on drain-restart: an explicit --mode beats a
  # recorded mode, and kaola-acp.py supplies that default only when neither
  # is set.
  [[ "$model_given" == true ]] && acp_args+=(--model "$model")
  [[ "$effort_given" == true ]] && acp_args+=(--effort "$effort")
  [[ "$tier_given" == true ]] && acp_args+=(--tier "$tier")
  [[ "$fast_given" == true ]] && acp_args+=(--fast "$fast")
fi
if [[ "$permission_mode_given" == true ]]; then
  acp_args+=(--mode "$permission_mode")
elif [[ "$command_name" == start ]]; then
  # Measured ACP skip knobs only. Cursor/OpenCode have no configOptions.mode skip
  # value; Grok ACP is agent always-approve with no approval option.
  case "$platform" in
    kimi-cli) acp_args+=(--mode yolo) ;;
    devin) acp_args+=(--mode bypass) ;;
    claude-code) acp_args+=(--mode bypassPermissions) ;;
    codex) acp_args+=(--mode agent-full-access) ;;
    zcode) acp_args+=(--mode yolo) ;;
    droid) acp_args+=(--mode auto-high) ;;
  esac
fi
[[ "$command_name" == capture ]] && acp_args+=(--lines "$lines")
[[ "$command_name" == key ]] && acp_args+=(--key "$key_name")
[[ -n "$decision_id" ]] && acp_args+=(--request-id "$decision_id")
if [[ "$command_name" == preflight ]]; then
  # Issue #114: the adapter's base fields (runtime_version, detail, ...) are
  # added here as evidence under the ACP receipt, which wins on shared keys. A missing native binary is reported, never a gate on the ACP answer.
  base_json="$(
    repo="$(canonical_dir "$repo")"
    runtime_override="$(printenv "$ADAPTER_BIN_ENV" 2>/dev/null || true)"
    if RUNTIME_BIN="$(resolve_tool "${runtime_override:-$ADAPTER_DEFAULT_BIN}")"; then
      adapter_preflight >/dev/null 2>&1 || true
    else
      RUNTIME_BIN=""; PREFLIGHT_VERSION=unknown
      PREFLIGHT_DETAIL="$ADAPTER_DISPLAY_NAME executable not found (override with $ADAPTER_BIN_ENV)"
    fi
    emit_json "s:runtime:$ADAPTER_DISPLAY_NAME" "s:runtime_version:${PREFLIGHT_VERSION:-unknown}" "s:runtime_binary:$RUNTIME_BIN" "b:workflow_next:${PREFLIGHT_WORKFLOW_NEXT:-false}" "b:kaola_workflow_finalize:${PREFLIGHT_FINALIZE:-false}" "s:recurring_execution:$ADAPTER_RECURRING_EXECUTION" "s:project_materialization:${PREFLIGHT_PROJECT_MATERIALIZATION:-unknown}" "s:detail:${PREFLIGHT_DETAIL:-}"
  )" || base_json='{}'
  acp_rc=0; acp_receipt="$("${acp_args[@]}")" || acp_rc=$?
  BASE_JSON="$base_json" ACP_RECEIPT="$acp_receipt" "$PYTHON_BIN" -c 'import json,os
try: d=json.loads(os.environ["ACP_RECEIPT"])
except ValueError: os.environ["ACP_RECEIPT"] and print(os.environ["ACP_RECEIPT"]); raise SystemExit
if isinstance(d,dict) and "result" not in d:
  base=json.loads(os.environ["BASE_JSON"] or "{}")
  base["result"]="error" if "error" in d else "ready"
  d={**base,**d}
print(json.dumps(d,ensure_ascii=False,sort_keys=True))'
  exit "$acp_rc"
fi
exec "${acp_args[@]}"
