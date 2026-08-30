#!/usr/bin/env bash
set -euo pipefail

# Live-smoke acceptance for the two adapters whose terminal contracts cannot be
# reduced to launch arguments.  The runtime binaries, Cursor authority, Git
# repositories, and tmux server are all fixtures under issue_setup's temporary
# root; no user-level Kimi/Cursor state or real tmux session is consulted.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
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

expect_status() {
  local label="$1" platform="$2" repo="$3" session="$4" expected="$5" status
  status="$(run_runner "$platform" status --repo "$repo" --session "$session" 2>&1)" || {
    fail "$label" "status failed: $status"
    return
  }
  json_assert "$label" "d['result'] == 'present' and d['activity'] == '$expected' and d['tui_detected'] is True" "$status"
}

stop_force() {
  local platform="$1" repo="$2" session="$3"
  run_runner "$platform" stop --repo "$repo" --session "$session" --force >/dev/null 2>&1 || \
    "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
}

run_runner() {
  TMUX_BIN="$issue_tmux_bin" bash "$runner" "$@"
}

prepare_kimi_surface() {
  local repo="$1"
  mkdir -p "$repo/.kimi-code/skills/workflow-next" \
    "$repo/.kimi-code/skills/kaola-workflow-finalize" \
    "$repo/.kimi-code/agents" "$repo/.kimi-code/kaola-workflow/scripts" \
    "$KIMI_CODE_HOME/skills"
  printf '%s\n' workflow-next >"$repo/.kimi-code/skills/workflow-next/SKILL.md"
  printf '%s\n' finalize >"$repo/.kimi-code/skills/kaola-workflow-finalize/SKILL.md"
  printf '%s\n' 'fixture agent manifest' >"$repo/.kimi-code/agents/.kaola-workflow-agent-manifest"
  printf '%s\n' 'fixture claim hook' >"$repo/.kimi-code/kaola-workflow/scripts/kaola-workflow-claim.js"
}

make_kimi_fake() {
  local path="$issue_tmp_root/kimi-live-fake"
  local log="$issue_tmp_root/kimi-live-argv.log"
  cat >"$path" <<'FAKE_KIMI'
#!/usr/bin/env bash
set -euo pipefail

log="${FAKE_RUNTIME_LOG:?}"
printf 'cwd=%s\targs=' "$PWD" >>"$log"
printf '%q ' "$@" >>"$log"
printf '\n' >>"$log"

if [[ "${1:-}" == doctor ]]; then
  printf '%s\n' '{"kaolaWorkflow":true,"workflowNext":true,"finalize":true,"authority":"isolated-fixture"}'
  exit 0
fi
if [[ "${1:-}" == --version ]]; then
  printf '%s\n' 'kimi-fixture 1.0.0'
  exit 0
fi

printf '\033]0;Kimi Code\007'
printf '%s\n' 'Kimi Code' 'Kaola Workflow surface'
case "${FAKE_RUNTIME_STATE:-idle}" in
  trust)
    printf '%s\n' 'Trust this folder?' 'Enter select  Esc exit'
    ;;
  idle)
    printf '%s\n' '│ > │'
    ;;
  busy)
    printf '%s\n' 'thinking...'
    ;;
  session)
    printf '%s\n' 'Session: session_01234567-89ab-cdef-0123-456789abcdef' '│ > │'
    ;;
  legacy-session)
    printf '%s\n' 'Session ID: 01ARZ3NDEKTSV4RRFFQ69G5FAV' '│ > │'
    ;;
  *)
    printf '%s\n' 'unknown fixture state'
    ;;
esac

while IFS= read -r line; do
  if [[ "$line" == '/exit' || "$line" == '/quit' ]]; then
    exit 0
  fi
  printf 'ECHO:%s\n' "$line"
done
FAKE_KIMI
  chmod +x "$path"
  printf '%s\t%s\n' "$path" "$log"
}

prepare_cursor_authority() {
  mkdir -p "$CURSOR_HOME/commands" "$CURSOR_HOME/kaola-workflow"
  printf '%s\n' 'workflow-next fixture authority bytes' >"$CURSOR_HOME/commands/workflow-next.md"
  printf '%s\n' 'finalize fixture authority bytes' >"$CURSOR_HOME/commands/kaola-workflow-finalize.md"
  CURSOR_ROOT="$CURSOR_HOME" python3 - <<'PY'
import hashlib
import json
import os
import pathlib
import stat

root = pathlib.Path(os.environ["CURSOR_ROOT"])
files = {}
for relative in ("commands/workflow-next.md", "commands/kaola-workflow-finalize.md"):
    path = root / relative
    files[relative] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mode": stat.S_IMODE(path.stat().st_mode),
    }
