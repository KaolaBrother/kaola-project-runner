#!/usr/bin/env bash
# Issue #101: run one validate suite under a wall-clock budget so a hung suite
# is killed and diagnosed instead of stalling ./scripts/validate.sh forever.
#
# The suite runs in this script's foreground, so terminal signals reach it
# exactly as they did before. A background monitor watches this script's pid;
# once the budget elapses with the suite still running it records a receipt
# (the live process tree, then `lsof -p` and `sample` of the deepest
# childless process, which is where the Issue #101 self-held here-document
# pipe sat) and only then kills every process below this script, deepest
# first, TERM then KILL. The script exits 124 on a trip and otherwise with the
# suite's own status. macOS ships no timeout(1), hence this file.
#
# This file must never use a here-document or here-string: it exists to catch
# the hang that those cause under pipe-KVA pressure (Issue #78, Issue #101),
# and tests/contract/test-issue-78-heredoc-deadlock.py scans it.
#
# usage: validate-watchdog.sh --label NAME [--budget SECONDS] [--interval SECONDS]
#                             [--receipt-dir DIR] -- COMMAND [ARG...]
set -euo pipefail

usage_line='usage: validate-watchdog.sh --label NAME [--budget SECONDS] [--interval SECONDS] [--receipt-dir DIR] -- COMMAND [ARG...]'
label=""
budget=600
interval=5
receipt_dir="${TMPDIR:-/tmp}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --label|--budget|--interval|--receipt-dir)
      [[ $# -ge 2 ]] || { printf 'validate-watchdog: %s needs a value\n' "$1" >&2; exit 2; }
      case "$1" in
        --label) label="$2" ;;
        --budget) budget="$2" ;;
        --interval) interval="$2" ;;
        --receipt-dir) receipt_dir="$2" ;;
      esac
      shift 2
      ;;
    --) shift; break ;;
    *) printf 'validate-watchdog: unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done
[[ -n "$label" && $# -gt 0 ]] || { printf '%s\n' "$usage_line" >&2; exit 2; }
[[ "$budget" =~ ^[0-9]+$ && "$interval" =~ ^[1-9][0-9]*$ ]] || {
  printf 'validate-watchdog: --budget and --interval take whole seconds\n' >&2
  exit 2
}

# Issue #151: the monitor below needs bash >= 4 (mapfile, BASHPID). On bash 3.2
# (the macOS /bin/bash) mapfile is not a builtin, so under set -e the monitor
# dies the moment it trips and the hung suite it was meant to kill outlives
# it. Detection, not weakening: with the features present the monitor below
# runs unchanged; without them, print one receipt and run the command
# unwatched, its own exit status passing through.
if ! type mapfile >/dev/null 2>&1 || [[ -z "${BASHPID:-}" ]]; then
  printf 'validate-watchdog: SKIP watchdog on bash < 4 (mapfile/BASHPID missing; detected bash %s); running %s unwatched\n' \
    "${BASH_VERSION:-unknown}" "$label" >&2
  status=0
  "$@" || status=$?
  exit "$status"
fi

owner=$$
command_text="$*"
receipt="$receipt_dir/$label.watchdog.txt"
tripping="$receipt_dir/$label.tripping"
tripped="$receipt_dir/$label.tripped"
mkdir -p "$receipt_dir"
rm -f "$receipt" "$tripping" "$tripped"

# Every live process below $owner except the monitor's own subtree ($1). The
# first line is the deepest childless pid (empty when there is none); the
# remaining lines are every descendant, deepest first, which is the kill order.
descendants() {
  ps -axo pid=,ppid= | python3 -c 'import sys
owner, skip = int(sys.argv[1]), int(sys.argv[2])
children = {}
for line in sys.stdin:
    parts = line.split()
    if len(parts) == 2:
        children.setdefault(int(parts[1]), []).append(int(parts[0]))
order = []
def walk(pid, depth):
    for child in children.get(pid, []):
        if child == skip:
            continue
        order.append((depth, child))
        walk(child, depth + 1)
walk(owner, 1)
leaves = [(depth, pid) for depth, pid in order if pid not in children]
print(max(leaves)[1] if leaves else "")
for _, pid in sorted(order, key=lambda item: -item[0]):
    print(pid)' "$owner" "$1"
}

monitor() {
  # $BASHPID here is the monitor subshell; inside a process substitution it
  # would be that substitution's pid, and the monitor would list itself.
  local self=$BASHPID waited=0 tree leaf pid sample_bin sample_file
  while (( waited < budget )); do
    sleep "$interval"
    kill -0 "$owner" 2>/dev/null || exit 0
    waited=$((waited + interval))
  done
  : >"$tripping"
  mapfile -t tree < <(descendants "$self")
  leaf="${tree[0]:-}"
  tree=("${tree[@]:1}")
  if (( ${#tree[@]} == 0 )); then
    # The suite finished as the budget ran out; nothing to diagnose or kill.
    rm -f "$tripping"
    exit 0
  fi
  {
    printf 'watchdog receipt: %s\n' "$label"
    printf 'tripped at: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'budget: %s s (polled every %s s)\n' "$budget" "$interval"
    printf 'owner pid: %s\n' "$owner"
    printf 'command: %s\n' "$command_text"
    printf 'leaf pid: %s\n' "$leaf"
    printf '\n== process tree below the owner (ps) ==\n'
    ps -o pid,ppid,stat,etime,command -p "$(IFS=,; printf '%s' "${tree[*]}")" 2>&1 || true
    if [[ -n "$leaf" ]]; then
      printf '\n== lsof -p %s ==\n' "$leaf"
      lsof -p "$leaf" 2>&1 || true
      printf '\n== sample %s 5 ==\n' "$leaf"
      # The macOS profiler lives in /usr/bin; a Homebrew shim of the same
      # name may shadow it on PATH (and did on the development Mac).
      sample_bin=/usr/bin/sample
      [[ -x "$sample_bin" ]] || sample_bin="$(command -v sample 2>/dev/null || true)"
      if [[ -n "$sample_bin" ]]; then
        sample_file="$receipt_dir/$label.sample.tmp"
        "$sample_bin" "$leaf" 5 -file "$sample_file" >/dev/null 2>&1 || printf 'sample exited %s\n' "$?"
        cat "$sample_file" 2>/dev/null || true
        rm -f "$sample_file"
      else
        printf 'sample(1) not found\n'
      fi
    fi
  } >"$receipt" 2>&1
  for pid in "${tree[@]}"; do kill -TERM "$pid" 2>/dev/null || true; done
  sleep 2
  for pid in "${tree[@]}"; do kill -KILL "$pid" 2>/dev/null || true; done
  : >"$tripped"
}

# The monitor gets no stdio of its own: a command-substitution caller must not
# wait on a pipe end held by the monitor or its sleeping child.
monitor >/dev/null 2>&1 </dev/null & monitor_pid=$!
status=0
"$@" || status=$?
if [[ -e "$tripping" ]]; then
  # The monitor is diagnosing and killing the suite tree; let it finish.
  wait "$monitor_pid" || true
else
  kill "$monitor_pid" 2>/dev/null || true
  wait "$monitor_pid" 2>/dev/null || true
fi
if [[ -e "$tripped" ]]; then
  rm -f "$tripping" "$tripped"
  printf 'FAILED: %s (watchdog: still running after %s s; process tree killed; receipt %s)\n' \
    "$label" "$budget" "$receipt" >&2
  exit 124
fi
rm -f "$tripping"
exit "$status"
