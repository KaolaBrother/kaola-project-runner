#!/usr/bin/env bash
set -euo pipefail

# Contract coverage for the runtime-neutral installer: named runtimes,
# --skills-dir, link/copy methods, receipts, coexistence, and bin-link scope.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
installer_source="$project_root/scripts/install-local.sh"
validator_source="$project_root/scripts/validate-skill.py"

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

assert_absent() {
  local name="$1" path="$2"
  [[ ! -e "$path" && ! -L "$path" ]] || fail "$name" "unexpected path remains: $path"
}

assert_dir() {
  local name="$1" path="$2"
  [[ -d "$path" && ! -L "$path" ]] || fail "$name" "expected real directory at $path"
}

assert_file() {
  local name="$1" path="$2"
  [[ -f "$path" ]] || fail "$name" "expected file at $path"
}

source_for() {
  local root="$1" name="$2"
  (cd "$root/skills/$name" && pwd -P)
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
  for id in grok claude-code opencode kimi-cli cursor-cli devin droid codex zcode; do
    case "$id" in
      grok) name=grok-kaola-project-runner ;;
      claude-code) name=claude-code-kaola-project-runner ;;
      opencode) name=opencode-kaola-project-runner ;;
      kimi-cli) name=kimi-cli-kaola-project-runner ;;
      cursor-cli) name=cursor-cli-kaola-project-runner ;;
      devin) name=devin-kaola-project-runner ;;
      droid) name=droid-kaola-project-runner ;;
      codex) name=codex-kaola-project-runner ;;
      zcode) name=zcode-kaola-project-runner ;;
    esac
    mkdir -p "$root/skills/$name/scripts"
    printf '%s\n' "$name" >"$root/skills/$name/.generated-by-kaola-project-runner"
    printf '%s\n' '# fixture Skill' >"$root/skills/$name/SKILL.md"
    printf '%s\n' '#!/usr/bin/env bash' 'exit 0' >"$root/skills/$name/scripts/runtime-tmux.sh"
    chmod +x "$root/skills/$name/scripts/runtime-tmux.sh"
  done
}

run_installer() {
  # HOME/DEVIN_CONFIG_DIR/CODEX_HOME are redirected so nothing touches real
  # user dirs; a caller-provided CODEX_HOME still wins for codex-runtime cases.
  local root="$1" home="$2"
  shift 2
  HOME="$home" DEVIN_CONFIG_DIR="$home/devin-config" \
    CODEX_HOME="${CODEX_HOME:-$home/codex-default}" "$root/scripts/install-local.sh" "$@"
}

tmp_root="$(cd "$(mktemp -d "${TMPDIR:-/tmp}/kaola-installer-runtimes.XXXXXX")" && pwd -P)"
trap 'rm -rf "$tmp_root"' EXIT

# --- named runtimes resolve to their verified native directories ------------
repo="$tmp_root/repo-runtimes"
make_fixture "$repo"
home="$tmp_root/home-runtimes"
output="$(run_installer "$repo" "$home" --runtime claude-code --platform grok --method link 2>&1)" \
  || fail "test_runtime_claude_code_install" "install failed: $output"
assert_link "test_runtime_claude_code_install" "$home/.claude/skills/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"
assert_absent "test_runtime_claude_code_no_external" "$home/.claude/skills/kaola-delegator"
assert_absent "test_runtime_claude_code_no_bin_links" "$home/.local/bin/kaola-acp"

output="$(run_installer "$repo" "$home" --runtime cursor --platform grok --method link 2>&1)" \
  || fail "test_runtime_cursor_install" "install failed: $output"
assert_link "test_runtime_cursor_install" "$home/.cursor/skills/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"

output="$(run_installer "$repo" "$home" --runtime devin --platform grok --method link 2>&1)" \
  || fail "test_runtime_devin_install" "install failed: $output"
assert_link "test_runtime_devin_install" "$home/devin-config/skills/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"
assert_absent "test_runtime_devin_no_bin_links" "$home/.local/bin/kaola-acp"

# ZCode is a worker platform and a native skill-directory Host:
# --runtime zcode installs to $HOME/.zcode/skills.
output="$(run_installer "$repo" "$home" --runtime zcode --platform grok --method link 2>&1)" \
  || fail "test_runtime_zcode_install" "install failed: $output"
assert_link "test_runtime_zcode_install" "$home/.zcode/skills/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"
assert_absent "test_runtime_zcode_no_external" "$home/.zcode/skills/kaola-delegator"
assert_absent "test_runtime_zcode_no_bin_links" "$home/.local/bin/kaola-acp"

# --- argument validation -----------------------------------------------------
set +e
output="$(run_installer "$repo" "$home" --runtime bogus --platform grok 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_unknown_runtime_refused" "unexpected success"
set +e
output="$(run_installer "$repo" "$home" --runtime grok --platform grok 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_runtime_grok_is_not_host" "unexpected success"
[[ "$output" == *"unknown runtime: grok"* ]] || fail "test_runtime_grok_is_not_host" "expected grok host/worker distinction, got: $output"
[[ "$output" == *"bridge host"* ]] || fail "test_runtime_grok_is_not_host" "expected bridge-host hint, got: $output"
[[ "$output" == *"--platform grok"* ]] || fail "test_runtime_grok_is_not_host" "expected platform grok hint, got: $output"
set +e
output="$(run_installer "$repo" "$home" --platform grok-bot 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_platform_grok_bot_refused" "unexpected success"
[[ "$output" == *"unknown platform"* ]] || fail "test_platform_grok_bot_refused" "expected unknown platform, got: $output"
set +e
output="$(run_installer "$repo" "$home" --runtime codex --skills-dir "$tmp_root/x" 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_runtime_skills_dir_mutually_exclusive" "unexpected success"
set +e
output="$(run_installer "$repo" "$home" --skills-dir relative/path 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_relative_skills_dir_refused" "unexpected success"
set +e
output="$(run_installer "$repo" "$home" --method bogus 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_unknown_method_refused" "unexpected success"

