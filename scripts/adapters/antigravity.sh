#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="antigravity"
ADAPTER_DISPLAY_NAME="Antigravity"
ADAPTER_DEFAULT_BIN="agy"
ADAPTER_BIN_ENV="AGY_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"
ADAPTER_ANSWER_MODE="unsupported"
ADAPTER_DEFAULT_MODEL_NAME="Gemini 4 Argon"
ADAPTER_DEFAULT_MODEL_ID="gemini-4-argon-medium"
ADAPTER_DEFAULT_MODEL_EFFORT="medium"
ADAPTER_NAMED_TIERS="xhigh"
ADAPTER_XHIGH_MODEL_NAME="Gemini 4 Argon"
ADAPTER_XHIGH_MODEL_ID="gemini-4-argon-high"
ADAPTER_XHIGH_MODEL_EFFORT="high"
ADAPTER_FAST_MECHANISM="none"

# agy discovers workspace Skills at <workspace>/.agents/skills/<name>/SKILL.md
# (its own embedded help text). The user root lives under ~/.gemini, which the
# Runner never reads or writes, so the carrier is reported for the workspace
# root only and a missing carrier never gates communication.
antigravity_surface() {
  local root="$1"
  [[ -f "$root/workflow-next/SKILL.md" || -f "$root/workflow-next.md" ]] || return 1
  [[ -f "$root/kaola-workflow-finalize/SKILL.md" || -f "$root/kaola-workflow-finalize.md" ]] || return 1
}

adapter_preflight() {
  local carrier=""
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"; [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  PREFLIGHT_WORKFLOW_NEXT=false; PREFLIGHT_FINALIZE=false
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  if antigravity_surface "$repo/.agents/skills"; then carrier="$repo/.agents/skills"; fi
  [[ -n "$carrier" ]] && PREFLIGHT_WORKFLOW_NEXT=true PREFLIGHT_FINALIZE=true
  # Sign-in is deliberately not probed here: a model turn is the only thing that
  # tells a signed-in account from an unsigned or ineligible one, and preflight
  # never spends a turn. The ACP probe reports login_required from session/new.
  PREFLIGHT_DETAIL="Antigravity communication is available; Kaola carrier=${carrier:-not-discovered}; sign-in is reported by the ACP probe (login_required), not here"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  # agy's headless stream protocol is the only transport: ACP is spoken by the
  # in-repo adapter, which owns the real agy argv (model, mode, --conversation).
  ADAPTER_LAUNCH_ARGS=(--input-format stream-json --output-format stream-json)
  :
}

adapter_prepare_model_environment() {
  # The model is an ACP config option applied by the adapter as --model,
  # never an environment override.
  ADAPTER_MODEL_ENV=()
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" =~ [Aa][Gg][Yy] || "$command" == agy* || "$command" == *"/agy" ]] || \
    printf '%s\n' "$capture" | grep -Eq 'agy --input-format|Antigravity'
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

# agy conversation ids are UUIDs and reach the Runner through the adapter's
# native_session_identity update, never through pane text.
adapter_extract_session_id() {
  printf '%s\n' "$1" | sed -nE \
    's/.*[Cc]onversation( ID| id)?:?[[:space:]]+([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}).*/\2/p' | tail -1
}
