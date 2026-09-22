#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="dsh"
ADAPTER_DISPLAY_NAME="dsh"
ADAPTER_DEFAULT_BIN="dsh"
ADAPTER_BIN_ENV="DSH_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"
ADAPTER_ANSWER_MODE="unsupported"
ADAPTER_DEFAULT_MODEL_NAME="DeepSeek V4.1 Flash (OpenCode Go)"
ADAPTER_DEFAULT_MODEL_ID="opencode-go/deepseek-v4.1-flash"
ADAPTER_DEFAULT_MODEL_EFFORT=""
ADAPTER_UPGRADE_MODEL_NAME="DeepSeek V4.1 Flash (OpenCode Go)"
ADAPTER_UPGRADE_MODEL_ID="opencode-go/deepseek-v4.1-flash"
ADAPTER_UPGRADE_MODEL_EFFORT=""
ADAPTER_FAST_MECHANISM="none"

# dsh discovers local skills from these roots (dsh-skill-filesystem ranks
# project-dsh, project-agents, then user-dsh). The user root is read, never
# written: the Runner must not modify anything under $DSH_HOME.
dsh_surface() {
  local root="$1"
  [[ -f "$root/workflow-next/SKILL.md" || -f "$root/workflow-next.md" ]] || return 1
  [[ -f "$root/kaola-workflow-finalize/SKILL.md" || -f "$root/kaola-workflow-finalize.md" ]] || return 1
}

adapter_preflight() {
  local dsh_home="${DSH_HOME:-$HOME/.dsh}" carrier="" acp_profile=missing
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"; [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  PREFLIGHT_WORKFLOW_NEXT=false; PREFLIGHT_FINALIZE=false
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  if dsh_surface "$repo/.dsh/skills"; then carrier="$repo/.dsh/skills"
  elif dsh_surface "$repo/.agents/skills"; then carrier="$repo/.agents/skills"
  elif dsh_surface "$dsh_home/skills"; then carrier="$dsh_home/skills"
  fi
  [[ -n "$carrier" ]] && PREFLIGHT_WORKFLOW_NEXT=true PREFLIGHT_FINALIZE=true
  # The ACP transport boots the `acp` profile. Its absence is reported, never
  # repaired: creating one needs --from-default-profile, which writes under
  # $DSH_HOME, and that is an operator act.
  [[ -f "$dsh_home/profiles/acp/package.json" ]] && acp_profile=present
  PREFLIGHT_DETAIL="dsh communication is available; Kaola carrier=${carrier:-not-discovered}; acp profile=$acp_profile under $dsh_home (read-only)"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  # dsh ships no terminal UI. Its shipped profile templates are exactly acp,
  # headless, sdk, sdk-minimal and web (@deepseek-ai/dsh-app-boot's
  # PROFILE_TEMPLATES): web is a browser app, headless answers one task and
  # exits, sdk/sdk-minimal are programmatic, and acp is a JSON-RPC stdio
  # server. None is a pane conversation; ACP is the only transport (#130).
  ADAPTER_LAUNCH_ARGS=(--profile acp)
  # The acp profile accepts no application arguments: resume is the protocol
  # call session/resume, and --continue is unsupported because session/list
  # carries no updatedAt to order candidates by.
  :
}

adapter_prepare_model_environment() {
  # The model is an ACP config option (configId `model`), never an argv or env
  # override, so a resolved selection travels over the protocol instead.
  ADAPTER_MODEL_ENV=()
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" =~ [Dd][Ss][Hh] || "$command" == dsh* || "$command" == *"/dsh" ]] || \
    printf '%s\n' "$capture" | grep -Eq 'dsh --profile|DeepSeek Harness'
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 16)"
  if printf '%s\n' "$tail_sample" | grep -Eqi 'esc to cancel|esc to interrupt|Thinking|Working|Responding'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|>)'; then printf '%s\n' idle
  else printf '%s\n' unknown
  fi
}

adapter_observe_frame() {
  local frame="$1" pane_facts="${2:-}" hint helper python_bin
  [[ -n "$pane_facts" ]] || pane_facts='{}'
  hint="$(adapter_activity_hint "$frame")"
  helper="${OBSERVATION_HELPER:-$(dirname "$ADAPTER_SOURCE_DIR")/kaola-observation.py}"
  python_bin="${PYTHON_BIN:-python3}"
  printf '%s' "$frame" | KPR_ADAPTER_PANE_FACTS="$pane_facts" "$python_bin" "$helper" generic-frame "$hint"
}

# dsh session ids are bare UUIDs and only ever reach the Runner through the ACP
# session/new result, never through pane text, so there is nothing to scrape.
adapter_extract_session_id() {
  printf '%s\n' "$1" | sed -nE \
    's/.*[Ss]ession( ID)?:?[[:space:]]+([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}).*/\2/p' | tail -1
}
