# Issue #249 guidance candidate

Branch: `workflow/issue-249`. Worktree: `.kw/worktrees/issue-249`.
Candidate: `5bbbe6ab` (`Add bounded Sidekick duty reconciliation guidance (#249)`); full commit id in `candidate.txt`.

The owner's scope correction authorizes normal renderer-owned bridge and pin
bookkeeping. The documented content/pin cycle was reopened by setting
`templates/grok-bot/accepted-revision.json` to `stage: content` and removing the
old commit/release. The normal renderer then wrote the three bridge outputs.
No frozen golden templates, byte ceilings, ACP source/copies or assertions were
edited. No script, timer, JSON schema, protocol token, approval gate or automatic
snapshot mutation was added. No actual CLI agent session was started.

## Exact guidance paths

| Source | Renderer-owned output |
|---|---|
| `templates/orchestrator/SKILL.md.tmpl` | `skills/kaola-project-runner/SKILL.md` |
| `templates/orchestrator/references/host-startup.md.tmpl` | `skills/kaola-project-runner/references/host-startup.md` |
| `templates/orchestrator/references/duty-reconcile.md` | `skills/kaola-project-runner/references/duty-reconcile.md` |
| `templates/kaola-delegator/references/snapshot.md` | `skills/kaola-delegator/references/snapshot.md` |

The ten worker `scripts/main-skill-build.json` outputs carry the updated main
Skill build, including the new reference. Additional normal generated outputs
are `hosts/grok-bot/kaola-delegator.md`, `hosts/grok-bot/bridge.json` and
`hosts/grok-bot/INSTALL.md`. These were written by the renderer, not hand edited.
The bridge is a development content-stage output (`saveable: false`); no new pin,
release, tag or install was performed. The Host must coordinate these generated
results with #247 ownership at merge time; this run has not edited its worktree.

## Commands, exits and resulting sizes

All commands ran from the #249 worktree root. Adjacent logs and `.exit` files
record the checks. Full validation completed; its baseline failure and environment limits are recorded below.

| Command | Exit | Result |
|---|---:|---|
| `./scripts/render-skills.py --write` | 0 | Normal renderer; 10 workers, main, Delegator and bridge; budgets OK. |
| `./scripts/render-skills.py --check` | 0 | PASS; content stage, no pin assertion bypass. |
| `./scripts/validate.sh` | 1 | One baseline dispatch-timeout failure; all other suites completed. See details below. |
| `python3 tests/contract/test-progressive-disclosure.py` | 0 | 15 tests; repeated for final generated bridge. |
| `python3 tests/contract/test-issue-41-orchestrator.py` | 0 | 23 tests. |
| `python3 tests/contract/test-issue-74-kaola-delegator.py` | 0 | 188 assertions, no failed tests. |
| `python3 tests/contract/test-generated-skills.py` | 0 | PASS against final normal render. |
| `python3 scripts/validate-skill.py skills/kaola-project-runner` | 0 | PASS. |
| `python3 scripts/validate-skill.py skills/kaola-delegator` | 0 | PASS. |
| `./scripts/render-skills.py --verify-install "$PWD/skills"` | 0 | Read-only checkout verification, not an install: all 12 bundles aligned, no missing/skew. |
| `git diff --check` | 0 | No whitespace errors. |
| `git diff --cached --check` | 0 | Candidate staging has no whitespace errors. |
| `python3 tests/contract/test-issue-244-dispatch.py DispatchEntry.test_timeout_and_unknown_mutation_are_not_failed_or_returned` | 1 | Isolated candidate reproduces the full-run mismatch. |
| Same isolated command at main checkout `c47daa1e` | 1 | Unchanged parent baseline reproduces exactly the same mismatch; writes only its temporary fixtures and receipts in the #249 worktree. |
| `git diff HEAD^ HEAD -- scripts/kaola-dispatch.py tests/contract/test-issue-244-dispatch.py` | 0 | Empty diff: dispatch implementation and failing assertion were not changed. |
| `git diff --exit-code HEAD -- scripts/kaola-acp.py 'skills/*/scripts/kaola-acp.py' templates/budgets.json templates/grok-golden templates/orchestrator/references/dispatch-collect.md skills/kaola-project-runner/references/dispatch-collect.md` | 0 | Protected tracked bytes unchanged. |
| `wc -c skills/kaola-project-runner/SKILL.md skills/kaola-project-runner/references/duty-reconcile.md skills/kaola-project-runner/references/host-startup.md skills/kaola-project-runner/references/dispatch-collect.md skills/kaola-delegator/SKILL.md skills/kaola-delegator/references/snapshot.md` | 0 | Guidance sizes below. |
| `wc -c hosts/grok-bot/kaola-delegator.md hosts/grok-bot/INSTALL.md hosts/grok-bot/bridge.json` | 0 | Generated bridge sizes below. |