# --- --skills-dir with spaces, link method -----------------------------------
repo="$tmp_root/repo-spaces"
make_fixture "$repo"
home="$tmp_root/home-spaces"
dest="$tmp_root/dest with spaces/skills"
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method link --platform grok,codex 2>&1)" \
  || fail "test_skills_dir_with_spaces" "install failed: $output"
assert_link "test_skills_dir_with_spaces_grok" "$dest/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"
assert_link "test_skills_dir_with_spaces_codex" "$dest/codex-kaola-project-runner" \
  "$(source_for "$repo" codex-kaola-project-runner)"
assert_absent "test_skills_dir_no_bin_links" "$home/.local/bin/kaola-acp"

# A workspace .zcode/skills destination (a live-verified ZCode Host default
# discovery root; .agents/skills is verified too, and configured
# skills.roots/plugins.dirs roots also scan) goes through --skills-dir; the
# payload is identical.
ws="$tmp_root/workspace-zcode/.zcode/skills"
output="$(run_installer "$repo" "$home" --skills-dir "$ws" --method link --platform zcode 2>&1)" \
  || fail "test_workspace_zcode_skills_dir" "install failed: $output"
assert_link "test_workspace_zcode_skills_dir" "$ws/zcode-kaola-project-runner" \
  "$(source_for "$repo" zcode-kaola-project-runner)"
assert_orch="$tmp_root/workspace-zcode/.zcode/skills/kaola-project-runner"
assert_link "test_workspace_zcode_orchestrator" "$assert_orch" \
  "$(source_for "$repo" kaola-project-runner)"
assert_link "test_workspace_zcode_external" "$tmp_root/workspace-zcode/.zcode/skills/kaola-delegator" \
  "$(source_for "$repo" kaola-delegator)"

# --- copy method: payload identical, receipt outside the payload -------------
repo="$tmp_root/repo-copy"
make_fixture "$repo"
home="$tmp_root/home-copy"
dest="$tmp_root/copy-dest/skills"
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok 2>&1)" \
  || fail "test_copy_install" "install failed: $output"
assert_dir "test_copy_install_is_real_dir" "$dest/grok-kaola-project-runner"
assert_file "test_copy_install_payload" "$dest/grok-kaola-project-runner/SKILL.md"
assert_file "test_copy_install_marker" "$dest/grok-kaola-project-runner/.generated-by-kaola-project-runner"
assert_file "test_copy_install_receipt" "$dest/.kaola-install-receipts/grok-kaola-project-runner.json"
[[ -x "$dest/grok-kaola-project-runner/scripts/runtime-tmux.sh" ]] \
  || fail "test_copy_install_exec_bits" "copied script lost execute permission"
if [[ -e "$dest/grok-kaola-project-runner/.kaola-install-receipts" ]]; then
  fail "test_copy_receipt_outside_payload" "receipt written inside Skill payload"
fi
diff -r "$repo/skills/grok-kaola-project-runner" "$dest/grok-kaola-project-runner" >/dev/null \
  || fail "test_copy_identical_content" "copied content differs from source payload"

# identical owned content is a no-op
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok 2>&1)" \
  || fail "test_copy_reinstall_noop" "reinstall failed: $output"
[[ "$output" == *"already installed:"* ]] \
  || fail "test_copy_reinstall_noop" "expected no-op report, got: $output"

# Runtime-generated Python cache is not an installed payload edit.
mkdir -p "$dest/grok-kaola-project-runner/scripts/__pycache__"
printf '%s\n' bytecode >"$dest/grok-kaola-project-runner/scripts/__pycache__/runtime.cpython-314.pyc"
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok 2>&1)" \
  || fail "test_copy_cache_is_advisory" "cache-only reinstall failed: $output"
[[ "$output" == *"already installed:"* ]] \
  || fail "test_copy_cache_is_advisory" "cache-only drift was not a no-op: $output"

# source update replaces the unmodified owned copy and refreshes the receipt
mkdir -p "$repo/skills/grok-kaola-project-runner/scripts/__pycache__"
printf '%s\n' source-bytecode >"$repo/skills/grok-kaola-project-runner/scripts/__pycache__/runtime.cpython-314.pyc"
printf '%s\n' '# updated fixture' >>"$repo/skills/grok-kaola-project-runner/SKILL.md"
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok 2>&1)" \
  || fail "test_copy_update" "update failed: $output"
[[ "$output" == *"update:"* ]] || fail "test_copy_update" "expected update report, got: $output"
grep -q 'updated fixture' "$dest/grok-kaola-project-runner/SKILL.md" \
  || fail "test_copy_update" "destination did not receive updated content"
assert_absent "test_copy_excludes_source_cache" "$dest/grok-kaola-project-runner/scripts/__pycache__"

