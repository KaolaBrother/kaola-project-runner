# ZCode adapter

- Platform ID: `zcode`
- Default binary: `zcode`
- Binary override: `ZCODE_BIN`
- Default tmux session prefix: `zcode-kaola`
- Continue: `--continue`
- Exact resume: `--resume <session-id>`
- Runner default preset (`--tier default`): **enabled Coding Plan, first listed model** — `` with ``
- Runner upgrade preset (`--tier upgrade`): **enabled Coding Plan, first listed model** — `` with ``
- Fast support: no native Fast toggle; thought level is a separate config option (low/high/max)

## Preflight

Verify the explicit ZCode runtime path and report app-server readiness and Coding Plan provider facts without PATH discovery; the bundled runtime ships no terminal UI.

Preflight is read-only. Optional Kaola/Workflow surfaces and runtime health are reported as evidence;
their absence does not block starting the CLI. The Runner never installs, upgrades, adopts, or
rewrites runtime configuration.

Model catalogs are probed read-only. Selection precedence is explicit `--model` over the chosen
`--tier` preset; explicit `--effort` overrides preset effort only on the model it was given with,
and a different explicit model without explicit effort leaves native effort untouched. Encoded
effort/Fast model IDs are not followed by invented extra configuration calls. Saved picker/config
values never become the Runner default; on `--resume`/`--continue` the saved native selection is
preserved unless the caller supplies tier/model/effort, while Fast stays a per-run request. If the
requested model is absent from or unknown to the readable catalog, the exact declared literal is
still launched and the catalog fact is reported. Actual-model mismatch or unreadable evidence never
blocks ordinary observe, capture, send, key, or stop transport chosen by the Agent.

## Launch

Launch the installed ZCode CLI from explicit KAOLA_ZCODE_ENTRY and KAOLA_ZCODE_NODE (or ZCODE_BIN) with --mode yolo (CLI 0.16.5 permission mode that bypasses per-tool prompts; --permission-mode is the legacy alias). ACP (the default) runs Skill-relative kaola-zcode-acp.py over app-server --stdio; ACP start sets mode=yolo after initialize. Explicit --transport pty is a known-unsupported diagnostic entry, not a login or fallback channel: the bundled runtime cannot open a terminal UI (Cannot find package @zcode/tui) and headless --prompt needs ~/.zcode/cli/config.json. The adapter reads the desktop provider registry (~/.zcode/v2/config.json) read-only and selects the enabled GLM Coding Plan provider (Start Plan and pay-as-you-go refused). Because the shipped 3.12.x entry cannot locate its own bundled provider table, the adapter resolves that table next to the verified entry and injects both ZCODE_BUILTIN_PROVIDER_CONFIG_FILE and ZCODE_PERSONAL_PROVIDER_CONFIG_FILE (both or neither, never inherited). On 3.12+ it registers the plan through provider/updateAccountConfig, creates the session with no model channel, selects the model on the account:* provider through session/setModel with persistAsWorkspaceLastUsed false, and answers interaction/requestProviderRuntimeHeaders per model request; a pre-3.12 app-server keeps the in-memory runtimeModel overlay, chosen by that backend's own error rather than a version gate. It never writes ~/.zcode/cli/config.json, never injects auth env, and never logs the plan credential. Login happens in the ZCode desktop App, never through the Runner.

Use `"$SKILL_DIR/scripts/runtime-tmux.sh"` for every preflight, start, observe, status, capture,
send, key, answer, and stop operation, where `SKILL_DIR` is the absolute path of the installed Skill
directory containing SKILL.md (quote it — the destination may contain spaces). Read
[transport.md](transport.md) before any action that can change the runtime.
Do not reconstruct ownership checks from process names or fuzzy tmux matches.

Runner `--continue` and `--resume` select the native continuation/resume syntax listed above;
adapters translate these options for the platform. The native session ID is the CLI's own
conversation identifier, distinct from the Runner's tmux session name. What a platform persists and can resume is its own verified behavior, not a
universal Runner promise; when exact resume is unavailable or ambiguous, the Agent chooses
`--continue`, a new session, or existing work records. `stop` releases only the owned runtime
resources and never deletes platform history.

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
