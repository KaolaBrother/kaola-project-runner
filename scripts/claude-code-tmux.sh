#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Preserve the historical root entrypoint, whose callers supplied the platform
# explicitly, while keeping one behavioral control plane for every runtime.
if [[ "${1:-}" == claude-code ]]; then
  shift
fi
export KAOLA_CLAUDE_PROFILE_REQUIRED=true
exec "$script_dir/kaola-tmux.sh" claude-code "$@"
