#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

failures=0
fail() {
  printf 'RED: %s — %s\n' "$1" "$2" >&2
  failures=$((failures + 1))
}

capture_command() {
  # The Issue #8 model contract is a PTY-surface receipt; ACP-default manifests
  # would route these calls to the holder instead of the adapter/fake binary.
  local output rc
  set +e
  output="$(TMUX_BIN="$issue_tmux_bin" bash "$runner" "$@" --transport pty 2>&1)"
  rc=$?
  set -e
  COMMAND_OUTPUT="$output"
  COMMAND_RC="$rc"
}

json_has_model_contract() {
  JSON_INPUT="$1" python3 - <<'PY'
import json
import os

try:
    payload = json.loads(os.environ["JSON_INPUT"])
except Exception:
    raise SystemExit(1)

required = {
    "requested_model_source",
    "requested_model_name",
    "resolved_runtime_model_id",
    "resolved_parameters",
    "actual_runtime_model_id",
    "actual_parameters",
    "model_verified",
    "model_mismatch_reason",
}

def dictionaries(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dictionaries(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionaries(child)

keys = set().union(*(item.keys() for item in dictionaries(payload)))
raise SystemExit(0 if required <= keys else 1)
PY
}

assert_model_evidence() {
  local label="$1" input="$2" source="$3" requested="$4" resolved="$5" actual="$6" verified="$7" effort="$8"
  if ! LABEL="$label" JSON_INPUT="$input" EXPECTED_SOURCE="$source" EXPECTED_REQUESTED="$requested" \
      EXPECTED_RESOLVED="$resolved" EXPECTED_ACTUAL="$actual" EXPECTED_VERIFIED="$verified" \
      EXPECTED_EFFORT="$effort" python3 - <<'PY'
import json
import os

label = os.environ["LABEL"]
payload = json.loads(os.environ["JSON_INPUT"])

def dictionaries(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dictionaries(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionaries(child)

objects = list(dictionaries(payload))

def field(name):
    values = [obj[name] for obj in objects if name in obj]
    if not values:
        raise AssertionError(f"{label}: missing machine-readable {name}")
    return values[0]

assert field("requested_model_source") == os.environ["EXPECTED_SOURCE"]
assert field("requested_model_name") == os.environ["EXPECTED_REQUESTED"]
assert field("resolved_runtime_model_id") == os.environ["EXPECTED_RESOLVED"]

actual = field("actual_runtime_model_id")
expected_actual = os.environ["EXPECTED_ACTUAL"]
if expected_actual == "__UNREADABLE__":
    assert actual in (None, "", "unknown", "unreadable"), actual
else:
    assert actual == expected_actual, actual

verified = field("model_verified")
if isinstance(verified, bool):
    verified = str(verified).lower()
assert verified == os.environ["EXPECTED_VERIFIED"], verified

resolved_parameters = field("resolved_parameters")
assert isinstance(resolved_parameters, dict), resolved_parameters
expected_effort = os.environ["EXPECTED_EFFORT"]
if expected_effort:
    assert resolved_parameters.get("effort") == expected_effort, resolved_parameters
if os.environ["EXPECTED_RESOLVED"] == "cursor-grok-4.6-xhigh":
    assert resolved_parameters.get("fast") is False, resolved_parameters

actual_parameters = field("actual_parameters")
assert actual_parameters is None or isinstance(actual_parameters, dict), actual_parameters

reason = field("model_mismatch_reason")
if os.environ["EXPECTED_VERIFIED"] == "true":
    assert reason in (None, ""), reason
else:
    assert isinstance(reason, str) and reason.strip(), reason

provenance = None
for name in ("model_evidence_provenance", "model_provenance"):
    matches = [obj[name] for obj in objects if name in obj]
    if matches:
        provenance = matches[0]
        break
assert isinstance(provenance, dict) and provenance, "missing structured model evidence provenance"
assert any(key in provenance for key in ("catalog", "catalog_probe", "resolution", "requested")), provenance
if os.environ["EXPECTED_VERIFIED"] in {"true", "false"}:
    assert any(key in provenance for key in ("actual", "runtime", "tui", "session")), provenance
PY
  then
    fail "$label" "model evidence assertion failed: $input"
  fi
}

assert_unavailable_evidence() {
  local label="$1" input="$2" requested="$3"
  if ! LABEL="$label" JSON_INPUT="$input" EXPECTED_REQUESTED="$requested" python3 - <<'PY'
import json
import os

label = os.environ["LABEL"]
payload = json.loads(os.environ["JSON_INPUT"])

def dictionaries(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dictionaries(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionaries(child)

objects = list(dictionaries(payload))

def field(name):
    values = [obj[name] for obj in objects if name in obj]
    if not values:
        raise AssertionError(f"{label}: missing {name}")
    return values[0]

assert field("requested_model_source") == "user"
assert field("requested_model_name") == os.environ["EXPECTED_REQUESTED"]
assert field("resolved_runtime_model_id") in (None, "", "unavailable")
verified = field("model_verified")
if isinstance(verified, bool):
    verified = str(verified).lower()
assert verified in ("false", "unknown"), verified
reason = field("model_mismatch_reason")
assert isinstance(reason, str) and reason.strip(), reason
provenance = None
for name in ("model_evidence_provenance", "model_provenance"):
    matches = [obj[name] for obj in objects if name in obj]
    if matches:
        provenance = matches[0]
        break
assert isinstance(provenance, dict) and provenance, provenance
PY
  then
    fail "$label" "typed unavailable evidence assertion failed: $input"
  fi
}

assert_no_workflow_injection() {
  local label="$1" input_log="$2"
  if [[ -f "$input_log" ]] && grep -Fqi 'workflow-next' "$input_log"; then
    fail "$label" "Runner injected workflow-next: $(cat "$input_log")"
  fi
}

stop_or_kill() {
  local platform="$1" repo="$2" session="$3"
  TMUX_BIN="$issue_tmux_bin" bash "$runner" "$platform" stop --repo "$repo" --session "$session" --force --transport pty >/dev/null 2>&1 ||
    "$issue_tmux_bin" kill-session -t "=$session" 2>/dev/null || true
}

write_fake_runtime() {
  local path="$1"
  cat >"$path" <<'FAKE_RUNTIME'
#!/usr/bin/env bash
set -euo pipefail

runtime="${FAKE_RUNTIME_NAME:?}"
argv_log="${FAKE_ARGV_LOG:?}"
input_log="${FAKE_INPUT_LOG:?}"
printf 'cwd=%q\targs=' "$PWD" >>"$argv_log"
printf '%q ' "$@" >>"$argv_log"
printf '\teffort_env=%q\n' "${KIMI_MODEL_THINKING_EFFORT:-}" >>"$argv_log"

if [[ "${1:-}" == --version || "${1:-}" == version ]]; then
  printf '%s\n' "$runtime model-policy-fixture 1.0.0"
  exit 0
fi

emit_catalog_json() {
  python3 - <<'PY'
import json
import os

def entry(model_id, name, efforts):
    value = {"id": model_id, "name": name, "efforts": efforts, "fast": False}
    if os.environ.get("FAKE_CATALOG_SERVICE_TIER"):
        value["service_tiers"] = [{"id": "priority", "name": "Fast"}]
        value["additional_speed_tiers"] = ["fast"]
    return value

models = [
    entry(
        os.environ["FAKE_DEFAULT_MODEL_ID"],
        os.environ["FAKE_DEFAULT_MODEL_NAME"],
        [os.environ["FAKE_DEFAULT_EFFORT"]],
    ),
    entry(
        os.environ["FAKE_OVERRIDE_MODEL_ID"],
        os.environ["FAKE_OVERRIDE_MODEL_ID"],
        ["medium", "high", "max"],
    ),
    entry(
        os.environ["FAKE_UPGRADE_MODEL_ID"],
        os.environ["FAKE_UPGRADE_MODEL_NAME"],
        [os.environ["FAKE_UPGRADE_EFFORT"]],
    ),
]
if os.environ.get("FAKE_CATALOG_FAST_VARIANT"):
    models.append(entry(
        os.environ["FAKE_DEFAULT_MODEL_ID"] + "-fast",
        os.environ["FAKE_DEFAULT_MODEL_NAME"] + " Fast",
        [os.environ["FAKE_DEFAULT_EFFORT"]],
    ))
print(json.dumps({
    "version": "model-policy-fixture 1.0.0",
    "grokVersion": "model-policy-fixture 1.0.0",
    "models": models,
    "skills": [{"name": "workflow-next"}, {"name": "kaola-workflow-finalize"}],
}))
PY
}

case "${1:-}" in
  inspect)
    emit_catalog_json
    exit 0
    ;;
  doctor)
    emit_catalog_json
    exit 0
    ;;
  debug|provider)
    emit_catalog_json
    exit 0
    ;;
  --help|-h|help)
    printf '%s\n' \
      '--model <model>' \
      '--effort <low|medium|high|max>' \
      '--reasoning-effort <low|medium|high|xhigh>' \
      '--variant <low|high|max>' \
      "${FAKE_DEFAULT_MODEL_NAME}|${FAKE_DEFAULT_MODEL_ID}|effort=${FAKE_DEFAULT_EFFORT}|fast=false" \
      "${FAKE_OVERRIDE_MODEL_ID}|${FAKE_OVERRIDE_MODEL_ID}|effort=high|fast=false"
    exit 0
    ;;
  models|model-list|list-models|--list-models|catalog|schema)
    emit_catalog_json
    exit 0
    ;;
  model)
    if [[ "${2:-}" =~ ^(list|ls|catalog)$ ]]; then
      emit_catalog_json
      exit 0
    fi
    ;;
esac

selected=""
effort=""
has_resume=false
fast_tier=""
args=("$@")
index=0
while (( index < ${#args[@]} )); do
  argument="${args[$index]}"
  case "$argument" in
    --model|-m)
      index=$((index + 1))
      selected="${args[$index]:-}"
      ;;
    --model=*) selected="${argument#--model=}" ;;
    --effort|--reasoning-effort|--variant)
      index=$((index + 1))
      effort="${args[$index]:-}"
      ;;
    --effort=*|--reasoning-effort=*|--variant=*) effort="${argument#*=}" ;;
    --settings)
      index=$((index + 1))
      if [[ -n "${args[$index]:-}" && -r "${args[$index]}" ]]; then
        read -r settings_model settings_effort < <(SETTINGS_PATH="${args[$index]}" python3 - <<'PY'
import json
import os
try:
    data = json.load(open(os.environ["SETTINGS_PATH"], encoding="utf-8"))
except Exception:
    raise SystemExit(0)
print((str(data.get("model") or "")) + " " + (str(data.get("reasoningEffort") or "")))
PY
)
        [[ -z "$selected" && -n "$settings_model" ]] && selected="$settings_model"
        [[ -z "$effort" && -n "$settings_effort" ]] && effort="$settings_effort"
      fi
      ;;
    -c|--config)
      index=$((index + 1))
      case "${args[$index]:-}" in
        model_reasoning_effort=*)
          effort="${args[$index]#model_reasoning_effort=}"
          effort="${effort%\"}"
          effort="${effort#\"}"
          ;;
        service_tier=*)
          fast_tier="${args[$index]#service_tier=}"
          fast_tier="${fast_tier%\"}"
          fast_tier="${fast_tier#\"}"
          ;;
      esac
      ;;
    resume)
      has_resume=true
      ;;
    --resume|--session)
      has_resume=true
      index=$((index + 1))
      ;;
  esac
  index=$((index + 1))
