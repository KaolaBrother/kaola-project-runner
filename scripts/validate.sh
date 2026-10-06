#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"

# Issue #265: the contract-suite inventory plus a bounded selector. The
# no-argument entry runs the whole inventory unchanged. `--suite NAME` runs
# only the named suites through this same controlled entry (sandbox HOME,
# validate TMPDIR, KAOLA_* scrub, render/Skill checks, watchdog, sweep). The
# Host chooses the set from the actual affected interfaces and remaining
# uncertainty; this script never infers dependency coverage from filenames,
# a commit identity or a graph. A selected run says it is a subset and never
# claims full-inventory coverage.
usage() {
  printf '%s\n' \
    'usage: scripts/validate.sh [--suite NAME]... [--list] [--help]' \
    '' \
    'With no arguments, run the full contract-suite inventory.' \
    '  --suite NAME  run only the named contract suite(s); repeatable.' \
    '                NAME is an inventory basename (with extension) or a' \
    '                unique stem. Unknown or ambiguous names are rejected.' \
    '  --list        print the valid suite names and exit (read-only).' \
    '  --help        print this help and exit (read-only).' \
    '' \
    'A run (no argument or --suite) keeps the controlled HOME/TMPDIR, the' \
    'inherited KAOLA_* scrub, the required render/Skill checks, the per-suite' \
    'watchdog and the exact sweep. A selected run prints that it is a subset' \
    'and never claims full coverage. --list and --help run no check.'
}

