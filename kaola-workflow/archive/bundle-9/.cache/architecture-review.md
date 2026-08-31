## Architecture: Issue #9 minimal communication-only runner restoration

### Design Decisions

- **Keep the post-`de5f258` transport, remove later semantic authority.** The useful baseline at
  `de5f258:scripts/grok-tmux.sh:295-340,343-402` was exact-session start/read/send/stop. Retain the
  managed relay, exact owner/platform/repository/one-pane checks, same-UID socket/epoch/child
  attestation, byte fingerprints, C0/C1 rejection, bracketed paste, DECRQM fence, and exact shutdown
  reconciliation added later. Remove only decisions based on UI/editor/model catalog meaning.
- **Split force containment before `prepare_transaction`.** Current
  `scripts/kaola-tmux.sh:453-455` invokes `prepare_transaction` before testing `--force`, while
  `prepare_transaction` at `341-346` requires successful relay bootstrap. `stop --force` must first
  validate independent tmux identity (`owned`, platform, canonical repo, one pane, exact relay pane
  command/PID), then use live-relay containment when attestation works or exact dead-relay containment
  when it does not. Do not add a `dead-relay` state machine or broad process sweep.
- **Dead-relay containment stays exact and truthful.** Before mutation, record the exact pane relay
  PID/start identity and any uniquely attributable direct runtime child/PGID and attached descendant
  start identities. Kill only `=$session`; if recorded identities survive, TERM/CONT then bounded KILL
  only identities that still match their recorded start fingerprints. Clean only the canonical
  same-UID epoch socket accepted by `cleanup_terminal_socket` (`256-271`). Report `stopped` only for
  facts actually proved absent; represent unavailable escaped-descendant evidence as unknown. If a
  known exact identity survives, return existing `termination-uncertain` semantics with
  `mutation_performed:true` and measured final facts. Session absence must still permit a same-name
  restart.
- **A present but dead relay is not reusable.** Current `start` at `412-414` treats a non-empty socket
  marker as `already-running`; an isolated dead-socket measurement returned rc 0 and
  `result:already-running` while `relay.managed:false`. Reuse only after responsive bootstrap proves
  the relay PID equals the pane PID. Otherwise return existing `existing-session-not-reusable` plus
  evidence, without killing or replacing the session. Suppress bootstrap traceback noise and leave
  force-stop to an explicit Agent choice.
- **Delete prepared-editor authorization, retain byte receipts.** Delete
  `prepared_surface_result` and `prepared_answer_surface_result` (`303-330`) and their calls in
  `send` (`436-437`), `answer` (`429-434`), and graceful `stop` (`503`). The relay already disables
  pane input, serializes by lease, checks queued outer bytes, attests the prepared payload fingerprint,
  and submits only after the controller asks (`scripts/kaola-pane-relay.py:487-518,707-741`). For
  `answer`, a prepared-frame capture may remain solely to form the evidence-only later-output receipt;
  none of its editor/activity/decision values may refuse submit. Remove prepared recaptures entirely
  from `send` and graceful `stop`, where they have no non-gating consumer.
- **Pass the exact Agent-selected model literal.** `scripts/kaola-model-policy.py:96-160` may still
  probe and report the catalog, but must always retain `candidate_id` as the launch ID, including when
  a readable catalog omits it. Do not rewrite a user literal through display-name matching, omit
  `--model`, or choose a fallback. `scripts/kaola-tmux.sh:117-134,412-415` must stop turning catalog
  absence into `model-unavailable`; adapters continue building argv arrays from the exact ID
  (`scripts/adapters/*.sh:adapter_build_launch`). Actual CLI acceptance/rejection/fallback remains
  post-launch model evidence. Terminal-control validation at `kaola-tmux.sh:91-95` stays.
- **Delete, do not bound, the duplicate tmux mutation lock.** `kaola-tmux.sh:333-346` adds an
  unbounded `tmux wait-for -L` outside the relay's already exclusive 2-second lease and 5-second
  transaction deadline (`kaola-pane-relay.py:41-42,640-658,866-867`). A killed controller can strand
  the tmux lock; bounding acquisition portably would add another recovery mechanism. Remove
  `MUTATION_LOCK*`, `lock_mutation`, `unlock_mutation`, related trap/calls, and the
  `mutation_lock_released` restoration claim. Prove concurrent controller attempts finish within a
  bound and that at most the relay lease owner mutates.
- **Delete dormant Cursor materialization code and contradictory prose.** Core never calls
  `scripts/adapters/cursor-cli.sh:34-55`; it references otherwise undefined materializer variables.
  Delete the function. Keep read-only preflight at `17-32` and launch argv at `57-67`.
  `docs/architecture.md:114-118` is stale and contradicts README `125-127`, API `137-139`, and current
  tests. Historical live-smoke documents remain historical; do not rewrite their recorded facts.
