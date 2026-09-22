# One Host handoff

Outer Agents start, continue, or restore the project's one ZCode Host here;
Project Runner inside it owns workers, heartbeat, and close-out. No new tool,
queue, registry, scheduler, or Delegator pointer file — Git worktree, Workflow
run / ledger, Issues, and Runner records already hold durable facts.

```bash
ZCODE="<skills>/zcode-kaola-project-runner/scripts/runtime-tmux.sh"
PROJECT="/abs/path/to/consumer-project"          # bound canonical Git root
HOST="zcode-<PROJECT_CODE>-orchestrator-main"    # e.g. zcode-KPR-orchestrator-main
```

`<skills>` is the sibling Skill directory, or `ROOT/skills` after the bridge
located ROOT. A missing `$ZCODE` is a hard stop — no ZCode Runner, no Host.

`<PROJECT_CODE>` is the project's established short code. Ask once if
unrecorded. Inner workers keep `<platform>-<PROJECT_CODE>-i<ISSUE>-<purpose>`
(#72). The Host name is not an Issue worker and does not use `i0`.

Three identities stay separate — read them from existing Runner `status`,
start receipts, and Host events; never synthesize one from another:

| Field | Source | Use |
|---|---|---|
| Runner `--session` | `$HOST` (or a uniquely recorded live name) | live attach, observe, send, stop |
| `acp_session_id` | start / `status` receipt | ACP bridge id |
| native `sess_*` | `native_session_identity.nativeSessionId` | `start --resume` after the holder stopped |

`session_meta` does not automatically hold `sess_*`: `start` has no
`native_session_identity` before the first prompt; a stopped app-server
does not restore it.

## Grok Bot co-location (account bridge only)

Loaded from the Grok Bot account bridge (ROOT, bound target, and project
given as inputs): before each Host `status`, `start` (including `--resume`),
`send`, and `stop` on that bound target, run the existing locator with full
attestation. Codex and generic Skill-directory hosts skip this.
No second locator, ledger, or schema.

```bash
kaola-project-runner-locate --target local|cloud --expect-revision <accepted> \
  --project "$PROJECT" --worker zcode --session "$HOST"
```

`$HOST` is the exact session about to be used: the standard name, or a
uniquely adopted live nonstandard name — never any other session. Refuse any
`refused` receipt; do not operate the Host.

## Recover

1. Bind the same execution target and `$PROJECT`; derive `$HOST` from the
   short code (Grok Bot bridge: attest first). Probe the existing Runner:

   ```bash
   "$ZCODE" status --repo "$PROJECT" --session "$HOST"
   ```

   Read existing Runner records/receipts too: if they uniquely name a live
   Host whose session is not `$HOST`, adopt that locator — never rename or
   start a second Host; a missing `$HOST` proves nothing.
   Ambiguous location: report and do not start.
2. **Live Host** (exact platform/repo/session still serves, and
   `holder_instance_id` plus `acp_session_id` match the receipts): do not
   `start`. Continue on that holder. If `status` shows a different
   `holder_instance_id`, it is not H1 — do not `send`/`stop` as H1; re-verify.
   Do not replay the first handoff. An outer-Agent change neither stops the
   Host nor re-asks authorization; apply only the user's latest change.
3. **Confirmed stopped** and no other live orchestrator on this `$PROJECT`:
   if existing receipts attest a native `sess_*`, try only:

   ```bash
   "$ZCODE" start --repo "$PROJECT" --session "$HOST" --resume "$NATIVE_SESS"
   ```

   Never use `--continue` to guess a same-directory worker. After exact
   `stop`, try attested `--resume` of that `sess_*` first. Native resume
   is backend-dependent; `session/close` may not spend it.
   On proven failure (`Session not found` or no attested id) a **new**
   `$HOST` is allowed after step 4. That is a new ACP session and a new
   holder — say so. Rebuild the frontier from Git, Workflow claim / ledger,
   Issues, and run receipts — never re-claim, re-dispatch, or redo. Do not
   `start` until step 4 completes.
4. A new Host (first start, or after failed `--resume`) needs current
   authorization **before** `start`: goal and remaining work; allowed worker
   platforms/members; counts and concurrency; the quota given, in its own
   units; priority; delivery and stop boundary. Restore them from the latest
   project facts. Missing, conflicting, or expired key
   values: ask the user; do not `start`. A unit the user never gave is none
   of those: send it `unspecified`. Do not guess and do not reuse a stale
   quota. Do not open a blank Host. A live Host A→B attach is not a new
   session: do not re-ask the full set.
5. With step 4 complete and no live Host: start once under `$HOST` at
   `$PROJECT`. Confirm `session`/`repo`/`acp_session_id`/`holder_instance_id`
   from the start receipt, then send the first handoff. `$HOST` `start` /
   `--resume` pins GLM 5.3 + effort `max`, verified in `host_selection`;
   a `host-model-*` refusal escalates.

## Handoff and updates

Do not start another platform.

Idle Host: `send` is enough — `--no-wait` is admitted, not delivered, not
project complete; a first `end_turn` is only that beat.

Busy Host (`prompt-in-progress` / turn active): never claim a `--no-wait`
send consumed — `steer` injects the running turn verbatim (no new `Skill`
invocation) or wait for idle; `steer --steer-mode interrupt`
resends verbatim on a new turn — not a Host entry; supply the first line
yourself to open a Host round.
`unknown`/`not_consumed` is not a resend. No queue.

```bash
"$ZCODE" send --repo "$PROJECT" --session "$HOST" --no-wait --text '<handoff>'
"$ZCODE" observe --repo "$PROJECT" --session "$HOST"
"$ZCODE" capture --repo "$PROJECT" --session "$HOST" --lines 200
```

Every turn-opening Host prompt — handoff and later updates alike — opens
with `/kaola-project-runner` as its own first line: the native Skill entry,
idempotent across re-invocation and after compaction (non-ZCode: its
`host_skill_entry`). Install the generated
Skill under a discovered root — default `<repo>/.zcode/skills/`,
`<repo>/.agents/skills/`, `~/.zcode/skills/`, or `~/.agents/skills/`
(configured `skills.roots`/`plugins.dirs` roots also scan); else plain text. No `AGENTS.md` block or manual `SKILL.md` read is the carrier.

Handoff text (quota units never merge; `unspecified` is not unlimited):

```text
/kaola-project-runner
You are the ZCode Host for this run.
platform=zcode session=<HOST> repo=<PROJECT>
goal=<user goal>
done=<already done>
remaining=<remaining work>
authorized_platforms=<id:count, ...>
quota_concurrency=<as given>
quota_account=<as given>
quota_token=<as given>
priority=<as given>
delivery_stop_boundary=<as given>
project_context=<canonical root and other given facts>
Finish planning, worker dispatch, heartbeat, acceptance, and Workflow
close-out internally. Missing authorization stays missing:
do not expand it.
```

## After the first Host beat

Do not trust the Host's self-description. After the first `end_turn`, check the
Project Plan and current authorization against file-read or work-product
evidence and the first worker dispatch receipt — including
`<project>/.kaola/heartbeat-prompt.json` with a usable `body`. The beat's
`capture` shows a `Skill` tool_call for that entry; none means the install
is wrong — fix it, never a manual `read`. In that `start`
receipt the worker `--session` is an issue-scoped worker name, not `$HOST`;
platforms, counts, and the stop boundary must match. Mismatch or missing evidence:
correct on this Host; do not accept completion. No new script, gate, ledger,
or store.

## Afterward

Read delivery with `observe` / `capture`; the outer Agent is not
automatically awakened by inner Host activity. Escalate only an
unrecoverable decision. Do not `stop` while workers, acceptance, or
Workflow close-out remain; then stop the exact holder from the existing
start/`status` receipt — not inner workers or name-only:

```bash
"$ZCODE" stop --repo "$PROJECT" --session "$HOST" \
  --expected-holder-instance-id "$HOLDER"
```

`$HOLDER` is `holder_instance_id` on that receipt. `holder-instance-mismatch`
means this name now serves a different instance: do not stop it; re-read
`status`.
