# Finalization Summary — Issue #98

project: issue-98
issue: #98 — dsh (DeepSeek Harness) as the tenth Project Runner worker, ACP transport only
branch: `workflow/issue-98`
baseline: `main` @ d300c7a
candidate: `27f3fe6`
sink: merge
date: 2026-09-20

## Delivered

**dsh 0.1.5-rc.2 is the tenth Project Runner worker platform, ACP only.** The change is a manifest,
an adapter, the roster registrations, and two shared receipt fixes — no bridge, no proxy, no
translator, and no new transport code, because the holder already branched on
`agentCapabilities.sessionCapabilities.resume` and already sent `configId`.

Every platform fact was measured against the running binary before it was written down. Four depart
from the OpenCode template that this issue named as its reference shape, and each departure is
backed by a verbatim frame in `evidence/raw/`:

1. **Resume is `session/resume`, not `session/load`** — `session/load` answers `-32601`. Confirmed
   live by resuming session `e1995cb7-…` from a fresh process; no holder change was needed.
2. **`--continue` is unsupported** — `session/list` carries no `updatedAt`, so `latest_session()`
   answers `continue-ambiguous` even for a single session. Recorded `continue_syntax: unsupported`
   instead of advertising a flag that cannot work.
3. **There is no approval gate at all** — not OpenCode's "no skip-all". Zero
   `session/request_permission` across two tool turns, including a bash write to an absolute path
   outside the session workspace, which succeeded unattended. `session/set_mode` is `-32601` and
   there is no `mode` option, so there is nothing to skip and, with no terminal UI, nothing to
   bypass either.
4. **The shipped `acp` profile pins the unauthenticated `deepseek-official` route** and ignores the
   user's `agent-default-model`, so `session/new` reaches `ready` and only the first prompt fails
   `-32603 … no API key`. `acp_model_map` is the escape hatch; `["opencode-go","deepseek-v4.1-flash"]`
   answered live in 2.52 s.

Native steering is unsupported (all four candidate methods `-32601`), but `session/cancel` settles
in **0.01 s**, so the existing composite `--steer-mode interrupt` works at the default timeout.

Two shared-code fixes came out of the work and affect **every** platform's receipts, not just dsh:
`config_option_choices()` in `kaola-acp-holder.py` expands grouped select options one level (dsh is
the first platform to ship them, and without this a grouped platform silently lost
`value_name`/`value_description` from its selection receipt), and `acp_value_params` in
`kaola-acp.py` guards JSON-array descriptor values.

`~/.dsh/` was never written by this run: 16/16 config files byte-identical before and after, checked
at every phase.

## Files Changed

86 files, +10918 / −152, across three commits:

- `cb689a7` — the platform (manifest, adapter, roster, regenerated Skills)
- `45f6c68` — the review repairs (measured evidence, both grouped-option sites, guards)
- `27f3fe6` — finalize documentation docking

| Area | Count | Notes |
|---|---|---|
| `skills/` | 55 | generated output; 12 are the new `dsh-kaola-project-runner` package, the rest are the shared-script propagation of the two holder/acp fixes to all ten workers plus `skills/kaola-project-runner/SKILL.md` |
| `tests/` | 14 | 1 new suite, 13 re-counted or extended |
| `scripts/` | 10 | 1 new adapter, 2 behaviour changes, 7 pure roster registrations |
| `docs/` | 3 | `api.md`, `architecture.md`, `conventions.md` |
| root | 3 | `README.md`, `AGENTS.md`, `CHANGELOG.md` |
| `platforms/` | 1 | `platforms/dsh.yaml` |

`templates/grok-golden/` and `hosts/grok-bot/` are **byte-unchanged** against `main` (empty diff),
as the frozen-template contract requires.

## Test Coverage

