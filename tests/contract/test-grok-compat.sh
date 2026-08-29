#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
wrapper="$project_root/scripts/grok-tmux.sh"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

failures=0
fail() {
  printf 'RED: %s — %s\n' "$1" "$2" >&2
  failures=$((failures + 1))
}

json_assert() {
  local label="$1" expression="$2" input="$3"
  JSON_INPUT="$input" python3 -c "import json, os; d=json.loads(os.environ['JSON_INPUT']); assert $expression, d" || \
    fail "$label" "JSON assertion failed: $input"
}

expect_fail() {
  local label="$1"
  shift
  local output rc
  set +e
  output="$("$@" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || fail "$label" "expected non-zero exit"
  printf '%s\n' "$output"
}

issue_setup
trap issue_cleanup EXIT

repo="$(issue_new_repo grok-compat-repo)"
canonical_repo="$(cd "$repo" && pwd -P)"
IFS=$'\t' read -r fake_grok fake_log < <(issue_make_fake_runtime grok)
export FAKE_RUNTIME_NAME=grok FAKE_RUNTIME_LOG="$fake_log" FAKE_RUNTIME_SESSION_ID=grok-compat-session
export GROK_BIN="$fake_grok" GROK_START_TIMEOUT=4 KAOLA_START_TIMEOUT=4
session="grok-compat-$$"
legacy_session="grok-legacy-$$"
unrelated="grok-compat-unrelated-$$"

run_wrapper() {
  TMUX_BIN="$issue_tmux_bin" bash "$wrapper" "$@"
}

if [[ ! -f "$wrapper" ]]; then
  fail "test_grok_compat_wrapper_exists" "missing $wrapper"
else
  preflight="$(run_wrapper preflight --repo "$repo" --session "$session")" || fail "test_grok_wrapper_preflight" "preflight failed: $preflight"
  json_assert "test_grok_wrapper_preserves_legacy_preflight_fields" "d['result'] == 'ready' and d['workflow_next'] and d['kaola_workflow_finalize']" "$preflight"
  json_assert "test_grok_wrapper_preserves_legacy_version_and_project_root" "d['grok_version'] == 'fixture' and d['project_root'] == 'fixture'" "$preflight"
  json_assert "test_grok_wrapper_exposes_neutral_preflight_identity" "d['platform'] == 'grok' and 'recurring_execution' in d" "$preflight"

  "$issue_tmux_bin" new-session -d -s "$unrelated" -c "$repo"
  started="$(run_wrapper start --repo "$repo" --session "$session")" || fail "test_grok_wrapper_start" "start failed: $started"
  json_assert "test_grok_wrapper_start" "d['result'] == 'started' and d['platform'] == 'grok' and d['owned'] and d['platform_match'] and d['repo_match'] and d['tui_detected'] and d['grok_tui']" "$started"

  [[ "$("$issue_tmux_bin" show-environment -t "=$session" KAOLA_PROJECT_RUNNER 2>/dev/null)" == 'KAOLA_PROJECT_RUNNER=1' ]] || \
    fail "test_grok_wrapper_writes_neutral_owner_marker" "new owner marker absent"
  [[ "$("$issue_tmux_bin" show-environment -t "=$session" KAOLA_PROJECT_RUNNER_PLATFORM 2>/dev/null)" == 'KAOLA_PROJECT_RUNNER_PLATFORM=grok' ]] || \
    fail "test_grok_wrapper_writes_platform_marker" "platform marker absent"
  [[ "$("$issue_tmux_bin" show-environment -t "=$session" GROK_KAOLA_PROJECT_RUNNER 2>/dev/null)" == 'GROK_KAOLA_PROJECT_RUNNER=1' ]] || \
    fail "test_grok_wrapper_writes_legacy_marker" "legacy owner marker absent"

  status_json="$(run_wrapper status --repo "$repo" --session "$session")"
  json_assert "test_grok_wrapper_preserves_legacy_status_shape" "d['grok_tui'] and d['activity'] == 'idle' and d['repo_match']" "$status_json"
  json_assert "test_grok_wrapper_status_has_neutral_shape" "d['platform'] == 'grok' and d['tui_detected'] and d['platform_match'] and d['runtime'] == 'Grok CLI'" "$status_json"
  json_assert "test_grok_wrapper_extracts_runtime_session_id" "d['runtime_session_id'] == 'grok-compat-session'" "$status_json"

  # A pre-existing legacy session is reusable only when its old owner and repo
  # markers are both exact; the wrapper must expose the migration state without
  # adopting an unrelated session.
  "$issue_tmux_bin" new-session -d -s "$legacy_session" -c "$repo" "$fake_grok"
  "$issue_tmux_bin" set-environment -t "=$legacy_session" GROK_KAOLA_PROJECT_RUNNER 1
  "$issue_tmux_bin" set-environment -t "=$legacy_session" GROK_KAOLA_REPO "$canonical_repo"
  legacy_status="$(run_wrapper status --repo "$repo" --session "$legacy_session")"
  json_assert "test_grok_wrapper_reads_legacy_owned_session" "d['owned'] and d['legacy_ownership'] and d['platform_match'] and d['repo_match'] and d['grok_tui']" "$legacy_status"
  expect_fail "test_grok_wrapper_wrong_repo_legacy_refusal" run_wrapper send --repo "$(issue_new_repo grok-compat-wrong)" --session "$legacy_session" --text wrong-repo >/dev/null
  "$issue_tmux_bin" has-session -t "=$legacy_session" || fail "test_grok_wrapper_preserves_legacy_session" "legacy session disappeared"

  run_wrapper stop --repo "$repo" --session "$session" --force >/dev/null || fail "test_grok_wrapper_force_stop" "force stop failed"
  "$issue_tmux_bin" has-session -t "=$unrelated" || fail "test_grok_wrapper_does_not_touch_unrelated" "unrelated session was changed"
  "$issue_tmux_bin" kill-session -t "=$legacy_session" 2>/dev/null || true
fi

if [[ "$failures" -gt 0 ]]; then
  printf 'Grok compatibility acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Grok compatibility acceptance: PASS\n'