done
if [[ -z "$effort" && "$runtime" == kimi-cli ]]; then
  effort="${KIMI_MODEL_THINKING_EFFORT:-}"
fi
if [[ -z "$effort" && "$runtime" == cursor-cli ]]; then
  effort=xhigh
fi
if [[ -z "$effort" ]]; then
  case "$selected" in
    *-xhigh) effort=xhigh ;;
    *-high) effort=high ;;
    *-medium) effort=medium ;;
    *-low) effort=low ;;
    *-max) effort=max ;;
  esac
fi
selected_fast=false
case "$selected" in *-fast|*-priority) selected_fast=true ;; esac
[[ "$fast_tier" == fast ]] && selected_fast=true

actual="$selected"
[[ -n "$actual" ]] || actual="${FAKE_SAVED_MODEL_ID:?}"
case "${FAKE_MODEL_SCENARIO:-match}" in
  mismatch) actual="${FAKE_SAVED_MODEL_ID:?}" ;;
  resume-mismatch) [[ "$has_resume" == true ]] && actual="${FAKE_SAVED_MODEL_ID:?}" ;;
esac

printf 'event=launch\tselected=%q\teffort=%q\tactual=%q\tresume=%s\tfast_tier=%q\n' \
  "$selected" "$effort" "$actual" "$has_resume" "$fast_tier" >>"$argv_log"

