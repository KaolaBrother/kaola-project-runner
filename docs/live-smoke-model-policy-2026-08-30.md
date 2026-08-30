# Issue #8 live model-policy smoke — 2026-08-30

This run used five exact Runner-owned tmux sessions in the Issue #8 worktree. The controlling Agent
read each TUI, selected one verification prompt, transferred it through the Runner, read the reply,
and stopped only the matching session. The Runner did not inject `workflow-next` itself.

## Prompt

Each available runtime received the same verification-only instruction with a platform-specific
receipt token:

```text
Use workflow-next to inspect and resume the already-active Issue #8 workflow in verification-only
mode. Read the current workflow state and mission list, do not edit files or forge state, and reply
exactly KPR_I8_<platform>_WORKFLOW_NEXT_RECEIVED issue-8.
```

## Results

| Runtime | Exact session | Selected and actual model evidence | Communication result |
|---|---|---|---|
| Grok 1.0.13 | `kpr-i8-live-grok` | argv `--model grok-4.6 --reasoning-effort xhigh`; TUI/footer `Grok 4.6 (xhigh)`; `model_verified=true`, FAST not exposed | Loaded `workflow-next`, read the active run, returned `KPR_I8_grok_WORKFLOW_NEXT_RECEIVED issue-8` |
| Claude Code 2.1.246 | `kpr-i8-live-claude-code` | argv `--model opus --effort high`; TUI `Opus 5 with high effort`; `model_verified=true` | Prompt rendered in the main conversation, then `Login expired · Please run /login`; backend execution was not available and is not claimed |
| OpenCode 1.18.23 | `kpr-i8-live-opencode` | argv `--model zhipuai-coding-plan/glm-5.3`; TUI footer `Build · GLM-5.3`; sanitized export of exact latest session `ses_fae859cd5ffeFshZH9HamPXcs8` recorded provider `zhipuai-coding-plan`, model `glm-5.3`, variant `max` | Read the active run and returned `KPR_I8_opencode_WORKFLOW_NEXT_RECEIVED issue-8` |
| Kimi Code 0.39.1 | `kpr-i8-live-kimi-cli` | per-session `KIMI_MODEL_THINKING_EFFORT=max`, argv `--model kimi-code/k3`; TUI footer `K3 thinking: max`; `model_verified=true` | Agent selected native workspace trust, Kimi loaded `workflow-next`, read the run, and returned `KPR_I8_kimi_cli_WORKFLOW_NEXT_RECEIVED issue-8` |
| Cursor Agent 2026.08.25-3e8eec8 | `kpr-i8-live-cursor-cli` | argv `--model cursor-grok-4.6-xhigh`; TUI/footer `Cursor Grok 4.6 Extra High`; `fast=false`, `model_verified=true` | Read the installed Cursor workflow-next command and active run, then returned `KPR_I8_cursor_cli_WORKFLOW_NEXT_RECEIVED issue-8` |

OpenCode's main TUI exposes the model but not the variant, so a frame-only observation truthfully
reports the effort as unreadable; the runtime's sanitized session export is the durable proof for
`variant=max`. This is evidence, not a communication gate.

## Evidence corrections and side effects

- Shell launch preambles are excluded from actual-model parsing. Before this correction, an argv
  model plus `Max` in the host name could produce a false OpenCode/Kimi match.
- A runtime-owned confirmation is retained as last-known session evidence when later output scrolls
  the model header/footer away. The unreadable new frame is retained separately as the latest
  observation; it does not erase or fabricate a model change.
- Cursor native `/model` was not used in this live smoke. Earlier read-only investigation proved that
  selecting even the same model rewrites `~/.cursor/cli-config.json`; the pre-run bytes were not
  retained, so they cannot be restored exactly. The current picker facts remained Grok 4.6, xhigh,
  FAST off and max mode off. This side effect is reported rather than hidden.
- `templates/grok-golden/` had zero modified paths. The verified Grok protocol and prompt boundary
  remain frozen.

## Shutdown

OpenCode, Kimi, and Cursor accepted graceful exact-session stop. Grok and Claude did not confirm
their prepared quit payload, so the Runner restored both before the Agent chose exact-session
`--force` containment. Both force-stop receipts proved child group stopped, session absent, and relay
socket absent. Final `status` returned `result=absent` and `present=false` for all five session names;
`tmux list-sessions` contained no `kpr-i8-live-*` residue.
