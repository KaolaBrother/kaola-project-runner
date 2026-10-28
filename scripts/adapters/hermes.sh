#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="hermes"
ADAPTER_DISPLAY_NAME="Hermes Agent"
ADAPTER_DEFAULT_BIN="hermes"
ADAPTER_BIN_ENV="HERMES_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="unmeasured (source-read only; #417 measures live)"
ADAPTER_ANSWER_MODE="unsupported"
ADAPTER_DEFAULT_MODEL_NAME="DeepSeek V4.1 Flash 1017"
ADAPTER_DEFAULT_MODEL_ID="deepseek/deepseek-flash"
ADAPTER_DEFAULT_MODEL_EFFORT="high"
ADAPTER_NAMED_TIERS="max"
ADAPTER_MAX_MODEL_NAME="DeepSeek V4.1 Flash 1017"
ADAPTER_MAX_MODEL_ID="deepseek/deepseek-flash"
ADAPTER_MAX_MODEL_EFFORT="max"
ADAPTER_FAST_MECHANISM="none"

# Hermes skill discovery is unmeasured (source-read only; #417 measures live).
# The Runner never reads or writes under $HERMES_HOME, so only a workspace
# carrier is ever reported and a missing carrier never gates communication.
hermes_surface() {
  local root="$1"
  [[ -f "$root/workflow-next/SKILL.md" || -f "$root/workflow-next.md" ]] || return 1
  [[ -f "$root/kaola-workflow-finalize/SKILL.md" || -f "$root/kaola-workflow-finalize.md" ]] || return 1
}

adapter_preflight() {
  local carrier="" acp_check=unavailable
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"; [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  PREFLIGHT_WORKFLOW_NEXT=false; PREFLIGHT_FINALIZE=false
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  if hermes_surface "$repo/.agents/skills"; then carrier="$repo/.agents/skills"; fi
  [[ -n "$carrier" ]] && PREFLIGHT_WORKFLOW_NEXT=true PREFLIGHT_FINALIZE=true
  # `hermes acp --check` is a read-only diagnostic and is reported, never a
  # gate. Provider setup is a human act: the Runner never runs `--setup` or
  # `--setup-browser` and never reads ~/.hermes/.env or anything under
  # $HERMES_HOME.
  "$RUNTIME_BIN" acp --check >/dev/null 2>&1 && acp_check=passed || acp_check=failed
  PREFLIGHT_DETAIL="Hermes Agent communication is available; Kaola carrier=${carrier:-not-discovered}; acp --check=$acp_check (non-gating); provider setup is a human act (\`hermes acp --setup\` or \`hermes model\`)"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  # Hermes speaks ACP through the in-repo adapter, which owns the real argv
  # (`hermes --yolo acp`, never `--accept-hooks`). The protocol has no argv
  # resume surface: resume is `session/load` and --continue is unsupported.
  ADAPTER_LAUNCH_ARGS=(acp)
  :
}

adapter_prepare_model_environment() {
  # The model is an ACP config option (configId `model`, translated by the
  # adapter to `session/set_model`), never an argv or env override.
  ADAPTER_MODEL_ENV=()
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" =~ [Hh][Ee][Rr][Mm][Ee][Ss] || "$command" == hermes* || "$command" == *"/hermes" ]] || \
    printf '%s\n' "$capture" | grep -Eq 'hermes (--yolo )?acp|Hermes Agent'
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

# Hermes session ids only ever reach the Runner through ACP session results,
# never through pane text, so there is nothing to scrape.
adapter_extract_session_id() {
  printf '%s\n' "$1" | sed -nE \
    's/.*[Ss]ession( ID)?:?[[:space:]]+([0-9a-fA-F-]{8,}).*/\2/p' | tail -1
}
