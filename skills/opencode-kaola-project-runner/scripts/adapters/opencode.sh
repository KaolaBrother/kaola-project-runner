#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="opencode"
ADAPTER_DISPLAY_NAME="OpenCode"
ADAPTER_DEFAULT_BIN="opencode"
ADAPTER_BIN_ENV="OPENCODE_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"
ADAPTER_ANSWER_MODE="unsupported"

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
  local config_root="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}" carrier
  if opencode_surface "$repo/.opencode"; then carrier="$repo/.opencode"
  elif opencode_surface "$config_root"; then carrier="$config_root"
  else die "missing complete OpenCode Kaola commands, agents, plugin, or support scripts"
  fi
  [[ -f "$repo/opencode.json" || -f "$config_root/opencode.json" ]] || \
    die "missing project or user OpenCode configuration"
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1)"
  PREFLIGHT_WORKFLOW_NEXT=true
  PREFLIGHT_FINALIZE=true
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  PREFLIGHT_DETAIL="complete OpenCode Kaola carrier at $carrier; user opencode.json preserved"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=("$launch_repo" --mini)
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--session "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  # OpenCode 1.18.x keeps the terminal title at the host name. Under the managed relay tmux's
  # foreground command is the attested Python relay, so use the live stable TUI chrome only after
  # the core has bound the exact child runtime path.
  [[ "$title" =~ [Oo]pen[Cc]ode || "$command" == opencode* ]] && return 0
  [[ "$capture" == *OpenCode* && "$capture" == *'Ask anything'* && "$capture" == *'ctrl+p cmd'* ]]
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 18)"
  if printf '%s\n' "$tail_sample" | grep -Eqi 'working|thinking|running|responding|esc to cancel|interrupt'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|>)|Ask anything|ctrl\+p cmd'; then printf '%s\n' idle
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