# A receipt-owned edited payload is repaired from the canonical source, with
# the previous bytes retained for the controlling Agent to inspect.
printf '%s\n' '# user edit' >>"$dest/grok-kaola-project-runner/SKILL.md"
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok 2>&1)"
[[ "$output" == *"repair:"* && "$output" == *"drift"* ]] \
  || fail "test_edited_copy_repaired" "expected actionable drift report, got: $output"
! grep -q 'user edit' "$dest/grok-kaola-project-runner/SKILL.md" \
  || fail "test_edited_copy_repaired" "canonical payload not restored"
backup="$(find "$dest" -maxdepth 1 -type d -name '.grok-kaola-project-runner.drift.*' -print -quit)"
[[ -n "$backup" ]] || fail "test_edited_copy_backup" "missing recoverable drift backup"
grep -q 'user edit' "$backup/SKILL.md" \
  || fail "test_edited_copy_backup" "previous edited bytes not preserved"

# Uninstall still protects a subsequently edited copy because deleting it is
# a separate destructive operation, not a transport or install gate.
printf '%s\n' '# user edit' >>"$dest/grok-kaola-project-runner/SKILL.md"
set +e
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --platform grok --uninstall 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_edited_copy_uninstall_refused" "unexpected success"
assert_dir "test_edited_copy_uninstall_refused" "$dest/grok-kaola-project-runner"
grep -q 'user edit' "$dest/grok-kaola-project-runner/SKILL.md" \
  || fail "test_edited_copy_uninstall_refused" "edited content was removed"
python3 - "$dest/grok-kaola-project-runner/SKILL.md" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
open(path, "w").write(text.replace("# user edit\n", ""))
PY

# uninstall of an unmodified owned copy removes dir, receipt, and empty receipt dir
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --platform grok --uninstall 2>&1)" \
  || fail "test_copy_uninstall" "uninstall failed: $output"
assert_absent "test_copy_uninstall_dir" "$dest/grok-kaola-project-runner"
assert_absent "test_copy_uninstall_receipt" "$dest/.kaola-install-receipts/grok-kaola-project-runner.json"
assert_absent "test_copy_uninstall_receipts_dir" "$dest/.kaola-install-receipts"

# --- method switching --------------------------------------------------------
repo="$tmp_root/repo-switch"
make_fixture "$repo"
home="$tmp_root/home-switch"
dest="$tmp_root/switch-dest/skills"
run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok >/dev/null
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method link --platform grok 2>&1)" \
  || fail "test_copy_to_link" "relink failed: $output"
assert_link "test_copy_to_link" "$dest/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"
assert_absent "test_copy_to_link_receipt" "$dest/.kaola-install-receipts/grok-kaola-project-runner.json"
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok 2>&1)" \
  || fail "test_link_to_copy" "copy-over-link failed: $output"
assert_dir "test_link_to_copy" "$dest/grok-kaola-project-runner"
assert_file "test_link_to_copy_receipt" "$dest/.kaola-install-receipts/grok-kaola-project-runner.json"

# A drifted owned copy can also return to an explicit development link. The
# prior payload remains recoverable rather than being silently removed.
printf '%s\n' '# changed before relink' >>"$dest/grok-kaola-project-runner/SKILL.md"
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method link --platform grok --no-orchestrator 2>&1)" \
  || fail "test_drifted_copy_to_link" "relink failed: $output"
assert_link "test_drifted_copy_to_link" "$dest/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"
[[ "$output" == *"repair:"* && "$output" == *"drift"* ]] \
  || fail "test_drifted_copy_to_link" "missing drift diagnosis: $output"
backup="$(find "$dest" -maxdepth 1 -type d -name '.grok-kaola-project-runner.drift.*' -print -quit)"
[[ -n "$backup" ]] || fail "test_drifted_copy_to_link_backup" "missing previous copy"
grep -q 'changed before relink' "$backup/SKILL.md" \
  || fail "test_drifted_copy_to_link_backup" "previous payload not retained"

# --- foreign paths are never replaced, even with a .generated marker ---------
repo="$tmp_root/repo-foreign-dir"
make_fixture "$repo"
home="$tmp_root/home-foreign-dir"
dest="$tmp_root/foreign-dest/skills"
mkdir -p "$dest/grok-kaola-project-runner"
printf '%s\n' 'grok-kaola-project-runner' >"$dest/grok-kaola-project-runner/.generated-by-kaola-project-runner"
printf '%s\n' 'foreign' >"$dest/grok-kaola-project-runner/SKILL.md"
set +e
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_foreign_dir_marker_not_authority" "copy replaced receipt-less directory"
[[ "$(cat "$dest/grok-kaola-project-runner/SKILL.md")" == foreign ]] \
  || fail "test_foreign_dir_marker_not_authority" "foreign content changed"
set +e
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --platform grok --uninstall 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_foreign_dir_uninstall_refused" "removed receipt-less directory"
assert_dir "test_foreign_dir_uninstall_refused" "$dest/grok-kaola-project-runner"

# --- two installations coexist; scoped uninstall + shared bin links ----------
repo="$tmp_root/repo-coexist"
make_fixture "$repo"
home="$tmp_root/home-coexist"
codex_home="$tmp_root/coexist-codex"
dest_b="$tmp_root/coexist-b/skills"
output="$(CODEX_HOME="$codex_home" run_installer "$repo" "$home" --runtime codex --platform grok --method link 2>&1)" \
  || fail "test_coexist_install_a" "install failed: $output"
