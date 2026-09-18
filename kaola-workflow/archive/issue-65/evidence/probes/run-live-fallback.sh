#!/usr/bin/env bash
# Issue #65: how a SECOND ordinary prompt behaves mid-turn on platforms with no
# native steering entry — injected / queued / cancels the original / rejected.
# This characterises the fallback only; the Runner's holder refuses a second
# prompt, so none of this is Runner behaviour.
set -u
ROOT="/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner"
P="$ROOT/kaola-workflow/issue-65/evidence/probes/steer_probe.py"
OUT="$ROOT/kaola-workflow/issue-65/evidence/fallback"
mkdir -p "$OUT"
run(){ id="$1"; shift; echo "### $id start $(date +%T)"; python3 "$P" --id "$id" --live --budget 260 --hard-timeout 420 --out "$OUT/$id.json" "$@" >/dev/null 2>"$OUT/$id.stderr"; echo "### $id exit=$? $(date +%T)"; }
run droid      --cmd "droid exec --output-format acp"
run grok       --cmd "grok agent --always-approve stdio"
run kimi-cli   --cmd "kimi acp"
run opencode   --cmd "opencode acp"
run devin      --cmd "devin acp"
run cursor-cli --cmd "cursor-agent --yolo acp" --meta '{"parameterizedModelPicker": true}'
echo "ALL DONE $(date +%T)"
