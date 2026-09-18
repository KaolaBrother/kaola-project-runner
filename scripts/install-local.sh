#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"
mode=install
method=copy
runtime_alias=""
skills_dir=""
bin_links_request=""
selection=()
platform_given=false
install_orchestrator=true
orchestrator_skill_name="kaola-project-runner"
external_skill_name="zcode-orchestrator"
installer_python="${PYTHON_BIN:-python3}"

command -v "$installer_python" >/dev/null 2>&1 || {
  printf 'python3 executable not found: %s\n' "$installer_python" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./scripts/install-local.sh [--runtime NAME | --skills-dir ABS_PATH]
                                  [--method link|copy] [--platform ID[,ID...]]
                                  [--no-orchestrator]
                                  [--bin-links | --no-bin-links] [--uninstall]

Consuming runtimes (verified native skill directories):
  codex        ${CODEX_HOME:-$HOME/.codex}/skills
  claude-code  ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills
  cursor       $HOME/.cursor/skills
  devin        ${DEVIN_CONFIG_DIR:-$HOME/.config/devin}/skills
  zcode        $HOME/.zcode/skills (ZCode Host install; the live-verified
               discovery form is the workspace .zcode/skills, which
               --skills-dir covers; the user-level directory follows the
               same layout, see docs/zcode-host.md)
Grok Bot is a bridge host, not an installer destination: the account holds one
thin generated Skill (hosts/grok-bot/zcode-orchestrator.md) that loads the
Zcode Orchestrator Skill from this checkout on the bound execution target
through the device-local locator kaola-project-runner-locate
(scripts/kaola-locate.py register --target local|cloud, which validates the
checkout, links the command, and writes its registration receipt beside the
link; a bare --bin-links link carries no receipt). See docs/grok-bot-host.md.
Grok CLI worker uses --platform grok, not --runtime grok.
ZCode is both a worker platform (--platform zcode) and a native
skill-directory Host (--runtime zcode installs to $HOME/.zcode/skills; a
workspace .zcode/skills destination goes through --skills-dir; see
docs/zcode-host.md).

--skills-dir installs into any explicit destination parent (including
project-local paths) and is mutually exclusive with --runtime.
--method copy (default) installs a standalone copy tracked by a per-Skill
receipt. --method link is an explicit development choice that symlinks each
Skill to this checkout. An owned source link migrates to a copy on a default
or --method copy reinstall.
Platforms: grok, claude-code, opencode, kimi-cli, cursor-cli, devin, codex, zcode, droid
--platform filters worker Skills only. The main Skill kaola-project-runner
(display name Project Runner) is installed for every destination unless
--no-orchestrator is passed. Codex and generic --skills-dir destinations also
install zcode-orchestrator (display name Zcode Orchestrator) unless that flag
is passed. Neither control-plane Skill is a platform ID.
With no --platform, installs all nine worker Skills plus the control-plane
Skills for that destination (unless skipped). With no destination flags the
legacy Codex destination is used. Existing foreign paths are never replaced.
--bin-links also manages the $HOME/.local/bin/kaola-acp* helper links and the
kaola-project-runner-locate locator link; it is on by default only for the
Codex runtime destination. Uninstall never removes bin
links unless --bin-links is passed explicitly.
EOF
}

skill_name_for() {
  case "$1" in
    grok) printf '%s\n' 'grok-kaola-project-runner' ;;
    claude-code) printf '%s\n' 'claude-code-kaola-project-runner' ;;
    opencode) printf '%s\n' 'opencode-kaola-project-runner' ;;
    kimi-cli) printf '%s\n' 'kimi-cli-kaola-project-runner' ;;
    cursor-cli) printf '%s\n' 'cursor-cli-kaola-project-runner' ;;
    devin) printf '%s\n' 'devin-kaola-project-runner' ;;
    codex) printf '%s\n' 'codex-kaola-project-runner' ;;
    zcode) printf '%s\n' 'zcode-kaola-project-runner' ;;
    droid) printf '%s\n' 'droid-kaola-project-runner' ;;
    *) return 1 ;;
  esac
}