- **New suite `tests/contract/test-issue-98-dsh-acp.py`** — 24 tests in 5 classes, wired into
  `validate.sh`. Covers both changed shared functions (which had **zero** test references repo-wide
  before this run), the dsh manifest against the measured ACP frames, every roster registration,
  and that the adapter never writes under `$DSH_HOME`. Proven **RED with 15 failures** against the
  pre-fix implementations, green with them.
- **New class `DshHasNoApprovalGateAtAll`** in `tests/contract/test-issue-88-permission-defaults.py`
  (suite now 41 tests). The pre-existing roster check was satisfied by the word "dsh" appearing
  anywhere in `README.md`; the reviewer demonstrated that softening the paragraph into OpenCode's
  weaker "no skip-all" shape kept the suite green. The new class pins the claim on all three
  surfaces, requires it inside the operator brief itself, and rejects OpenCode's shape near `dsh`.
  Mutation-proven: the reviewer's exact softening fails 2 tests; the real text passes 41/41.
- **Roster reconciliation, nine → ten**, across 13 suites, changing counts without weakening any
  assertion's intent. Five test files carried their own `WORKER_IDS`; two installer suites built
  fixtures from a hardcoded id list and were the first failures, because a missing
  `skills/dsh-kaola-project-runner` made the installer refuse.
- **Live tmux ACP smoke through the generated Skill's own scripts**, session `dsh-KT-i98-smoke`:
  preflight → start → send → capture → steer → stop, ending `residual_pids []`. Receipts
  `evidence/live/01..10`, narrative `evidence/live-smoke.md`.

## Validation

- **command:** `env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE ./scripts/validate.sh`
- **verdict:** `pass` — `VALIDATE_EXIT=0`
- **at candidate:** `27f3fe6`; `validated_candidate_hash`
  `89bccad412488db78d69a3e1bf59e1bb9fc2365761eadf8c3c3b69c73c9c58b9`
- **result:** 680 tests, **0 FAILED, 0 ERROR, 0 RED, 0 skipped**
- **render:** `./scripts/render-skills.py --check` PASS —
  `10 workers + kaola-project-runner + kaola-delegator + grok-bot host`, budgets OK
- **log:** `evidence/validate-finalize-27f3fe6.txt`; receipt `.cache/final-validation.md`

Acceptance legs:

| Leg | Status | Evidence |
|---|---|---|
| Automated suite | PASS | above; and the run's own `evidence/validate-final.txt` at `45f6c68` |
| Local live (real binary, through the generated Skill) | PASS | `evidence/live-smoke.md`, `evidence/live/01..10`, `residual_pids []` |
| Independent review | PASS, both cuts | two `code-reviewer` subagents on frozen `cb689a7`; 17 findings, every one dispositioned; repairs in `45f6c68` |
| Manual / UAT on a consuming machine | **NOT EXECUTED** | the dsh worker has never been installed or driven on a machine other than this one |

Two honest qualifications on the `env -u`:

- `tests/contract/test-zcode-acp-contract.py::test_resolve_runtime_fails_closed` fails whenever
  `KAOLA_ZCODE_ENTRY` / `KAOLA_ZCODE_NODE` are exported, because the test does not clear them. This
  is **pre-existing and unrelated to dsh** — reproduced on a clean `main` checkout at d300c7a. The
  exit-0 runs cleared exactly those two variables and nothing else. It is reported, not hidden, and
  not repaired here because it is outside this issue.
- The first finalize `validate.sh` **hung for 13 minutes** in `install-local.sh` and was killed
  (`VALIDATE_EXIT=143`). This is the intermittent hang PR #100 already flagged as unreproduced;
  this run captured the first live process evidence for it. It is **not** caused by this change —
  the hang was in the `grok` platform on an invocation that did not include `dsh`, and the
  installer diff is three pure roster registrations (`+5/−2`). Three standalone re-runs of the
  suite and the full re-run all passed. Captured in `evidence/finalize-installer-hang.md`, filed
  as **#101**.

## Changed Paths

Reported by the finalize transaction (source-scoped; it does not list `README.md`, `CHANGELOG.md`,
`AGENTS.md` doc-only edits or `docs/`):

