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

prepare_surface() {
  local platform="$1" repo="$2"
  case "$platform" in
    grok)
      : # grok inspect --json is the runtime-native authority surface.
      ;;
    claude-code)
      mkdir -p "$repo/.claude/commands" "$repo/.claude/agents" "$repo/.claude/kaola-workflow/scripts"
      printf '%s\n' workflow-next >"$repo/.claude/commands/workflow-next.md"
      printf '%s\n' finalize >"$repo/.claude/commands/kaola-workflow-finalize.md"
      printf '%s\n' 'fixture agent manifest' >"$repo/.claude/agents/.kaola-workflow-agent-manifest"
      printf '%s\n' 'fixture claim hook' >"$repo/.claude/kaola-workflow/scripts/kaola-workflow-claim.js"
      ;;
    opencode)
      mkdir -p "$repo/.opencode/agents" "$repo/.opencode/commands" "$repo/.opencode/plugins" "$repo/.opencode/kaola-workflow/scripts"
      printf '%s\n' agent >"$repo/.opencode/agents/kaola.md"
      printf '%s\n' workflow-next >"$repo/.opencode/commands/workflow-next.md"
      printf '%s\n' finalize >"$repo/.opencode/commands/kaola-workflow-finalize.md"
      printf '%s\n' plugin >"$repo/.opencode/plugins/kaola.js"
      printf '%s\n' 'fixture claim hook' >"$repo/.opencode/kaola-workflow/scripts/kaola-workflow-claim.js"
      printf '%s\n' '{}' >"$repo/opencode.json"
      ;;
    kimi-cli)
      mkdir -p "$repo/.kimi-code/skills/workflow-next" "$repo/.kimi-code/skills/kaola-workflow-finalize" "$repo/.kimi-code/agents" "$repo/.kimi-code/kaola-workflow/scripts"
      printf '%s\n' workflow-next >"$repo/.kimi-code/skills/workflow-next/SKILL.md"
      printf '%s\n' finalize >"$repo/.kimi-code/skills/kaola-workflow-finalize/SKILL.md"
      printf '%s\n' 'fixture agent manifest' >"$repo/.kimi-code/agents/.kaola-workflow-agent-manifest"
      printf '%s\n' 'fixture claim hook' >"$repo/.kimi-code/kaola-workflow/scripts/kaola-workflow-claim.js"
      mkdir -p "$KIMI_CODE_HOME/skills"
      ;;
    cursor-cli)
      mkdir -p "$CURSOR_HOME/commands" "$CURSOR_HOME/kaola-workflow"
      printf '%s\n' workflow-next >"$CURSOR_HOME/commands/workflow-next.md"
      printf '%s\n' finalize >"$CURSOR_HOME/commands/kaola-workflow-finalize.md"
      # Cursor preflight validates a versioned authority receipt against every
      # managed file's exact bytes and mode.  Build that receipt from the
      # fixture itself instead of weakening the acceptance surface with a
      # hand-written placeholder.
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
      # Start now performs point-of-use materialization through the installed
      # global authority helper.  Keep this fixture fully isolated and
      # idempotent so continue/resume launch checks do not touch ~/.cursor.
      mkdir -p "$CURSOR_HOME/kaola-workflow/scripts"
      cat >"$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js" <<'CURSOR_SURFACE'
#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const args = process.argv.slice(2);

if (args.includes("--doctor")) {
  process.stdout.write(JSON.stringify({authority: {receipt_status: "valid", freshness: "current"}}) + "\n");
  process.exit(0);
}
const index = args.indexOf("--ensure-target");
if (index === -1 || !args[index + 1] || !path.isAbsolute(args[index + 1])) process.exit(2);
const target = args[index + 1];
const names = ["workflow-next.md", "kaola-workflow-finalize.md"];
const commandDir = path.join(target, ".cursor", "commands");
const sourceRoot = process.env.CURSOR_HOME;
const collisions = [];
for (const name of names) {
  const destination = path.join(commandDir, name);
  if (fs.existsSync(destination)) {
    const source = path.join(sourceRoot, "commands", name);
    if (!fs.readFileSync(destination).equals(fs.readFileSync(source))) collisions.push(destination);
  }
}
if (collisions.length) {
  process.stderr.write(JSON.stringify({status: "foreign-collision", scope: "project", target, files: collisions}) + "\n");
  process.exit(23);
}
fs.mkdirSync(commandDir, {recursive: true});
for (const name of names) {
  const destination = path.join(commandDir, name);
  if (!fs.existsSync(destination)) fs.copyFileSync(path.join(sourceRoot, "commands", name), destination);
}
process.stdout.write(JSON.stringify({status: "current", scope: "project", target, files: names.length}) + "\n");
CURSOR_SURFACE
      chmod +x "$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
      CURSOR_ROOT="$CURSOR_HOME" CURSOR_HELPER="$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js" python3 - <<'PY'
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
      ;;
  esac
}

