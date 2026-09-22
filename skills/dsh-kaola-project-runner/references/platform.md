# dsh adapter

- Platform ID: `dsh`
- Default binary: `dsh`
- Binary override: `DSH_BIN`
- Default session prefix: `dsh-kaola`
- Continue: `unsupported`
- Exact resume: `session/resume <session-id> over ACP`
- Runner default preset (`--tier default`): **DeepSeek V4.1 Flash (OpenCode Go)** — `opencode-go/deepseek-v4.1-flash` with `no Runner effort override`
- Runner upgrade preset (`--tier upgrade`): **DeepSeek V4.1 Flash (OpenCode Go)** — `opencode-go/deepseek-v4.1-flash` with `no Runner effort override`
- Fast support: no native Fast toggle and no Fast config option on the ACP surface; the catalog's flash-named routes are explicit model choices, not a Fast switch

## Preflight

Verify the dsh executable, report `dsh --version` and whether an `acp` profile exists under $DSH_HOME, and never write anything under that home.

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

Launch `dsh --profile acp`, the shipped automation-only ACP v1 stdio server; the acp profile accepts no application arguments. The profile bundle pins provider deepseek-official and ignores the user's agent-default-model, so a session can start ready and still fail its first prompt with `no API key for provider route "deepseek-official"`: supply DEEPSEEK_API_KEY in the environment or pass --model to select a credentialed route. The Runner default preset selects opencode-go/deepseek-v4.1-flash, whose ACP wire value is the JSON-encoded pair ["opencode-go","deepseek-v4.1-flash"] already carried by acp_model_map; "DeepSeek V4.1 Flash (OpenCode Go)" is a Runner-side display name, not a catalog string -- the catalog's own display name is the bare lowercase deepseek-v4.1-flash, and the similarly spelled deepseek-official/deepseek-flash (displayed "DeepSeek-V41-Flash") is a different route. Because the shipped profile pins deepseek-official, this opencode-go default now needs its own credentialed provider on the ordinary path. dsh's ACP composition never sends session/request_permission; its permission mode is the launch variable DSH_PERMISSION_MODE, and the Runner starts dsh with danger-full-access (no Seatbelt sandbox, approval never) — the same full-access default as every other platform's measured bypass — unless the caller sets DSH_PERMISSION_MODE or passes --mode (read-only, workspace-write or danger-full-access; bypassPermissions maps to danger-full-access). A caller that wants the sandbox sets it explicitly: under dsh's own default workspace-write, shell writes outside the workspace, /tmp and $TMPDIR are denied, and a Runner start run from that shell inherits the sandbox (Issue #120). The Issue #98 outside-workspace probe wrote to /tmp, which is inside that writable set.

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
