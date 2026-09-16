#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="droid"
ADAPTER_DISPLAY_NAME="Droid"
ADAPTER_DEFAULT_BIN="droid"
ADAPTER_BIN_ENV="DROID_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/quit"
ADAPTER_ANSWER_MODE="unsupported"
ADAPTER_DEFAULT_MODEL_NAME="Auto Model"
ADAPTER_DEFAULT_MODEL_ID="auto"
ADAPTER_DEFAULT_MODEL_EFFORT=""
ADAPTER_UPGRADE_MODEL_NAME="Auto Model"
ADAPTER_UPGRADE_MODEL_ID="auto"
ADAPTER_UPGRADE_MODEL_EFFORT=""
ADAPTER_FAST_MECHANISM="none"

droid_surface() {
  local root="$1"
  [[ -f "$root/skills/workflow-next/SKILL.md" || -f "$root/commands/workflow-next.md" ]] || return 1
  [[ -f "$root/skills/kaola-workflow-finalize/SKILL.md" || -f "$root/commands/kaola-workflow-finalize.md" ]] || return 1
}

adapter_preflight() {
  local settings model_value effort_value parsed user_root carrier=""
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"; [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  PREFLIGHT_WORKFLOW_NEXT=false; PREFLIGHT_FINALIZE=false
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  user_root="${FACTORY_HOME:-$HOME/.factory}"
  if droid_surface "$repo/.factory"; then carrier="$repo/.factory"
  elif droid_surface "$user_root"; then carrier="$user_root"
  fi
  [[ -n "$carrier" ]] && PREFLIGHT_WORKFLOW_NEXT=true PREFLIGHT_FINALIZE=true
  # Read-only native settings facts (~/.factory/settings.json) are evidence,
  # never a communication gate. A missing or unreadable file reports unknown.
  settings="${FACTORY_SETTINGS_FILE:-$user_root/settings.json}"
  model_value=unknown; effort_value=unknown
  if [[ -r "$settings" ]]; then
    parsed="$(DROID_SETTINGS_FILE="$settings" "$PYTHON_BIN" - 2>/dev/null || true)"
    if [[ -n "$parsed" ]]; then
      model_value="${parsed%%$'\t'*}"
      effort_value="${parsed#*$'\t'}"
      [[ -n "$model_value" ]] || model_value=unknown
      [[ -n "$effort_value" ]] || effort_value=unknown
    fi
  fi
  PREFLIGHT_DETAIL="Droid communication is available; Kaola carrier=${carrier:-not-discovered}; native settings model=${model_value} reasoningEffort=${effort_value}"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3" settings_path
  ADAPTER_LAUNCH_ARGS=()
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--resume "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--resume --last)
  fi
  # Droid PTY has no --model flag: the model comes from session defaults,
  # overridable per process through a --settings file merged for that process
  # only. The overlay is written into the run's temp area -- never ~/.factory,
  # never the repository. Auto Model is the Runner default; reasoningEffort
  # is pinned only when the caller explicitly selected it.
  if [[ -n "$RESOLVED_MODEL_ID" || -n "$RESOLVED_MODEL_EFFORT" ]]; then
    settings_path="$(mktemp "${TMPDIR:-/tmp}/kpr-droid-settings.XXXXXX")"
    DROID_MODEL_ID="$RESOLVED_MODEL_ID" DROID_MODEL_EFFORT="$RESOLVED_MODEL_EFFORT" \
      "$PYTHON_BIN" - "$settings_path" <<'PY'
import json, os, sys
payload = {}
if os.environ.get("DROID_MODEL_ID"):
    payload["model"] = os.environ["DROID_MODEL_ID"]
if os.environ.get("DROID_MODEL_EFFORT"):
    payload["reasoningEffort"] = os.environ["DROID_MODEL_EFFORT"]
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(payload, handle, sort_keys=True)
PY
    ADAPTER_LAUNCH_ARGS+=(--settings "$settings_path")
  fi
  # Permission modes: default bypass is --skip-permissions-unsafe, the
  # autonomy levels --auto low|medium|high, and manual gets no flag.
  case "${permission_mode:-bypassPermissions}" in
    bypassPermissions) ADAPTER_LAUNCH_ARGS+=(--skip-permissions-unsafe) ;;
    low|medium|high) ADAPTER_LAUNCH_ARGS+=(--auto "$permission_mode") ;;
    manual) ;;
  esac
}

adapter_prepare_model_environment() { ADAPTER_MODEL_ENV=(); }

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" =~ [Dd]roid || "$command" == droid* ]] || \
    printf '%s\n' "$capture" | grep -Eqi 'Droid' || \
    printf '%s\n' "$capture" | grep -Fqi 'Waiting for response'
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 16)"
  # Live droid 0.220.0 TUI (verified 2026-09-17): every generation spinner row
  # carries "(Press ESC to stop)" regardless of its verb, and the ready input
  # row is the boxed composer "│ >" prompt; bare "❯/›/>" rows are selection
  # dialogs, not the composer. Busy wins first, so the always-present composer
  # row reports idle only once the spinner row is gone.
  if printf '%s\n' "$tail_sample" | grep -Eqi 'Waiting for response|Press Esc to interrupt|esc to stop|Working|Thinking|Thinking…|Responding|running tool|esc to interrupt'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|>)|^│[[:space:]]*>'; then printf '%s\n' idle
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

adapter_extract_session_id() {
  printf '%s\n' "$1" | sed -nE \
    's/.*Session ID: ([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}).*/\1/p' | tail -1
}
