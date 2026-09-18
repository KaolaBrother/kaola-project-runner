#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
installer_source="$project_root/scripts/install-local.sh"

failures=0
fail() {
  printf 'RED: %s — %s\n' "$1" "$2" >&2
  failures=$((failures + 1))
}

assert_link() {
  local name="$1" target="$2" expected="$3"
  if [[ ! -L "$target" ]]; then
    fail "$name" "expected symlink at $target"
    return
  fi
  local actual
  actual="$(readlink "$target")"
  [[ "$actual" == "$expected" ]] || fail "$name" "link is $actual, expected $expected"
}

source_for() {
  local root="$1" name="$2"
  (cd "$root/skills/$name" && pwd -P)
}

assert_absent() {
  local name="$1" path="$2"
  [[ ! -e "$path" && ! -L "$path" ]] || fail "$name" "unexpected path remains: $path"
}

make_fixture() {
  local root="$1"
  mkdir -p "$root/scripts" "$root/skills"
  cp "$installer_source" "$root/scripts/install-local.sh"
  chmod +x "$root/scripts/install-local.sh"
  cp "$project_root/scripts/kaola-acp.py" "$root/scripts/kaola-acp.py"
  cp "$project_root/scripts/kaola-acp-holder.py" "$root/scripts/kaola-acp-holder.py"
  cp "$project_root/scripts/kaola-locate.py" "$root/scripts/kaola-locate.py"
  mkdir -p "$root/skills/kaola-project-runner"
  printf '%s\n' 'kaola-project-runner' >"$root/skills/kaola-project-runner/.generated-by-kaola-project-runner"
  printf '%s\n' '# fixture Skill' >"$root/skills/kaola-project-runner/SKILL.md"
  mkdir -p "$root/skills/kaola-delegator"
  printf '%s\n' 'kaola-delegator' >"$root/skills/kaola-delegator/.generated-by-kaola-project-runner"
  printf '%s\n' '# fixture Skill' >"$root/skills/kaola-delegator/SKILL.md"
  for id in grok claude-code opencode kimi-cli cursor-cli devin codex zcode droid; do
    case "$id" in
      grok) name=grok-kaola-project-runner ;;
      claude-code) name=claude-code-kaola-project-runner ;;
      opencode) name=opencode-kaola-project-runner ;;
      kimi-cli) name=kimi-cli-kaola-project-runner ;;
      cursor-cli) name=cursor-cli-kaola-project-runner ;;
      devin) name=devin-kaola-project-runner ;;
      codex) name=codex-kaola-project-runner ;;
      zcode) name=zcode-kaola-project-runner ;;
      droid) name=droid-kaola-project-runner ;;
    esac
    mkdir -p "$root/skills/$name"
    printf '%s\n' "$name" >"$root/skills/$name/.generated-by-kaola-project-runner"
    printf '%s\n' '# fixture Skill' >"$root/skills/$name/SKILL.md"
  done
}

run_installer() {
  local root="$1" codex_home="$2"
  shift 2
  # HOME is redirected (uniquely per codex_home) so the installer's
  # ~/.local/bin links stay inside the fixture instead of touching the
  # developer's real bin directory.
  HOME="$tmp_root/home-$(basename "$codex_home")" CODEX_HOME="$codex_home" "$root/scripts/install-local.sh" "$@"
}

tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/kaola-installer-issue-1.XXXXXX")"
trap 'rm -rf "$tmp_root"' EXIT

ids=(grok claude-code opencode kimi-cli cursor-cli devin codex zcode droid)
names=(grok-kaola-project-runner claude-code-kaola-project-runner opencode-kaola-project-runner kimi-cli-kaola-project-runner cursor-cli-kaola-project-runner devin-kaola-project-runner codex-kaola-project-runner zcode-kaola-project-runner droid-kaola-project-runner)

if [[ ! -f "$installer_source" ]]; then
  fail "test_installer_exists" "missing $installer_source"
