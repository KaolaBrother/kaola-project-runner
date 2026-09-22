# Kimi CLI adapter

- Platform ID: `kimi-cli`
- Default binary: `kimi`
- Binary override: `KIMI_BIN`
- Default session prefix: `kimi-cli-kaola`
- Continue: `--continue`
- Exact resume: `--session <session-id>`
- Runner default preset (`--tier default`): **Kimi K3 Max** — `kimi-code/k3` with `thinking=max`
- Runner upgrade preset (`--tier upgrade`): **Kimi K3 Max** — `kimi-code/k3` with `thinking=max`
- Runner alternative preset (`--tier alternative`): **Kimi K2.8** — `kimi-code/kimi-for-coding` with `thinking=max`
- Fast support: no native Fast toggle; speed-named catalog models such as kimi-code/kimi-for-coding-highspeed are explicit model choices, not a Fast switch

## Preflight

Verify the Kimi executable and report optional Kaola carrier/doctor evidence without gating communication.

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

Launch kimi --yolo from the canonical repository root. On Kimi Code CLI 2.x --yolo is Ask When Needed (routine edits and commands auto-run; risky actions, questions, and plans still ask) and is mutually exclusive with --auto (Never Ask), which the Runner no longer passes; --yes/--auto-approve are hidden aliases of --yolo. Runner --resume renders --session <session-id> (-r/--resume is a hidden alias) and Runner --continue renders --continue; 2.x rejects --session together with --continue at startup because both mean resume, so the Runner sends at most one. Thinking effort travels through thinking.effort (env KIMI_MODEL_THINKING_EFFORT: low/medium/high/xhigh/max), not a reasoning_effort wire parameter; ACP start sets mode=yolo and applies effort through the ACP thinking config option, whose ladder is the three values low/high/max rather than that five-level env ladder -- max is valid on both, but the two sets are not the same. The ACP model currentValue is kimi-code/kimi-for-coding, so the kimi-code/k3 default preset is applied, never inherited, and "Kimi K3 Max" names the composition model=kimi-code/k3 plus thinking=max: the catalog carries no "Max" in any display name. Workspace-trust remains a separate TUI surface.

Use `"$SKILL_DIR/scripts/runtime-tmux.sh"` for every preflight, start, observe, status, capture,
send, steer, permit, cancel, and stop operation, where `SKILL_DIR` is the absolute path of the installed Skill
directory containing SKILL.md (quote it — the destination may contain spaces). Read
[acp.md](acp.md) before any action that can change the runtime.
Do not reconstruct ownership checks from process names or fuzzy session matches.

Runner `--continue` and `--resume` select the native continuation/resume syntax listed above;
adapters translate these options for the platform. The native session ID is the CLI's own
conversation identifier, distinct from the Runner's `--session` name. What a platform persists and can resume is its own verified behavior, not a
universal Runner promise; when exact resume is unavailable or ambiguous, the Agent chooses
`--continue`, a new session, or existing work records. `stop` releases only the owned runtime
resources and never deletes platform history.

## Measured interaction loop

Start from `observe` and read the holder, agent, event, permission, and repository evidence. The
Runner does not classify this runtime for the Agent. The Agent decides whether to wait, send a
prompt, settle a permission with `permit`, cancel the turn, open a clean conversation, or surface a
human decision.

Transfer the chosen prompt with `send`; an optional snapshot only correlates the receipt. Then
immediately `observe` and `capture` again to read the runtime's actual response. Give changed
evidence to the Agent rather than blocking the action. If the Agent chose a Workflow task, it
separately verifies the relevant durable repository and forge state.

No launch selects scheduling or recurring behavior. Reported recurring capability is evidence only;
the Agent chooses any execution carrier and cadence outside this Runner.
