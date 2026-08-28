#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
helper="$project_root/scripts/grok-tmux.sh"
tmux_bin="${TMUX_BIN:-$(command -v tmux)}"
tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/grok-kaola-runner-test.XXXXXX")"
session="gkpr-test-$$"
unrelated="gkpr-unrelated-$$"

cleanup() {
  "$tmux_bin" kill-session -t "$session" 2>/dev/null || true
  "$tmux_bin" kill-session -t "$unrelated" 2>/dev/null || true
  rm -rf "$tmp_root"
}
trap cleanup EXIT

repo="$tmp_root/repo"
other_repo="$tmp_root/other-repo"
fake_grok="$tmp_root/grok"
mkdir -p "$repo" "$other_repo"
git -C "$repo" init -q -b main
git -C "$other_repo" init -q -b main

cat >"$fake_grok" <<'FAKE'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "inspect" && "${2:-}" == "--json" ]]; then
  printf '%s\n' '{"grokVersion":"test","projectRoot":"test","skills":[{"name":"workflow-next"},{"name":"kaola-workflow-finalize"}]}'
  exit 0
fi

printf '\033]0;grok\007'
printf 'Grok Build test\nminimal · /help\n❯\n'
while IFS= read -r line; do
  if [[ "$line" == "/quit" ]]; then
    exit 0
  fi
  if [[ "$line" == "BUSY" ]]; then
    printf 'Waiting for response…'
    sleep 2
    printf '\r\033[2KDONE\nminimal · /help\n❯\n'
  else
    printf 'ECHO:%s\nminimal · /help\n❯\n' "$line"
  fi
done
FAKE
chmod +x "$fake_grok"

run_helper() {
  TMUX_BIN="$tmux_bin" GROK_BIN="$fake_grok" GROK_START_TIMEOUT=5 "$helper" "$@"
}

json_assert() {
  local expression="$1"
  JSON_INPUT="$(cat)" python3 -c "import json,os; d=json.loads(os.environ['JSON_INPUT']); assert $expression, d"
}

run_helper preflight --repo "$repo" --session "$session" | \
  json_assert "d['result'] == 'ready' and d['workflow_next'] and d['kaola_workflow_finalize']"

"$tmux_bin" new-session -d -s "$unrelated" -c "$other_repo"

run_helper start --repo "$repo" --session "$session" | \
  json_assert "d['result'] == 'started' and d['owned'] and d['repo_match'] and d['grok_tui']"

run_helper status --repo "$repo" --session "$session" | \
  json_assert "d['result'] == 'present' and d['activity'] == 'idle' and d['pane_count'] == 1"

literal='literal ; $(touch SHOULD_NOT_EXIST) `touch ALSO_NOT`'
run_helper send --repo "$repo" --session "$session" --text "$literal" | \
  json_assert "d['result'] == 'sent'"
sleep 1
capture="$(run_helper capture --repo "$repo" --session "$session" --lines 40)"
printf '%s\n' "$capture" | grep -Fq 'ECHO:literal ; $(touch SHOULD_NOT_EXIST) `touch ALSO_NOT`'
[[ ! -e "$repo/SHOULD_NOT_EXIST" && ! -e "$repo/ALSO_NOT" ]]

if run_helper send --repo "$other_repo" --session "$session" --text wrong-repo >/dev/null 2>&1; then
  printf 'expected repo mismatch to fail\n' >&2
  exit 1
fi

run_helper send --repo "$repo" --session "$session" --text BUSY >/dev/null
sleep 1
if run_helper send --repo "$repo" --session "$session" --text must-wait >/dev/null 2>&1; then
  printf 'expected busy session injection to fail\n' >&2
  exit 1
fi
sleep 2

run_helper stop --repo "$repo" --session "$session" | \
  json_assert "d['result'] == 'stopped' and not d['present']"

"$tmux_bin" has-session -t "$unrelated"
run_helper status --repo "$repo" --session "$session" | \
  json_assert "d['result'] == 'absent' and not d['present']"

printf 'grok-tmux tests: PASS\n'
