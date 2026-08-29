#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"
codex_root="${CODEX_HOME:-$HOME/.codex}"
target_parent="$codex_root/skills"
mode=install
selection=()
installer_python="${PYTHON_BIN:-python3}"

command -v "$installer_python" >/dev/null 2>&1 || {
  printf 'python3 executable not found: %s\n' "$installer_python" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./scripts/install-local.sh [--platform ID[,ID...]] [--uninstall]

Platforms: grok, claude-code, opencode, kimi-cli, cursor-cli
With no --platform, installs all five Skills. Existing foreign paths are never replaced.
EOF
}

skill_name_for() {
  case "$1" in
    grok) printf '%s\n' 'grok-kaola-project-runner' ;;
    claude-code) printf '%s\n' 'claude-code-kaola-project-runner' ;;
    opencode) printf '%s\n' 'opencode-kaola-project-runner' ;;
    kimi-cli) printf '%s\n' 'kimi-cli-kaola-project-runner' ;;
    cursor-cli) printf '%s\n' 'cursor-cli-kaola-project-runner' ;;
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
      shift 2
      ;;
    --uninstall) mode=uninstall; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ${#selection[@]} -eq 0 ]]; then
  selection=(grok claude-code opencode kimi-cli cursor-cli)
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

actions=()
for platform in "${selection[@]}"; do
  name="$(skill_name_for "$platform")"
  source="$repo_root/skills/$name"
  target="$target_parent/$name"

  if [[ "$mode" == install ]]; then
    [[ -f "$source/SKILL.md" && -f "$source/.generated-by-kaola-project-runner" ]] || {
      printf 'generated Skill is missing; run ./scripts/render-skills.py --write: %s\n' "$source" >&2
      exit 1
    }
    if [[ -L "$target" ]]; then
      current="$(canonical_existing_target "$target" || true)"
      if [[ -n "$current" && "$current" -ef "$source" ]]; then
        actions+=("already|$platform|$source|$target")
      elif [[ "$platform" == grok && -n "$current" && "$current" -ef "$repo_root" ]]; then
        actions+=("migrate|$platform|$source|$target")
      else
        printf 'refusing to replace existing symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
        exit 1
      fi
    elif [[ -e "$target" ]]; then
      printf 'refusing to replace existing path: %s\n' "$target" >&2
      exit 1
    else
      actions+=("install|$platform|$source|$target")
    fi
  else
    if [[ -L "$target" ]]; then
      current="$(canonical_existing_target "$target" || true)"
      if [[ -n "$current" && ( "$current" -ef "$source" || ( "$platform" == grok && "$current" -ef "$repo_root" ) ) ]]; then
        actions+=("uninstall|$platform|$source|$target")
      else
        printf 'refusing to remove foreign symlink: %s -> %s\n' "$target" "$(readlink "$target")" >&2
        exit 1
      fi
    elif [[ -e "$target" ]]; then
      printf 'refusing to remove non-symlink path: %s\n' "$target" >&2
      exit 1
    else
      actions+=("absent|$platform|$source|$target")
    fi
  fi
done

mkdir -p "$target_parent"

for row in "${actions[@]}"; do
  IFS='|' read -r action platform source target <<<"$row"
  case "$action" in
    already)
      printf 'already installed: %s -> %s\n' "$target" "$source"
      ;;
    install|migrate)
      temp="$target_parent/.${target##*/}.tmp.$$"
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
      printf '%s: %s -> %s\n' "$action" "$target" "$source"
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