runtime_skills_dir() {
  case "$1" in
    codex) printf '%s\n' "${CODEX_HOME:-$HOME/.codex}/skills" ;;
    claude-code) printf '%s\n' "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills" ;;
    cursor) printf '%s\n' "$HOME/.cursor/skills" ;;
    devin) printf '%s\n' "${DEVIN_CONFIG_DIR:-$HOME/.config/devin}/skills" ;;
    zcode) printf '%s\n' "$HOME/.zcode/skills" ;;
    *) return 1 ;;
  esac
}

append_selection() {
  local raw="$1" item
  IFS=',' read -r -a items <<<"$raw"
  for item in "${items[@]}"; do
    skill_name_for "$item" >/dev/null || {
      printf 'unknown platform: %s\n' "$item" >&2
      exit 2
    }
    selection+=("$item")
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      [[ $# -ge 2 ]] || { printf '%s\n' '--platform needs a value' >&2; exit 2; }
      append_selection "$2"
      platform_given=true
      shift 2
      ;;
    --runtime)
      [[ $# -ge 2 ]] || { printf '%s\n' '--runtime needs a value' >&2; exit 2; }
      if [[ "$2" == grok ]]; then
        printf 'unknown runtime: grok\nGrok CLI is worker platform id grok (--platform grok). Grok Bot is a bridge host with no installer destination (see docs/grok-bot-host.md).\n' >&2
        exit 2
      fi
      if [[ "$2" == grok-bot || "$2" == grokbot ]]; then
        printf 'unknown runtime: %s\nGrok Bot is a bridge host, not an installer destination: save hosts/grok-bot/zcode-orchestrator.md on the account and register the locator with scripts/kaola-locate.py register on the execution target (see docs/grok-bot-host.md). --platform grok is the Grok CLI worker.\n' "$2" >&2
        exit 2
      fi
      runtime_skills_dir "$2" >/dev/null || { printf 'unknown runtime: %s\n' "$2" >&2; exit 2; }
      [[ -z "$runtime_alias" ]] || { printf '%s\n' '--runtime may be given once' >&2; exit 2; }
      runtime_alias="$2"
      shift 2
      ;;
    --skills-dir)
      [[ $# -ge 2 ]] || { printf '%s\n' '--skills-dir needs a value' >&2; exit 2; }
      [[ -z "$skills_dir" ]] || { printf '%s\n' '--skills-dir may be given once' >&2; exit 2; }
      skills_dir="$2"
      shift 2
      ;;
    --method)
      [[ $# -ge 2 ]] || { printf '%s\n' '--method needs a value' >&2; exit 2; }
      case "$2" in link|copy) ;; *) printf 'unknown method: %s\n' "$2" >&2; exit 2 ;; esac
      method="$2"
      shift 2
      ;;
    --no-orchestrator) install_orchestrator=false; shift ;;
    --bin-links) bin_links_request=on; shift ;;
    --no-bin-links) bin_links_request=off; shift ;;
    --uninstall) mode=uninstall; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -n "$runtime_alias" && -n "$skills_dir" ]]; then
  printf '%s\n' '--runtime and --skills-dir are mutually exclusive' >&2
  exit 2
fi