- `platforms/dsh.yaml`, `scripts/adapters/dsh.sh` — the new platform
- `scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py` — the two shared behaviour changes
- `scripts/install-local.sh`, `scripts/kaola-grok-bot-verify.py`, `scripts/kaola-locate.py`,
  `scripts/kaola-model-policy.py`, `scripts/kaola-tmux.sh`, `scripts/render-skills.py`,
  `scripts/validate.sh` — roster registrations
- `skills/dsh-kaola-project-runner/**` (12 files, generated) plus the shared-script propagation into
  the nine existing worker packages and `skills/kaola-project-runner/SKILL.md`
- `tests/contract/**` — 1 new suite, 13 re-counted or extended
- `AGENTS.md`
- `dirty_paths: []`

## Documentation Docking

`DOCKED` — evidence `.cache/doc-docking.md`.

Missions 4 and 6 docked `README.md`, `AGENTS.md`, `CHANGELOG.md`, `docs/api.md` and
`docs/architecture.md`. This finalize pass found `docs/conventions.md` still counting **nine**
worker Skills in three present-tense statements — the change-boundary paragraph, the source-of-truth
entry for `templates/SKILL.md.tmpl`, and the issue-scoped dispatch rule — and docked all three to
ten in `27f3fe6`. The remaining "nine" mentions repo-wide are historical `CHANGELOG.md` entries,
archived run evidence, and two test comments where nine is the correct count of the *other* workers
beside dsh; none was rewritten, because each states what was true when written.

## Follow-Up Items

- **#101** (bug, P2) — `validate.sh` intermittently hangs in `install-local.sh` `place_staged`;
  self-held here-document pipe under bash 5.3. Filed with the captured process tree, descriptors,
  and fixture state; cause is recorded as hypothesis, not fact, and the proposed remedy is labelled
  non-binding. Confirmed OPEN with a non-empty body (4290 B).
