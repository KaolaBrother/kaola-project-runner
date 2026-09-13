# Codex CLI adapter

- Platform ID: `codex`
- Default binary: `codex`
- Binary override: `CODEX_BIN`
- Default tmux session prefix: `codex-kaola`
- Continue: `resume --last`
- Exact resume: `resume <session-id>`
- Runner default main model: **GPT-5.6 Luna Low**
- Current resolved launch identity: `gpt-5.6-luna` with `effort=low`

## Preflight

Verify the Codex executable and report optional Kaola Workflow skill or plugin carrier evidence without making Workflow availability a communication gate.

Preflight is read-only. Optional Kaola/Workflow surfaces and runtime health are reported as evidence;
their absence does not block starting the CLI. The Runner never installs, upgrades, adopts, or
rewrites runtime configuration.

Model catalogs are probed read-only. A user-provided per-run `--model`/`--effort` overrides the
Runner default; saved picker/config values never become the Runner default. If the requested model
is absent from or unknown to the readable catalog, the exact declared literal is still launched and
the catalog fact is reported. Actual-model mismatch or unreadable evidence never blocks ordinary
observe, capture, send, key, or stop transport chosen by the Agent.

## Launch

Launch codex --cd <repo> --no-alt-screen with literal --model, -c model_reasoning_effort, and the mapped sandbox/approval pair (default agent-full-access). ACP process is the pinned npx codex-acp wrapper.

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
