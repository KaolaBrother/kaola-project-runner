# Lifecycle implementation completion report — six owner requirements

Scope: the final integrated candidate on `workflow/issue-264` at `ff5a5383` — `f562560f` (QA-r2 integration),
`082da503` (capability-gap table), `544b58c5` (this report), `0b3af748` (steer cells), `19faebfd` (dot corrections),
`c44e87a7`/`2c3d253b`/`e4cf481b` (review-round fixes), `94f62785` (E1 Class A+B+C), `ec90bb02`/`4d919d24` (#267
integration + closed-contract proof), `72257366` (#268 integration), `3a58b431` (#268 boundary fixes + B-delta),
`aa659981` (dot recheck proof), `b5472308` (E1 lane fix + lane-integrity regression), `984cdd48` (#267 mask+gap1-3),
`5e462f4a` (#133 docstring fix), `d4de8685` (#267 effort-order + production-bind), `ff5a5383` (explicit
effort-limitation docs; the body-capability removal decision is `a1e98b38`).
Requirements source: `.kw/worktrees/issue-264/AGENTS.md` §
"Project special requirements — lifecycle implementation (#255)" at
`3c7e7417`, plus owner clarifications relayed 2026-10-06 through the dot main
session (capability table Sentinel_27d913395e90819199545f470d8c6421 /
_15c6ec9ed9b08191a982e2d62258f92a / _e3b97d4346908191a717f86890655ad6;
support criterion Sentinel_993c0853c4c08191843176126322f9b2; Fable-at-ready
Sentinel_76e2d79995308191893e4ceb49466050). Each was adopted verbatim into
the heartbeat task records (revisions 85–88) before implementation — the
record → relay → adoption → implementation/QA → final-answer path this
report closes. Review gate: actual dot main-thread + Claude Code Fable
personal PASS both remain pending; PATCH publication stays held.

## 1. Template fidelity

**Mechanism.** Two typed routine JSONs with fixed schemas and role-owned
writes: `.kaola/heartbeat-prompt.json` (`kaola-heartbeat-prompt/2`; `body`
written only by the `state` tool, skeleton-conformant generated Host view)
and `.kaola/delegator-heartbeat.json` (`kaola-delegator-heartbeat/1`, owned
by the dot Delegator, read-only to the Host). Skill-side templates are
canonical under `templates/`; installed copies are render output only
(`render-skills.py --check` PASS at both commits, byte budgets intact).

**Drift detection and correction.** Every write carries revision checks:
`--expect-rev`/`--expect-revision` refusals were observed and honored in
live operation (task `expect-rev-required` at rev 82; section retry 1107 →
1108); `state check` reports problems (observed `ok / problems[]` at rev
1101); `state migrate` plan mode reports `current`; it writes no v1 copy (the
existing `heartbeat-prompt.v1-754a4d19cefe.json` is an earlier release's
leftover, kept, `trusted: false`), and `state-overwritten` is not raised
from copies — an older writer replacing the current file is no longer
detected that way (recover from project, Runner and forge records); that
reduced overwrite detection is a real limitation of this mechanism. The 2026-10-06 Host switch surfaced real drift —
`recovery.host` still narrating the retired Codex Host — and the tool
refused prose ("object of identity fields"; forbidden `native_session_id`
key listed) until the write matched the typed template.

**Native timer readback unavailable.** The dot timer entry carries a static
`timer_template` that locates the repo file — changing project state never
enters timer text; when native readback is absent, that static locator is
the documented fallback.

**Limitations.** The top-level `carrier` identity stamp is not rewritten by
`update`/`migrate` in the current tool version (observed with both the
frozen c337 writer and the installed dispatch tool; capability/size
semantics unaffected — file ≈44.5 KiB < 64 KiB, `check` ok). Identity
custody is carried by `recovery.host`, per-record `writer`/`writer_holder`,
the Delegator snapshot (rev 20) and Runner records instead.

## 2. Structured, current and inspectable information

**Mechanism.** Current-only collections (`tasks`, `holds`, `alerts`,
`decisions`): a handled row leaves atomically via `clear/resolve/retire`
with original evidence — no tombstone, no copy in another field (now
canonically tested in `test-issue-255`); role views and injected bodies
derive from the stored collection; workers are refused as writers;
Sideagent transcripts need `--host-turn`. `f562560f` makes the stored and
injected heartbeat body the plain shared projection a holder recomputes at
read time, while the catalog-enriched capability stays on demand
(`state view --role host`, `project`) — the owner's 2026-10-06 no-compulsory-
injection direction, completed by dot's same-day technical decision: the
routine stored/injected body no longer carries the duplicate grant-derived
`capability{presets,shared_seats}` projection either (full effective
authorization in the same body is the single source; the on-demand
dispatch/project views keep capability; no switch, no persistent field,
grant semantics unchanged); the `24a2355a`-measured chains remain valid across it
because current holders recompute rather than inject the stored body, and
the only attention change is the unbound ordinary-change case, which every
measured chain (bound node-mode Sideagent, typed recovery input) never
exercised. Evidence stays by reference; the Host view is bounded.

**Repeated-cycle evidence.** The run's own succession demonstrates
non-accumulation: handoff snapshot rev 1097 → adoption writes 1098–1111
replaced stale handoff prose with current facts each beat; maintenance
`handled_host_revision` advanced 813 → 815 → 818 via node batches
`b-680c4b4ba30c`, `b-512bf8d97734`, `b-b2efdd13e7db`; superseded timer/quota
narrative (Grok-era, Codex-era) was replaced, not retained alongside
(the completed Codex→ZCode handoff order was later retired from
`project.stop` and the typed `recovery.host` provenance refreshed in an
ordinary Host write, per the Fable delta round).
Efficiency is judged by outcome: worker events were judged and integrated
in the same beat (delivery-r2 accepted → integration `f562560f` within one
beat), the 21:15 Delegator inquiry reused existing evidence without a
second audit, and no bookkeeping engine was added.

**Limitations.** The dispatch index keeps its old-dispatcher correlation
rows (correlation-only, by contract — historical provenance, not live
ownership); five older in-flight rows remain until their lifecycle close.

## 3. Host autonomy and Sideagent lifecycle

**Mechanism.** The Host owns plan, dispatch, acceptance and QA; Sideagent is
one maintenance node per meaningful batch of Host changes — fresh node,
checkpoint, exact stop — with no compulsory round trip: `f562560f` removes
the node duty for ordinary unbound Host business changes while a typed
`recovery_input` stays visible without any binding (three-case canonical
test added). Worker events go to the Host; the node wakes the Host only
when attention changed.

**Trace.** Role entry: native `/kaola-project-runner` Skill invocation (E1)
with `KAOLA_ACP_DISPATCHER` identity and host-exists admission. Actual calls
this run, all receipted: `list` sweeps (3 live rows, no orphans),
`rebind-host` ×2 (same holders, carriers moved), one identity-guarded
`send --no-wait` (repair prompt fingerprint `4f60504d…`), exact `stop` ×2
(exit 0, residuals []), and the state writes above. Node lifecycle:
`zcode-KPR-node-inquiry` batches with verified scoped checkpoints and
stops; the compaction-recovery chain itself is proven per runtime in
`docs/host-compact-capabilities.md` (e.g. Kimi verified scoped checkpoint
`b-e93d1a2aaa85` on fixed `24a2355a`).

**Parallel split** followed independent context boundaries (core / hooks /
edge / baseline-QA lanes disjoint; no fixed reviewer count, no all-branch
barrier).

**Limitations.** Devin seam checkpoint honestly partial
(`recovery-originals-unavailable` on links — fixture local-record evidence,
named recovery retained); Cursor and Droid compaction stages remain
unverified (no native completed signal in bounded attempts). Kimi's
completed signal is a text match on an agent message chunk
(`kimi-compaction-chunk`, `occurrence_id: null`), not a native structured
event.

## 4. Recovery and informed autonomy

**Mechanism.** `--preserve-dispatched-workers` stop + per-seat `rebind-host`
carrier continuity (live on Codex and ZCode); `--session`, `acp_session_id`
and native `sess_*` kept as three separate facts (a Git worktree is never an
ACP id); `drain-restart` for stale seats; the transient-failure contract
(≥3 safe reconciled retries, no blind replay, in-progress ≠ failed);
environment/configuration failures distinguished from model behavior.

**Real cases.** (a) The 2026-10-06 Codex→ZCode Host switch: exact
preserve-stop (exit 0, spared pgids 78497/81677, swept []), successor
rebound both workers in place with unchanged holders, no resend or restart,
and the run continued in-beat. (b) Same-assignment recovery: the baseline-QA
repair went to the exact rebound seat once, identity-guarded, never
re-sent. (c) QA failure reading: fixture count discrepancy classified
source-supported; the binding-gate proposal rejected for hiding a real
recovery duty; pre-existing `t259` failures isolated by a stash control run
(clean HEAD: 8 failures; integrated: 7 — `1248` repaired, zero new
regressions) instead of being blamed on the change.

**Limitations.** `lifecycle-state.md` lists relay-across-holder-death,
timer read-back and real (≈1 MiB) state size as unproven. Correction
(dot review): `RealAcpInjection` is a mock-ACP/real-holder test, not a
live-runtime need — its empty log was `MOCK_ACP_LOG` being deliberately
dropped by the launch broker's env allowlist (commit `24a2355a`); fixed by
carrying the log path in the agent command (`--log`), keeping the
projected-goal-marker real-injection assertion intact.

## 5. Continuous improvement and evolution

**Mechanism.** Redundancy and staleness are noticed in ordinary planning,
review and QA without waiting for user reminders; corrections take the
smallest sufficient form; obsolete guidance is retired rather than a rule
added per incident.

**Actual instances (no failure prerequisite).** Stale heartbeat-capability
wording retired from `SKILL.md.tmpl` and `worker-profiles.md.tmpl` (on-demand
projection); the stale "pending decision stays" assertion reconciled with
the 2026-10-06 current-only contract (doc + test message); the superseded
Grok/Codex handoff narrative replaced by the typed identity object; a
scoped count-2 fixture instead of weakening module AUTH; two byte-budget
overruns corrected by compressing wording (never by raising the locked
budgets); scratch counterexamples promoted to canonical tests only where
coverage was absent (three-case maintenance attention; plain-body holder
assertion).

**Evidence.** Diffs of `f562560f` / `082da503`; the tool refusals that
forced precision; unchanged valid evidence reused rather than regenerated
(ZCode row reused byte-identical `4b247` bridge facts).

**Limitations.** The seven `t259` failures observed at `0b3af748` (all
pre-existing at clean `3c7e7417`) were resolved by the dot-correction
revision, keeping the original obligations: the six `watch_alias` subtests
compared stored authorization byte-shape across the catalog-derived `class`
removal and now assert exact effective-authority equivalence (preset set,
count and every non-derived key preserved; `class` absent as a stored
copy; illegal aliases still refused with zero file writes); the
`RealAcpInjection` fix is described under requirement 4.

## 6. Future upgrade continuity

**Mechanism.** `state migrate` (plan → write; unknown schema refused; repeat reports
`current`; writes no v1 copy — older-writer overwrite detection was
removed with it, a stated limitation); the
`heartbeat-state/2` carrier size contract; render-only generated surfaces
with locked byte budgets; the CHANGELOG `Seats:` convention and per-release
pin/adapter operator test (`docs/conventions.md`); and the capability-table
update convention from `082da503` — re-check a row only against actual
runtime version, adapter and measured evidence, fill a gap only when
verified, and never write unverified as unsupported or fully supported.

**Evidence.** This run exercised the real continuity events: an updated
Skill reload reconciled against live state; a Host replacement preserving
grants, duties and in-flight work with zero worker restarts; integration on
the same claim/worktree with revision-guarded state; and explicit
evidence-reuse rules in the matrix. The grouped-grant reader proof is a
scratch/source check (docs/conventions.md), not an all-runtime installed
upgrade result.

**Limitations.** #267 effort raise: the reset-on-effort path is not implemented (no catalog field declares an order; the raise branch is unreachable), so a same-preset effort change never resets a segment today; a preset change is a responsibility handoff and does reset with index evidence; record a repair with the delivery evidence locator and dispatch item in the same write — a bare verdict is counted as unknown; ordinary Runner receipts without task_id bind through existing dispatch/item/session/index locators (native live sample: the i268-b-delta index row); conservative unknown keeps count and pending duties. Consumer-side install UAT is intentionally not performed
(no-install boundary): installed runtime Skills remain at the prior release
until the authorized PATCH release/install step; relay across holder death
and timer read-back remain unproven as above. The delegator consumer view
still projects main's superseded seven-item/Opus AGENTS until the final
lifecycle sink replaces them; that view is re-read and verified from
canonical main after the sink, never declared correct from the candidate.

## Evidence locators

Revision-guard refusals and adoption receipts: rebind/stop receipts
`/tmp/kpr-zcode-host-baseline-qa-exact-stop.json`,
`/tmp/kpr-zcode-host-edge-exact-stop.json`; repair send
`/tmp/kpr-zcode-host-baseline-qa-repair-send.json` (fingerprint
`4f60504d…`); task-rev refusals appear in the adoption beat's tool output
(rev 82 `expect-rev-required`; section retry 1107→1108; `state check` ok
at 1101). Fable's base/candidate reproduction logs:
`/tmp/kpr-fable-review-20261006/logs/`; its review:
`/tmp/kpr-i264-final-fable-review-20261006.md`.

## Gate status

CODE CANDIDATE / GATE STATUS (current): the release candidate is the tip of `workflow/issue-264` after the
Fable O1–O5 docs-and-test fix and the D1–D4 narrow corrections (`7ddfe5d5` plus this commit). Scope delivered and
judged: E1 (root cause, lane fix, integrity regression), #267 (binding/replay/conflict/pending, catalog-declared
effort order with the not-implemented reset documented, production dispatch-locator binding, one-transition
handoff), #268 (four-fact continuity, no false preserved, per-axis readback, no intent inference). Root scoped
PASSes cover the segments listed in state; Fable's final review passed the product code, tests, the seven issues
as delivered, the six owner requirements and the capability table, with O1–O5 docs/test objections fixed on top.
Final pending gates: one full inventory at the final SHA (subset checks green first), Fable's delta verdict on
the narrow-fix commit, root's release decision, then the seven-issue lifecycle close, Seats/pins, main sink and
consumer-view re-read. Review history (superseded): the full review of `0b3af748` returned FAIL on E1 — twelve
no-log SKIPs root-caused to suites registered in the replay list but never in an execution lane (the `--suite`
narrowing masked it), fixed at `204456e9`, pinned at `b5472308`; the earlier five-issue successor-frontier text
is retired to this history note. Engineering evidence: `render-skills.py --check`
PASS; `t255` full 128 OK; `t259` full 60/60; generated+progressive
suites 15 OK — these cover the AFFECTED checks only; the full inventory
is red as described above. Regression scope, precisely: at
`0b3af748` the full `t259` file had 7 failures, each already present at
clean `3c7e7417` under the same stash-controlled, same-machine runs (8
there; `1248` was repaired by `f562560f`); no new regression within the
tested set (full `t255`/`t259` files plus the generated/progressive
suites). Review bindings: (a) the dot main thread personally reviewed `0b3af748`
(six answers, README table, both behavioral diffs, retire wording,
seven-failure originals) and returned NOT PASS with four bounded
corrections — implemented at `19faebfd` (mock `--log` past the broker env
allowlist with empirical confirmation, effective-authority equivalence
assertions, restored Sideagent copy semantics, review-binding and
scoped-regression precision), which also pre-resolved Fable's O2. (b)
Claude Code Fable personally reviewed the same `0b3af748` (independent
base/candidate reproduction; product code, tests, evidence copies,
capability table and steer cells pass its review) and returned FAIL on
O1–O4 — report/template wording only, no behavioural objection; R1–R4 are
implemented in this delta revision (migration wording, delegator snapshot +
README + Skill capability-wording alignment, the Kimi matrix-row
self-contradiction, steer-cell qualifiers, completed-handoff retirement
from live state), and a delta re-review of those hunks was requested; the
residual grant-derived `capability` preset list in the injected body is
decided by dot within the owner's standing rule and implemented at
`a1e98b38` (this paragraph is the resolved history of that question). Pending: dot main-thread personal PASS, Claude Code Fable
personal PASS (owner decision Sentinel_76e2d799: Claude authentication is
fixed — the real Fable review starts when this report makes the candidate
review-ready; no probe start, no authentication investigation, existing
all-tier shared-1 standing grant, no automatic model switch), original
259/263/264/265/266 lifecycle close, release pins/content/`Seats`, and the
next UNUSED stable PATCH under HOLD.