else
  # A normal install must atomically prepare all nine workers plus the orchestrator.
  repo="$tmp_root/repo-all"
  codex="$tmp_root/codex-all"
  make_fixture "$repo"
  output="$(run_installer "$repo" "$codex" --method link 2>&1)" || fail "test_install_all_nine" "install failed: $output"
  for i in "${!ids[@]}"; do
    assert_link "test_install_all_nine_${ids[$i]}" "$codex/skills/${names[$i]}" "$(source_for "$repo" "${names[$i]}")"
  done
  assert_link "test_install_all_includes_orchestrator" "$codex/skills/kaola-project-runner" \
    "$(source_for "$repo" kaola-project-runner)"

  # The exact old root link is the one and only legacy carrier that may migrate.
  repo="$tmp_root/repo-migrate"
  codex="$tmp_root/codex-migrate"
  make_fixture "$repo"
  mkdir -p "$codex/skills"
  ln -s "$repo" "$codex/skills/grok-kaola-project-runner"
  output="$(run_installer "$repo" "$codex" --method link 2>&1)" || fail "test_legacy_grok_root_symlink_migrates" "install failed: $output"
  for i in "${!ids[@]}"; do
    assert_link "test_legacy_grok_root_symlink_migrates_${ids[$i]}" "$codex/skills/${names[$i]}" "$(source_for "$repo" "${names[$i]}")"
  done
  assert_link "test_legacy_migrate_includes_orchestrator" "$codex/skills/kaola-project-runner" \
    "$(source_for "$repo" kaola-project-runner)"

  before="$(find "$codex/skills" -maxdepth 1 -type l -print -exec readlink {} \; | sort)"
  output="$(run_installer "$repo" "$codex" --method link 2>&1)" || fail "test_install_is_idempotent" "second install failed: $output"
  after="$(find "$codex/skills" -maxdepth 1 -type l -print -exec readlink {} \; | sort)"
  [[ "$before" == "$after" ]] || fail "test_install_is_idempotent" "second install changed carrier set"

  # Foreign carriers are refused before any sibling Skill is installed.
  repo="$tmp_root/repo-foreign"
  codex="$tmp_root/codex-foreign"
  foreign="$tmp_root/foreign-target"
  make_fixture "$repo"
  mkdir -p "$foreign" "$codex/skills"
  ln -s "$foreign" "$codex/skills/grok-kaola-project-runner"
  set +e
  output="$(run_installer "$repo" "$codex" --method link 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || fail "test_foreign_symlink_is_refused" "installer unexpectedly succeeded"
  [[ "$(readlink "$codex/skills/grok-kaola-project-runner")" == "$foreign" ]] || fail "test_foreign_symlink_is_refused" "foreign symlink changed"
  for name in "${names[@]:1}"; do
    assert_absent "test_foreign_symlink_is_refused_no_partial_${name}" "$codex/skills/$name"
  done
  assert_absent "test_foreign_symlink_is_refused_no_partial_orchestrator" "$codex/skills/kaola-project-runner"

  # A refusal applies equally to directories, regular files, and FIFOs.
  for carrier in directory file fifo; do
    repo="$tmp_root/repo-$carrier"
    codex="$tmp_root/codex-$carrier"
    make_fixture "$repo"
    mkdir -p "$codex/skills"
    case "$carrier" in
      directory) mkdir "$codex/skills/grok-kaola-project-runner" ;;
      file) printf '%s\n' foreign >"$codex/skills/grok-kaola-project-runner" ;;
      fifo) mkfifo "$codex/skills/grok-kaola-project-runner" ;;
    esac
    set +e
    output="$(run_installer "$repo" "$codex" --method link 2>&1)"
    rc=$?
    set -e
    [[ "$rc" -ne 0 ]] || fail "test_${carrier}_carrier_is_refused" "installer unexpectedly succeeded"
    case "$carrier" in
      directory) [[ -d "$codex/skills/grok-kaola-project-runner" ]] || fail "test_${carrier}_carrier_is_refused" "directory changed" ;;
      file) [[ -f "$codex/skills/grok-kaola-project-runner" ]] || fail "test_${carrier}_carrier_is_refused" "file changed" ;;
      fifo) [[ -p "$codex/skills/grok-kaola-project-runner" ]] || fail "test_${carrier}_carrier_is_refused" "FIFO changed" ;;
    esac
    for name in "${names[@]:1}"; do
      assert_absent "test_${carrier}_carrier_is_refused_no_partial_${name}" "$codex/skills/$name"
    done
    assert_absent "test_${carrier}_carrier_is_refused_no_partial_orchestrator" "$codex/skills/kaola-project-runner"
  done
fi

if [[ "$failures" -gt 0 ]]; then
  printf 'installer migration acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'installer migration acceptance: PASS\n'
