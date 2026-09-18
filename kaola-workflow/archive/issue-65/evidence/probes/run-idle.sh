#!/usr/bin/env bash
# Issue #65 phase-1 idle steering-entry discovery across ACP platforms.
# Isolated: each run spawns its own agent child in its own scratch cwd.
set -u
ROOT="/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner"
P="$ROOT/kaola-workflow/issue-65/evidence/probes/steer_probe.py"
OUT="$ROOT/kaola-workflow/issue-65/evidence/idle"
mkdir -p "$OUT"
run(){ id="$1"; shift; echo "### $id start $(date +%T)"; python3 "$P" --id "$id" --out "$OUT/$id.json" "$@" >/dev/null 2>"$OUT/$id.stderr"; echo "### $id exit=$? $(date +%T)"; }
run claude-code --cmd "node $ROOT/vendor/claude-code-acp/dist/index.js"
run codex       --cmd "npx --yes --package @openai/codex@0.153.4 --package @agentclientprotocol/codex-acp@1.11.0 codex-acp"
run cursor-cli  --cmd "cursor-agent --yolo acp" --meta '{"parameterizedModelPicker": true}'
run droid       --cmd "droid exec --output-format acp"
run grok        --cmd "grok agent --always-approve stdio"
run kimi-cli    --cmd "kimi acp"
run opencode    --cmd "opencode acp"
run devin       --cmd "devin acp"
echo "ALL DONE $(date +%T)"
