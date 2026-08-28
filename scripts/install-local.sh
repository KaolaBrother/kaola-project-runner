#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
skill_dir="$(cd "$script_dir/.." && pwd -P)"
codex_root="${CODEX_HOME:-$HOME/.codex}"
target_parent="$codex_root/skills"
target="$target_parent/grok-kaola-project-runner"

mkdir -p "$target_parent"

if [[ -L "$target" ]]; then
  current="$(readlink "$target")"
  if [[ "$current" == "$skill_dir" ]]; then
    printf 'already installed: %s -> %s\n' "$target" "$skill_dir"
    exit 0
  fi
  printf 'refusing to replace existing symlink: %s -> %s\n' "$target" "$current" >&2
  exit 1
fi

if [[ -e "$target" ]]; then
  printf 'refusing to replace existing path: %s\n' "$target" >&2
  exit 1
fi

ln -s "$skill_dir" "$target"
printf 'installed: %s -> %s\n' "$target" "$skill_dir"
