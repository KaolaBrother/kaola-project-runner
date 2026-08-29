#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"
codex_root="${CODEX_HOME:-$HOME/.codex}"
validator="$codex_root/skills/.system/skill-creator/scripts/quick_validate.py"

if [[ ! -f "$validator" ]]; then
  printf 'skill validator not found: %s\n' "$validator" >&2
  exit 1
fi

python3 "$repo_root/scripts/render-skills.py" --check
for skill_dir in "$repo_root"/skills/*-kaola-project-runner; do
  python3 "$validator" "$skill_dir"
done
"$repo_root/tests/test-grok-tmux.sh"
"$repo_root/tests/test-issue-1-acceptance.sh"
