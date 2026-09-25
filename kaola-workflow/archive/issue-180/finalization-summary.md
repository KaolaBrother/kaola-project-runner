# Finalization summary — issue-180

## Delivered

Issue #180 implemented to its acceptance, reviewed, repaired, and re-reviewed.

1. **`pre_spawn_refusal` is the single start-decision site.** It returns
   `(refusal, facts)`: the refusal receipt, or `None` with the worker Skill
   alignment, the main alignment (`None` unless the worker alignment
   applies), `hostish`, and the heartbeat resolution in `facts`.
   `command_start` reuses them; its five mirrored refusal branches
   (worker-skill root/skew, main-skill skew, ZCode Host model request,
   heartbeat host) could never fire — `pre_spawn_refusal` ran first on the
   same args in the same process with only pure filesystem/args reads between
   (#169's determinism argument) — and are deleted.
2. **Installed Skill roots hashed once per start.** A call counter proves
   `worker_skill_alignment` runs exactly once per `start` and twice per
   `drain-restart` (down from three): the stop is a state boundary, so the
   post-stop start re-decides on post-stop state instead of reusing pre-stop
   facts — the reason issue scope item 3 asked to be recorded when the second
   call is kept.
3. **The `--version` probe is off the refusal path (folds #171, resolves
   #172).** A refused `start`/`drain-restart` never runs the runtime
   `--version` (the old probe bound was 15 s), keeps its bridge and
   runtime-binary facts minus `version`, and `preflight` still reports
   `version`. `bridge_runtime_error`'s "does not spawn, write, or search
   PATH" is exactly true of its refusal caller too, and no comment on the
   refusal path claims `--version` or preflight parity.
4. **Receipt shape preserved.** `worker_skill_build`, `worker_skill_roots`,
   and `main_skill_build` keep their exact values in all three cases
   (aligned, unaligned hostish start, neither) after the repair merged the
   two build-fact branches; every refusal reason and receipt is otherwise
   unchanged, including the drain-restart pre-stop refusal leaving a live
   seat up.

Candidate: workflow/issue-180 @ 36d765f, directly on main 8ab96d7 (no rebase
owed; origin/main unmoved at finalize time).

Acceptance: independent Claude Code review — round-1 verdict FAIL on one
paperwork item only (net-lines +204 vs the required net-negative; every
technical point confirmed correct) — then the repair (counter test folded
into the #164 suite, the standalone suite and its validate.sh registrations
deleted, the CHANGELOG entry cut 26→12, `command_start` trimmed: `hostish`
reused from facts, the two build-fact branches merged, docstring and
comments shortened, no behavioral assertion weakened) — then **VERDICT: PASS
for issue #180** on repair commit 36d765f.

**Amended acceptance, item 6 (net-negative LOC, source + tests + docs,
generated copies excluded):** the production source is net-negative —
`scripts/kaola-acp.py` **−14 lines** (35 added / 49 removed) vs base 8ab96d7 —
while the mandated acceptance tests bring the total positive: **+105**
(`tests/contract/test-issue-164-pre-spawn-bridge-facts.py` +107 — the #171
hanging-`--version` latency proof, the refusal-facts-minus-`version`
coverage, and the folded #180 call counter; `CHANGELOG.md` +12;
`scripts/validate.sh` byte-identical to base). Round-1 arithmetic: +204 with a
standalone 129-line counter suite; the review's repair list removed 99 net
lines and cannot go further without deleting assertions the review explicitly
required to keep. The PASS verdict was granted with this breakdown, recorded
on the issue before close.

Acceptance legs: automated — full `./scripts/validate.sh` green at rest on the
frozen candidate (exit 0, 0 FAILED; log /tmp/kpr-i180-validate3.log), plus
focused 164 (7/7, including the folded counter), 119 (11/11), and 74.
Local/manual/UAT — none owed: an offline consolidation inside one script
plus its contract suites; no live platform CLI behavior is claimed beyond
the refusal receipt's `version` key, which the #164 suite proves.
Unexecuted — none.

Review PASS and the amended net-lines breakdown recorded on the issue before
close (issuecomment-5837707715).

## Files Changed

- `scripts/kaola-acp.py` (+35/−49): `pre_spawn_refusal` returns
  `(refusal, facts)` with `hostish` in the facts; the five unreachable
  refusal branches and the recomputation deleted from `command_start`; the
  two Skill-build fact branches merged into one (receipt shape preserved);
  the refusal path calls `bridge_facts(args)` without the version probe;
  comments made exactly true.
- `tests/contract/test-issue-164-pre-spawn-bridge-facts.py` (+110/−3):
  refusal facts equal preflight's minus `version` (rebuilt-dict helper), the
  hanging-`--version` latency proof for both refusals, and the folded
  `worker_skill_alignment` call counter (1 per `start`, 2 per
  `drain-restart`, `MOCK_ACP_RESUME_ANY` resume replay).
- `CHANGELOG.md` (+12): the Unreleased entry (consolidation, the
  `--version` refusal-path drop superseding #171/resolving #172, Seats:
  restart not required from the empty operator test).
- `skills/**` (10 copies): rendered copies of `scripts/kaola-acp.py`,
  regenerated by `render-skills.py --write`, `--check` PASS byte-identical.
- `tests/contract/test-issue-180-start-decision.py`: created round-1
  (+129), deleted by the repair; never lands in the merge.
- `scripts/validate.sh`: +2 registration lines round-1, removed by the
  repair; byte-identical to base in the merged candidate.

Net excluding rendered copies: **+157/−52 (+105 lines)** — production source
**−14**; the mandated tests bring the total positive. See Delivered for the
amended acceptance and the recorded arithmetic.

## Test Coverage

`tests/contract/test-issue-164-pre-spawn-bridge-facts.py` holds all three
#180 proofs: the refusal facts equal preflight's minus `version` (start,
drain-restart, and ZCode-runtime refusals), the hanging-`--version` mock
proves both refusals return well under the old 15 s bound with the live seat
left up, and the in-process call counter proves `worker_skill_alignment`
runs once per `start` and twice per `drain-restart`. #122/#132
host-entry/host-exists coverage stays green in its own suites.
Full-suite green at `/tmp/kpr-i180-validate3.log`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-164-pre-spawn-bridge-facts.py

## Documentation Docking

DOCKED — `.cache/doc-docking.md`: CHANGELOG updated; `docs/api.md` checked —
its `runtime_binary` fact list already scopes the `--version` line to
`preflight`, exactly true after this change, and the `drain-restart`
pre-spawn paragraph is unchanged in meaning; README, docs/architecture.md,
docs/conventions.md, and docs/zcode-host.md checked with no impact. Rendered
copies regenerated, `--check` PASS.

## Follow-Up Items

None filed. No run-discovered defect fell outside this issue's scope: the
round-1 net-lines finding was in-scope paperwork and was repaired in the
repair commit rather than deferred. #171 and #172 are folded into this
merge and close with it.

## Readiness

Ready. All four missions done (ledger 4/4 done), final validation pass, docs
docked, review PASS on the repaired candidate, no rebase owed (the branch
sits on current main 8ab96d7). Sink: merge of workflow/issue-180 to main,
closing #180; no PR, no release, no tag, no pin.

## Finalize Findings

### residue_unattributed

The `chore: finalize` commit did NOT carry the paths below: this branch's
own commits touch no file in their directories, so the transaction has no
evidence they are this run's work. Nothing was committed, reverted or
deleted — they are exactly where they were. Read them before the sink runs:
commit what belongs to the run, remove what does not.

Paths not attributed to this run:

- .cache/

Resolution before the sink: `.cache/doc-docking.md` (this run's docking
evidence, written into the candidate worktree) is placed into this archive's
`.cache/`, matching the archived shape of issue-179's run; the worktree
`.cache/` leftover is removed. The `chore: finalize issue-180` commit —
which carried `finalization-summary.md` at the worktree root because the
summary was authored there instead of the main run folder — is dropped from
the unpushed branch so the sink merges exactly the reviewed candidate
36d765f and the freshly recomputed code-tree hash stays bound to
`validated_candidate_hash` bb9ffaff237163bd828c49d6696284f51e118f56ca0c34e7698766ea83a46527;
this file is the summary's durable home, with the transaction's measured
`## Validation` and `## Changed Paths` sections filled in above.