requested_suites=()
resolved_suites=()
select_full=1
list_names=0
# Empty until preparation begins; a read-only --list must not sweep or report.
run_started=""
while (( $# )); do
  case "$1" in
    --suite)
      [[ $# -ge 2 ]] || { printf 'validate: --suite needs a NAME\n' >&2; exit 2; }
      requested_suites+=("$2")
      select_full=0
      shift 2
      ;;
    --suite=*)
      requested_suites+=("${1#--suite=}")
      select_full=0
      shift
      ;;
    --list) list_names=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'validate: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

# The whole suite runs in a controlled temporary HOME: no Codex (or other
# runtime) configuration is required, and real user configuration is never
# read or modified.
sandbox_home="$(mktemp -d "${TMPDIR:-/tmp}/kaola-validate-home.XXXXXX")"
# Issue #63: the suites run under one validate-owned TMPDIR root, so every
# fixture temp root and the shared kaola-<uid>-acp ACP socket dir — and with
# them every spawned holder's --record-dir/--socket — lands under it. An
# interrupted or early-exited run (set -e, SIGINT, SIGTERM) then sweeps
# exactly its own holders on the way out instead of leaking them re-parented
# to launchd. The root is short and flat because ACP admin sockets live
# under it and AF_UNIX sun_path is ~104 bytes on macOS.
validate_tmp="$(mktemp -d "/tmp/kaola-val.XXXXXX")"
# Issue #101: every suite runs under scripts/validate-watchdog.sh, which kills
# and diagnoses a suite that is still running after the budget instead of
# letting validate hang forever (the observed hang sat 13 min before a manual
# kill and left no stack). The budget is 600 s per suite: the slowest single
# suite finishes well inside 400 s and the two Python lanes take ~200 s
# combined, so a trip at 10 min is a hang, not a slow machine, while still
# bounding the loss of a hit to one suite budget. Receipts (process tree,
# lsof and sample of the stuck leaf) land under $watchdog_dir, and a run that
# tripped keeps $validate_tmp so they survive cleanup.
suite_budget="${KAOLA_VALIDATE_SUITE_BUDGET:-600}"
watchdog_dir="$validate_tmp/watchdog"
watched() {
  local label="$1"
  shift
  local t0="${EPOCHREALTIME:-$SECONDS}" rc=0
  "$script_dir/validate-watchdog.sh" --label "$label" --budget "$suite_budget" \
    --receipt-dir "$watchdog_dir" -- "$@" || rc=$?
  local t1="${EPOCHREALTIME:-$SECONDS}"
  printf 'validate: elapsed %-44s %.3f s\n' "$label" \
    "$(awk "BEGIN{print $t1-$t0}" 2>/dev/null || printf '?')" \
    >>"$validate_tmp/elapsed.txt" 2>/dev/null || true
  return "$rc"
}
# Issue #265: report per-suite elapsed lines before the root removal, and the
# true total wall time after this invocation's cleanup. A read-only --list ran
# no suite and reports nothing.
print_elapsed() {
  [[ -n "$run_started" ]] || return 0
  if [[ -f "$validate_tmp/elapsed.txt" ]]; then
    while IFS= read -r line; do
      printf '%s\n' "$line"
    done <"$validate_tmp/elapsed.txt"
  fi
  return 0
}
total_wall() {
  # Never format an unavailable measurement as 0.
  if [[ -z "${wall_start:-}" ]]; then
    printf 'unknown'
    return 0
  fi
  awk "BEGIN{print ${EPOCHREALTIME:-$SECONDS}-$wall_start}" 2>/dev/null || printf 'unknown'
}
# Issue #265 repair: stop every process this invocation started — the lane
# subshells, their watchdogs and the suites they run — before the holder sweep
# and the root removal. A writer that stays alive can recreate $validate_tmp
# after the removal, which is the observed interrupted-cleanup failure (SIGINT
# mid-suite: exit 130, empty sweep residue, rm "Directory not empty"). Only
# descendants of this process are enumerated and signalled, so foreign and
# unrelated work is never named or touched. The TERM/KILL sequence mirrors
# validate-watchdog.sh; it is not a new supervisor.
stop_owned_writers() {
  local -a pids=()
  local pid listing
  # The enumerator runs ps as its own child and drops its whole subtree, so
  # the transient enumerator never counts as a writer (a clean run then has no
  # descendant and pays no grace).
  listing="$(python3 -c '
import os, subprocess, sys
owner = int(sys.argv[1])
out = subprocess.run(["ps", "-axo", "pid=,ppid="],
                     capture_output=True, text=True).stdout
children = {}
parent = {}
for line in out.splitlines():
    parts = line.split()
    if len(parts) == 2:
        pid, ppid = int(parts[0]), int(parts[1])
        children.setdefault(ppid, []).append(pid)
        parent[pid] = ppid
excluded = set()
def collect(pid):
    excluded.add(pid)
    for child in children.get(pid, []):
        collect(child)
# Drop the enumerator: itself, its own subtree (the ps child) and every
# ancestor below the owner (the command-substitution subshell).
collect(os.getpid())
p = parent.get(os.getpid(), 0)
while p not in (0, 1, owner):
    collect(p)
    p = parent.get(p, 0)
order = []
def walk(pid, depth):
    for child in children.get(pid, []):
        if child in excluded:
            continue
        order.append((depth, child))
        walk(child, depth + 1)
walk(owner, 1)
for _, pid in sorted(order, key=lambda item: -item[0]):
    print(pid)' "$$")"
  for pid in $listing; do
    if [[ "$pid" =~ ^[0-9]+$ ]]; then
      pids+=("$pid")
    fi
  done
  (( ${#pids[@]} )) || return 0
  for pid in "${pids[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  sleep 2
  for pid in "${pids[@]}"; do
    kill -KILL "$pid" 2>/dev/null || true
  done
  return 0
}
cleanup_done=""
cleanup() {
  if [[ -z "$cleanup_done" ]]; then
    cleanup_done=1
    print_elapsed
    if [[ -n "$run_started" ]]; then
      # Stop and reap this invocation's writers before the holder sweep and
      # the root removal. Nothing outside this invocation is signalled.
      stop_owned_writers
      if [[ -n "${lane_a:-}" ]]; then wait "$lane_a" 2>/dev/null || true; fi
      if [[ -n "${lane_b:-}" ]]; then wait "$lane_b" 2>/dev/null || true; fi
      # Sweep before removal and never let a nonzero sweep block the removal.
      python3 "$repo_root/scripts/kaola-acp-sweep.py" --root "$validate_tmp" || true
    fi
    if compgen -G "$watchdog_dir/*.watchdog.txt" >/dev/null; then
      printf 'validate: watchdog receipt(s) retained under %s\n' "$watchdog_dir" >&2
      rm -rf "$sandbox_home" || true
    else
      rm -rf "$validate_tmp" "$sandbox_home" || true
    fi
    if [[ -n "$run_started" ]]; then
      printf 'validate: total wall: %s s\n' "$(total_wall)"
    fi
  fi
  return 0
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
export HOME="$sandbox_home"
export TMPDIR="$validate_tmp"
unset CODEX_HOME CLAUDE_CONFIG_DIR DEVIN_CONFIG_DIR
# Issue #115: a seat a live Host dispatched inherits that Host's binding
# (KAOLA_ACP_HEARTBEAT_HOST[_SOCKET], KAOLA_ACP_DISPATCHER, KAOLA_ZCODE_ENTRY/
# NODE, KAOLA_CLAUDE_PROFILE_REQUIRED, ...), and fixture starts that copy
# os.environ then bind to the real Host. Every suite sets the KAOLA_* fixtures
# it needs itself, so the whole inherited KAOLA_* namespace is dropped here
# (not a fixed list that each new binding name would outgrow); only validate's
# own KAOLA_VALIDATE_* knobs survive.
scrubbed_names=()
for name in $(compgen -e); do
  if [[ "$name" == KAOLA_* && "$name" != KAOLA_VALIDATE_* ]]; then
    unset "$name"
    scrubbed_names+=("$name")
  fi
done

python_suites_all=(
  "test-issue-78-heredoc-deadlock.py"
  "test-devin-regressions.py"
  "test-acp-contract.py"
  "test-acp-watch-contract.py"
  "test-acp-follow-contract.py"
  "test-acp-holder-continue.py"
  "test-acp-sweep-contract.py"
  "test-issue-33-config-meta.py"
  "test-runner-v2.py"
  "test-generated-skills.py"
  "test-issue-24-opencode-no-skip-all.py"
  "test-issue-41-orchestrator.py"
  "test-issue-68-heartbeat-snapshot.py"
  "test-issue-72-session-naming.py"
  "test-issue-73-canonical-root.py"
  "test-issue-49-grok-bot-host.py"
  "test-progressive-disclosure.py"
  "test-issue-50-claude-acp-bridge.py"
  "test-issue-50-runner-integration.py"
  "test-zcode-acp-contract.py"
  "test-droid-acp-contract.py"
  "test-issue-51-runner-integration.py"
  "test-zcode-host-contract.py"
  "test-zcode-heartbeat-contract.py"
  "test-issue-52-workflow-worktree.py"
  "test-issue-64-receipt-bound.py"
  "test-issue-65-steering.py"
  "test-issue-65-steer-race.py"
  "test-issue-65-host-contract.py"
  "test-issue-70-binding-fact.py"
  "test-issue-76-permission-wake.py"
  "test-issue-79-zcode-312.py"
  "test-issue-83-lane-failure-visibility.py"
  "test-issue-74-kaola-delegator.py"
  "test-issue-75-codex-compact-hook.py"
  "test-issue-94-zcode-native-skill-entry.py"
  "test-issue-84-zcode-native-resume.py"
  "test-issue-85-zcode-resume-advertised-model.py"
  "test-issue-86-delegator-quota.py"
  "test-issue-88-permission-defaults.py"
  "test-issue-90-event-confirmation-race.py"
  "test-issue-173-codex-system-error-turn.py"
  "test-issue-92-permission-wake-recovery.py"
  "test-issue-95-reader-exception.py"
  "test-issue-97-codex-user-compact-hook.py"
  "test-issue-98-dsh-acp.py"
  "test-issue-101-validate-watchdog.py"
  "test-issue-111-model-tiers.py"
  "test-issue-118-seat-cap.py"
  "test-issue-119-host-entry.py"
  "test-issue-123-shared-refs.py"
  "test-issue-133-mission-ledger.py"
  "test-issue-147-installed-survey.py"
  "test-issue-148-quota-packages.py"
  "test-issue-146-session-new-wait.py"
  "test-lifecycle-contract.py"
  "test-issue-22-bypass-all-approvals.py"
  "test-issue-130-pty-retired.py"
  "test-issue-162-upgrade-safety.py"
  "test-issue-164-pre-spawn-bridge-facts.py"
  "test-issue-165-path-drift.py"
  "test-issue-168-drift-enumeration.py"
  "test-issue-186-claude-native-identity.py"
  "test-issue-187-delegator-any-host.py"
  "test-issue-215-install-truthfulness.py"
  "test-issue-218-preset-ids.py"
  "test-issue-236-install-completion.py"
  "test-issue-237-model-display.py"
  "test-issue-244-dispatch.py"
  "test-issue-244-holder-prompt-binding.py"
  "test-issue-245-session-role.py"
  "test-issue-247-codex-child.py"
  "test-issue-260-transport.py"
  "test-issue-254-opencode-model.py"
  "test-issue-255-lifecycle-state.py"
)
python_suites_a=(
  "test-issue-79-zcode-312.py"
  "test-issue-84-zcode-native-resume.py"
  "test-issue-85-zcode-resume-advertised-model.py"
  "test-issue-65-steering.py"
  "test-acp-contract.py"
  "test-zcode-heartbeat-contract.py"
  "test-issue-76-permission-wake.py"
  "test-acp-follow-contract.py"
  "test-progressive-disclosure.py"
  "test-droid-acp-contract.py"
  "test-issue-41-orchestrator.py"
  "test-issue-68-heartbeat-snapshot.py"
  "test-issue-72-session-naming.py"
  "test-runner-v2.py"
  "test-issue-83-lane-failure-visibility.py"
  "test-issue-88-permission-defaults.py"
  "test-issue-92-permission-wake-recovery.py"
  "test-issue-97-codex-user-compact-hook.py"
  "test-issue-98-dsh-acp.py"
  "test-issue-101-validate-watchdog.py"
  "test-issue-118-seat-cap.py"
  "test-issue-146-session-new-wait.py"
  "test-lifecycle-contract.py"
  "test-issue-215-install-truthfulness.py"
  "test-issue-218-preset-ids.py"
  "test-issue-236-install-completion.py"
  "test-issue-237-model-display.py"
  "test-issue-255-lifecycle-state.py"
)
python_suites_b=(
  "test-issue-78-heredoc-deadlock.py"
  "test-issue-33-config-meta.py"
  "test-issue-50-runner-integration.py"
  "test-issue-49-grok-bot-host.py"
  "test-acp-watch-contract.py"
  "test-acp-holder-continue.py"
  "test-zcode-host-contract.py"
  "test-issue-50-claude-acp-bridge.py"
  "test-issue-51-runner-integration.py"
  "test-acp-sweep-contract.py"
  "test-zcode-acp-contract.py"
  "test-generated-skills.py"
  "test-devin-regressions.py"
  "test-issue-52-workflow-worktree.py"
  "test-issue-24-opencode-no-skip-all.py"
  "test-issue-64-receipt-bound.py"
  "test-issue-65-steer-race.py"
  "test-issue-65-host-contract.py"
  "test-issue-70-binding-fact.py"
  "test-issue-73-canonical-root.py"
  "test-issue-74-kaola-delegator.py"
  "test-issue-75-codex-compact-hook.py"
  "test-issue-94-zcode-native-skill-entry.py"
  "test-issue-86-delegator-quota.py"
  "test-issue-90-event-confirmation-race.py"
  "test-issue-173-codex-system-error-turn.py"
  "test-issue-95-reader-exception.py"
  "test-issue-111-model-tiers.py"
  "test-issue-119-host-entry.py"
  "test-issue-123-shared-refs.py"
  "test-issue-133-mission-ledger.py"
  "test-issue-147-installed-survey.py"
  "test-issue-148-quota-packages.py"
  "test-issue-22-bypass-all-approvals.py"
  "test-issue-130-pty-retired.py"
  "test-issue-162-upgrade-safety.py"
  "test-issue-164-pre-spawn-bridge-facts.py"
  "test-issue-165-path-drift.py"
  "test-issue-168-drift-enumeration.py"
  "test-issue-186-claude-native-identity.py"
  "test-issue-187-delegator-any-host.py"
  "test-issue-244-dispatch.py"
  "test-issue-244-holder-prompt-binding.py"
  "test-issue-245-session-role.py"
  "test-issue-247-codex-child.py"
  "test-issue-260-transport.py"
  "test-issue-254-opencode-model.py"
)

# Selectable shell contract suites: they run serially before the Python lanes.
shell_suites=(
  "test-installer-migration.sh"
  "test-installer-runtimes.sh"
)

array_contains() {
  local needle="$1" item
  shift
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

# Resolve one requested name to its canonical inventory basename. Exact
# basenames win; otherwise a unique stem resolves. Zero matches is unknown;
# several matches is ambiguous. Both are refused with the matches named.
resolve_suite() {
  local want="$1" suite stem
  local matches=()
  for suite in "${shell_suites[@]}" "${python_suites_all[@]}"; do
    [[ "$suite" == "$want" ]] && { printf '%s\n' "$suite"; return 0; }
  done
  for suite in "${shell_suites[@]}" "${python_suites_all[@]}"; do
    stem="${suite%.*}"
    [[ "$stem" == "$want" ]] && matches+=("$suite")
  done
  if (( ${#matches[@]} == 1 )); then
    printf '%s\n' "${matches[0]}"
    return 0
  fi
  if (( ${#matches[@]} > 1 )); then
    printf 'validate: ambiguous suite %s matches: %s\n' "$want" "${matches[*]}" >&2
    return 2
  fi
  printf 'validate: unknown suite: %s\n' "$want" >&2
  return 1
}

if (( list_names )); then
  for suite in "${shell_suites[@]}" "${python_suites_all[@]}"; do
    printf '%s\n' "$suite"
  done
  exit 0
fi

printf 'validate: scrubbed inherited env: %s\n' "${scrubbed_names[*]:-none}"

inventory_total=$(( ${#shell_suites[@]} + ${#python_suites_all[@]} ))

if (( ! select_full )); then
  for name in "${requested_suites[@]}"; do
    if canonical="$(resolve_suite "$name")"; then
      array_contains "$canonical" "${resolved_suites[@]}" || resolved_suites+=("$canonical")
    else
      printf 'validate: valid names are contract suite basenames; list them with: ./scripts/validate.sh --list\n' >&2
      exit 2
    fi
  done
  # Narrow the Python lanes to the selected suites; the replay below still
  # walks python_suites_all, now the selected set. The no-argument path leaves
  # every array untouched.
  keep_all=()
  keep_a=()
  keep_b=()
  for suite in "${python_suites_all[@]}"; do
    if array_contains "$suite" "${resolved_suites[@]}"; then
      keep_all+=("$suite")
      if array_contains "$suite" "${python_suites_a[@]}"; then
        keep_a+=("$suite")
      else
        keep_b+=("$suite")
      fi
    fi
  done
  python_suites_all=("${keep_all[@]+"${keep_all[@]}"}")
  python_suites_a=("${keep_a[@]+"${keep_a[@]}"}")
  python_suites_b=("${keep_b[@]+"${keep_b[@]}"}")
fi

suite_selected() {
  (( select_full )) && return 0
  array_contains "$1" "${resolved_suites[@]}"
}

# Candidate commit and dirty state are execution context for the receipt. They
# are not a complete source identity, and a new commit alone does not
# invalidate an unchanged valid result.
if git -C "$repo_root" rev-parse --git-dir >/dev/null 2>&1; then
  candidate_commit="$(git -C "$repo_root" rev-parse --short HEAD 2>/dev/null || printf 'unknown')"
  if [[ -n "$(git -C "$repo_root" status --porcelain 2>/dev/null)" ]]; then
    candidate_state="dirty"
  else
    candidate_state="clean"
  fi
else
  candidate_commit="unavailable"
  candidate_state="not a git checkout"
fi

if (( select_full )); then
  printf 'validate: coverage: FULL INVENTORY (%s suites; no-argument run)\n' "$inventory_total"
  printf 'validate: selected: all %s inventory suites\n' "$inventory_total"
else
  printf 'validate: coverage: SUBSET RUN (%s of %s suites selected; not full-inventory coverage)\n' \
    "${#resolved_suites[@]}" "$inventory_total"
  printf 'validate: selected: %s\n' "${resolved_suites[*]}"
fi
printf 'validate: candidate: %s (%s) - execution context, not complete input identity\n' \
  "$candidate_commit" "$candidate_state"

wall_start="${EPOCHREALTIME:-$SECONDS}"
run_started=1

watched render-check python3 "$repo_root/scripts/render-skills.py" --check
for skill_dir in "$repo_root"/skills/*kaola-project-runner "$repo_root"/skills/kaola-delegator; do
  watched "validate-skill.${skill_dir##*/}" python3 "$repo_root/scripts/validate-skill.py" "$skill_dir"
done
bash -n "$repo_root/scripts/kaola-tmux.sh" "$repo_root"/scripts/adapters/*.sh \
  "$repo_root/scripts/install-local.sh" "$repo_root/scripts/validate-watchdog.sh"
# Issue #265: a selected run runs only the named shell suites. The no-argument
# inventory runs both. The body stays at column 0 so the watchdog wiring is
# visible and unchanged.
if suite_selected test-installer-migration.sh; then
watched installer-migration bash "$repo_root/tests/contract/test-installer-migration.sh"
fi
if suite_selected test-installer-runtimes.sh; then
watched installer-runtimes bash "$repo_root/tests/contract/test-installer-runtimes.sh"
fi

# The contract suites dominate validate wall time (measured ~200 s combined).
# Every suite is a self-contained fixture under the validate-owned TMPDIR
# root — its temp dirs, ACP record dirs, and the shared kaola-<uid>-acp
# socket dir all descend from $validate_tmp — so they run as concurrent
# lanes instead of one serial list. Nothing is skipped: each suite runs the
# identical command it ran serially, its log is replayed in the original
# order after every lane finishes, and the logs live under $validate_tmp so
# the Issue #63 sweep still covers exactly this invocation's holders and the
# root removal takes the logs with it. A lane reports FAILED per failing
# suite but still runs every suite, and the script exits nonzero only after
# every suite has run; a suite that somehow left no log is reported SKIPPED
# rather than letting a missing-log cat error abort the replay (Issue #83).
run_suite_lane() {
  local status=0 rc
  for suite in "$@"; do
    rc=0
    if [[ "$suite" == *.sh ]]; then
      watched "$suite" bash "$repo_root/tests/contract/$suite" >"$validate_tmp/$suite.log" 2>&1 || rc=$?
    else
      watched "$suite" python3 "$repo_root/tests/contract/$suite" >"$validate_tmp/$suite.log" 2>&1 || rc=$?
    fi
    if (( rc == 124 )); then
      printf 'FAILED: %s (watchdog: still running after %s s, killed; receipt %s)\n' \
        "$suite" "$suite_budget" "$watchdog_dir/$suite.watchdog.txt"
      status=1
    elif (( rc != 0 )); then
      printf 'FAILED: %s\n' "$suite"
      status=1
    fi
  done
  return "$status"
}
run_suite_lane "${python_suites_a[@]+"${python_suites_a[@]}"}" & lane_a=$!
run_suite_lane "${python_suites_b[@]+"${python_suites_b[@]}"}" & lane_b=$!
python_status=0
wait "$lane_a" || python_status=1
wait "$lane_b" || python_status=1
for suite in "${python_suites_all[@]}"; do
  if [[ -f "$validate_tmp/$suite.log" ]]; then
    cat "$validate_tmp/$suite.log"
  else
    printf 'SKIPPED: %s (no log; execution status unknown)\n' "$suite"
    python_status=1
  fi
done
if (( python_status )); then
  exit 1
fi
watched grok-bot-verify python3 "$repo_root/scripts/kaola-grok-bot-verify.py" "$repo_root/hosts/grok-bot" --repo "$repo_root"

# Acceptance line "git diff --check clean": tracked changes must carry no whitespace errors.
if git -C "$repo_root" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$repo_root" diff --check
  git -C "$repo_root" diff --check --cached
fi