runtime_env() {
  local platform="$1" path="$2"
  case "$platform" in
    grok) GROK_BIN="$path" ;;
    claude-code) CLAUDE_BIN="$path" ;;
    opencode) OPENCODE_BIN="$path" ;;
    kimi-cli) KIMI_BIN="$path" ;;
    cursor-cli) CURSOR_AGENT_BIN="$path" ;;
  esac
  export GROK_BIN CLAUDE_BIN OPENCODE_BIN KIMI_BIN CURSOR_AGENT_BIN
}

runtime_env_name() {
  case "$1" in
    grok) printf '%s\n' GROK_BIN ;;
    claude-code) printf '%s\n' CLAUDE_BIN ;;
    opencode) printf '%s\n' OPENCODE_BIN ;;
    kimi-cli) printf '%s\n' KIMI_BIN ;;
    cursor-cli) printf '%s\n' CURSOR_AGENT_BIN ;;
  esac
}

run_runner() {
  TMUX_BIN="$issue_tmux_bin" bash "$runner" "$@"
}

issue_setup
trap issue_cleanup EXIT

if [[ ! -f "$runner" ]]; then
  fail "test_adapter_entrypoint_exists" "missing $runner"
else
  fake_paths=()
  fake_logs=()
  repo="$(issue_new_repo adapters-repo)"
  canonical_repo="$(cd "$repo" && pwd -P)"
  export KIMI_CODE_HOME="$issue_tmp_root/kimi-home"
  export CURSOR_HOME="$issue_tmp_root/cursor-home"
  export KAOLA_START_TIMEOUT=3

  platforms=(grok claude-code opencode kimi-cli cursor-cli)
  for platform in "${platforms[@]}"; do
    IFS=$'\t' read -r fake log < <(issue_make_fake_runtime "$platform")
    fake_paths+=("$fake")
    fake_logs+=("$log")
    prepare_surface "$platform" "$repo"
    runtime_env "$platform" "$fake"
    case "$platform" in
      grok) runtime_session_id=grok-session-fixture ;;
      claude-code) runtime_session_id=0123456789abcdef0123 ;;
      opencode) runtime_session_id=ses_fixture ;;
      kimi-cli) runtime_session_id=01ARZ3NDEKTSV4RRFFQ69G5FAV ;;
      cursor-cli) runtime_session_id=cursor-fixture ;;
    esac
    export FAKE_RUNTIME_NAME="$platform" FAKE_RUNTIME_LOG="$log" FAKE_RUNTIME_SESSION_ID="$runtime_session_id"

    preflight="$(run_runner "$platform" preflight --repo "$repo" --session "${platform}-preflight-$$")" || fail "test_${platform}_preflight_present_surface" "preflight failed: $preflight"
    if [[ "$platform" == grok ]]; then
      expected_recurring=supported
      expected_materialization=not-required
    elif [[ "$platform" == cursor-cli ]]; then
      expected_recurring=unsupported
      expected_materialization=required-at-point-of-use
    else
      expected_recurring=unsupported
      expected_materialization=not-required
    fi
    json_assert "test_${platform}_preflight_capability_declaration" "d['result'] == 'ready' and d['platform'] == '$platform' and d['workflow_next'] and d['kaola_workflow_finalize'] and d['recurring_execution'] == '$expected_recurring' and d['project_materialization'] == '$expected_materialization'" "$preflight"
    json_assert "test_${platform}_preflight_version" "'fixture' in d['runtime_version']" "$preflight"

    # Every adapter must reject a missing executable before touching tmux.
    binary_env="$(runtime_env_name "$platform")"
    missing="$(expect_fail "test_${platform}_missing_binary" env TMUX_BIN="$issue_tmux_bin" "$binary_env=$issue_tmp_root/no-such-$platform" bash "$runner" "$platform" preflight --repo "$repo" --session "${platform}-missing-$$")"
    grep -Eqi 'not found|missing|executable' <<<"$missing" || fail "test_${platform}_missing_binary" "missing-binary refusal lacks evidence: $missing"

    # Verify each launch shape through the real tmux control plane and fake CLI.
    session="${platform}-launch-$$"
    start_output=""
    if ! start_output="$(run_runner "$platform" start --repo "$repo" --session "$session" 2>&1)"; then
      fail "test_${platform}_new_launch" "new start failed: $start_output"
      "$issue_tmux_bin" kill-session -t "=$session" 2>/dev/null || true
      continue
    fi
    status_json="$(run_runner "$platform" status --repo "$repo" --session "$session")"
    json_assert "test_${platform}_runtime_session_id" "d['runtime_session_id'] == '$runtime_session_id'" "$status_json"
    log_text="$(cat "${fake_logs[$(( ${#fake_logs[@]} - 1 ))]}")"
    if [[ "$platform" == claude-code || "$platform" == kimi-cli ]]; then
      grep -Fq $'cwd='"$canonical_repo"$'\targs=' <<<"$log_text" || fail "test_${platform}_new_launch" "runtime did not start from canonical repo cwd: $log_text"
    elif [[ "$platform" == opencode ]]; then
      grep -Fq "args=$canonical_repo --mini" <<<"$log_text" || fail "test_${platform}_new_launch" "OpenCode launch lacks repo --mini shape: $log_text"
    elif [[ "$platform" == cursor-cli ]]; then
      grep -Fq "args=--workspace $canonical_repo" <<<"$log_text" || fail "test_${platform}_new_launch" "Cursor launch lacks --workspace shape: $log_text"
    else
      grep -Fq "args=--cwd $canonical_repo --minimal" <<<"$log_text" || fail "test_${platform}_new_launch" "Grok launch lacks --cwd/--minimal shape: $log_text"
    fi
    run_runner "$platform" stop --repo "$repo" --session "$session" --force >/dev/null || "$issue_tmux_bin" kill-session -t "=$session" 2>/dev/null || true

    # Continue and exact resume are separate launch modes and must not be conflated.
    session="${platform}-continue-$$"
    run_runner "$platform" start --repo "$repo" --session "$session" --continue >/dev/null || fail "test_${platform}_continue_launch" "continue start failed"
    run_runner "$platform" stop --repo "$repo" --session "$session" --force >/dev/null || true
    log_text="$(cat "${fake_logs[$(( ${#fake_logs[@]} - 1 ))]}")"
    case "$platform" in
      grok|opencode|cursor-cli) grep -Fq -- '--continue' <<<"$log_text" || fail "test_${platform}_continue_launch" "--continue absent from invocation: $log_text" ;;
      claude-code|kimi-cli) grep -Fq -- '--continue' <<<"$log_text" || fail "test_${platform}_continue_launch" "--continue absent from invocation: $log_text" ;;
    esac

    session="${platform}-resume-$$"
    resume_value="$runtime_session_id"
    run_runner "$platform" start --repo "$repo" --session "$session" --resume "$resume_value" >/dev/null || fail "test_${platform}_exact_resume_launch" "resume start failed"
    run_runner "$platform" stop --repo "$repo" --session "$session" --force >/dev/null || true
    log_text="$(cat "${fake_logs[$(( ${#fake_logs[@]} - 1 ))]}")"
    grep -Fq -- "$resume_value" <<<"$log_text" || fail "test_${platform}_exact_resume_launch" "resume identifier absent from invocation: $log_text"
    case "$platform" in
      opencode|kimi-cli) grep -Fq -- '--session' <<<"$log_text" || fail "test_${platform}_exact_resume_launch" "session option absent: $log_text" ;;
      grok|claude-code|cursor-cli) grep -Fq -- '--resume' <<<"$log_text" || fail "test_${platform}_exact_resume_launch" "resume option absent: $log_text" ;;
    esac

    # Surface absence is a typed preflight refusal, not an implicit installation.
    case "$platform" in
      claude-code)
        rm "$repo/.claude/commands/workflow-next.md"
        ;;
      opencode)
        rm "$repo/.opencode/agents/kaola.md"
        ;;
      kimi-cli)
        rm "$repo/.kimi-code/skills/workflow-next/SKILL.md"
        ;;
      cursor-cli)
        rm "$CURSOR_HOME/kaola-workflow/cursor-authority.json"
        ;;
      grok)
        # Grok's inspect authority is controlled by the fake runtime output;
        # the missing-surface case is covered by a second fixture below.
        ;;
    esac
    if [[ "$platform" != grok ]]; then
      expect_fail "test_${platform}_missing_kaola_surface" run_runner "$platform" preflight --repo "$repo" --session "${platform}-missing-surface-$$" >/dev/null
    fi
  done

  # Grok must refuse an inspect result that omits either required capability.
  grok_fake="${fake_paths[0]}"
  grok_missing="$issue_tmp_root/grok-missing"
  cat >"$grok_missing" <<'FAKE_GROK_MISSING'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == inspect && "${2:-}" == --json ]]; then
  printf '%s\n' '{"grokVersion":"fixture","skills":[{"name":"workflow-next"}]}'
  exit 0
fi
exec "${REAL_GROK_FIXTURE:?}" "$@"
FAKE_GROK_MISSING
  chmod +x "$grok_missing"
  export REAL_GROK_FIXTURE="$grok_fake"
  runtime_env grok "$grok_missing"
  expect_fail "test_grok_missing_finalize_surface" run_runner grok preflight --repo "$repo" --session grok-missing-finalize-$$ >/dev/null
fi

if [[ "$failures" -gt 0 ]]; then
  printf 'adapter acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'adapter acceptance: PASS\n'
