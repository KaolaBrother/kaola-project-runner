#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
skill_dir="$(cd "$script_dir/.." && pwd -P)"
codex_root="${CODEX_HOME:-$HOME/.codex}"
validator="$codex_root/skills/.system/skill-creator/scripts/quick_validate.py"

if [[ ! -f "$validator" ]]; then
  printf 'skill validator not found: %s\n' "$validator" >&2
  exit 1
fi

python3 "$validator" "$skill_dir"
"$skill_dir/tests/test-grok-tmux.sh"
