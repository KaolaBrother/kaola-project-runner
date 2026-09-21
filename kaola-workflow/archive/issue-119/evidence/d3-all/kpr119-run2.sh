#!/usr/bin/env bash
# Standalone start under the shadow HOME and the isolated record root.
for v in $(env | grep -o '^KAOLA_[A-Z_]*' | grep -v '^KAOLA_ZCODE_'); do unset "$v"; done
export HOME=/tmp/kpr119-home KAOLA_ACP_RECORD_ROOT=/tmp/kpr119-records
exec /Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-119/scripts/kaola-tmux.sh "$@"
