#!/usr/bin/env bash
# Issue #126: Runner call under the shadow HOME and the isolated record root.
for v in $(env | grep -o '^\(KAOLA\|KPR\)_[A-Z_]*' | grep -v '^KAOLA_ZCODE_'); do unset "$v"; done
unset CODEX_HOME
export HOME=/tmp/kpr126-home KAOLA_ACP_RECORD_ROOT=/tmp/kpr126-records npm_config_cache=/Users/ylminiserver/.npm
exec /Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-126/scripts/kaola-tmux.sh "$@"