assert_link "test_coexist_install_a_link" "$codex_home/skills/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"
output="$(run_installer "$repo" "$home" --skills-dir "$dest_b" --method copy --platform grok --bin-links 2>&1)" \
  || fail "test_coexist_install_b" "install failed: $output"
assert_dir "test_coexist_install_b_copy" "$dest_b/grok-kaola-project-runner"
assert_link "test_coexist_bin_link" "$home/.local/bin/kaola-acp" "$repo/scripts/kaola-acp.py"
# uninstall the --skills-dir copy: the codex link install and bin links survive
output="$(run_installer "$repo" "$home" --skills-dir "$dest_b" --platform grok --uninstall 2>&1)" \
  || fail "test_coexist_uninstall_b" "uninstall failed: $output"
assert_absent "test_coexist_uninstall_b_dir" "$dest_b/grok-kaola-project-runner"
assert_link "test_coexist_bin_link_preserved" "$home/.local/bin/kaola-acp" "$repo/scripts/kaola-acp.py"
assert_link "test_coexist_install_a_survives" "$codex_home/skills/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"
# explicit --bin-links removal only touches exact-owned links
ln -s /foreign/path "$home/.local/bin/kaola-acp-foreign"
output="$(run_installer "$repo" "$home" --skills-dir "$dest_b" --platform grok --uninstall --bin-links 2>&1)" \
  || fail "test_bin_links_explicit_removal" "uninstall failed: $output"
assert_absent "test_bin_links_explicit_removal" "$home/.local/bin/kaola-acp"
assert_absent "test_bin_links_explicit_removal_holder" "$home/.local/bin/kaola-acp-holder"
assert_link "test_foreign_bin_link_preserved" "$home/.local/bin/kaola-acp-foreign" "/foreign/path"

# --- codex default uninstall keeps shared bin links --------------------------
repo="$tmp_root/repo-legacy"
make_fixture "$repo"
home="$tmp_root/home-legacy"
output="$(CODEX_HOME="$tmp_root/legacy-codex" run_installer "$repo" "$home" --platform grok 2>&1)" \
  || fail "test_legacy_install_bin_links" "install failed: $output"
assert_link "test_legacy_install_bin_links" "$home/.local/bin/kaola-acp" "$repo/scripts/kaola-acp.py"
output="$(CODEX_HOME="$tmp_root/legacy-codex" run_installer "$repo" "$home" --platform grok --uninstall 2>&1)" \
  || fail "test_legacy_uninstall_keeps_bin_links" "uninstall failed: $output"
assert_absent "test_legacy_uninstall_skill" "$tmp_root/legacy-codex/skills/grok-kaola-project-runner"
assert_link "test_legacy_uninstall_keeps_bin_links" "$home/.local/bin/kaola-acp" "$repo/scripts/kaola-acp.py"

# --- foreign helper links are refused on both install and uninstall ----------
repo="$tmp_root/repo-foreign-bin"
make_fixture "$repo"
home="$tmp_root/home-foreign-bin"
mkdir -p "$home/.local/bin"
ln -s /foreign/path "$home/.local/bin/kaola-acp"
set +e
output="$(run_installer "$repo" "$home" --runtime claude-code --platform grok --bin-links 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_foreign_bin_link_install_refused" "unexpected success"
assert_link "test_foreign_bin_link_install_refused" "$home/.local/bin/kaola-acp" "/foreign/path"
assert_absent "test_foreign_bin_link_no_partial_install" "$home/.claude/skills/grok-kaola-project-runner"
set +e
output="$(run_installer "$repo" "$home" --runtime claude-code --platform grok --uninstall --bin-links 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_foreign_bin_link_uninstall_refused" "unexpected success"
assert_link "test_foreign_bin_link_uninstall_refused" "$home/.local/bin/kaola-acp" "/foreign/path"

# --- place_staged fault injection: second rename failure + failed rollback ---
# PYTHON_BIN stub prepends an os.replace patch to every `python3 -` heredoc;
# it raises only on the staged (.<name>.tmp.$$) and rollback (.<name>.old.$$)
# source basenames, so only place_staged's second/third renames are faulted.
repo="$tmp_root/repo-rollback"
make_fixture "$repo"
home="$tmp_root/home-rollback"
dest="$tmp_root/rollback-dest/skills"
run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok >/dev/null
assert_file "test_rollback_setup" "$dest/.kaola-install-receipts/grok-kaola-project-runner.json"
printf '%s\n' '# updated fixture' >>"$repo/skills/grok-kaola-project-runner/SKILL.md"

pybin="$tmp_root/fault-python"
real_python="$(command -v python3)"
cat >"$pybin" <<EOF
#!/usr/bin/env bash
if [[ "\$1" == "-" ]]; then
  shift
  { printf '%s\n' \
    'import os' \
    '_orig_replace = os.replace' \
    'def _patched(src, dst):' \
    '    b = os.path.basename(str(src))' \
    '    if ".tmp." in b and os.environ.get("KPR_TEST_FAIL_STAGED"):' \
    '        raise OSError(13, "injected staged->target rename failure")' \
    '    if ".old." in b and os.environ.get("KPR_TEST_FAIL_ROLLBACK"):' \
    '        raise OSError(13, "injected rollback rename failure")' \
    '    return _orig_replace(src, dst)' \
    'os.replace = _patched'
    cat; } | "$real_python" - "\$@"
else
  exec "$real_python" "\$@"
fi
EOF
chmod +x "$pybin"