(root / "kaola-workflow/cursor-authority.json").write_text(
    json.dumps({"schema_version": 1, "kind": "cursor_global_authority", "forge": "github", "files": files}) + "\n",
    encoding="utf-8",
)
PY
}

make_cursor_surface_helper() {
  local path="$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'CURSOR_SURFACE'
#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const log = process.env.CURSOR_HELPER_LOG;
if (log) fs.appendFileSync(log, JSON.stringify(args) + "\n");

if (args.includes("--doctor")) {
  process.stdout.write(JSON.stringify({authority: {receipt_status: "valid", freshness: "current"}}) + "\n");
  process.exit(0);
}

const index = args.indexOf("--ensure-target");
if (index !== -1) {
  const target = args[index + 1];
  if (!target || !path.isAbsolute(target)) {
    process.stderr.write(JSON.stringify({status: "error", scope: "project", target: target || null, files: []}) + "\n");
    process.exit(2);
  }
  const commandDir = path.join(target, ".cursor", "commands");
  const names = ["workflow-next.md", "kaola-workflow-finalize.md"];
  const collisions = [];
  for (const name of names) {
    const destination = path.join(commandDir, name);
    if (fs.existsSync(destination)) collisions.push(destination);
  }
  if (collisions.length) {
    process.stderr.write(JSON.stringify({status: "foreign-collision", scope: "project", target, files: collisions}) + "\n");
    process.exit(23);
  }
  fs.mkdirSync(commandDir, {recursive: true});
  const sourceRoot = process.env.CURSOR_HOME;
  for (const name of names) {
    fs.copyFileSync(path.join(sourceRoot, "commands", name), path.join(commandDir, name));
  }
  // The installed helper reports the materialized-file count as `files`.
  process.stdout.write(JSON.stringify({status: "materialized", scope: "project", target, files: names.length}) + "\n");
  process.exit(0);
}

process.stderr.write("unsupported cursor surface invocation\n");
process.exit(2);
CURSOR_SURFACE
  chmod +x "$path"
  CURSOR_ROOT="$CURSOR_HOME" CURSOR_HELPER="$path" python3 - <<'PY'
import hashlib
import json
import os
import pathlib
import stat

root = pathlib.Path(os.environ["CURSOR_ROOT"])
helper = pathlib.Path(os.environ["CURSOR_HELPER"])
receipt_path = root / "kaola-workflow/cursor-authority.json"
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
relative = helper.relative_to(root).as_posix()
receipt.setdefault("files", {})[relative] = {
    "sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
    "mode": stat.S_IMODE(helper.stat().st_mode),
}
receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
PY
}

make_cursor_fake() {
  local path="$issue_tmp_root/cursor-live-fake"
  local log="$issue_tmp_root/cursor-live-argv.log"
  cat >"$path" <<'FAKE_CURSOR'
#!/usr/bin/env bash
set -euo pipefail

log="${FAKE_RUNTIME_LOG:?}"
printf 'cwd=%s\targs=' "$PWD" >>"$log"
printf '%q ' "$@" >>"$log"
printf '\n' >>"$log"

if [[ "${1:-}" == --version ]]; then
  printf '%s\n' 'cursor-agent-fixture 1.0.0'
  exit 0
fi

printf '\033]0;Cursor Agent\007'
printf '%s\n' 'Cursor Agent' 'Kaola Workflow surface'
case "${FAKE_RUNTIME_STATE:-idle}" in
  idle)
    printf '%s\n' '→ Plan, search, build anything'
    ;;
  busy)
    printf '%s\n' '⠋ Globbing 42 tokens' 'ctrl+c to stop'
    ;;
  history)
    # A completed historical spinner must not win over the current idle prompt.
    printf '%s\n' '✓ Globbing 41 tokens' '→ Plan, search, build anything'
    ;;
  *)
    printf '%s\n' 'unknown fixture state'
    ;;
esac

while IFS= read -r line; do
  if [[ "$line" == '/exit' || "$line" == '/quit' ]]; then
    exit 0
  fi
  printf 'ECHO:%s\n' "$line"
done
FAKE_CURSOR
  chmod +x "$path"
  printf '%s\t%s\n' "$path" "$log"
}

