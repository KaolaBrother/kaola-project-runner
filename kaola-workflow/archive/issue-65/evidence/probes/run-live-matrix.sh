#!/usr/bin/env bash
# Issue #65 round 3: the actually-usable ACP steering path, live, per platform.
set -u
ROOT="/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner"
S="$ROOT/kaola-workflow/issue-65/evidence/probes/live-steer-matrix.sh"
export KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs
export KAOLA_ZCODE_NODE="$(command -v node)"
for spec in "$@"; do
  p="${spec%%:*}"; m="${spec##*:}"
  echo "########################## $p ($m)"
  STEER_AFTER="${STEER_AFTER:-25}" "$S" "$p" "$m" 2>&1
done
echo "MATRIX DONE $(date +%T)"