# staged->target rename fails once; rollback restores the previous install
set +e
output="$(KPR_TEST_FAIL_STAGED=1 PYTHON_BIN="$pybin" \
  run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_staged_rename_fail_rc" "unexpected success"
[[ "$output" == *"previous installation restored"* ]] \
  || fail "test_staged_rename_fail_restored" "no restore report: $output"
assert_dir "test_staged_rename_fail_target" "$dest/grok-kaola-project-runner"
[[ "$(cat "$dest/grok-kaola-project-runner/SKILL.md")" == "# fixture Skill" ]] \
  || fail "test_staged_rename_fail_old_content" "old contents lost"
assert_file "test_staged_rename_fail_receipt" \
  "$dest/.kaola-install-receipts/grok-kaola-project-runner.json"
tmp_leftovers=("$dest"/.grok-kaola-project-runner.tmp.*)
old_leftovers=("$dest"/.grok-kaola-project-runner.old.*)
if [[ -e "${tmp_leftovers[0]}" || -L "${tmp_leftovers[0]}" \
  || -e "${old_leftovers[0]}" || -L "${old_leftovers[0]}" ]]; then
  fail "test_staged_rename_fail_no_leftovers" "staged/backup path left behind"
fi

# staged->target AND rollback both fail: backup retained and reported
set +e
output="$(KPR_TEST_FAIL_STAGED=1 KPR_TEST_FAIL_ROLLBACK=1 PYTHON_BIN="$pybin" \
  run_installer "$repo" "$home" --skills-dir "$dest" --method copy --platform grok 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_rollback_fail_rc" "unexpected success"
[[ "$output" == *"previous installation retained at"* ]] \
  || fail "test_rollback_fail_reported" "recovery path not reported: $output"
assert_absent "test_rollback_fail_target_absent" "$dest/grok-kaola-project-runner"
backup_dirs=("$dest"/.grok-kaola-project-runner.old.*)
[[ -d "${backup_dirs[0]}" ]] || fail "test_rollback_fail_backup_retained" "backup deleted"
[[ "$(cat "${backup_dirs[0]}/SKILL.md" 2>/dev/null)" == "# fixture Skill" ]] \
  || fail "test_rollback_fail_backup_content" "old contents not usable at backup"
assert_file "test_rollback_fail_receipt" \
  "$dest/.kaola-install-receipts/grok-kaola-project-runner.json"
tmp_leftovers=("$dest"/.grok-kaola-project-runner.tmp.*)
if [[ -e "${tmp_leftovers[0]}" || -L "${tmp_leftovers[0]}" ]]; then
  fail "test_rollback_fail_no_tmp" "staged temp left behind"
fi

# --- Issue #41: orchestrator installs with every destination; --platform is workers only ---
repo="$tmp_root/repo-orch"
make_fixture "$repo"
home="$tmp_root/home-orch"

assert_orchestrator_link() {
  local name="$1" dest="$2"
  assert_link "$name" "$dest/kaola-project-runner" "$(source_for "$repo" kaola-project-runner)"
}

output="$(run_installer "$repo" "$home" --runtime claude-code --method link 2>&1)" \
  || fail "test_orchestrator_runtime_claude_code" "install failed: $output"
assert_orchestrator_link "test_orchestrator_runtime_claude_code" "$home/.claude/skills"
assert_absent "test_orchestrator_runtime_claude_code_no_external" "$home/.claude/skills/kaola-delegator"
assert_link "test_orchestrator_runtime_claude_code_still_installs_workers" \
  "$home/.claude/skills/grok-kaola-project-runner" "$(source_for "$repo" grok-kaola-project-runner)"
assert_link "test_default_install_includes_zcode" \
  "$home/.claude/skills/zcode-kaola-project-runner" "$(source_for "$repo" zcode-kaola-project-runner)"

output="$(run_installer "$repo" "$home" --runtime cursor --platform grok --method link 2>&1)" \
  || fail "test_orchestrator_runtime_cursor_with_platform" "install failed: $output"
assert_orchestrator_link "test_orchestrator_runtime_cursor_with_platform" "$home/.cursor/skills"
assert_link "test_platform_filter_still_selects_named_worker" \
  "$home/.cursor/skills/grok-kaola-project-runner" "$(source_for "$repo" grok-kaola-project-runner)"
assert_absent "test_platform_filter_does_not_select_other_workers" \
  "$home/.cursor/skills/codex-kaola-project-runner"

output="$(run_installer "$repo" "$home" --runtime devin --platform grok --method link 2>&1)" \
  || fail "test_orchestrator_runtime_devin" "install failed: $output"
assert_orchestrator_link "test_orchestrator_runtime_devin" "$home/devin-config/skills"

codex_home="$tmp_root/orch-codex"
output="$(CODEX_HOME="$codex_home" run_installer "$repo" "$home" --runtime codex --platform grok --method link 2>&1)" \
  || fail "test_orchestrator_runtime_codex" "install failed: $output"
assert_orchestrator_link "test_orchestrator_runtime_codex" "$codex_home/skills"
assert_absent "test_external_runtime_codex_needs_zcode" "$codex_home/skills/kaola-delegator"
[[ "$output" == *"skipping kaola-delegator"* ]] \
  || fail "test_external_runtime_codex_skip_message" "expected skip note, got: $output"
codex_home_z="$tmp_root/orch-codex-z"
output="$(CODEX_HOME="$codex_home_z" run_installer "$repo" "$home" --runtime codex --platform grok,zcode --method link 2>&1)" \
  || fail "test_external_runtime_codex_with_zcode" "install failed: $output"
