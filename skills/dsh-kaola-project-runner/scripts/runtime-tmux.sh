#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
exec "$script_dir/kaola-tmux.sh" dsh "$@"
