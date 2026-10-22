# Finalization Summary — Issue #405

## Delivered

Holder-timing contract waits synchronize on observed progress instead of
wall-clock windows, closing the flake class where the suites
(`test-issue-76-permission-wake.py`, `test-issue-255-lifecycle-state.py`,
`test-issue-341-agent-initiated-turn.py`) failed in gate runs under machine
load while every subtest was green standalone — each `wait_for`/`wait_until`
had treated a fixed elapsed window as the synchronization contract while the
producer chain legitimately exceeded it under load.

- `tests/contract/test-issue-299-delegator-webhook.py`: the shared
  `wait_for` takes an optional `probe`. With one, the numeric budget becomes
  a stall watchdog — reset by any change in the probe signature or the
  check's own value — and an absolute `max(6 * timeout, 60)`-second ceiling
  stays only as the hang backstop; `probe=None` keeps the previous deadline
  semantics exactly.
- `tests/contract/test-issue-341-agent-initiated-turn.py`: probes the
  fixture tree (excluding `.git`), the endpoint post count, and — at most
  once a second — the fixture holder's children by `ppid` (long-lived
  holder/mock agent contribute pid only; short-lived spawns — the
  `delegator-webhook deliver` child, `run_ps` scan children — contribute
  pid+CPU). Guessed sleeps for the noise burst, replay tail and post-cancel
  tail became observed-event waits; `wait_stable` replaces 'nothing more
  arrives' settles.
- `tests/contract/test-issue-255-lifecycle-state.py`: `wait_observed` plus a
  `HolderFixture` probe (fixture tree, node bookkeeping, pending events,
  fake prompts/stops, stub sends, spawned node runner pid+CPU) behind both
  `wait_for` wrappers and the converted polls; `wait_still` replaces the
  no-more-node settles.
- `tests/contract/test-issue-76-permission-wake.py`: `Sandbox.progress` +
  `sandbox.wait_until`; worker-side carrier receipts are now waited on
  rather than bare-read (a real lag race the conversion exposed).
- `tests/contract/test-zcode-heartbeat-contract.py`: `wait_until(probe)`
  and `wait_still` for the no-periodic-carrier assertion.
- `scripts/validate.sh --help` and `docs/conventions.md`: the accepted
  recovery for a suspected load flake — a standalone
  `./scripts/validate.sh --suite NAME` rerun on the same tree keeping both
  receipts; never more full-gate copies; budgets are stall watchdogs only
  where a probe exists and socket traffic is never a probed surface.

## Review

Host verdict on `86a42506`: ACCEPTED. First review failed the candidate on
tautological probes (`.git` churn and long-lived-process CPU were read as
progress); repair `86a42506` excluded `.git` from every probe walk, moved
341 to ppid-children coverage of the real stall hop (`holders_dispatched_by`
scans, deliver child), and added negative-control receipts — never-true
predicates in idle fixtures fail at the stated budget, not the ceiling.

Candidate: `86a42506967753bdebee74d61cc32e766bbd1dde` on
`workflow/issue-405` (implementation `b0f53250`..`42fe48ff` + Host review
repair `86a42506`).

## Evidence

- Repro: `/tmp/kpr-405-repro/` (full-gate failures on main 22814695,
  immediate standalone greens).
- Focused receipts: `/tmp/kpr-405/suite-76-r1.log` (5, exit 0),
  `suite-341-r2.log` (9 incl. f2, exit 0), `suite-255-r1.log` (171, exit 0),
  `suite-hb-r1.log` (24/24, exit 0) on the repair candidate.
- Negative controls: `/tmp/kpr-405/negctl-76.out`,
  `/tmp/kpr-405/negctl-341-r1.out` — never-true predicates fail at ≈10 s
  stated budget (10.02–10.33 s), not the 60 s ceiling.
- Full inventory: `/tmp/kpr-405/fullgate-42fe48ff.log` — 164 suites, 0
  FAILED, wall 2162.84 s, during concurrent KPM build activity (a concurrent
  full gate is not evidenced). The repair changed only the four suites'
  probe internals; each repaired suite reran green, so the gate receipt
  stands for the untouched surface.