assert_link "test_external_runtime_codex_with_zcode" "$codex_home_z/skills/kaola-delegator" \
  "$(source_for "$repo" kaola-delegator)"

# Full install then a filtered reinstall/uninstall must not leave a stale Delegator.
dest_stale="$tmp_root/delegator-stale/skills"
output="$(run_installer "$repo" "$home" --skills-dir "$dest_stale" --method link 2>&1)" \
  || fail "test_external_full_install_for_filter" "install failed: $output"
assert_link "test_external_full_install_for_filter" "$dest_stale/kaola-delegator" \
  "$(source_for "$repo" kaola-delegator)"
output="$(run_installer "$repo" "$home" --skills-dir "$dest_stale" --method link --platform grok 2>&1)" \
  || fail "test_external_filtered_reinstall_keeps_delegator" "reinstall failed: $output"
assert_link "test_external_filtered_reinstall_keeps_delegator" "$dest_stale/kaola-delegator" \
  "$(source_for "$repo" kaola-delegator)"
assert_link "test_external_filtered_reinstall_still_has_zcode_worker" \
  "$dest_stale/zcode-kaola-project-runner" "$(source_for "$repo" zcode-kaola-project-runner)"
dest_stale_un="$tmp_root/delegator-stale-un/skills"
output="$(run_installer "$repo" "$home" --skills-dir "$dest_stale_un" --method link 2>&1)" \
  || fail "test_external_full_install_for_uninstall" "install failed: $output"
output="$(run_installer "$repo" "$home" --skills-dir "$dest_stale_un" --platform grok --uninstall 2>&1)" \
  || fail "test_external_filtered_uninstall_removes_delegator" "uninstall failed: $output"
assert_absent "test_external_filtered_uninstall_removes_delegator" "$dest_stale_un/kaola-delegator"
assert_absent "test_external_filtered_uninstall_removes_orchestrator" "$dest_stale_un/kaola-project-runner"
assert_absent "test_external_filtered_uninstall_removes_grok" "$dest_stale_un/grok-kaola-project-runner"
assert_link "test_external_filtered_uninstall_keeps_zcode_worker" \
  "$dest_stale_un/zcode-kaola-project-runner" "$(source_for "$repo" zcode-kaola-project-runner)"

dest="$tmp_root/orch-skills-dir/skills"
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --method link --platform grok,codex 2>&1)" \
  || fail "test_orchestrator_skills_dir" "install failed: $output"
assert_orchestrator_link "test_orchestrator_skills_dir" "$dest"
assert_absent "test_external_skills_dir_needs_zcode" "$dest/kaola-delegator"
assert_link "test_orchestrator_skills_dir_workers_filtered" \
  "$dest/grok-kaola-project-runner" "$(source_for "$repo" grok-kaola-project-runner)"
assert_link "test_orchestrator_skills_dir_codex_worker" \
  "$dest/codex-kaola-project-runner" "$(source_for "$repo" codex-kaola-project-runner)"
assert_absent "test_orchestrator_skills_dir_unselected_worker" \
  "$dest/devin-kaola-project-runner"

set +e
output="$(run_installer "$repo" "$home" --runtime claude-code --platform grok --method link --no-orchestrator 2>&1)"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail "test_no_orchestrator_flag_accepted" "install failed: $output"

home_skip="$tmp_root/home-no-orch"
set +e
output="$(run_installer "$repo" "$home_skip" --runtime cursor --platform grok --method link --no-orchestrator 2>&1)"
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  fail "test_no_orchestrator_skips_main_skill" "install failed: $output"
else
  assert_link "test_no_orchestrator_skips_main_skill_worker" \
    "$home_skip/.cursor/skills/grok-kaola-project-runner" "$(source_for "$repo" grok-kaola-project-runner)"
  assert_absent "test_no_orchestrator_skips_main_skill" "$home_skip/.cursor/skills/kaola-project-runner"
  assert_absent "test_no_orchestrator_skips_external" "$home_skip/.cursor/skills/kaola-delegator"
fi

dest_skip="$tmp_root/no-orch-skills/skills"
set +e
output="$(run_installer "$repo" "$home" --skills-dir "$dest_skip" --method link --no-orchestrator 2>&1)"
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  fail "test_no_orchestrator_skills_dir" "install failed: $output"
else
  assert_absent "test_no_orchestrator_skills_dir" "$dest_skip/kaola-project-runner"
  assert_absent "test_no_orchestrator_skills_dir_external" "$dest_skip/kaola-delegator"
  assert_link "test_no_orchestrator_skills_dir_worker" \
    "$dest_skip/grok-kaola-project-runner" "$(source_for "$repo" grok-kaola-project-runner)"
fi

set +e
output="$(run_installer "$repo" "$home" --skills-dir "$tmp_root/platform-id-refuse/skills" --platform kaola-project-runner 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_orchestrator_is_not_a_platform_id" "unexpected success"
[[ "$output" == *"unknown platform"* ]] \
  || fail "test_orchestrator_is_not_a_platform_id" "expected unknown platform, got: $output"

# Uninstall --platform filters workers only; --no-orchestrator leaves the main Skill.
dest_un="$tmp_root/orch-uninstall/skills"
output="$(run_installer "$repo" "$home" --skills-dir "$dest_un" --method link --platform grok 2>&1)" \
  || fail "test_orchestrator_uninstall_setup" "install failed: $output"