- **Regenerate, never hand-edit, active Skills.** `scripts/render-skills.py:87-134` copies the shared
  core/helpers plus one adapter into all five packages. Run `--write`, then `--check`; commit every
  generated delta. Keep every byte under `templates/grok-golden/` unchanged; its reviewed hashes are
  enforced by `tests/contract/test-generated-skills.py:202-244`.

### Evidence Classification

| Finding | Classification | Evidence |
|---|---|---|
| Dead socket blocks force recovery | Confirmed regression | Issue #9 reproduction plus current `stop` control flow; isolated current-byte run returned `relay-attestation-failed`, rc 1, session still present |
| Dead socket is reported reusable by `start` | Confirmed regression | Isolated current-byte run returned rc 0 / `already-running` with `relay.managed:false` and connection refused |
| Prepared editor parsing false-refuses valid operations | Confirmed regression | Owner reports live Grok/Claude false refusals; branches at `kaola-tmux.sh:313,327` authorize Enter from inferred UI text despite relay byte receipt |
| Readable catalog blocks exact selected model | Confirmed regression | `kaola-model-policy.py:103-120`, core `412-414`, and `test-model-policy.sh:438-451` require refusal/no session |
| Cursor materialization function is dormant and docs conflict | Confirmed code/docs drift, not a live blocker | No core call site; README/API say no materialization while architecture says it is required |
| tmux lock can strand forever | Unmeasured risk | No abandoned-lock test or observed incident; acquisition has no bound, while relay lease is bounded |
| Runtime internally changes its editor after byte preparation | Unmeasured platform-semantic risk | Synthetic Issue #6 fixtures model it; UI parsing cannot reliably distinguish it from repaint and must not be transport authority |
| Escaped descendants after relay state becomes unreadable | Unmeasured evidence gap | Dead relay cannot return its private tracked set; report unknown unless an exact pre-kill identity was independently captured |
| Post-fix real communication on all five installed CLIs | Required, currently unmeasured | Existing dated smoke docs predate Issue #9 bytes and cannot prove the new build |

### Files to Create

| File | Purpose | Priority |
|---|---|---|
| `tests/contract/test-issue-9-transport.sh` | One public-runner regression suite for dead/refusing socket force-stop + restart, dead-relay start result, prepared semantic-frame submission, no outer tmux lock, and exact-session isolation | P0 |
| `tests/fixtures/issue-9/*` | Deterministic raw-PTY semantic repaint and catalog-missing runtime fixtures shared by the Issue #9 suite | P0 |
| `docs/live-smoke-issue-9-2026-08-31.md` | New, immutable command/result record for the five real CLIs; do not edit older smoke history | P2 |

### Files to Modify

| File | Changes | Priority |
|---|---|---|
| `scripts/kaola-tmux.sh` | Split independent identity from live relay preparation; add exact dead-relay force branch/reconciliation; make start reuse require live attestation; delete UI prepared guards and duplicate tmux lock; keep transport receipts and bounded polling | P0 |
| `scripts/kaola-model-policy.py` | Make catalog resolution evidence-only and keep exact candidate literal as launch ID; preserve actual-model verification | P0 |
| `scripts/adapters/cursor-cli.sh` | Delete dormant `adapter_prepare_launch`; keep preflight and exact `--workspace/--model` launch | P1 |
| `tests/contract/test-model-policy.sh` | Across all five platforms, replace catalog-missing refusal/no-session assertions with exact argv launch, captured CLI outcome, no fallback/omission, and shell-literal safety | P0 |
| `tests/contract/test-guarded-actions.sh` | Remove expectations that inferred editor mismatch refuses send/stop/answer; keep relay fingerprint, identity, restoration, whole-editor, and exact force tests | P0 |
| `tests/contract/test-long-wrapped-send.sh` | Remove synthetic runtime-editor mutation as a hardgate oracle; retain exact wrapped/LF/TAB transfer tests. Outer-byte races remain covered by relay fence tests | P0 |
| `tests/contract/test-tmux-native-atomicity.sh` | Preserve legacy-direct mutation refusal, but assert the objective relay identity reason rather than requiring the removed force transaction shape | P1 |
| `tests/contract/test-relay-pty.py`, `test-relay-fence.py`, `test-relay-escaped-descendant.py` | Retain byte fence, lease recovery, live-relay force, escaped-descendant proof; add/adjust bounded concurrent-lease evidence if the new public suite does not own it | P1 |
| `tests/contract/test-adapters.sh` | Keep five launch shapes and extend the per-platform loop to send/capture actual echo and exact stop/status absence if not covered elsewhere | P1 |
| `tests/contract/test-live-smoke-adapters.sh`, `test-cursor-authority-receipt.sh` | Remove obsolete materializer fixture machinery where no longer needed; continue proving Cursor preflight/start are read-only and never execute the helper | P1 |
| `tests/test-issue-1-acceptance.sh` | Register the Issue #9 regression suite | P0 |
| `templates/SKILL.md.tmpl`, `templates/references/transport.md.tmpl` | State catalog absence and runtime observations are evidence-only; document independent dead-relay force boundary; remove tmux-lock restoration claim | P1 |
| `README.md`, `docs/architecture.md`, `docs/api.md`, `docs/conventions.md`, `CHANGELOG.md` | Align model, force recovery, serialization, and Cursor behavior; remove the obsolete catalog/materializer exceptions | P1 |
| `skills/{grok,claude-code,opencode,kimi-cli,cursor-cli}-kaola-project-runner/**` | Deterministic renderer output only: shared core/model helper/template references in all five; Cursor adapter only in Cursor package | P1 |