case "$runtime" in
  grok) title=grok ;;
  claude-code) title='Claude Code' ;;
  opencode) title=OpenCode ;;
  kimi-cli) title=Kimi ;;
  cursor-cli) title=Cursor ;;
  devin) title=Devin ;;
  codex) title='OpenAI Codex' ;;
  droid) title=droid ;;
esac
printf '\033]0;%s\007' "$title"
printf '%s\n' "$title Kaola TUI"
if [[ "${FAKE_MODEL_SCENARIO:-match}" == unreadable ]]; then
  printf '%s\n' 'Active model evidence unavailable'
else
  printf 'Active model: %s | effort=%s | fast=%s\n' "$actual" "$effort" "$selected_fast"
  ACTUAL_MODEL="$actual" ACTUAL_EFFORT="$effort" ACTUAL_FAST="$selected_fast" python3 - <<'PY'
import json
import os
print("KPR_MODEL_EVIDENCE " + json.dumps({
    "model_id": os.environ["ACTUAL_MODEL"],
    "parameters": {
        "effort": os.environ["ACTUAL_EFFORT"],
        "fast": os.environ["ACTUAL_FAST"] == "true",
    },
    "source": "main-tui",
}))
PY
fi
printf '%s\n' 'Ask anything' 'ctrl+p cmd' 'minimal · /help' '❯ '
while IFS= read -r line; do
  printf '%s\n' "$line" >>"$input_log"
  [[ "$line" == /exit || "$line" == /quit ]] && exit 0
  printf 'ECHO:%s\n❯ ' "$line"
done
FAKE_RUNTIME
  chmod +x "$path"
}

issue_setup
trap issue_cleanup EXIT

repo="$(issue_new_repo model-policy)"
export KAOLA_START_TIMEOUT=4

