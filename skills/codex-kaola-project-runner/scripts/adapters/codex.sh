#!/usr/bin/env bash

# Codex CLI adapter: Codex surfaces may come from ~/.codex/skills, the repo
# .codex/skills, or a marketplace plugin carrier under ~/.codex/plugins/cache.

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="codex"
ADAPTER_DISPLAY_NAME="Codex CLI"
ADAPTER_DEFAULT_BIN="codex"
ADAPTER_BIN_ENV="CODEX_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/quit"
ADAPTER_ANSWER_MODE="unsupported"
ADAPTER_DEFAULT_MODEL_NAME="GPT-6 Sol High"
ADAPTER_DEFAULT_MODEL_ID="gpt-6-sol"
ADAPTER_DEFAULT_MODEL_EFFORT="high"
ADAPTER_UPGRADE_MODEL_NAME="GPT-6 Astra High"
ADAPTER_UPGRADE_MODEL_ID="gpt-6-astra"
ADAPTER_UPGRADE_MODEL_EFFORT="high"
ADAPTER_FAST_MECHANISM="config"

codex_surface() {
  local root="$1"
  { [[ -f "$root/skills/kaola-workflow-next/SKILL.md" ]] || \
    [[ -f "$root/skills/workflow-next/SKILL.md" ]]; } && \
  { [[ -f "$root/skills/kaola-workflow-finalize/SKILL.md" ]] || \
    [[ -f "$root/skills/workflow-finalize/SKILL.md" ]]; }
}

adapter_preflight() {
  local codex_root="${CODEX_HOME:-$HOME/.codex}" carrier="" source=""
  if codex_surface "$repo/.codex"; then
    carrier="$repo/.codex"
    source="project"
  elif codex_surface "$codex_root"; then
    carrier="$codex_root"
    source="user"
  else
    local skills_dir
    for skills_dir in "$codex_root"/plugins/cache/*/*/*/skills; do
      [[ -d "$skills_dir" ]] || continue
      if codex_surface "${skills_dir%/skills}"; then
        carrier="${skills_dir%/skills}"
        source="plugin-cache"
        break
      fi
    done
  fi
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>/dev/null | head -1 | tr -d '\r')"
  PREFLIGHT_VERSION="${PREFLIGHT_VERSION:-unknown}"
  PREFLIGHT_WORKFLOW_NEXT=false
  PREFLIGHT_FINALIZE=false
  if [[ -n "$carrier" ]]; then
    PREFLIGHT_WORKFLOW_NEXT=true
    PREFLIGHT_FINALIZE=true
  fi
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  PREFLIGHT_DETAIL="Codex CLI communication is available; Kaola carrier=${carrier:-not-discovered}${source:+ ($source)}"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=()
  if [[ -n "$resume_id" ]]; then
    ADAPTER_LAUNCH_ARGS+=(resume "$resume_id")
  elif [[ "$continue_mode" == true ]]; then
    ADAPTER_LAUNCH_ARGS+=(resume --last)
  fi
  ADAPTER_LAUNCH_ARGS+=(--cd "$launch_repo" --no-alt-screen)
  if [[ -n "$RESOLVED_MODEL_ID" ]]; then
    ADAPTER_LAUNCH_ARGS+=(--model "$RESOLVED_MODEL_ID")
  fi
  if [[ -n "$RESOLVED_MODEL_EFFORT" ]]; then
    ADAPTER_LAUNCH_ARGS+=(-c "model_reasoning_effort=\"$RESOLVED_MODEL_EFFORT\"")
  fi
  # Fast is a per-run service tier override scoped to this launch only.
  case "$RESOLVED_FAST" in
    on) ADAPTER_LAUNCH_ARGS+=(-c "service_tier=\"fast\"") ;;
    off) ADAPTER_LAUNCH_ARGS+=(-c "service_tier=\"default\"") ;;
  esac
  case "$permission_mode" in
    read-only)
      ADAPTER_LAUNCH_ARGS+=(--sandbox read-only --ask-for-approval on-request)
      ;;
    agent)
      ADAPTER_LAUNCH_ARGS+=(--sandbox workspace-write --ask-for-approval on-request)
      ;;
    agent-full-access)
      ADAPTER_LAUNCH_ARGS+=(--sandbox danger-full-access --ask-for-approval never)
      ;;
    *)
      die "unsupported Codex permission mode ${permission_mode:-<unset>}: expected read-only|agent|agent-full-access"
      ;;
  esac
}

adapter_prepare_model_environment() { ADAPTER_MODEL_ENV=(); }

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" =~ [Cc]odex ]] || {
    [[ "$capture" == *"OpenAI Codex"* ]] && \
    [[ "$capture" == *"Ask Codex to do anything"* || "$capture" == *"model:"* ]]
  }
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 16)"
  if printf '%s\n' "$tail_sample" | grep -Eq 'esc[[:space:]]+to[[:space:]]+(interrupt|cancel)|Working[[:space:]]*\(|Thinking|Starting[[:space:]]+MCP'; then
    printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eq 'HUMAN_DECISION_REQUIRED|[Aa]pproval|Would[[:space:]]+you[[:space:]]+like|Trust[[:space:]]+this|Update[[:space:]]+available|Press[[:space:]]+enter'; then
    printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq 'Ask Codex to do anything|^›'; then
    printf '%s\n' idle
  else
    printf '%s\n' unknown
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
  # Codex's default frame does not publish a session id; resume identity stays
  # caller-supplied. Never derive one from echoed prompt text.
  printf ''
}