### Data Flow

```text
start(existing exact session)
  -> independent owner/platform/repo/one-pane/relay-process facts
  -> responsive same-epoch relay + pane PID match ? already-running
  -> otherwise existing-session-not-reusable + evidence (no mutation)

send/key/answer/graceful stop
  -> independent identity -> same-UID relay attestation -> bounded relay lease
  -> action-time evidence (advisory) -> exact payload/key prepare receipt
  -> objective fingerprint/capability checks -> submit
  -> capture/read actual runtime result

force stop
  -> independent exact identity BEFORE prepare_transaction
  -> live relay? containment/terminate + exact known descendant reconciliation
  -> dead relay? record exact pane-owned identities -> kill only =session
       -> bounded exact-identity TERM/CONT/KILL if still matching
       -> safe same-UID epoch socket cleanup -> measured final facts/unknowns
  -> same-name start is possible once session absence is proved

model
  -> exact Agent/default candidate literal
  -> catalog probes add evidence only
  -> adapter argv contains that same literal
  -> CLI output supplies acceptance/rejection/fallback and actual-model evidence
```

### Acceptance Surfaces

1. Baseline Issue #9 test must fail on current bytes for: refusing socket force-stop, dead-relay
   `already-running`, semantic-frame prepared refusal, and readable-catalog launch refusal.
2. Dead-relay force test starts a managed fixture, records child/socket, stops the child, replaces the
   epoch path with an owned AF_UNIX socket that refuses connections, preserves an unrelated session,
   force-stops the exact target, verifies measured final facts, restarts the same name, then stops it.
3. Prepared-input test uses a raw PTY whose visible editor/activity/decision frame disagrees while its
   actual editor bytes remain the exact relay payload; send and graceful stop must submit from the relay
   fingerprint and later capture must show the actual CLI response.
4. Safety regression remains green for unowned, foreign-platform, repository-mismatched, multi-pane,
   legacy-direct mutation, terminal controls, missing bracketed paste, outer-byte fence races, child
   identity mismatch, live-relay force, and tracked escaped descendants.
5. `test-model-policy.sh` loops Grok, Claude Code, OpenCode, Kimi, and Cursor with a readable catalog
   missing the selected literal; every CLI argv log must contain that literal exactly, and no fallback
   or shell side effect may appear.
6. Run `./scripts/render-skills.py --write`, `--check`, and `./scripts/validate.sh`; verify frozen Grok
   hashes unchanged and no generated drift.
7. Real five-platform evidence must use each generated `runtime-tmux.sh` for
   preflight -> start exact session/model -> observe/capture -> send a unique verification prompt ->
   capture the actual response -> stop exact session -> status absent. Record runtime version, selected
   argv/model evidence, prompt receipt, reply, and zero unrelated/residual sessions. Cursor must use
   `cursor-grok-4.6-xhigh`, xhigh, Fast disabled, and never `/model`. Claude may prove command receipt
   plus the authentication error if account execution is unavailable; do not claim model execution.

### Build Sequence

1. Freeze baseline evidence and add the failing Issue #9 public acceptance plus five-platform
   catalog-missing assertions; do not alter acceptance meaning after production changes.
2. In `kaola-tmux.sh`, extract/reuse the independent exact identity predicate, move force dispatch
   before `prepare_transaction`, implement bounded dead-relay reconciliation, and correct existing
   dead-relay start reuse.
3. Delete prepared-editor guards/unused recaptures and delete the outer tmux lock; retain relay lease,
   byte/fence/capability checks, and truthful restoration fields.
4. Make model catalog evidence-only in `kaola-model-policy.py`; verify each adapter passes the exact
   selected literal and never falls back.
5. Delete Cursor's dormant materialization function and update source docs/templates. Do not touch
   `templates/grok-golden/` or rewrite historical smoke records.
6. Regenerate all five Skills, run renderer check, focused Issue #9/model/relay/identity suites, then
   the full `./scripts/validate.sh`.
7. Run and record the five real CLI communication loops. Only after all executed evidence is captured
   should the new smoke document and changelog be finalized.

### Deliberate Limits

- No new status taxonomy, model fallback, retry policy, Workflow orchestration, editor parser, process
  name sweep, dependency, or recovery command.
- Dead-relay escaped descendants that were not independently observable are reported unknown; that
  uncertainty neither broadens process cleanup nor keeps an exact broken tmux session forever.
- Historical Grok golden bytes and prior dated live-smoke evidence remain untouched.