platforms=(grok claude-code opencode kimi-cli cursor-cli devin codex droid)
for platform in "${platforms[@]}"; do
  case "$platform" in
    claude-code)
      default_name='Opus High'; default_id=opus; default_effort=high; binary_env=CLAUDE_BIN
      upgrade_name='Fable High'; upgrade_id=fable; upgrade_effort=high
      override_id=sonnet; override_effort=medium
      ;;
    cursor-cli)
      default_name='Grok 4.6 Extra High'; default_id=cursor-grok-4.6-xhigh; default_effort=xhigh; binary_env=CURSOR_AGENT_BIN
      upgrade_name='Claude Fable 5.1 High'; upgrade_id=claude-fable-5-1-high; upgrade_effort=high
      override_id=cursor-gpt-5.2; override_effort=high
      ;;
    grok)
      default_name='Grok 4.6 Extra High'; default_id=grok-4.6; default_effort=xhigh; binary_env=GROK_BIN
      upgrade_name='Grok 4.6 Extra High'; upgrade_id=grok-4.6; upgrade_effort=xhigh
      override_id=grok-code-fast-1; override_effort=high
      ;;
    opencode)
      default_name='CLI native opening model'; default_id=''; default_effort=''; binary_env=OPENCODE_BIN
      upgrade_name='CLI native opening model'; upgrade_id=''; upgrade_effort=''
      override_id=openai/gpt-5.2-codex; override_effort=high
      ;;
    kimi-cli)
      default_name='Kimi 2.8 Max'; default_id=kimi-code/kimi-for-coding; default_effort=max; binary_env=KIMI_BIN
      upgrade_name='Kimi K3 Max'; upgrade_id=kimi-code/k3; upgrade_effort=max
      override_id=kimi-code/k2.5; override_effort=high
      ;;
    devin)
      default_name='SWE-2 Max'; default_id=swe-2-max; default_effort=''; binary_env=DEVIN_BIN
      upgrade_name='Fusion High (Fable 5.1 High + SWE-2 Medium)'; upgrade_id=fusion-claude-fable-5-1-high-sidekick-swe-2-medium; upgrade_effort=''
      override_id=claude-sonnet-5-high; override_effort=''
      ;;
    codex)
      default_name='GPT-5.6 Sol High'; default_id=gpt-5.6-sol; default_effort=high; binary_env=CODEX_BIN
      upgrade_name='GPT-6 Astra High'; upgrade_id=gpt-6-astra; upgrade_effort=high
      override_id=gpt-6-astra; override_effort=high
      ;;
    droid)
      default_name='Auto Model'; default_id=auto; default_effort=''; binary_env=DROID_BIN
      upgrade_name='Auto Model'; upgrade_id=auto; upgrade_effort=''
      override_id=gpt-5.6-sol; override_effort=high
      ;;
  esac

  fake="$issue_tmp_root/$platform-model-fake"
  argv_log="$issue_tmp_root/$platform-model-argv.log"
  input_log="$issue_tmp_root/$platform-model-input.log"
  write_fake_runtime "$fake"
  printf -v "$binary_env" '%s' "$fake"
  export "$binary_env"
  export FAKE_RUNTIME_NAME="$platform" FAKE_ARGV_LOG="$argv_log" FAKE_INPUT_LOG="$input_log"
  export FAKE_DEFAULT_MODEL_NAME="$default_name" FAKE_DEFAULT_MODEL_ID="$default_id"
  export FAKE_DEFAULT_EFFORT="$default_effort" FAKE_OVERRIDE_MODEL_ID="$override_id"
  export FAKE_UPGRADE_MODEL_NAME="$upgrade_name" FAKE_UPGRADE_MODEL_ID="$upgrade_id"
  export FAKE_UPGRADE_EFFORT="$upgrade_effort"
  export FAKE_SAVED_MODEL_ID="saved-picker/$platform-other" FAKE_MODEL_SCENARIO=match
  export FAKE_CATALOG_FAST_VARIANT= FAKE_CATALOG_SERVICE_TIER=

  preflight_session="model-preflight-${platform}-$$"
  capture_command "$platform" preflight --repo "$repo" --session "$preflight_session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_default_model_preflight" "preflight failed: $COMMAND_OUTPUT"
    continue
  fi
  if ! json_has_model_contract "$COMMAND_OUTPUT"; then
    fail "test_${platform}_default_model_preflight" "missing Issue #8 model contract: $COMMAND_OUTPUT"
    # Avoid a cascade of slow tmux cases on a baseline with no model-policy
    # surface. Once the preflight contract exists, every behavioral case below
    # becomes mandatory for this platform.
    continue
  fi
  if [[ "$platform" == opencode ]]; then
    # Issue #34: OpenCode presets keep the CLI's own opening model — no Runner
    # model or effort override is resolved or launched.
    assert_model_evidence "test_${platform}_default_model_preflight" "$COMMAND_OUTPUT" \
      runner-default "$default_name" "" __UNREADABLE__ unknown ""
    capture_command "$platform" preflight --repo "$repo" --session "$preflight_session" --tier upgrade
    assert_model_evidence "test_${platform}_upgrade_tier_preflight" "$COMMAND_OUTPUT" \
      runner-upgrade "$upgrade_name" "" __UNREADABLE__ unknown ""
  else
    assert_model_evidence "test_${platform}_default_model_preflight" "$COMMAND_OUTPUT" \
      runner-default "$default_name" "$default_id" __UNREADABLE__ unknown "$default_effort"
    capture_command "$platform" preflight --repo "$repo" --session "$preflight_session" --tier upgrade
    assert_model_evidence "test_${platform}_upgrade_tier_preflight" "$COMMAND_OUTPUT" \
      runner-upgrade "$upgrade_name" "$upgrade_id" __UNREADABLE__ unknown "$upgrade_effort"
  fi

  session="model-default-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_runner_default_overrides_saved_picker" "start failed: $COMMAND_OUTPUT"
  else
    if [[ "$platform" == opencode ]]; then
      assert_model_evidence "test_${platform}_runner_default_keeps_native_opening_model" "$COMMAND_OUTPUT" \
        runner-default "$default_name" "" "$FAKE_SAVED_MODEL_ID" unknown ""
      status_json="$(TMUX_BIN="$issue_tmux_bin" bash "$runner" "$platform" status --repo "$repo" --session "$session" --transport pty)"
      assert_model_evidence "test_${platform}_status_preserves_model_provenance" "$status_json" \
        runner-default "$default_name" "" "$FAKE_SAVED_MODEL_ID" unknown ""
      grep -Fq "event=launch" "$argv_log" || fail "test_${platform}_runner_default_launches" "runtime launch was not recorded"
      if grep -Eq -- '--model|--variant' <<<"$(grep 'args=' "$argv_log" | tail -1)"; then
        fail "test_${platform}_runner_default_keeps_native_opening_model" "Runner forced a model/effort override on the native preset: $(cat "$argv_log")"
      fi
    else
      assert_model_evidence "test_${platform}_runner_default_overrides_saved_picker" "$COMMAND_OUTPUT" \
        runner-default "$default_name" "$default_id" "$default_id" true "$default_effort"
      status_json="$(TMUX_BIN="$issue_tmux_bin" bash "$runner" "$platform" status --repo "$repo" --session "$session" --transport pty)"
      assert_model_evidence "test_${platform}_status_preserves_model_provenance" "$status_json" \
        runner-default "$default_name" "$default_id" "$default_id" true "$default_effort"
      grep -Fq "event=launch" "$argv_log" || fail "test_${platform}_runner_default_launches" "runtime launch was not recorded"
      grep -Fq "selected=$default_id" "$argv_log" || fail "test_${platform}_runner_default_overrides_saved_picker" "resolved model absent from launch argv: $(cat "$argv_log")"
      grep -Fq "selected=${FAKE_SAVED_MODEL_ID}" "$argv_log" && fail "test_${platform}_saved_picker_not_runner_default" "saved picker was launched as Runner default"
    fi
  fi
  assert_no_workflow_injection "test_${platform}_default_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=match
  session="model-upgrade-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --tier upgrade
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_upgrade_tier_launch" "upgrade-tier start failed: $COMMAND_OUTPUT"
  else
    if [[ "$platform" == opencode ]]; then
      assert_model_evidence "test_${platform}_upgrade_tier_launch" "$COMMAND_OUTPUT" \
        runner-upgrade "$upgrade_name" "" "$FAKE_SAVED_MODEL_ID" unknown ""
    else
      assert_model_evidence "test_${platform}_upgrade_tier_launch" "$COMMAND_OUTPUT" \
        runner-upgrade "$upgrade_name" "$upgrade_id" "$upgrade_id" true "$upgrade_effort"
      grep -Fq "selected=$upgrade_id" "$argv_log" || \
        fail "test_${platform}_upgrade_tier_launch" "upgrade model absent from launch argv: $(cat "$argv_log")"
    fi
  fi
  assert_no_workflow_injection "test_${platform}_upgrade_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  session="model-user-${platform}-$$"
  if [[ -n "$override_effort" ]]; then
    capture_command "$platform" start --repo "$repo" --session "$session" --model "$override_id" --effort "$override_effort"
  else
    capture_command "$platform" start --repo "$repo" --session "$session" --model "$override_id"
  fi
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_user_model_override" "start failed: $COMMAND_OUTPUT"
  else
    assert_model_evidence "test_${platform}_user_model_override" "$COMMAND_OUTPUT" \
      user "$override_id" "$override_id" "$override_id" true "$override_effort"
  fi
  assert_no_workflow_injection "test_${platform}_user_override_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  session="model-user-noeffort-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --model "$override_id"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_user_model_without_effort" "start failed: $COMMAND_OUTPUT"
  else
    # Issue #34: a different explicit model without explicit effort leaves the
    # native effort alone — no preset effort is attached.
    assert_model_evidence "test_${platform}_user_model_without_effort_keeps_native_effort" "$COMMAND_OUTPUT" \
      user "$override_id" "$override_id" "$override_id" true ""
  fi
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  session="model-unavailable-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --model "unavailable/$platform"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_unavailable_model_is_not_a_launch_gate" "catalog-missing literal was refused: $COMMAND_OUTPUT"
  else
    assert_model_evidence "test_${platform}_unavailable_model_launches_literal_with_catalog_evidence" \
      "$COMMAND_OUTPUT" user "unavailable/$platform" "unavailable/$platform" "unavailable/$platform" true ""
    grep -Fq "selected=unavailable/$platform" "$argv_log" || \
      fail "test_${platform}_unavailable_model_launches_literal" "literal model absent from launch argv: $(cat "$argv_log")"
  fi
  if "$issue_tmux_bin" has-session -t "=$session" 2>/dev/null; then
    stop_or_kill "$platform" "$repo" "$session"
  fi
  assert_no_workflow_injection "test_${platform}_unavailable_does_not_inject_workflow" "$input_log"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=mismatch
  session="model-mismatch-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_actual_mismatch_is_evidence_not_communication_gate" "start was blocked: $COMMAND_OUTPUT"
  else
    if [[ "$platform" == opencode ]]; then
      assert_model_evidence "test_${platform}_actual_mismatch_is_reported" "$COMMAND_OUTPUT" \
        runner-default "$default_name" "" "$FAKE_SAVED_MODEL_ID" unknown ""
    else
      assert_model_evidence "test_${platform}_actual_mismatch_is_reported" "$COMMAND_OUTPUT" \
        runner-default "$default_name" "$default_id" "$FAKE_SAVED_MODEL_ID" false "$default_effort"
    fi
  fi
  assert_no_workflow_injection "test_${platform}_mismatch_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=unreadable
  session="model-unreadable-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_unreadable_actual_is_evidence_not_communication_gate" "start was blocked: $COMMAND_OUTPUT"
  else
    if [[ "$platform" == opencode ]]; then
      assert_model_evidence "test_${platform}_unreadable_actual_is_unknown" "$COMMAND_OUTPUT" \
        runner-default "$default_name" "" __UNREADABLE__ unknown ""
    else
      assert_model_evidence "test_${platform}_unreadable_actual_is_unknown" "$COMMAND_OUTPUT" \
        runner-default "$default_name" "$default_id" __UNREADABLE__ unknown "$default_effort"
    fi
  fi
  assert_no_workflow_injection "test_${platform}_unreadable_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=match
  session="model-continue-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --continue
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_continue_preserves_saved_model" "continue failed: $COMMAND_OUTPUT"
  else
    # Issue #34: --continue/--resume with no tier/model/effort preserves the
    # saved native session selection; the actual model is evidence, not a
    # comparison against a Runner-resolved target.
    assert_model_evidence "test_${platform}_continue_preserves_saved_model" "$COMMAND_OUTPUT" \
      resume-preserved "native saved session selection" "" "$FAKE_SAVED_MODEL_ID" unknown ""
    if grep -Eq -- '--model|--reasoning-effort|--variant|model_reasoning_effort' <<<"$(grep 'args=' "$argv_log" | tail -1)"; then
      fail "test_${platform}_continue_preserves_saved_model" "Runner overrode the preserved selection: $(cat "$argv_log")"
    fi
  fi
  assert_no_workflow_injection "test_${platform}_continue_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  session="model-resume-preserve-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --resume "fixture-$platform-session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_resume_preserves_saved_model" "resume failed: $COMMAND_OUTPUT"
  else
    assert_model_evidence "test_${platform}_resume_preserves_saved_model" "$COMMAND_OUTPUT" \
      resume-preserved "native saved session selection" "" "$FAKE_SAVED_MODEL_ID" unknown ""
  fi
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  session="model-resume-tier-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --resume "fixture-$platform-session" --tier upgrade
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_resume_tier_overrides_preserved" "resume+tier failed: $COMMAND_OUTPUT"
  else
    if [[ "$platform" == opencode ]]; then
      assert_model_evidence "test_${platform}_resume_tier_overrides_preserved" "$COMMAND_OUTPUT" \
        runner-upgrade "$upgrade_name" "" "$FAKE_SAVED_MODEL_ID" unknown ""
    else
      assert_model_evidence "test_${platform}_resume_tier_overrides_preserved" "$COMMAND_OUTPUT" \
        runner-upgrade "$upgrade_name" "$upgrade_id" "$upgrade_id" true "$upgrade_effort"
    fi
  fi
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=resume-mismatch
  session="model-resume-${platform}-$$"
  if [[ -n "$override_effort" ]]; then
    capture_command "$platform" start --repo "$repo" --session "$session" --resume "fixture-$platform-session" \
      --model "$override_id" --effort "$override_effort"
  else
    capture_command "$platform" start --repo "$repo" --session "$session" --resume "fixture-$platform-session" \
      --model "$override_id"
  fi
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_resume_mismatch_is_evidence_not_communication_gate" "resume was blocked: $COMMAND_OUTPUT"
  else
    assert_model_evidence "test_${platform}_resume_does_not_claim_override" "$COMMAND_OUTPUT" \
      user "$override_id" "$override_id" "$FAKE_SAVED_MODEL_ID" false "$override_effort"
  fi
  assert_no_workflow_injection "test_${platform}_resume_mismatch_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=match
  marker="$repo/model-input-executed-$platform"
  malicious="model with spaces (x) [y]; \$(touch $marker); \`touch $marker.backtick\`"
  session="model-literal-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --model "$malicious"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_malicious_model_is_not_a_launch_gate" "malicious literal was refused: $COMMAND_OUTPUT"
  else
    assert_model_evidence "test_${platform}_malicious_model_is_reported_literally" \
      "$COMMAND_OUTPUT" user "$malicious" "$malicious" "$malicious" true ""
  fi
  [[ ! -e "$marker" && ! -e "$marker.backtick" ]] || \
    fail "test_${platform}_model_input_is_literal_safe" "model input executed shell syntax"
  if "$issue_tmux_bin" has-session -t "=$session" 2>/dev/null; then
    stop_or_kill "$platform" "$repo" "$session"
  fi
  assert_no_workflow_injection "test_${platform}_malicious_input_does_not_inject_workflow" "$input_log"

  : >"$input_log"
  session="model-fast-${platform}-$$"
  case "$platform" in
    codex)
      # Config-mechanism platform: Fast off is applied as service_tier=default;
      # --fast on applies service_tier=fast — per-run, never a global write.
      capture_command "$platform" start --repo "$repo" --session "$session"
      if [[ "$COMMAND_RC" -eq 0 ]]; then
        grep -Fq 'service_tier=\"default\"' "$argv_log" || \
          fail "test_${platform}_fast_off_applies_default_tier" "launch argv lacks service_tier=default: $(cat "$argv_log")"
      else
        fail "test_${platform}_fast_off_applies_default_tier" "start failed: $COMMAND_OUTPUT"
      fi
      stop_or_kill "$platform" "$repo" "$session"
      session="model-fast-on-${platform}-$$"
      capture_command "$platform" start --repo "$repo" --session "$session" --fast on
      if [[ "$COMMAND_RC" -eq 0 ]]; then
        grep -Fq 'service_tier=\"fast\"' "$argv_log" || \
          fail "test_${platform}_fast_on_applies_fast_tier" "launch argv lacks service_tier=fast: $(cat "$argv_log")"
        assert_model_evidence "test_${platform}_fast_on_applies_fast_tier" "$COMMAND_OUTPUT" \
          runner-default "$default_name" "$default_id" "$default_id" true "$default_effort"
      else
        fail "test_${platform}_fast_on_applies_fast_tier" "start failed: $COMMAND_OUTPUT"
      fi
      ;;
    cursor-cli)
      # Model-variant platform: --fast on picks the catalog's -fast variant.
      export FAKE_CATALOG_FAST_VARIANT=true
      capture_command "$platform" start --repo "$repo" --session "$session" --fast on
      export FAKE_CATALOG_FAST_VARIANT=
      if [[ "$COMMAND_RC" -eq 0 ]]; then
        grep -Fq "selected=${default_id}-fast" "$argv_log" || \
          fail "test_${platform}_fast_on_resolves_catalog_variant" "fast variant absent from launch argv: $(cat "$argv_log")"
      else
        fail "test_${platform}_fast_on_resolves_catalog_variant" "start failed: $COMMAND_OUTPUT"
      fi
      session="model-fast-fable-${platform}-$$"
      capture_command "$platform" start --repo "$repo" --session "$session" --tier upgrade --fast on
      if [[ "$COMMAND_RC" -eq 0 ]]; then
        grep -Fq "selected=$upgrade_id" "$argv_log" || \
          fail "test_${platform}_fable_fast_unsupported_keeps_base_model" "unexpected model in launch argv: $(cat "$argv_log")"
        if ! JSON_INPUT="$COMMAND_OUTPUT" python3 -c 'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["model"].get("resolved_fast") == "unsupported", d.get("model")'; then
          fail "test_${platform}_fable_fast_unsupported_keeps_base_model" "expected resolved_fast=unsupported: $COMMAND_OUTPUT"
        fi
      else
        fail "test_${platform}_fable_fast_unsupported_keeps_base_model" "start failed: $COMMAND_OUTPUT"
      fi
      ;;
    devin)
      # Model-variant platform whose presets advertise no fast variant.
      capture_command "$platform" start --repo "$repo" --session "$session" --fast on
      if [[ "$COMMAND_RC" -eq 0 ]]; then
        grep -Fq "selected=$default_id" "$argv_log" || \
          fail "test_${platform}_preset_fast_unsupported_keeps_base_model" "unexpected model in launch argv: $(cat "$argv_log")"
        if ! JSON_INPUT="$COMMAND_OUTPUT" python3 -c 'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["model"].get("resolved_fast") == "unsupported", d.get("model")'; then
          fail "test_${platform}_preset_fast_unsupported_keeps_base_model" "expected resolved_fast=unsupported: $COMMAND_OUTPUT"
        fi
      else
        fail "test_${platform}_preset_fast_unsupported_keeps_base_model" "start failed: $COMMAND_OUTPUT"
      fi
      ;;
    claude-code)
      # Settings-mechanism platform: --settings '{"fastMode": ...}' is a
      # process-scoped launch pin passed verbatim — false by default, true
      # on explicit opt-in. The native CLI decides model support; the Runner
      # never infers it and never changes the selected model.
      capture_command "$platform" start --repo "$repo" --session "$session"
      if [[ "$COMMAND_RC" -eq 0 ]]; then
        grep -Eq -- 'fastMode.{0,6}false' "$argv_log" || \
          fail "test_${platform}_fast_off_pins_settings" "launch argv lacks fastMode=false pin: $(cat "$argv_log")"
      else
        fail "test_${platform}_fast_off_pins_settings" "start failed: $COMMAND_OUTPUT"
      fi
      stop_or_kill "$platform" "$repo" "$session"
      session="model-fast-on-${platform}-$$"
      capture_command "$platform" start --repo "$repo" --session "$session" --fast on
      if [[ "$COMMAND_RC" -eq 0 ]]; then
        launch_args="$(grep 'args=' "$argv_log" | tail -1)"
        grep -Eq -- 'fastMode.{0,6}true' <<<"$launch_args" || \
          fail "test_${platform}_fast_on_applies_settings" "launch argv lacks fastMode=true: $launch_args"
        if ! JSON_INPUT="$COMMAND_OUTPUT" python3 -c 'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["model"].get("resolved_fast") == "on", d.get("model")'; then
          fail "test_${platform}_fast_on_applies_settings" "expected resolved_fast=on: $COMMAND_OUTPUT"
        fi
      else
        fail "test_${platform}_fast_on_applies_settings" "start failed: $COMMAND_OUTPUT"
      fi
      stop_or_kill "$platform" "$repo" "$session"
      session="model-fast-explicit-${platform}-$$"
      capture_command "$platform" start --repo "$repo" --session "$session" --model "$upgrade_id" --fast on
      if [[ "$COMMAND_RC" -eq 0 ]]; then
        # An explicit model + --fast on passes fastMode=true verbatim: the
        # Runner does not classify model support — the selection is
        # preserved exactly and native support is the CLI's determination.
        explicit_args="$(grep 'args=' "$argv_log" | grep -F -- "--model $upgrade_id" | tail -1)"
        grep -Eq -- 'fastMode.{0,6}true' <<<"$explicit_args" || \
          fail "test_${platform}_explicit_fast_passes_verbatim" "launch argv lacks fastMode=true: $explicit_args"
        grep -Fq "selected=$upgrade_id" "$argv_log" || \
          fail "test_${platform}_explicit_fast_keeps_selected_model" "unexpected model in launch argv: $(cat "$argv_log")"
        if ! JSON_INPUT="$COMMAND_OUTPUT" python3 -c 'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["model"].get("resolved_fast") == "on", d.get("model")'; then
          fail "test_${platform}_explicit_fast_passes_verbatim" "expected resolved_fast=on: $COMMAND_OUTPUT"
        fi
      else
        fail "test_${platform}_explicit_fast_passes_verbatim" "start failed: $COMMAND_OUTPUT"
      fi
      ;;
    *)
      # No native Fast mechanism: --fast on is reported unsupported, never
      # applied, and never blocks the launch.
      capture_command "$platform" start --repo "$repo" --session "$session" --fast on
      if [[ "$COMMAND_RC" -eq 0 ]]; then
        if ! JSON_INPUT="$COMMAND_OUTPUT" python3 -c 'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["model"].get("resolved_fast") == "unsupported", d.get("model")'; then
          fail "test_${platform}_fast_on_unsupported_is_reported" "expected resolved_fast=unsupported: $COMMAND_OUTPUT"
        fi
      else
        fail "test_${platform}_fast_on_unsupported_is_reported" "start failed: $COMMAND_OUTPUT"
      fi
      ;;
  esac
  if "$issue_tmux_bin" has-session -t "=$session" 2>/dev/null; then
    stop_or_kill "$platform" "$repo" "$session"
  fi
  export FAKE_MODEL_SCENARIO=match
