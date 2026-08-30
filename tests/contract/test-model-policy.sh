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
  local output rc
  set +e
  output="$(TMUX_BIN="$issue_tmux_bin" bash "$runner" "$@" 2>&1)"
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
  TMUX_BIN="$issue_tmux_bin" bash "$runner" "$platform" stop --repo "$repo" --session "$session" --force >/dev/null 2>&1 ||
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

models = [
    {
        "id": os.environ["FAKE_DEFAULT_MODEL_ID"],
        "name": os.environ["FAKE_DEFAULT_MODEL_NAME"],
        "efforts": [os.environ["FAKE_DEFAULT_EFFORT"]],
        "fast": False,
    },
    {
        "id": os.environ["FAKE_OVERRIDE_MODEL_ID"],
        "name": os.environ["FAKE_OVERRIDE_MODEL_ID"],
        "efforts": ["medium", "high", "max"],
        "fast": False,
    },
]
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
  models|model-list|list-models|catalog|schema)
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

actual="$selected"
[[ -n "$actual" ]] || actual="${FAKE_SAVED_MODEL_ID:?}"
case "${FAKE_MODEL_SCENARIO:-match}" in
  mismatch) actual="${FAKE_SAVED_MODEL_ID:?}" ;;
  resume-mismatch) [[ "$has_resume" == true ]] && actual="${FAKE_SAVED_MODEL_ID:?}" ;;
esac

printf 'event=launch\tselected=%q\teffort=%q\tactual=%q\tresume=%s\n' \
  "$selected" "$effort" "$actual" "$has_resume" >>"$argv_log"

case "$runtime" in
  grok) title=grok ;;
  claude-code) title='Claude Code' ;;
  opencode) title=OpenCode ;;
  kimi-cli) title=Kimi ;;
  cursor-cli) title=Cursor ;;
esac
printf '\033]0;%s\007' "$title"
printf '%s\n' "$title Kaola TUI"
if [[ "${FAKE_MODEL_SCENARIO:-match}" == unreadable ]]; then
  printf '%s\n' 'Active model evidence unavailable'
else
  printf 'Active model: %s | effort=%s | fast=false\n' "$actual" "$effort"
  ACTUAL_MODEL="$actual" ACTUAL_EFFORT="$effort" python3 - <<'PY'
