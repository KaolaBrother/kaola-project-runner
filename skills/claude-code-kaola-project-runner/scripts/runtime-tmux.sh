#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
export KAOLA_CLAUDE_PROFILE_REQUIRED=true
exec "$script_dir/kaola-tmux.sh" claude-code "$@"