| Generated surface | Bytes | Ceiling | Remaining |
|---|---:|---:|---:|
| Main `SKILL.md` | 17,301 | 17,408 | 107 |
| `references/duty-reconcile.md` | 4,803 | 8,192 | 3,389 |
| `references/host-startup.md` | 8,170 | 8,192 | 22 |
| `references/dispatch-collect.md` (unchanged) | 8,184 | 8,192 | 8 |
| Delegator `SKILL.md` (unchanged) | 4,094 | 4,096 | 2 |
| Delegator `references/snapshot.md` | 6,895 | 8,192 | 1,297 |
| Grok Bot bridge | 2,555 | 2,560 | 5 |
| Grok Bot installation guide | 7,965 | 8,192 | 227 |

The main entry adds one 82-byte sentence; source sizes and bridge manifest size
(830 bytes) are recorded in `byte-sizes.json`. #246's future omitted-wait default
and shared role-entry wording are absent. Budget contention remains visible.

## Guidance review and Host handoff

The new on-demand reference covers the four minimal-design points: bounded
source-first reading; independent source pointers including goal/stop and
relevant archived follow-ups; scoped receipt and four finding classes with
unknowns; Host decision/state ownership and the existing Sidekick lifecycle.
Later explicit corrections win; completed ledger outcomes stay immutable.
Trusted Delegator records remain usable without a raw transcript. Pending relay,
genuine in-flight work and current acceptance coverage are not missing duties.
No findings establishes only the checked scope; vanished unrecorded duties
cannot be reconstructed.

The final design consensus supplies existing wording examples, not a live
acceptance claim: R1'/R2' illustrates source-visible omission; #245/#247 later
corrections illustrate precedence; F5 illustrates unavailable sources; F6
illustrates unsupported completion. F1's pending relay and F4's covered
acceptance subclause were withdrawn as omissions. Sufficient unchanged scope or
an in-flight check is reused.

Scheduling reuses the existing Delegator `cadence`, `timer_owner` and static
Skill/project entry. That already provides recurring independent inquiry and
allows a plain-language request through the sole Host; the interval is an
opportunity, not an unconditional Sidekick dispatch or failure test. A
JSON-driven script is explicitly compared as a replacement for the single timer
carrier where native timing is insufficient, with ownership, wakeup, monitoring
and duplication costs. No evidence requires a new script here.

After the candidate exists the Host runs the bounded read-only Sidekick check
using the exact candidate guidance and existing records, demonstrates a
source-visible omission (a prior snapshot may be used without corrupting live
state), records its decision and any remaining duty in original state, and
reclaims the finished Sidekick. Host acceptance, outer integrated-prompt audit
and finalization remain pending. This run has not written either `.kaola` JSON.

## Historical attempts

`validation-before-scope-correction.md` retains the initial commands and receipts,
including the 8,225-byte pointer failure and pinned-stage failures. The pointer
was shortened before final rendering. The owner's correction allowed the
normal content-stage pin bookkeeping, so those pin failures are resolved in the
final candidate. The initial constrained-render command remains historical;
the final candidate was produced by the unmodified normal renderer.

## Full-suite result and limits

`validate.log` records one failing assertion at
`tests/contract/test-issue-244-dispatch.py:882`: expected `start-timeout`, got
`status-timeout`. The fixture has a 0.2-second Runner timeout. The same failure
reproduces both in an isolated candidate test and on unchanged parent checkout
`c47daa1e`; its cause has not been repaired or reinterpreted in this guidance
issue. Full validation remains exit 1, not a PASS. No assertion was weakened.

The suite reports Bash 3.2.57 lacking Bash >= 4 `mapfile`/`BASHPID`: watchdog
monitoring is explicitly skipped, and the two watchdog monitor/kill tests have
named prerequisite skips. All other suites completed. Cleanup reports
`matched_pids: []` and `residual_pids: []`. Per-platform real CLI smoke and the
issue's actual bounded Sidekick check were not run because this assignment
forbids a new real agent session and reserves that check to the Host after the
candidate exists. Existing mock integration checks ran inside normal validation.

All tracked candidate bytes are committed in `5bbbe6ab`; QA receipts are
untracked in this worktree and were not included in the guidance commit. The
main checkout's four protected untracked harness documents remain present, and
#245/#247 worktrees were not edited. #246 was not claimed or implemented. No
push, merge, finalization, release, tag, installation or live `.kaola` write
occurred. The #249 claim stays active for the Host's acceptance.