if [[ -n "$skills_dir" ]]; then
  [[ "$skills_dir" == /* ]] || { printf '%s\n' '--skills-dir must be an absolute path' >&2; exit 2; }
  target_parent="$skills_dir"
  resolved_runtime=generic
elif [[ -n "$runtime_alias" ]]; then
  target_parent="$(runtime_skills_dir "$runtime_alias")"
  resolved_runtime="$runtime_alias"
else
  target_parent="${CODEX_HOME:-$HOME/.codex}/skills"
  resolved_runtime=codex
fi
receipts_dir="$target_parent/.kaola-install-receipts"

if [[ "$mode" == install ]]; then
  if [[ "$bin_links_request" == on || ( -z "$bin_links_request" && "$resolved_runtime" == codex ) ]]; then
    want_bin_links=true
  else
    want_bin_links=false
  fi
else
  # Uninstall leaves shared helper links alone unless removal was explicitly
  # requested; they may belong to another installation.
  [[ "$bin_links_request" == on ]] && want_bin_links=true || want_bin_links=false
fi

if [[ ${#selection[@]} -eq 0 ]]; then
  selection=(grok claude-code opencode kimi-cli cursor-cli devin codex zcode droid)
fi

deduped=()
for item in "${selection[@]}"; do
  duplicate=false
  for seen in "${deduped[@]:-}"; do
    [[ "$seen" == "$item" ]] && duplicate=true
  done
  [[ "$duplicate" == true ]] || deduped+=("$item")
done
selection=("${deduped[@]}")

canonical_existing_target() {
  local target="$1" raw
  raw="$(readlink "$target")" || return 1
  if [[ "$raw" == /* ]]; then
    [[ -e "$raw" ]] || return 1
    (cd "$raw" 2>/dev/null && pwd -P)
  else
    [[ -e "$(dirname "$target")/$raw" ]] || return 1
    (cd "$(dirname "$target")/$raw" 2>/dev/null && pwd -P)
  fi
}

tree_digest() {
  "$installer_python" - "$1" <<'PY'
import hashlib, os, sys
root = sys.argv[1]
entries = []
for dirpath, dirnames, filenames in os.walk(root):
    # Python may cache imported helpers inside an installed Skill. These are
    # runtime byproducts, not generated payload bytes or ownership evidence.
    dirnames[:] = [name for name in dirnames if name != "__pycache__"]
    dirnames.sort()
    for name in dirnames + [name for name in filenames if not name.endswith((".pyc", ".pyo"))]:
        entries.append(os.path.join(dirpath, name))
digest = hashlib.sha256()
for path in sorted(entries, key=lambda p: os.path.relpath(p, root)):
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    if os.path.islink(path):
        digest.update(b"L" + rel.encode() + b"=" + os.readlink(path).encode() + b"\n")
    elif os.path.isdir(path):
        digest.update(b"D" + rel.encode() + b"\n")
    else:
        with open(path, "rb") as handle:
            content = hashlib.sha256(handle.read()).hexdigest()
        digest.update(b"F" + rel.encode() + b"=" + content.encode() + b"\n")
print(digest.hexdigest())
PY
}

receipt_digest() {
  # Print the recorded content hash when $1 is an exact-owned receipt for $2.
  "$installer_python" - "$1" "$2" <<'PY'
import json, sys
path, skill = sys.argv[1], sys.argv[2]
try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
except (OSError, ValueError):
    sys.exit(0)
if (
    data.get("receipt") == "kaola-project-runner-install/1"
    and data.get("skill") == skill
    and data.get("method") == "copy"
    and isinstance(data.get("content_sha256"), str)
):
    sys.stdout.write(data["content_sha256"])
PY
}

write_receipt() {
  # $1 skill name, $2 source dir, $3 content digest
  mkdir -p "$receipts_dir"
  "$installer_python" - "$receipts_dir/$1.json" "$1" "$2" "$3" <<'PY'
import json, sys, time
path, skill, source, digest = sys.argv[1:5]
data = {
    "receipt": "kaola-project-runner-install/1",
    "skill": skill,
    "method": "copy",
    "content_sha256": digest,
    "source": source,
    "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
}

drop_owned_receipt() {
  # Remove $1's receipt only when it parses as an exact-owned receipt for $2.
  local path="$receipts_dir/$1.json"
  [[ -f "$path" ]] || return 0
  [[ -n "$(receipt_digest "$path" "$1")" ]] && rm -f "$path" || true
}

stage_copy() {
  "$installer_python" - "$1" "$2" <<'PY'
import shutil, sys
shutil.copytree(sys.argv[1], sys.argv[2], symlinks=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
PY
}

place_staged() {
  # Move $1 into place at $2; an existing $2 is set aside at $3. Keep $3 on
  # managed drift so an Agent can inspect or restore the previous bytes.
  # If the staged rename fails, the previous target is restored from backup;
  # if restoration itself fails, the backup is retained and its recovery path
  # is reported instead of being deleted.
  "$installer_python" - "$1" "$2" "$3" "${4:-0}" <<'PY'
import os, shutil, sys
staged, target, backup, keep_previous = sys.argv[1:5]
moved = False
if os.path.lexists(target):
    try:
        os.replace(target, backup)
        moved = True
    except OSError as exc:
        sys.exit("place_staged: could not set aside %s -> %s: %s" % (target, backup, exc))
try:
    os.replace(staged, target)
except OSError as exc:
    if not moved:
        sys.exit("place_staged: rename %s -> %s failed: %s" % (staged, target, exc))
    try:
        os.replace(backup, target)
    except OSError as rb_exc:
        sys.exit(
            "place_staged: rename %s -> %s failed: %s; rollback failed: %s; "
            "previous installation retained at %s" % (staged, target, exc, rb_exc, backup)
        )
    sys.exit(
        "place_staged: rename %s -> %s failed: %s; previous installation restored from %s"
        % (staged, target, exc, backup)
    )
if os.path.lexists(backup) and keep_previous != "1":
    if os.path.isdir(backup) and not os.path.islink(backup):
        shutil.rmtree(backup)
    else:
        os.unlink(backup)
PY
}

# Plan every action before any write; a refusal anywhere aborts the whole run.
# $1 is the generated Skill directory name. $2 is the worker platform id, or
# empty for the main orchestrator Skill (not a platform id).
plan_skill() {
  local name="$1"
  local platform="${2-}"
  local source="$repo_root/skills/$name"
  local target="$target_parent/$name"

  if [[ "$mode" == install ]]; then
    [[ -f "$source/SKILL.md" && -f "$source/.generated-by-kaola-project-runner" ]] || {
      printf 'generated Skill is missing; run ./scripts/render-skills.py --write: %s\n' "$source" >&2
      exit 1
    }
    if [[ "$method" == link ]]; then
      if [[ -L "$target" ]]; then
        current="$(canonical_existing_target "$target" || true)"
        if [[ -n "$current" && "$current" -ef "$source" ]]; then
          actions+=("already|$name|$source|$target")
        elif [[ "$platform" == grok && -n "$current" && "$current" -ef "$repo_root" ]]; then
          actions+=("migrate|$name|$source|$target")
        else
          printf 'refusing to replace existing symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
          exit 1
        fi
      elif [[ -d "$target" ]]; then
        recorded="$(receipt_digest "$receipts_dir/$name.json" "$name")"
        actual="$(tree_digest "$target")"
        if [[ -n "$recorded" && "$actual" == "$recorded" ]]; then
          actions+=("relink|$name|$source|$target")
        elif [[ -n "$recorded" ]]; then
          actions+=("relink-drift|$name|$source|$target")
        else
          printf 'refusing to replace foreign directory without ownership receipt: %s\n' "$target" >&2
          exit 1
        fi
      elif [[ -e "$target" ]]; then
        printf 'refusing to replace existing path: %s\n' "$target" >&2
        exit 1
      else
        actions+=("install|$name|$source|$target")
      fi
    else
      if [[ -L "$target" ]]; then
        current="$(canonical_existing_target "$target" || true)"
        if [[ -n "$current" && ( "$current" -ef "$source" || ( "$platform" == grok && "$current" -ef "$repo_root" ) ) ]]; then
          actions+=("copy-over-link|$name|$source|$target")
        else
          printf 'refusing to replace existing symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
          exit 1
        fi
      elif [[ -d "$target" ]]; then
        recorded="$(receipt_digest "$receipts_dir/$name.json" "$name")"
        if [[ -z "$recorded" ]]; then
          printf 'refusing to replace foreign directory without ownership receipt: %s\n' "$target" >&2
          exit 1
        fi
        actual="$(tree_digest "$target")"
        if [[ "$actual" != "$recorded" ]]; then
          actions+=("repair|$name|$source|$target")
        elif [[ "$actual" == "$(tree_digest "$source")" ]]; then
          actions+=("already|$name|$source|$target")
        else
          actions+=("update|$name|$source|$target")
        fi
      elif [[ -e "$target" ]]; then
        printf 'refusing to replace existing path: %s\n' "$target" >&2
        exit 1
      else
        actions+=("install|$name|$source|$target")
      fi
    fi
  else
    if [[ -L "$target" ]]; then
      current="$(canonical_existing_target "$target" || true)"
      if [[ -n "$current" && ( "$current" -ef "$source" || ( "$platform" == grok && "$current" -ef "$repo_root" ) ) ]]; then
        actions+=("uninstall|$name|$source|$target")
      else
        printf 'refusing to remove foreign symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
        exit 1
      fi
    elif [[ -d "$target" ]]; then
      recorded="$(receipt_digest "$receipts_dir/$name.json" "$name")"
      if [[ -z "$recorded" ]]; then
        printf 'refusing to remove foreign directory without ownership receipt: %s\n' "$target" >&2
        exit 1
      fi
      if [[ "$(tree_digest "$target")" != "$recorded" ]]; then
        printf 'refusing to remove modified installed copy (user edits preserved): %s\n' "$target" >&2
        exit 1
      fi
      actions+=("uninstall-copy|$name|$source|$target")
    elif [[ -e "$target" ]]; then
      printf 'refusing to remove non-symlink path: %s\n' "$target" >&2
      exit 1
    else
      actions+=("absent|$name|$source|$target")
    fi
  fi
}

actions=()
for platform in "${selection[@]}"; do
  plan_skill "$(skill_name_for "$platform")" "$platform"
done
if [[ "$install_orchestrator" == true ]]; then
  plan_skill "$orchestrator_skill_name"
  if [[ "$resolved_runtime" == "codex" || "$resolved_runtime" == "generic" ]]; then
    plan_skill "$external_skill_name"
  fi
fi

bin_dir="$HOME/.local/bin"
bin_specs=(
  "kaola-acp|$script_dir/kaola-acp.py"
  "kaola-acp-holder|$script_dir/kaola-acp-holder.py"
  "kaola-project-runner-locate|$script_dir/kaola-locate.py"
)
bin_actions=()
if [[ "$want_bin_links" == true ]]; then
  for spec in "${bin_specs[@]}"; do
    IFS='|' read -r name source <<<"$spec"
    target="$bin_dir/$name"
    if [[ "$mode" == install ]]; then
      if [[ -L "$target" ]]; then
        if [[ "$target" -ef "$source" ]]; then
          bin_actions+=("already|$source|$target")
        else
          printf 'refusing to replace existing symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
          exit 1
        fi
      elif [[ -e "$target" ]]; then
        printf 'refusing to replace existing path: %s\n' "$target" >&2
        exit 1
      else
        bin_actions+=("install|$source|$target")
      fi
    else
      if [[ -L "$target" ]]; then
        if [[ "$target" -ef "$source" ]]; then
          bin_actions+=("uninstall|$source|$target")
        else
          printf 'refusing to remove foreign symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
          exit 1
        fi
      elif [[ -e "$target" ]]; then
        printf 'refusing to remove non-symlink path: %s\n' "$target" >&2
        exit 1
      else
        bin_actions+=("absent|$source|$target")
      fi
    fi
  done
fi

[[ "$mode" == install ]] && mkdir -p "$target_parent"
[[ "$want_bin_links" == true && "$mode" == install ]] && mkdir -p "$bin_dir"

for row in "${actions[@]}"; do
  IFS='|' read -r action name source target <<<"$row"
  case "$action" in
    already)
      printf 'already installed: %s\n' "$target"
      ;;
    install|update|copy-over-link|repair)
      temp="$target_parent/.${name}.tmp.$$"
      keep_previous=0
      if [[ "$action" == repair ]]; then
        backup="$target_parent/.${name}.drift.$$"
        keep_previous=1
      else
        backup="$target_parent/.${name}.old.$$"
      fi
      [[ ! -e "$temp" && ! -L "$temp" && ! -e "$backup" && ! -L "$backup" ]] || {
        printf 'temporary path exists: %s\n' "$temp" >&2; exit 1; }
      if [[ "$method" == copy ]]; then
        if ! stage_copy "$source" "$temp"; then
          rm -rf "$temp" 2>/dev/null || true
          printf 'staging copy failed: %s\n' "$source" >&2
          exit 1
        fi
        new_digest="$(tree_digest "$temp")"
      else
        ln -s "$source" "$temp"
      fi
      if ! place_staged "$temp" "$target" "$backup" "$keep_previous"; then
        rm -rf "$temp" 2>/dev/null || true
        printf 'atomic replacement failed: %s\n' "$target" >&2
        exit 1
      fi
      if [[ "$method" == copy ]]; then
        write_receipt "$name" "$source" "$new_digest"
      else
        drop_owned_receipt "$name"
      fi
      if [[ "$action" == repair ]]; then
        printf 'repair: %s (managed drift; previous copy: %s; edit repo templates/manifests, not installed Skills)\n' "$target" "$backup"
      else
        printf '%s: %s\n' "$action" "$target"
      fi
      ;;
    migrate|relink|relink-drift)
      temp="$target_parent/.${name}.tmp.$$"
      keep_previous=0
      if [[ "$action" == relink-drift ]]; then
        backup="$target_parent/.${name}.drift.$$"
        keep_previous=1
      else
        backup="$target_parent/.${name}.old.$$"
      fi
      [[ ! -e "$temp" && ! -L "$temp" && ! -e "$backup" && ! -L "$backup" ]] || {
        printf 'temporary path exists: %s\n' "$temp" >&2; exit 1; }
      ln -s "$source" "$temp"
      if ! place_staged "$temp" "$target" "$backup" "$keep_previous"; then
        rm -rf "$temp" 2>/dev/null || true
        printf 'atomic replacement failed: %s\n' "$target" >&2
        exit 1
      fi
      [[ "$action" == relink || "$action" == relink-drift ]] && drop_owned_receipt "$name"
      if [[ "$action" == relink-drift ]]; then
        printf 'repair: %s -> %s (managed drift; previous copy: %s; edit repo templates/manifests, not installed Skills)\n' "$target" "$source" "$backup"
      else
        printf '%s: %s -> %s\n' "$action" "$target" "$source"
      fi
      ;;
    uninstall)
      unlink "$target"
      drop_owned_receipt "$name"
      printf 'uninstalled: %s\n' "$target"
      ;;
    uninstall-copy)
      rm -rf "$target"
      drop_owned_receipt "$name"
      printf 'uninstalled: %s\n' "$target"
      ;;
    absent)
      drop_owned_receipt "$name"
      printf 'already absent: %s\n' "$target"
      ;;
  esac
done
[[ "$mode" == uninstall ]] && rmdir "$receipts_dir" 2>/dev/null || true

for row in ${bin_actions[@]+"${bin_actions[@]}"}; do
  IFS='|' read -r action source target <<<"$row"
  case "$action" in
    already)
      printf 'already installed: %s -> %s\n' "$target" "$source"
      ;;
    install)
      temp="$bin_dir/.${target##*/}.tmp.$$"
      [[ ! -e "$temp" && ! -L "$temp" ]] || { printf 'temporary path exists: %s\n' "$temp" >&2; exit 1; }
      ln -s "$source" "$temp"
      if ! "$installer_python" - "$temp" "$target" <<'PY'
import os, sys
os.replace(sys.argv[1], sys.argv[2])
PY
      then
        unlink "$temp" 2>/dev/null || true
        printf 'atomic symlink replacement failed: %s\n' "$target" >&2
        exit 1
      fi
      printf 'install: %s -> %s\n' "$target" "$source"
      ;;
    uninstall)
      unlink "$target"
      printf 'uninstalled: %s\n' "$target"
      ;;
    absent)
      printf 'already absent: %s\n' "$target"
      ;;
  esac
done
