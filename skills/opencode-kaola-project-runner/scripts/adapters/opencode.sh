#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="opencode"
ADAPTER_DISPLAY_NAME="OpenCode"
ADAPTER_DEFAULT_BIN="opencode"
ADAPTER_BIN_ENV="OPENCODE_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"
ADAPTER_ANSWER_MODE="unsupported"
ADAPTER_DEFAULT_MODEL_NAME="CLI native opening model"
ADAPTER_DEFAULT_MODEL_ID=""
ADAPTER_DEFAULT_MODEL_EFFORT=""
ADAPTER_UPGRADE_MODEL_NAME="CLI native opening model"
ADAPTER_UPGRADE_MODEL_ID=""
ADAPTER_UPGRADE_MODEL_EFFORT=""
ADAPTER_FAST_MECHANISM="none"

opencode_surface() {
  local root="$1"
  [[ -f "$root/commands/workflow-next.md" || -f "$root/command/workflow-next.md" ]] || return 1
  [[ -f "$root/commands/kaola-workflow-finalize.md" || -f "$root/command/kaola-workflow-finalize.md" ]] || return 1
  [[ -f "$root/agents/.kaola-workflow-agent-manifest" || -f "$root/agents/implementer.md" || \
     -f "$root/agents/kaola.md" ]] || return 1
  [[ -f "$root/plugins/kaola-workflow-hooks.js" || -f "$root/plugins/kaola.js" ]] || return 1
  [[ -f "$root/kaola-workflow/scripts/kaola-workflow-claim.js" ]] || return 1
}

adapter_preflight() {
  local config_root="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}" carrier="" config_state=missing
  local forward_proxy="${HTTP_PROXY:-${http_proxy:-${HTTPS_PROXY:-${https_proxy:-}}}}" loopback=direct
  if opencode_surface "$repo/.opencode"; then carrier="$repo/.opencode"
  elif opencode_surface "$config_root"; then carrier="$config_root"
  fi
  [[ -f "$repo/opencode.json" || -f "$config_root/opencode.json" ]] && config_state=present
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"; [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  PREFLIGHT_WORKFLOW_NEXT=false; PREFLIGHT_FINALIZE=false
  [[ -n "$carrier" ]] && PREFLIGHT_WORKFLOW_NEXT=true PREFLIGHT_FINALIZE=true
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  # Issue #112: OpenCode V2 reaches its own server over loopback HTTP for every
  # command. A forward proxy that does not exclude loopback swallows that hop —
  # `opencode acp` then answers every session method with ClientError and the
  # background service reads as stopped (upstream anomalyco/opencode#31096
  # fixed the same class on the V1 line). Report it; never gate on it.
  if [[ -n "$forward_proxy" ]]; then
    case ",${NO_PROXY:-${no_proxy:-}}," in
      *,127.0.0.1,*|*,localhost,*) loopback=excluded ;;
      *) loopback=proxied ;;
    esac
  fi
  PREFLIGHT_DETAIL="OpenCode communication is available; Kaola carrier=${carrier:-not-discovered}; configuration=$config_state; loopback=$loopback"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  # Issue #112, measured on opencode v2.0.11: the top-level command still takes
  # the directory and --auto, but V2 removed --mini ("Unrecognized flag: --mini
  # in command opencode"); `mini` is a subcommand that accepts neither a
  # directory nor --auto, so it cannot carry this launch. --session and
  # --continue remain top-level V2 flags.
  ADAPTER_LAUNCH_ARGS=("$launch_repo" --auto)
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--session "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
  # Issue #34: presets keep OpenCode's own opening model — no Runner model or
  # effort override. Issue #112: V2 also rejects top-level --model and --variant
  # ("Unrecognized flag"), so an explicit caller model rides
  # adapter_prepare_model_environment rather than argv; passing either flag here
  # would abort the launch outright.
}

adapter_prepare_model_environment() {
  if [[ -z "$RESOLVED_MODEL_ID" && -z "$RESOLVED_MODEL_EFFORT" ]]; then
    ADAPTER_MODEL_ENV=()
    return 0
  fi
  local existing="${OPENCODE_CONFIG_CONTENT:-}" merged
  merged="$(EXISTING_OPENCODE_CONFIG="$existing" MODEL_ID="$RESOLVED_MODEL_ID" MODEL_EFFORT="$RESOLVED_MODEL_EFFORT" "$PYTHON_BIN" - <<'PY'
import json, os
try:
    value = json.loads(os.environ.get("EXISTING_OPENCODE_CONFIG") or "{}")
except json.JSONDecodeError:
    value = {}
# Issue #112: the V2 migration guide renames `agent` to `agents` and folds the
# variant into the model reference after "#" (provider/model#variant), so the
# V1 sibling `variant` key no longer exists. Measured on 2.0.11:
# OPENCODE_CONFIG_CONTENT did not change the selected model on any of the acp,
# run, or models paths, so this payload is written in the shape the guide
# documents and is not relied on as a working override.
agent = value.setdefault("agents", {}).setdefault("build", {})
model_id = os.environ.get("MODEL_ID") or ""
effort = os.environ.get("MODEL_EFFORT") or ""
if model_id:
    agent["model"] = f"{model_id}#{effort}" if effort else model_id
print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
PY
)"
  ADAPTER_MODEL_ENV=("OPENCODE_CONFIG_CONTENT=$merged")
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  # OpenCode keeps the terminal title at the host name. Under the managed relay tmux's
  # foreground command is the attested Python relay, so use the live stable TUI chrome only after
  # the core has bound the exact child runtime path.
  [[ "$title" =~ [Oo]pen[Cc]ode || "$command" == opencode* ]] && return 0
  # Issue #112, captured live on 2.0.11: the V2 TUI draws the product name as block-character
  # art rather than the literal string, and its footer hint reads "ctrl+p commands" where 1.18.x
  # read "ctrl+p cmd" - "cmd" is not a substring of "commands", so the old three-way test could
  # no longer match. The footer is the one chrome element present on every frame; the "Ask
  # anything" placeholder only survives until the first turn completes.
  [[ "$capture" == *'ctrl+p cmd'* || "$capture" == *'ctrl+p command'* ]] && return 0
  [[ "$capture" == *OpenCode* && "$capture" == *'Ask anything'* ]]
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 18)"
  if printf '%s\n' "$tail_sample" | grep -Eqi 'working|thinking|running|responding|esc to cancel|interrupt'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|>)|Ask anything|ctrl\+p (cmd|command)'; then printf '%s\n' idle
  else printf '%s\n' unknown
  fi
}

adapter_observe_frame() {
  local frame="$1" pane_facts="${2:-}" hint helper python_bin
  [[ -n "$pane_facts" ]] || pane_facts='{}'
  hint="$(adapter_activity_hint "$frame")"
  helper="${OBSERVATION_HELPER:-$(dirname "$ADAPTER_SOURCE_DIR")/kaola-observation.py}"
  python_bin="${PYTHON_BIN:-python3}"
  printf '%s' "$frame" | KPR_ADAPTER_PANE_FACTS="$pane_facts" "$python_bin" "$helper" opencode-frame "$hint"
}

adapter_extract_session_id() { printf '%s\n' "$1" | sed -nE 's/.*(ses_[A-Za-z0-9_-]+).*/\1/p' | tail -1; }
