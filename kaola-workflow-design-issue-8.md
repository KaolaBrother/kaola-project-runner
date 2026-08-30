# Issue #8 — verified per-run main-model design

## Decision

Every new, continue, or exact-resume launch has one explicit requested main model. A current-request
user override wins; otherwise the adapter uses its repository-declared Runner default. Saved CLI
picker/config state is never policy. Resolution and launch are machine facts; semantic judgment stays
with the controlling Agent.

If a readable catalog proves the requested model absent, no model-unspecified child is created.
After a selected child exists, mismatch or unreadable actual evidence is reported as `false` or
`unknown` and never blocks observe/capture/send/key/stop. The Runner never injects `workflow-next`.

## Measured current mappings (2026-08-30)

| Runtime/version | Product default | Exact current invocation | Strongest actual evidence |
|---|---|---|---|
| Grok 1.0.13 | Grok 4.6 Extra High | `--model grok-4.6 --reasoning-effort xhigh` | session summary model/effort |
| Claude 2.1.246 | Opus 5 High | `--model opus --effort high` | TUI `Opus 5 with high effort`; backend auth unavailable |
| OpenCode 1.18.23 | GLM 5.3 Max | `--model zhipuai-coding-plan/glm-5.3`, invocation variant max | exported assistant model/variant |
| Kimi 0.39.1 | Kimi K3 Max | `KIMI_MODEL_THINKING_EFFORT=max`, `--model kimi-code/k3` | session log/wire binding |
| Cursor 2026.08.25 | Grok 4.6 Extra High, FAST off | `--model cursor-grok-4.6-xhigh` | main TUI footer |

OpenCode Max and Kimi Max are parameters, not model slugs. Grok exposes no FAST switch. Cursor's
FAST model is a separate `-fast` catalog entry; native `/model` is not a read-only probe because it
rewrites global picker configuration.

## Evidence contract

`preflight`, `start`, `observe`, and `status` carry requested source/name, resolved runtime ID and
parameters, actual runtime ID and parameters, tri-state verification, mismatch reason, and structured
catalog/actual provenance. User strings enter subprocess arrays literally; no `eval` or shell-built
model command exists.

Only runtime-owned TUI/session/export/log surfaces count as actual evidence; launch argv and relay
preambles remain resolution evidence. Once a runtime-owned confirmation exists, the per-session
policy retains it as last-known evidence when later output scrolls the model footer away, while the
new unreadable frame is recorded separately as the latest observation.

## Validation boundary

Fake-runtime contracts cover five platforms across default, user override, ambient saved picker,
unavailable model, mismatch, unreadable evidence, new/continue/resume, malicious literal input, and
zero implicit Workflow input. Real smokes record exact versions, catalog, selected argv/parameters,
tmux/relay identity, actual evidence, prompt/reply, and exact shutdown. Claude can prove command
receipt and UI selection only until account authentication is restored.

The exact live receipts and shutdown proof are recorded in
[`docs/live-smoke-model-policy-2026-08-30.md`](docs/live-smoke-model-policy-2026-08-30.md).