done

assert_launch_preamble_is_not_actual_evidence() {
  local platform="$1" frame="$2" expected_id="$3" effort="$4" frame_file output
  frame_file="$(mktemp "${TMPDIR:-/tmp}/kpr-model-frame.XXXXXX")"
  printf '%s\n' "$frame" >"$frame_file"
  output="$(python3 "$project_root/scripts/kaola-model-policy.py" verify \
    --platform "$platform" \
    --policy-json "{\"resolved_runtime_model_id\":\"$expected_id\",\"resolved_parameters\":{\"effort\":\"$effort\"}}" \
    --frame-file "$frame_file")"
  rm -f "$frame_file"
  if ! JSON_INPUT="$output" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["JSON_INPUT"])
assert payload["actual_runtime_model_id"] is None, payload
assert payload["actual_parameters"] is None, payload
assert payload["model_verified"] == "unknown", payload
assert payload["model_mismatch_reason"] == "actual-model-evidence-unreadable", payload
PY
  then
    fail "test_${platform}_launch_preamble_is_not_actual_model_evidence" "$output"
  fi
}

assert_launch_preamble_is_not_actual_evidence opencode \
  'exec kaola-pane-relay.py --runtime-path opencode -- --model zhipuai-coding-plan/glm-5.3
ylpromax5@YanleiMacBook-Pro-M5-Max issue-8 %
OpenCode
Ask anything...' \
  zhipuai-coding-plan/glm-5.3 max
