#!/usr/bin/env bash
# Issue #65 round 3: re-run the real ZCode Host acceptance on the CORRECTED
# generated Skill (round-2 cursor fix + round-3 steering scope).
# Scratch-only: creates /tmp/kw-i65-e2e2/repo, installs the Skills there with
# --method copy, and touches nothing outside it. No global install.
set -u
WT="/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-65"
SCRATCH="/tmp/kw-i65-e2e2/repo"
EV="/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/kaola-workflow/issue-65/evidence/live-host2"
export KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs
export KAOLA_ZCODE_NODE="$(command -v node)"
mkdir -p "$SCRATCH" "$EV"
cd "$SCRATCH" || exit 1
[ -d .git ] || { git init -q . && git commit -q --allow-empty -m "scratch"; }
"$WT/scripts/render-skills.py" --write >/dev/null
"$WT/scripts/install-local.sh" --skills-dir "$SCRATCH/.zcode/skills" --method copy \
  --platform zcode,codex >"$EV/0-install.log" 2>&1 || { tail -5 "$EV/0-install.log"; exit 1; }
ls "$SCRATCH/.zcode/skills"