assert_orchestrator_link "test_orchestrator_uninstall_setup" "$dest_un"
set +e
output="$(run_installer "$repo" "$home" --skills-dir "$dest_un" --platform grok --no-orchestrator --uninstall 2>&1)"
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  fail "test_uninstall_platform_keeps_orchestrator" "uninstall failed: $output"
else
  assert_absent "test_uninstall_platform_keeps_orchestrator_worker" "$dest_un/grok-kaola-project-runner"
  assert_orchestrator_link "test_uninstall_platform_keeps_orchestrator" "$dest_un"
fi

# --- Issue #46: omitted --method is an owned copy; owned links migrate --------
repo="$tmp_root/repo-issue-46"
make_fixture "$repo"
home="$tmp_root/home-issue-46"
dest="$tmp_root/issue-46-dest/skills"
source_skill="$(source_for "$repo" grok-kaola-project-runner)/SKILL.md"
source_orch="$(source_for "$repo" kaola-project-runner)/SKILL.md"

output="$(run_installer "$repo" "$home" --skills-dir "$dest" --platform grok 2>&1)" \
  || fail "test_default_method_is_copy" "install failed: $output"
assert_dir "test_default_method_is_copy_worker" "$dest/grok-kaola-project-runner"
assert_dir "test_default_method_is_copy_orchestrator" "$dest/kaola-project-runner"
assert_file "test_default_method_is_copy_worker_receipt" \
  "$dest/.kaola-install-receipts/grok-kaola-project-runner.json"
assert_file "test_default_method_is_copy_orchestrator_receipt" \
  "$dest/.kaola-install-receipts/kaola-project-runner.json"
if [[ "$dest/grok-kaola-project-runner/SKILL.md" -ef "$source_skill" ]]; then
  fail "test_default_copy_isolates_worker_inode" "installed worker SKILL.md still shares the source inode"
fi
if [[ "$dest/kaola-project-runner/SKILL.md" -ef "$source_orch" ]]; then
  fail "test_default_copy_isolates_orchestrator_inode" "installed orchestrator SKILL.md still shares the source inode"
fi
printf '%s\n' '# consumer edit' >>"$dest/kaola-project-runner/SKILL.md"
grep -q 'consumer edit' "$source_orch" \
  && fail "test_default_copy_isolates_orchestrator_inode" "consumer edit leaked into the source Skill"
python3 - "$dest/kaola-project-runner/SKILL.md" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
open(path, "w").write(text.replace("# consumer edit\n", ""))
PY

# Owned source link migrates to a copy when --method is omitted.
link_dest="$tmp_root/issue-46-link-migrate/skills"
output="$(run_installer "$repo" "$home" --skills-dir "$link_dest" --method link --platform grok 2>&1)" \
  || fail "test_owned_link_to_copy_setup" "link install failed: $output"
assert_link "test_owned_link_to_copy_setup" "$link_dest/grok-kaola-project-runner" \
  "$(source_for "$repo" grok-kaola-project-runner)"
assert_link "test_owned_link_to_copy_setup_orchestrator" "$link_dest/kaola-project-runner" \
  "$(source_for "$repo" kaola-project-runner)"
output="$(run_installer "$repo" "$home" --skills-dir "$link_dest" --platform grok 2>&1)" \
  || fail "test_owned_link_migrates_to_copy" "default reinstall failed: $output"
assert_dir "test_owned_link_migrates_to_copy" "$link_dest/grok-kaola-project-runner"
assert_dir "test_owned_link_migrates_to_copy_orchestrator" "$link_dest/kaola-project-runner"
assert_file "test_owned_link_migrates_to_copy_receipt" \
  "$link_dest/.kaola-install-receipts/grok-kaola-project-runner.json"
assert_file "test_owned_link_migrates_to_copy_orchestrator_receipt" \
  "$link_dest/.kaola-install-receipts/kaola-project-runner.json"
if [[ "$link_dest/grok-kaola-project-runner/SKILL.md" -ef "$source_skill" ]]; then
  fail "test_owned_link_migrates_to_copy_inode" "migrated copy still shares the source inode"
fi
[[ "$output" == *"copy-over-link:"* ]] \
  || fail "test_owned_link_migrates_to_copy" "expected copy-over-link report, got: $output"

# Legacy grok root link also migrates to a copy under the omitted --method.
root_dest="$tmp_root/issue-46-grok-root/skills"
mkdir -p "$root_dest"
ln -s "$repo" "$root_dest/grok-kaola-project-runner"
output="$(run_installer "$repo" "$home" --skills-dir "$root_dest" --platform grok --no-orchestrator 2>&1)" \
  || fail "test_grok_root_link_migrates_to_copy" "install failed: $output"
assert_dir "test_grok_root_link_migrates_to_copy" "$root_dest/grok-kaola-project-runner"
assert_file "test_grok_root_link_migrates_to_copy_receipt" \
  "$root_dest/.kaola-install-receipts/grok-kaola-project-runner.json"
if [[ "$root_dest/grok-kaola-project-runner/SKILL.md" -ef "$source_skill" ]]; then
  fail "test_grok_root_link_migrates_to_copy_inode" "migrated grok copy still shares the source inode"
fi

