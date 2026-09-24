# Codex CLI adapter

- Platform ID: `codex`
- Default binary: `codex`
- Binary override: `CODEX_BIN`
- Standalone session prefix: `codex-kaola-<purpose>` (under Project Runner the name is issue-scoped; see SKILL.md)
- Resume: `session/resume`/`session/load` per advertised capability; Continue: the latest `session/list` entry for the canonical cwd
- Runner default preset (`--tier default`): **GPT-6 Sol High** — `gpt-6-sol` with `effort=high`
- Runner upgrade preset (`--tier upgrade`): **GPT-6 Astra High** — `gpt-6-astra` with `effort=high`
- Fast support: Codex fast mode via ACP `fast-mode` configId (off/on); explicit off is applied, not assumed

## Preflight

Verify the Codex executable and report optional Kaola Workflow skill or plugin carrier evidence without making Workflow availability a communication gate.

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
blocks ordinary observe, capture, send, cancel, or stop transport chosen by the Agent.

## Launch

ACP runs the pinned npx codex-acp wrapper (@openai/codex plus @agentclientprotocol/codex-acp); ACP start sets mode=agent-full-access after initialize.

Use `"$SKILL_DIR/scripts/runtime-tmux.sh"` for every preflight, start, observe, status, capture,
send, steer, permit, cancel, and stop operation, where `SKILL_DIR` is the absolute path of the installed Skill
directory containing SKILL.md (quote it — the destination may contain spaces). Read
[acp.md](acp.md) before any action that can change the runtime.
Do not reconstruct ownership checks from process names or fuzzy session matches.

Runner `--resume` and `--continue` map onto the ACP methods listed above. The native session ID is the CLI's own
conversation identifier, distinct from the Runner's `--session` name. What a platform persists and can resume is its own verified behavior, not a
universal Runner promise; when exact resume is unavailable or ambiguous, the Agent chooses
`--continue`, a new session, or existing work records. `stop` releases only the owned runtime
resources and never deletes platform history.

## Measured interaction loop

Start from `observe` and read the holder, agent, event, permission, and repository evidence. The
Runner does not classify this runtime for the Agent. The Agent decides whether to wait, send a
prompt, settle a permission with `permit`, cancel the turn, open a clean conversation, or surface a
human decision.

Transfer the chosen prompt with `send`. Then
immediately `observe` and `capture` again to read the runtime's actual response. Give changed
evidence to the Agent rather than blocking the action. If the Agent chose a Workflow task, it
separately verifies the relevant durable repository and forge state.

No launch selects scheduling or recurring behavior. Reported recurring capability is evidence only;
the Agent chooses any execution carrier and cadence outside this Runner.
