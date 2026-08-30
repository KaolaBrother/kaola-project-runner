# Cursor CLI adapter

- Platform ID: `cursor-cli`
- Default binary: `cursor-agent`
- Binary override: `CURSOR_AGENT_BIN`
- Default tmux session prefix: `cursor-cli-kaola`
- Continue: `--continue`
- Exact resume: `--resume <chat-id>`

## Preflight

Verify the Cursor executable and report optional global/project Workflow command evidence without gating communication.

Preflight is read-only. Optional Kaola/Workflow surfaces and runtime health are reported as evidence;
their absence does not block starting the CLI. The Runner never installs, upgrades, adopts, or
rewrites runtime configuration.

## Launch

Launch cursor-agent --workspace <repo> without materializing or modifying project files.

Use `scripts/runtime-tmux.sh` for every preflight, start, observe, status, capture, send, key, answer,
and stop operation. Read [transport.md](transport.md) before any action that can change the runtime.
Do not reconstruct ownership checks from process names or fuzzy tmux matches.

## Measured interaction loop

Start from `observe` and read the complete `raw_current_frame` together with exact tmux, process,
relay, input/output and repository evidence. The Runner does not classify this runtime for the
Agent. The Agent decides whether to wait, send a prompt, transfer a native key, use a tested
whole-editor replace/clear route, open a clean conversation, or surface a human decision.

Transfer the chosen prompt with `send`; an optional snapshot only correlates the receipt. Then
immediately `observe` and `capture` again to read the runtime's actual response. Give retained editor
text and other changed evidence to the Agent rather than blocking the action. If the Agent chose a
Workflow task, it separately verifies the relevant durable repository and forge state. Native key
sequences are transported only after the Agent reads the current screen and names the key.

No launch selects scheduling or recurring behavior. Reported recurring capability is evidence only;
the Agent chooses any execution carrier and cadence outside this Runner.