- **Correction posted on #98 before closure** —
  [comment 5743598669](https://github.com/KaolaBrother/kaola-project-runner/issues/98#issuecomment-5743598669).
  Three items: the withdrawn PR-only delivery constraint; the issue's "no ACP skip-all" prediction,
  which understates the measured *no approval gate at all*; and the shipped-README
  `session/request_permission` row, which is documented but never reached.
- **Not carried forward as issues, recorded here:** the dsh worker has only ever run on this
  machine; the `~/.dsh/` acp profile is a documented operator precondition, not something the
  installer creates; and a consuming machine may need
  `dsh --profile acp --from-default-profile <name>`, which *does* write under `~/.dsh/` and which
  this run therefore never ran.

## Delivery route

This issue was claimed under a **PR-only** constraint: branch, open a PR, never merge, no
self-finalize. That was honoured — PR #100 was opened at tip `45f6c68` and nothing was merged. On
2026-09-20 the Host **withdrew** the PR-only instruction and returned delivery to this repository's
normal route: Kaola-Workflow finalize plus merge-sink to `main`. PR #100 is settled as residue
pointing at the sunk commits; it is not the delivery. Missions 1–7 were executed under the original
constraint and none of their recorded results changed.

## Readiness

**READY.** Validation green at the frozen candidate, documentation docked, acceptance legs recorded
with the one unexecuted leg named, run-discovered defect filed as #101, and the issue's own
inaccurate text corrected on the issue before closure.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-98/.cache/doc-docking.md
- kaola-workflow/archive/issue-98/.cache/final-validation.md
- kaola-workflow/archive/issue-98/.cache/mirror-digest.json
- kaola-workflow/archive/issue-98/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-98/evidence/dsh-acp-facts.md
- kaola-workflow/archive/issue-98/evidence/finalize-installer-hang.md
- kaola-workflow/archive/issue-98/evidence/integration-design.md
- kaola-workflow/archive/issue-98/evidence/live-smoke.md
- kaola-workflow/archive/issue-98/evidence/live/01-preflight.json
- kaola-workflow/archive/issue-98/evidence/live/02-start.json
- kaola-workflow/archive/issue-98/evidence/live/03-send.json
- kaola-workflow/archive/issue-98/evidence/live/04-capture.json
- kaola-workflow/archive/issue-98/evidence/live/05-send-longturn.json
- kaola-workflow/archive/issue-98/evidence/live/06-steer.json
- kaola-workflow/archive/issue-98/evidence/live/07-capture-after-steer.json
- kaola-workflow/archive/issue-98/evidence/live/08-stop.json
- kaola-workflow/archive/issue-98/evidence/live/09-start-after-d7-fix.json
- kaola-workflow/archive/issue-98/evidence/live/10-stop-after-d7-fix.json
- kaola-workflow/archive/issue-98/evidence/probes/dsh_acp_probe.py
- kaola-workflow/archive/issue-98/evidence/raw/cancel.txt
- kaola-workflow/archive/issue-98/evidence/raw/handshake.txt
- kaola-workflow/archive/issue-98/evidence/raw/method-surface.txt
- kaola-workflow/archive/issue-98/evidence/raw/outside.txt
- kaola-workflow/archive/issue-98/evidence/raw/profile-templates.txt
- kaola-workflow/archive/issue-98/evidence/raw/prompt-model.txt
- kaola-workflow/archive/issue-98/evidence/raw/prompt.txt
- kaola-workflow/archive/issue-98/evidence/raw/resume.txt
- kaola-workflow/archive/issue-98/evidence/raw/tool.txt
- kaola-workflow/archive/issue-98/evidence/validate-final.txt
- kaola-workflow/archive/issue-98/evidence/validate-finalize-27f3fe6.txt
- kaola-workflow/archive/issue-98/finalization-summary.md
- kaola-workflow/archive/issue-98/mission-list.md
- kaola-workflow/archive/issue-98/workflow-state.md

## Sink receipt (appended after the sink)

The sink ran after this summary was written, so the SHAs cited above are the **pre-sink** ones. The
sink could not fast-forward `main` — another run's `chore: archive issue-99 [sink]` (`78dba05`) had
landed in between — so it **rebased** the three commits onto it and republished them under new ids.
The pre-sink ids remain valid in PR #100's refs; on `main` they read:

| Pre-sink | Published on `main` | Commit |
|---|---|---|
| `cb689a7` | **`b70db19`** | feat(dsh): add dsh as the tenth worker platform, ACP only |
| `45f6c68` | **`d0e19b3`** | fix(dsh): close the Issue #98 review findings — *the accepted tip* |
| `27f3fe6` | **`33a8971`** | docs(conventions): dock the worker count to ten — *the validated candidate* |
| — | **`b3f9dcf`** | chore: archive issue-98 [sink] — this archive |

Each pair was verified with `git patch-id --stable`: **all three patch-ids match**, so the rebase
moved the commits without altering their content.

The validation evidence still binds the published tree. `git diff 27f3fe6 33a8971` is **8 files,
+719/−0, all of them `kaola-workflow/archive/issue-99/**`** — the concurrent run's archive and
nothing else. Zero source, test, skill, or documentation bytes differ between the tree that was
validated at `VALIDATE_EXIT=0` and the tree published on `main`.

- `main` head after sink: **`b3f9dcf`**, local and `origin/main` identical (`git rev-list
  --left-right --count main...origin/main` → `0  0`).
- Issue **#98 closed** by the sink; `remote_closed_after_publish: verified`.
- Branch `workflow/issue-98` deleted locally and on the remote; worktree
  `.kw/worktrees/issue-98` removed.
- **PR #100** was auto-closed (state `CLOSED`, `mergedAt: null`) when the sink deleted its head
  branch, at 2026-09-19T16:47:48Z. It is residue, not the delivery; a closing note on the PR points
  at the published commits above.
