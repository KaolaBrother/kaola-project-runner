#!/usr/bin/env bash
set -euo pipefail

# Shared, offline-only fixtures for Issue #1 acceptance tests. Every caller gets
# its own temporary tmux server and all runtime binaries are fakes in that tree.

issue_test_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
issue_project_root="$(cd "$issue_test_root/.." && pwd -P)"

issue_tmp_root=""
issue_tmux_socket=""
issue_tmux_bin=""
issue_fake_bin_dir=""

issue_setup() {
  issue_tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/kaola-project-runner-issue-1.XXXXXX")"
  issue_tmux_socket="kaola-issue-1-$$-${RANDOM}"
  issue_fake_bin_dir="$issue_tmp_root/bin"
  mkdir -p "$issue_fake_bin_dir"

  issue_tmux_bin="$issue_tmp_root/tmux"
  cat >"$issue_tmux_bin" <<'TMUX_SHIM'
#!/usr/bin/env bash
set -euo pipefail
exec tmux -L "$KAOLA_TEST_TMUX_SOCKET" "$@"
TMUX_SHIM
  chmod +x "$issue_tmux_bin"
  export KAOLA_TEST_TMUX_SOCKET="$issue_tmux_socket"
  export TMUX_BIN="$issue_tmux_bin"
  export PATH="$issue_fake_bin_dir:$PATH"
  export HOME="$issue_tmp_root/home"
  mkdir -p "$HOME"
}

issue_cleanup() {
  if [[ -n "$issue_tmux_socket" ]]; then
    tmux -L "$issue_tmux_socket" kill-server 2>/dev/null || true
  fi
  if [[ -n "$issue_tmp_root" ]]; then
    rm -rf "$issue_tmp_root"
  fi
}

issue_new_repo() {
  local name="$1"
  local path="$issue_tmp_root/$name"
  mkdir -p "$path"
  git -C "$path" init -q -b main
  git -C "$path" config user.name 'Issue 1 Acceptance'
  git -C "$path" config user.email 'issue-1@example.invalid'
  printf '%s\n' '# fixture' >"$path/README.md"
  git -C "$path" add README.md
  git -C "$path" commit -q -m fixture
  printf '%s\n' "$path"
}

issue_make_fake_runtime() {
  local runtime="$1"
  local path="$issue_tmp_root/${runtime}-fake"
  local log="$issue_tmp_root/${runtime}-argv.log"
  cat >"$path" <<'FAKE_RUNTIME'
#!/usr/bin/env bash
set -euo pipefail

runtime="${FAKE_RUNTIME_NAME:?}"
log="${FAKE_RUNTIME_LOG:?}"
printf 'cwd=%s\targs=' "$PWD" >>"$log"
printf '%q ' "$@" >>"$log"
printf '\n' >>"$log"

case "$runtime:$*" in
  grok:inspect\ --json)
    printf '%s\n' '{"grokVersion":"fixture","projectRoot":"fixture","skills":[{"name":"workflow-next"},{"name":"kaola-workflow-finalize"}]}'
    exit 0
    ;;
  kimi-cli:doctor|cursor-cli:doctor)
    printf '%s\n' '{"kaolaWorkflow":true,"workflowNext":true,"finalize":true,"authority":"fixture"}'
    exit 0
    ;;
  claude-code:--help|opencode:--help|kimi-cli:--help|cursor-cli:--help)
    printf '%s\n' 'workflow-next kaola-workflow-finalize'
    exit 0
    ;;
  *)
    if [[ "${1:-}" == '--version' || "${1:-}" == 'version' ]]; then
      printf '%s\n' "${runtime}-fixture 1.0.0"
      exit 0
    fi
    ;;
esac

case "${FAKE_RUNTIME_STATE:-ready}" in
  ready)
    printf '\033]0;%s\007' "$runtime"
    printf '%s\n' "${runtime} Kaola TUI" 'workflow-next available' 'kaola-workflow-finalize available' 'minimal · /help' 'Ready'
    if [[ -n "${FAKE_RUNTIME_SESSION_ID:-}" ]]; then
      printf 'session id: %s\n' "$FAKE_RUNTIME_SESSION_ID"
      printf 'Session ID: %s\n' "$FAKE_RUNTIME_SESSION_ID"
    fi
    printf '%s\n' '❯' '›'
    ;;
  busy)
    printf '\033]0;%s\007' "$runtime"
    printf '%s\n' "${runtime} Kaola TUI" 'Waiting for response' 'Press Esc to interrupt'
    while :; do sleep 1; done
    ;;
  decision)
    printf '\033]0;%s\007' "$runtime"
    printf '%s\n' "${runtime} Kaola TUI" 'HUMAN_DECISION_REQUIRED' 'Decision: choose fixture' '❯'
    ;;
esac

while IFS= read -r line; do
  if [[ "$line" == '/quit' || "$line" == '/exit' ]]; then
    exit 0
  fi
  if [[ "$line" == 'BUSY' ]]; then
    printf 'Waiting for response…'
    sleep "${FAKE_BUSY_SECONDS:-3}"
    printf '\r\033[2KDONE\nminimal · /help\n❯\n'
  else
    printf 'ECHO:%s\n' "$line"
    printf '%s\n' 'minimal · /help' '❯'
  fi
done
FAKE_RUNTIME
  chmod +x "$path"
  printf '%s\t%s\n' "$path" "$log"
}

issue_make_runtime_aliases() {
  local fake="$1"
  local name="$2"
  ln -s "$fake" "$issue_fake_bin_dir/$name"
}

issue_json_field() {
  local expression="$1"
  JSON_INPUT="$(cat)" python3 -c "import json, os; d=json.loads(os.environ['JSON_INPUT']); assert $expression, d"
}

issue_expect_fail() {
  local label="$1"
  shift
  local output rc
  set +e
  output="$("$@" 2>&1)"
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    printf 'FAIL: %s — expected non-zero exit\n' "$label" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
  printf '%s\n' "$output"
}

issue_assert_file_link() {
  local path="$1"
  local expected="$2"
  [[ -L "$path" ]] || {
    printf 'FAIL: expected symlink: %s\n' "$path" >&2
    return 1
  }
  local actual
  actual="$(readlink "$path")"
  [[ "$actual" == "$expected" ]] || {
    printf 'FAIL: symlink %s -> %s (expected %s)\n' "$path" "$actual" "$expected" >&2
    return 1
  }
}
