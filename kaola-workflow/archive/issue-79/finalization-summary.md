# Issue #79 — finalization summary

Run: `issue-79` · Issue: **#79** · Branch: `workflow/issue-79` · Sink: merge to `main`
Accepted candidate (outer review): `55f330fb99a57338c949c953d7c7e98327c603f2`
Finalized head (accepted candidate + documentation docking): `b40813f04f6c5faf00ef1866efe343dad4614253`

## Delivered

ZCode 3.12+ ACP app-server compatibility in the Runner-owned adapter, proven by a live model turn.
The installed desktop 3.12.3 build contains no `runtimeModel` at all, so the v0.39-era shape could
not start a turn. Three independent breaks were fixed minimally, without vendoring upstream bytes
and without replacing the owned adapter:

1. **The shipped 3.12.x entry cannot find its own bundled provider table.** It probes
   `<entryDir>/provider/` and a five-levels-up path that fits the source tree but not the `.app`,
   where the table sits one level up, so `app-server` exited 1 before serving anything. The adapter
   resolves the table from the already-verified entry and injects both
   `ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` and `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` (both or neither).
   Neither name is in `ENV_ALLOWLIST`, so an inherited, unowned value is dropped before the derived
   one is set.
2. **The 3.12+ provider registry starts empty**, because the app-server bootstrap omits its
   `standalone` option — the real cause of `Select a model before continuing`. The one enabled
   Coding Plan is registered through `provider/updateAccountConfig`, the session is created with no
   model channel, and the model is selected on the `account:*` provider through `session/setModel`
   with an explicit `options.reasoningLevel` and `persistAsWorkspaceLastUsed: false`.
3. **`interaction/requestProviderRuntimeHeaders` was answered with `{}`**, which cannot satisfy the
   strict response union and failed every turn. It now carries the credential for the one authorized
   provider and refuses any other.

The CLI version string is `0.16.5` on both the working 3.11.2 baseline and the broken 3.12.3, so no
version gate is possible: the protocol is chosen by the backend's own error, and a pre-3.12
app-server keeps the `runtimeModel` path. The one-enabled-Coding-Plan policy, fail-closed refusals
and redaction are unchanged; the credential stays in memory and never reaches disk, ACP output, a
log, a receipt, a fixture, or this archive.

## Files Changed

Eleven tracked files (`git diff --name-only main..HEAD`):
`README.md`, `CHANGELOG.md`, `docs/api.md`, `docs/zcode-host.md`, `platforms/zcode.yaml`,
`scripts/kaola-zcode-acp.py`, `scripts/validate.sh`, `third_party/zcode-acp/UPSTREAM.md`,
`tests/contract/fake-zcode-312-app-server.py`, `tests/contract/test-issue-79-zcode-312.py`, and the
regenerated `skills/zcode-kaola-project-runner/` outputs (`scripts/kaola-zcode-acp.py`,
`scripts/platform.yaml`, `references/acp.md`, `references/platform.md`).

Production adapter: +334 / −26, and all 26 deletions are re-indentations or replaced dispatch lines —
the legacy `setModel` block still exists verbatim under the new `else:`, and nine `runtimeModel`
references remain for pre-3.12 backends. `skills/` was regenerated through
`./scripts/render-skills.py --write`, never hand-edited.

## Test Coverage

New hermetic suite `tests/contract/test-issue-79-zcode-312.py` (**19 cases**) against a new
3.12.3-shaped fake backend `tests/contract/fake-zcode-312-app-server.py` that mirrors the measured
strictness, including the two requirements that only the live run revealed. Covers: candidate
resolution order including the shipped `.app` layout the CLI's own probe misses; both-or-neither env;
an inherited poisoned value never reaching the child; create-without-model then setModel; the account
snapshot's exact keys and casing; the revision hashing the PATH not the bytes; reasoning-level
resolution against rule ordering; the headers callback answered and the turn completing; the
mid-session model switch; a refused switch not committing local state; the credential absent from
every ACP and log byte; refusal of a model the plan does not offer; refusal to hand the key to a
foreign provider; two fail-closed cases; and a pre-3.12 backend still driven through the legacy
overlay.

Baseline proof: against the pre-change adapter (`f6be8a3`) 11 of the then-15 cases failed; the 4 that
passed are deliberately the back-compat and redaction guards that must hold on both. The three
review-driven cases were each written failure-first and reproduced their exact symptom before the fix.
No real secret appears anywhere: the only key is the fixture value already inside `tests/`.

Registered in `scripts/validate.sh` (`python_suites_all` + lane a).

## Validation

Recorded receipt: `verdict: pass`, `validated_candidate_hash`
`173632eec450cff746de86a57a2c6798d7d2f9e4800fa223bcd76ad855b18631`, finalize gate
`validation: chains_green`. Exact command:

```
./scripts/render-skills.py --check && python3 tests/contract/test-issue-79-zcode-312.py \
  && python3 tests/contract/test-zcode-acp-contract.py && python3 tests/contract/test-generated-skills.py \
  && python3 tests/contract/test-issue-51-runner-integration.py && python3 tests/contract/test-zcode-host-contract.py \
  && python3 tests/contract/test-zcode-heartbeat-contract.py && python3 tests/contract/test-issue-78-heredoc-deadlock.py \
  && git diff --check
```

Exit 0 (`evidence/10-scoped-validation-pass.log`): render --check PASS · #79 suite 19/19 ·
ZCode ACP contract 34/34 · generated Skills PASS · issue-51 runner integration 6/6 (119 checks) ·
zcode host and heartbeat exit 0 · inherited #78 heredoc guard 3/3 · `git diff --check` clean.

**`./scripts/validate.sh` as a whole exits 1 — this is NOT a green full validate, and no such claim
is made.** `evidence/09-full-validate-known-red.log` records the exact run:
`FAILED: test-issue-49-grok-bot-host.py`, an `[Errno 66] Directory not empty` race in
`TemporaryDirectory` teardown (43 tests, the single error in teardown, deterministic across repeats).
Reproduced identically at the original base `f6be8a3` in a throwaway worktree, so it is a pre-existing
baseline failure outside this run's production scope. **Owned by #80; release still waits on it.**

A single `validate.sh` invocation also stops early — a lane aborts at the first failing suite and the
log replay then hits a missing log under `set -e` — so it is not by itself evidence that the other
suites ran. The per-suite receipts above are the real coverage.

Live acceptance, twice, against the real installed desktop ZCode **3.12.3** in isolated disposable Git
repos through the Runner ACP path (never this repo, never a user project):

| leg | receipt |
|---|---|
| Mission 5, candidate `f5bb7dd` era | start `state: ready` + yolo applied · `final_text: "KAOLA79OK"`, `stop_reason: end_turn`, 4530 ms · stop `residual_pids: []` |
| Final, on the accepted candidate | start `state: ready` + yolo applied · `final_text: "KAOLA79FINAL"`, `stop_reason: end_turn`, 5463 ms · stop `residual_pids: []` |

Credential leak check over every receipt and the event log: **absent**. A scan of all evidence files
for the credential returns none.

Not executed: any second desktop version, machine, plan, or account; ZCode PTY transport (unsupported
by the bundled runtime by design); any release or global install.

## Changed Paths

As reported by the finalize transaction:

```
platforms/zcode.yaml
scripts/kaola-zcode-acp.py
scripts/validate.sh
skills/zcode-kaola-project-runner/references/acp.md
skills/zcode-kaola-project-runner/references/platform.md
skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py
skills/zcode-kaola-project-runner/scripts/platform.yaml
tests/contract/fake-zcode-312-app-server.py
tests/contract/test-issue-79-zcode-312.py
third_party/zcode-acp/UPSTREAM.md
```

Recorded discrepancy, not papered over: this list has ten entries, while
`git diff --name-only main..HEAD` has eleven — the transaction's list omits `README.md` (and predates
the documentation-docking commit that also touches `CHANGELOG.md`, `docs/api.md`,
`docs/zcode-host.md`). The Git diff is the authoritative set of what this branch changes.

## Documentation Docking

`.cache/doc-docking.md` — **DOCKED**. Fixed: `README.md` (stated the pre-3.12 mechanism as the
mechanism and implied the 2026-09-16 gate covered current ZCode; now names each live gate with the
desktop build it ran against and the boundary that neither carries over), `CHANGELOG.md` (new
Unreleased entry), `docs/api.md`, `docs/zcode-host.md` (said the in-memory overlay carries the
credential — true only pre-3.12), `third_party/zcode-acp/UPSTREAM.md`, `platforms/zcode.yaml`.
No impact: `docs/architecture.md`, `docs/README.md`, `docs/conventions.md`, `docs/decisions/`,
setup/environment, examples.

## Follow-Up Items

- **#80** — `test-issue-49-grok-bot-host.py` `[Errno 66]` teardown race. Pre-existing baseline,
  reproduced at `f6be8a3`, outside this run's production scope. Already filed by the outer review.
- **#82** — holder/mock process residue from standalone ACP tests. Already filed by the outer review;
  its audit is in progress, which is why this run keeps its worktree and performs no broad process
  cleanup.
- Release remains blocked on #80 and #82; no release or global install was performed here.
- Carried forward from the run, unresolved and non-blocking: upstream `william0wang/zcode-acp`
  0.43.2 changed the account-to-config provider id mapping again, so the 0.42.x mapping this adapter
  was cross-checked against is already stale upstream. The adapter derives its ids from the installed
  bundled table rather than from upstream, so this is a watch item, not a defect.

## Readiness

Accepted by independent outer review at `55f330f`; documentation docking added afterwards as
`b40813f04f6c5faf00ef1866efe343dad4614253`. Ready to archive and sink to `main` with the worktree kept for the #82 audit.