import json
import os
print("KPR_MODEL_EVIDENCE " + json.dumps({
    "model_id": os.environ["ACTUAL_MODEL"],
    "parameters": {"effort": os.environ["ACTUAL_EFFORT"], "fast": False},
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

platforms=(grok claude-code opencode kimi-cli cursor-cli)
for platform in "${platforms[@]}"; do
  case "$platform" in
    claude-code)
      default_name='Opus 5 High'; default_id=opus; default_effort=high; binary_env=CLAUDE_BIN
      override_id=sonnet; override_effort=medium
      ;;
    cursor-cli)
      default_name='Grok 4.6 Extra High'; default_id=cursor-grok-4.6-xhigh; default_effort=xhigh; binary_env=CURSOR_AGENT_BIN
      override_id=cursor-gpt-5.2; override_effort=high
      ;;
    grok)
      default_name='Grok 4.6 Extra High'; default_id=grok-4.6; default_effort=xhigh; binary_env=GROK_BIN
      override_id=grok-code-fast-1; override_effort=high
      ;;
    opencode)
      default_name='GLM 5.3 Max'; default_id=zhipuai-coding-plan/glm-5.3; default_effort=max; binary_env=OPENCODE_BIN
      override_id=openai/gpt-5.2-codex; override_effort=high
      ;;
    kimi-cli)
      default_name='Kimi K3 Max'; default_id=kimi-code/k3; default_effort=max; binary_env=KIMI_BIN
      override_id=kimi-code/k2.5; override_effort=high
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
  export FAKE_SAVED_MODEL_ID="saved-picker/$platform-other" FAKE_MODEL_SCENARIO=match

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
  assert_model_evidence "test_${platform}_default_model_preflight" "$COMMAND_OUTPUT" \
    runner-default "$default_name" "$default_id" __UNREADABLE__ unknown "$default_effort"

  session="model-default-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_runner_default_overrides_saved_picker" "start failed: $COMMAND_OUTPUT"
  else
    assert_model_evidence "test_${platform}_runner_default_overrides_saved_picker" "$COMMAND_OUTPUT" \
      runner-default "$default_name" "$default_id" "$default_id" true "$default_effort"
    status_json="$(TMUX_BIN="$issue_tmux_bin" bash "$runner" "$platform" status --repo "$repo" --session "$session")"
    assert_model_evidence "test_${platform}_status_preserves_model_provenance" "$status_json" \
      runner-default "$default_name" "$default_id" "$default_id" true "$default_effort"
    grep -Fq "event=launch" "$argv_log" || fail "test_${platform}_runner_default_launches" "runtime launch was not recorded"
    grep -Fq "selected=$default_id" "$argv_log" || fail "test_${platform}_runner_default_overrides_saved_picker" "resolved model absent from launch argv: $(cat "$argv_log")"
    grep -Fq "selected=${FAKE_SAVED_MODEL_ID}" "$argv_log" && fail "test_${platform}_saved_picker_not_runner_default" "saved picker was launched as Runner default"
  fi
  assert_no_workflow_injection "test_${platform}_default_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=match
  session="model-user-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --model "$override_id" --effort "$override_effort"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_user_model_override" "start failed: $COMMAND_OUTPUT"
  else
    assert_model_evidence "test_${platform}_user_model_override" "$COMMAND_OUTPUT" \
      user "$override_id" "$override_id" "$override_id" true "$override_effort"
  fi
  assert_no_workflow_injection "test_${platform}_user_override_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  session="model-unavailable-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --model "unavailable/$platform"
  if [[ "$COMMAND_RC" -eq 0 ]]; then
    fail "test_${platform}_unavailable_model_refuses_unselected_launch" "unavailable target unexpectedly launched: $COMMAND_OUTPUT"
  else
    assert_unavailable_evidence "test_${platform}_unavailable_model_reports_catalog_evidence" \
      "$COMMAND_OUTPUT" "unavailable/$platform"
  fi
  if "$issue_tmux_bin" has-session -t "=$session" 2>/dev/null; then
    fail "test_${platform}_unavailable_model_creates_no_session" "unavailable target created a session"
    "$issue_tmux_bin" kill-session -t "=$session" 2>/dev/null || true
  fi
  assert_no_workflow_injection "test_${platform}_unavailable_does_not_inject_workflow" "$input_log"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=mismatch
  session="model-mismatch-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_actual_mismatch_is_evidence_not_communication_gate" "start was blocked: $COMMAND_OUTPUT"
  else
    assert_model_evidence "test_${platform}_actual_mismatch_is_reported" "$COMMAND_OUTPUT" \
      runner-default "$default_name" "$default_id" "$FAKE_SAVED_MODEL_ID" false "$default_effort"
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
    assert_model_evidence "test_${platform}_unreadable_actual_is_unknown" "$COMMAND_OUTPUT" \
      runner-default "$default_name" "$default_id" __UNREADABLE__ unknown "$default_effort"
  fi
  assert_no_workflow_injection "test_${platform}_unreadable_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=match
  session="model-continue-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --continue
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "test_${platform}_continue_reverifies_model" "continue failed: $COMMAND_OUTPUT"
  else
    assert_model_evidence "test_${platform}_continue_reverifies_model" "$COMMAND_OUTPUT" \
      runner-default "$default_name" "$default_id" "$default_id" true "$default_effort"
  fi
  assert_no_workflow_injection "test_${platform}_continue_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"

  : >"$input_log"
  export FAKE_MODEL_SCENARIO=resume-mismatch
  session="model-resume-${platform}-$$"
  capture_command "$platform" start --repo "$repo" --session "$session" --resume "fixture-$platform-session" \
    --model "$override_id" --effort "$override_effort"
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
  if [[ "$COMMAND_RC" -eq 0 ]]; then
    fail "test_${platform}_malicious_unknown_model_refuses_unselected_launch" "malicious unknown model unexpectedly launched"
  else
    assert_unavailable_evidence "test_${platform}_malicious_model_is_reported_literally" "$COMMAND_OUTPUT" "$malicious"
  fi
  [[ ! -e "$marker" && ! -e "$marker.backtick" ]] || \
    fail "test_${platform}_model_input_is_literal_safe" "model input executed shell syntax"
  if "$issue_tmux_bin" has-session -t "=$session" 2>/dev/null; then
    fail "test_${platform}_malicious_model_creates_no_session" "malicious unknown model created a session"
  fi
  assert_no_workflow_injection "test_${platform}_malicious_input_does_not_inject_workflow" "$input_log"
  stop_or_kill "$platform" "$repo" "$session"
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