assert_launch_preamble_is_not_actual_evidence kimi-cli \
  'exec kaola-pane-relay.py --runtime-path kimi -- --model kimi-code/k3
ylpromax5@YanleiMacBook-Pro-M5-Max issue-8 %
Trust this folder?
Exit Kimi Code. Asked again next launch.' \
  kimi-code/k3 max
assert_launch_preamble_is_not_actual_evidence codex \
  'exec kaola-pane-relay.py --runtime-path codex -- --cd /repo --no-alt-screen --model gpt-5.6-luna -c model_reasoning_effort=\"low\"
ylpromax5@YanleiMacBook-Pro-M5-Max issue-8 %
OpenAI Codex' \
  gpt-5.6-luna low

verified_frame="$(mktemp "${TMPDIR:-/tmp}/kpr-model-frame.XXXXXX")"
scrolled_frame="$(mktemp "${TMPDIR:-/tmp}/kpr-model-frame.XXXXXX")"
printf '%s\n' 'Grok Build v1.0.13' 'Grok 4.6 (xhigh)' >"$verified_frame"
printf '%s\n' 'The model footer has scrolled away.' >"$scrolled_frame"
initial_policy='{"resolved_runtime_model_id":"grok-4.6","resolved_parameters":{"effort":"xhigh","fast":false},"actual_runtime_model_id":null,"actual_parameters":null,"model_verified":"unknown","model_mismatch_reason":"actual-model-evidence-not-yet-read","model_evidence_provenance":{}}'
verified_policy="$(python3 "$project_root/scripts/kaola-model-policy.py" verify --platform grok --policy-json "$initial_policy" --frame-file "$verified_frame")"
scrolled_policy="$(python3 "$project_root/scripts/kaola-model-policy.py" verify --platform grok --policy-json "$verified_policy" --frame-file "$scrolled_frame")"
rm -f "$verified_frame" "$scrolled_frame"
if ! JSON_INPUT="$scrolled_policy" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["JSON_INPUT"])
assert payload["actual_runtime_model_id"] == "grok-4.6", payload
assert payload["actual_parameters"] == {"effort": "xhigh", "fast": False}, payload
assert payload["model_verified"] is True, payload
assert payload["model_evidence_provenance"]["actual"]["source"] == "grok-main-tui", payload
assert payload["model_evidence_provenance"]["latest_observation"]["source"] == "unreadable", payload
PY
then
  fail "test_last_confirmed_model_survives_scrolled_frame" "$scrolled_policy"
fi

if [[ "$failures" -gt 0 ]]; then
  printf 'Issue #8 model-policy acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Issue #8 model-policy acceptance: PASS\n'
