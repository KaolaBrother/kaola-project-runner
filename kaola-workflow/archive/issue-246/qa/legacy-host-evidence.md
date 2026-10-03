# Issue #246 legacy Host compatibility follow-up

Candidate: 8115c73d (new commit on workflow/issue-246).
Base: 1b6c6f6642349a8838a6f0c0c5bb5bff03d29e82. Branch: workflow/issue-246.
Installed workflow-next resumed the existing issue-246 run via its installed claim
script's `resume --project issue-246 --json`, resolving the canonical checkout
read-only: `resumed: true`, issue 246. No startup or second claim.
Claim digest remains bca135097e6df14413eda101bd7bfc9e7aeca4eb1a6b53fd149301f64c425533.
Mission 1 and its commit remain unchanged. The user confines writes to this
worktree, so the main-checkout mission ledger is read and preserved, not extended
or copied. This evidence is worktree-local and is not a replacement ledger.

## Preserved failure

The reported live trial remains FAILURE: source standalone-default, wait true,
detail "caller record does not prove a live Host role and identity",
duration_ms 763316, outcome turn_completed. No passing Host behavior is inferred
from this outcome. No live record is edited to supply session_role.

## Existing evidence and cause

The actual live legacy Host is grok-KPR-orchestrator-main at the canonical root,
holder_instance_id 074ab8b888837ea60a0af9595579ad07. Its record lacks session_role;
agent_alive is true. Existing list/state identity verification returns verified,
and the established host_session() derivation returns host_class true.
The issue-246 worker codex-KPR-i246-legacy, holder
15ad9d6d7592d35a725a2e110289581a, independently verifies. Its recorded dispatcher
exactly names that Host's platform/session/repo/holder_instance_id; its carrier
binding names that same Host and existing deterministic socket.

List's role projection and start's role derivation already recognize standard
Hosts with host_session(). Omitted-wait resolution instead required the newer
persisted session_role field. This is a compatibility gap, not absent identity.
The patch reuses that exact established class fact only for absent/null roles.
It changes no holder, binding, probe, permission, admission or lifecycle code.
Explicit non-Host and unknown roles remain blocking. Names establish the legacy
class, never ownership; all existing exact ownership facts must still match.
There is no fuzzy match, added refusal, transport gate, or live-record rewrite.
Explicit wait/no-wait still returns first and the last supplied flag still wins.
Only the API's wait-selection paragraph changes; no Host guidance changes.

## Affected real proof

[real-record-proof.json](real-record-proof.json) executes the base and candidate
resolvers against the exact existing live Host and #246 worker records read-only.
Base reproduces the preserved fallback detail. Candidate returns
owning-host-default/wait false and pins the existing worker holder.
Missing caller, mismatched holder and foreign repo remain standalone-default/wait
true, with detail and no refusal. Both explicit flags win over malformed caller
identity. The actual Host still lacks session_role after the proof.
No send/retry was issued to the preserved live Host or worker.

An isolated real Grok CLI admission trial uses the installed grok-kaola-project-runner
transport guidance, pre-role source snapshot 959af8a4^ for a naturally legacy Host,
and candidate source for its bound worker. All QA records live under this
worktree's `.kw/qa/issue-246/real-records`, outside the protected temp record root.
No record is edited to add/remove role. Both native Grok agents run the platform's
default preset. A read-only source/API review is the useful task. Omitted send
returns owning-host-default/wait false/in_progress in 93 ms; status immediately
proves turn_active true; wait then reports turn_completed, with an actual answer
confirming explicit flags precede role derivation and exact identity still applies.
Capture and exact-holder stops succeed; both stops report residual_pids [].
Receipts: [real-admission-receipts.json](real-admission-receipts.json).
Summary: [real-admission-summary.json](real-admission-summary.json).
This is real transport proof, not model-driven Host assignment/turn-boundary/
permission/delivery acceptance. That original behavior trial remains failed and
needs Host-owned acceptance. No heartbeat file is written to manufacture it.

## Validation

Reuse the frozen full validate PASS on base 1b6c6f66 recorded in the original
candidate-evidence.md and validate-frozen.log. No new full validate run is claimed.
Affected final bytes pass:

- render-skills.py --write and --check; all generated ACP copies match source.
- test-issue-244-holder-prompt-binding.py: 7 tests; absent/null legacy roles,
  exact mismatch/missing facts, vague/worker/foreign names, unknown roles,
  expected-holder pinning and explicit flags bypassing identity reads.
- test-zcode-heartbeat-contract.py: 24/24 tests, 654 checks, no skips;
  includes the #246 direct/shared/runtime entry wait-selection contract (178 checks).
- test-acp-contract.py: 84 tests, exit 0.
- test-issue-76-permission-wake.py: 5 tests, 78 checks, exit 0.
- test-issue-245-session-role.py: 11 tests, exit 0.
- git diff --check; unchanged protected-source comparison, exit 0.

Focused test runs unset FORCE_COLOR/CLICOLOR_FORCE and set NO_COLOR=1/CLICOLOR=0.
No ceilings change: main Skill 17341/17408; host-startup 8181/8192;
zcode-host-dispatch 8185/8192. The #244 dispatch contract remains byte-for-byte
unchanged, including hang reason start-timeout. Heartbeat/Delegator/harness docs,
live temp-root records, issue #251, and the main-checkout ledger are untouched.
No install, merge, push, finalize, close, archive, release, or commit amendment.

## Lifecycle

This existing Host can be identified without refresh or resume. Calling the
candidate checkout's CLI uses the corrected decision while preserving the live
holder, without installing or restarting it. The preserved failure is not retried.
If exact identity cannot be recovered for a different caller, keep blocking and
report the failed fact. Existing lifecycle recovery keeps the exact Runner
session, platform, canonical repo, holder id, ACP id, available native resume id,
active claim digest and worktree/branch/HEAD checkpoint separate. An existing
verified live Host attaches in place. After confirmed stop, an authorized native
resume uses start --resume <native-session-id>; inability to resume requires current
authorization before a fresh standard-named Host continuing the same project
records. No blank Host, guessed id, second claim or blind retry is needed here.