assert_helper_call() {
  local label="$1" log="$2" repo="$3"
  CURSOR_CALL_LOG="$log" EXPECTED_REPO="$repo" python3 - <<'PY' || {
import json
import os
import pathlib

log = pathlib.Path(os.environ["CURSOR_CALL_LOG"])
expected = os.environ["EXPECTED_REPO"]
calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
for args in calls:
    try:
        index = args.index("--ensure-target")
    except ValueError:
        continue
    if index + 1 < len(args) and args[index + 1] == expected:
        raise SystemExit(0)
raise SystemExit(f"no exact --ensure-target {expected!r} call in {calls!r}")
PY
    fail "$label" "formal cursor authority was not called with --ensure-target $repo"
  }
}

issue_setup
trap issue_cleanup EXIT

if [[ ! -x "$runner" ]]; then
  fail test_live_smoke_entrypoint "missing executable $runner"
else
  export KIMI_CODE_HOME="$issue_tmp_root/kimi-home"
  export CURSOR_HOME="$issue_tmp_root/cursor-home"
  export KAOLA_START_TIMEOUT=3

  IFS=$'\t' read -r kimi_fake kimi_log < <(make_kimi_fake)
  export KIMI_BIN="$kimi_fake" FAKE_RUNTIME_LOG="$kimi_log"

  # Kimi's trust screen is evidence for the controlling Agent. The Runner must
  # still transfer an Agent-selected native key without deciding its meaning.
  kimi_repo="$(issue_new_repo kimi-trust-repo)"
  prepare_kimi_surface "$kimi_repo"
  export FAKE_RUNTIME_STATE=trust
  kimi_trust_session="kimi-trust-$$"
  trust_start="$(run_runner kimi-cli start --repo "$kimi_repo" --session "$kimi_trust_session" 2>&1)" || \
    fail test_kimi_trust_prompt_start "start failed: $trust_start"
  expect_status test_kimi_trust_prompt_waiting_human kimi-cli "$kimi_repo" "$kimi_trust_session" waiting-human
  trust_key="$(run_runner kimi-cli key --repo "$kimi_repo" --session "$kimi_trust_session" --key down 2>&1)" || \
    fail test_kimi_trust_prompt_key_transport "key transport failed: $trust_key"
  json_assert test_kimi_trust_prompt_key_transport "d['result'] == 'key-sent' and d['key'] == 'down' and d['mutation_performed'] is True and d['payload_fingerprint'].startswith('sha256:')" "$trust_key"
  stop_force kimi-cli "$kimi_repo" "$kimi_trust_session"

  kimi_repo="$(issue_new_repo kimi-idle-repo)"
  prepare_kimi_surface "$kimi_repo"
  export FAKE_RUNTIME_STATE=idle
  kimi_idle_session="kimi-idle-$$"
  run_runner kimi-cli start --repo "$kimi_repo" --session "$kimi_idle_session" >/dev/null 2>&1 || \
    fail test_kimi_idle_frame "start failed"
  expect_status test_kimi_idle_frame kimi-cli "$kimi_repo" "$kimi_idle_session" idle
  stop_force kimi-cli "$kimi_repo" "$kimi_idle_session"

  kimi_repo="$(issue_new_repo kimi-busy-repo)"
  prepare_kimi_surface "$kimi_repo"
  export FAKE_RUNTIME_STATE=busy
  kimi_busy_session="kimi-busy-$$"
  run_runner kimi-cli start --repo "$kimi_repo" --session "$kimi_busy_session" >/dev/null 2>&1 || \
    fail test_kimi_thinking_busy "start failed"
  expect_status test_kimi_thinking_busy kimi-cli "$kimi_repo" "$kimi_busy_session" busy
  stop_force kimi-cli "$kimi_repo" "$kimi_busy_session"

  kimi_repo="$(issue_new_repo kimi-session-repo)"
  prepare_kimi_surface "$kimi_repo"
  export FAKE_RUNTIME_STATE=session
  kimi_uuid_session="kimi-uuid-$$"
  run_runner kimi-cli start --repo "$kimi_repo" --session "$kimi_uuid_session" >/dev/null 2>&1 || \
    fail test_kimi_uuid_session_not_truncated "start failed"
  uuid_status="$(run_runner kimi-cli status --repo "$kimi_repo" --session "$kimi_uuid_session")"
  json_assert test_kimi_uuid_session_not_truncated "d['runtime_session_id'] == 'session_01234567-89ab-cdef-0123-456789abcdef'" "$uuid_status"
  stop_force kimi-cli "$kimi_repo" "$kimi_uuid_session"

  export FAKE_RUNTIME_STATE=legacy-session
  kimi_legacy_session="kimi-legacy-$$"
  run_runner kimi-cli start --repo "$kimi_repo" --session "$kimi_legacy_session" >/dev/null 2>&1 || \
    fail test_kimi_legacy_ulid_session_not_truncated "start failed"
  legacy_status="$(run_runner kimi-cli status --repo "$kimi_repo" --session "$kimi_legacy_session")"
  json_assert test_kimi_legacy_ulid_session_not_truncated "d['runtime_session_id'] == '01ARZ3NDEKTSV4RRFFQ69G5FAV' and len(d['runtime_session_id']) == 26" "$legacy_status"
  stop_force kimi-cli "$kimi_repo" "$kimi_legacy_session"

  IFS=$'\t' read -r cursor_fake cursor_log < <(make_cursor_fake)
  export CURSOR_AGENT_BIN="$cursor_fake" FAKE_RUNTIME_LOG="$cursor_log"
  prepare_cursor_authority
  make_cursor_surface_helper
  export CURSOR_HELPER_LOG="$issue_tmp_root/cursor-helper.log"
  : >"$CURSOR_HELPER_LOG"

  cursor_repo="$(issue_new_repo cursor-preflight-repo)"
  before_cursor_tree="$(find "$cursor_repo" -mindepth 1 -maxdepth 3 -print | sort)"
  preflight="$(run_runner cursor-cli preflight --repo "$cursor_repo" --session cursor-preflight-$$ 2>&1)" || \
    fail test_cursor_preflight_read_only "preflight failed: $preflight"
  after_cursor_tree="$(find "$cursor_repo" -mindepth 1 -maxdepth 3 -print | sort)"
  [[ "$before_cursor_tree" == "$after_cursor_tree" ]] || \
    fail test_cursor_preflight_read_only "preflight changed project tree"
  [[ ! -e "$cursor_repo/.cursor" ]] || fail test_cursor_preflight_read_only "preflight materialized .cursor"
  grep -q -- '--ensure-target' "$CURSOR_HELPER_LOG" && \
    fail test_cursor_preflight_read_only "preflight invoked point-of-use materialization"
  json_assert test_cursor_preflight_read_only "d['project_materialization'] == 'not-present'" "$preflight"

  export FAKE_RUNTIME_STATE=idle
  cursor_materialize_repo="$(issue_new_repo cursor-materialize-repo)"
  cursor_materialize_session="cursor-materialize-$$"
  run_runner cursor-cli start --repo "$cursor_materialize_repo" --session "$cursor_materialize_session" >/dev/null 2>&1 || \
    fail test_cursor_start_does_not_materialize_workflow "start failed"
  [[ ! -e "$cursor_materialize_repo/.cursor" ]] || \
    fail test_cursor_start_does_not_materialize_workflow "Runner start modified the repository"
  grep -q -- '--ensure-target' "$CURSOR_HELPER_LOG" && \
    fail test_cursor_start_does_not_materialize_workflow "Runner start invoked Workflow materialization"
  stop_force cursor-cli "$cursor_materialize_repo" "$cursor_materialize_session"

  cursor_collision_repo="$(issue_new_repo cursor-collision-repo)"
  mkdir -p "$cursor_collision_repo/.cursor/commands"
  printf '%s\n' 'foreign command must survive' >"$cursor_collision_repo/.cursor/commands/workflow-next.md"
  printf '%s\n' 'foreign finalize command must survive' >"$cursor_collision_repo/.cursor/commands/kaola-workflow-finalize.md"
  foreign_before="$(cat "$cursor_collision_repo/.cursor/commands/workflow-next.md")"
  foreign_finalize_before="$(cat "$cursor_collision_repo/.cursor/commands/kaola-workflow-finalize.md")"
  cursor_collision_session="cursor-collision-$$"
  collision_output="$(run_runner cursor-cli start --repo "$cursor_collision_repo" --session "$cursor_collision_session" 2>&1)" || \
    fail test_cursor_foreign_collision_is_advisory "start failed because of unrelated Workflow files: $collision_output"
  foreign_after="$(cat "$cursor_collision_repo/.cursor/commands/workflow-next.md")"
  foreign_finalize_after="$(cat "$cursor_collision_repo/.cursor/commands/kaola-workflow-finalize.md")"
  [[ "$foreign_after" == "$foreign_before" ]] || fail test_cursor_foreign_collision_refuses "foreign command was overwritten"
  [[ "$foreign_finalize_after" == "$foreign_finalize_before" ]] || fail test_cursor_foreign_collision_refuses "foreign finalize command was overwritten"
  stop_force cursor-cli "$cursor_collision_repo" "$cursor_collision_session"
fi

if [[ "$failures" -gt 0 ]]; then
  printf 'live-smoke adapter acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'live-smoke adapter acceptance: PASS\n'