# Foreign symlinks stay protected; managed drift is repaired under the default.
foreign="$tmp_root/issue-46-foreign-target"
foreign_dest="$tmp_root/issue-46-foreign/skills"
mkdir -p "$foreign" "$foreign_dest"
ln -s "$foreign" "$foreign_dest/grok-kaola-project-runner"
set +e
output="$(run_installer "$repo" "$home" --skills-dir "$foreign_dest" --platform grok 2>&1)"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "test_default_copy_foreign_symlink_refused" "installer unexpectedly succeeded"
[[ "$(readlink "$foreign_dest/grok-kaola-project-runner")" == "$foreign" ]] \
  || fail "test_default_copy_foreign_symlink_refused" "foreign symlink changed"
assert_absent "test_default_copy_foreign_symlink_no_partial_orchestrator" \
  "$foreign_dest/kaola-project-runner"

printf '%s\n' '# user edit' >>"$dest/grok-kaola-project-runner/SKILL.md"
output="$(run_installer "$repo" "$home" --skills-dir "$dest" --platform grok 2>&1)"
[[ "$output" == *"repair:"* && "$output" == *"drift"* ]] \
  || fail "test_default_copy_modified_repaired" "expected drift repair report, got: $output"
! grep -q 'user edit' "$dest/grok-kaola-project-runner/SKILL.md" \
  || fail "test_default_copy_modified_repaired" "canonical content not restored"
backup="$(find "$dest" -maxdepth 1 -type d -name '.grok-kaola-project-runner.drift.*' -print -quit)"
[[ -n "$backup" ]] || fail "test_default_copy_modified_backup" "missing recoverable backup"
grep -q 'user edit' "$backup/SKILL.md" \
  || fail "test_default_copy_modified_backup" "previous bytes not retained"

# --- neutral validator --------------------------------------------------------
good="$tmp_root/validator/good-skill"
mkdir -p "$good"
printf '%s\n' '---' 'name: good-skill' 'description: A portable skill.' '---' '' '# Body' >"$good/SKILL.md"
python3 "$validator_source" "$good" >/dev/null \
  || fail "test_validator_accepts_valid_skill" "valid skill rejected"

for case in missing badname mismatch unknownfield nodescription; do
  dir="$tmp_root/validator/$case-skill"
  mkdir -p "$dir"
  case "$case" in
    missing) ;;
    badname) printf '%s\n' '---' 'name: Bad_Name' 'description: x' '---' >"$dir/SKILL.md" ;;
    mismatch) printf '%s\n' '---' 'name: other-name' 'description: x' '---' >"$dir/SKILL.md" ;;
    unknownfield) printf '%s\n' '---' 'name: unknownfield-skill' 'description: x' 'bogus: y' '---' >"$dir/SKILL.md" ;;
    nodescription) printf '%s\n' '---' 'name: nodescription-skill' '---' >"$dir/SKILL.md" ;;
  esac
  set +e
  python3 "$validator_source" "$dir" >/dev/null 2>&1
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || fail "test_validator_rejects_$case" "invalid skill accepted"
done

# --- Grok Bot is a bridge host, never an installer destination ---------------
repo="$tmp_root/repo-grok-bot"
make_fixture "$repo"
home="$tmp_root/home-grok-bot"
mkdir -p "$home/.claude/skills/foreign-skill"
printf '%s\n' '# foreign' >"$home/.claude/skills/foreign-skill/SKILL.md"
for alias in grok-bot grokbot; do
  set +e
  output="$(run_installer "$repo" "$home" --runtime "$alias" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || fail "test_runtime_grok_bot_refused_$alias" "unexpected success"
  [[ "$output" == *"unknown runtime: $alias"* ]] || fail "test_runtime_grok_bot_refused_$alias" "expected unknown runtime, got: $output"
  [[ "$output" == *"bridge host"* && "$output" == *"hosts/grok-bot/kaola-delegator.md"* && "$output" == *"kaola-locate.py register"* ]] \
    || fail "test_runtime_grok_bot_refused_${alias}_hint" "expected bridge/locator hint, got: $output"
done
assert_absent "test_runtime_grok_bot_writes_nothing" "$home/.kaola"
assert_absent "test_runtime_grok_bot_no_bin_links" "$home/.local/bin/kaola-acp"
assert_file "test_runtime_grok_bot_foreign_untouched" "$home/.claude/skills/foreign-skill/SKILL.md"
[[ ! -e "$repo/hosts/grok-bot/kaola-project-runner" ]] || fail "test_no_runtime_copy_fixture" "fixture must not carry a runtime copy"

# --- locator bin link follows the existing --bin-links convention -------------
home="$tmp_root/home-locator"
output="$(run_installer "$repo" "$home" --runtime codex --platform grok --method link 2>&1)" \
  || fail "test_locator_bin_link_install" "install failed: $output"
assert_link "test_locator_bin_link_install" "$home/.local/bin/kaola-project-runner-locate" "$repo/scripts/kaola-locate.py"
output="$(run_installer "$repo" "$home" --runtime codex --platform grok --uninstall --bin-links 2>&1)" \
  || fail "test_locator_bin_link_uninstall" "uninstall failed: $output"
assert_absent "test_locator_bin_link_uninstall" "$home/.local/bin/kaola-project-runner-locate"

# --- generated payload stays valid under the neutral validator ----------------
for skill_dir in "$project_root"/skills/*kaola-project-runner "$project_root"/skills/kaola-delegator; do
  python3 "$validator_source" "$skill_dir" >/dev/null \
    || fail "test_validator_generated_$(basename "$skill_dir")" "generated Skill failed neutral validation"
done

if [[ "$failures" -gt 0 ]]; then
  printf 'installer runtimes acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'installer runtimes acceptance: PASS\n'
