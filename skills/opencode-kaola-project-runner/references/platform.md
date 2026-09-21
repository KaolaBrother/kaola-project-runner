# OpenCode adapter

- Platform ID: `opencode`
- Default binary: `opencode`
- Binary override: `OPENCODE_BIN`
- Default tmux session prefix: `opencode-kaola`
- Continue: `--continue`
- Exact resume: `--session <session-id>`
- Runner default preset (`--tier default`): **CLI native opening model** — `` with `no Runner model or effort override`
- Runner upgrade preset (`--tier upgrade`): **CLI native opening model** — `` with `no Runner model or effort override`
- Fast support: no native Fast toggle; speed-named catalog models such as zhipuai-coding-plan/glm-5.3-flash are explicit model choices, not a Fast switch

## Preflight

Verify the OpenCode executable and report optional Kaola carrier/configuration evidence without gating communication, plus loopback=direct|excluded|ensured: what the opencode child sees once a forward proxy is set (ensured means the Runner appends the missing loopback entries).

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

Launch opencode <repo> --auto. V2 removed the --mini flag, its mini subcommand takes neither a directory nor --auto, and top-level --model/--variant are rejected outright. Default ACP has no skip-all; PTY --auto via --transport pty is the bypass; configOptions.mode is agent identity (build/plan), not skip-all.

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
