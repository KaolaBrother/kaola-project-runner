# Finalization Summary — issue-324

## Delivered

Delegator FINAL scope (Yanlei 2026-10-14 19:05 Taipei, replaces addenda 30-34), all five points:

1. **Mechanism explanation first** (delivered by the Opus worker before implementation): the Host's
   holder triggers maintenance at every Host turn end / idle check; owed work is (a) Host business
   changes the Sideagent has not handled and (b) a recovery input registered after a verified Host
   compaction. The binding is `state.sideagent` in `.kaola/heartbeat-prompt.json` (node mode:
   `{platform, session, state: active, mode: node, recipe}`); the recipe is the exact Runner argv
   (no shell) for a fresh Sideagent node, and the state tool accepts that node's checkpoint write
   only under a stored active node binding. `binding-or-recipe-unavailable` fired because the
   binding lookup returns the same "nothing" for a missing binding as for a broken one.
2. **Root cause**: the KPR Host never had a binding (`state.sideagent` null since state init, backups
   empty, first input at host_revision 8; no node session record among all 28 records). Every
   legitimate Host state write raised `host_revision`; the next turn end selected it as an owed
   batch and recorded a fresh `batch:<rev>` failure plus a Host wake. The in-memory dedupe keyed on
   `batch:<rev>`, which changes on every write, so it never matched: 75 failures across the two
   event logs, 73 returned inputs (through batch:158, reproduced live during this run). Not version
   skew: the installed holder (#320) has the same branch as main. Secondary defect: the failure's
   evidence pointer named the stream event just before it (batch:157's pointer #42873 was the
   Host's own message chunk; the receipt is at #42876), and all pointers older than log cursor
   24,713 resolve into pruned space.
3. **Fixes** (commits `689391f7`, `0f3c9c73`, plus Host repair `394ac518`): an unbound Host owes
   nothing (no failure, no wake); a configured binding with an unusable recipe fails once (no
   re-queue while its input stays returned); the evidence pointer now names its own event; the node
   runtime is no longer a pin — a missing runner, failed start, or unadmitted batch moves the node
   to the next Worker-class preset the existing dispatch eligibility allows right now (grants,
   exclusions, holds, Delegator ceiling, availability; `zcode/default` first, then by id, never
   retrying a failed runtime; one `sideagent_node_fallback` event per move, no Host turn; an
   exhausted chain records one failure, once). On this install the live chain is empty (every
   Worker preset excluded; `claude-code/haiku` withheld by the Delegator ceiling), and KPR has no
   binding, so it now gets no failure and no turn.
4. **Kept**: the needs_decision fix — `needs_decision` now requires a registered open decision or a
   severe alert; standing Host rows (holds, non-severe alerts such as `maintenance-returned`,
   maintenance duties) wake nothing.
5. **Reverted**: the Sonnet WIP's all-idle changes (self_continuing, latch, tests, docs); the
   all-idle wake ordering and normal queue handling are unchanged.

## Candidate

Branch `workflow/issue-324`, merge base `1aa61f71`: `689391f7` + `0f3c9c73` + `394ac518`
(host repair: the Unreleased CHANGELOG `Seats:` line must be the exact rule phrase for #162).
Candidate hash bound by the recorder: `05c5f25148a481e7663552f11d5dae87e4122511892c37decd5da895950ac48a`.

## Evidence

- Worker seat `claude-code-KPR-i324-rootcause` (claude-code/default, Opus 5.5 high), dispatch fp
  `fd0a44079…`; live field evidence steered (fp `ad28c494…`), final scope steered (fp `45abec8b…`).
- Host verification: full `./scripts/validate.sh` on the branch, 1346 s wall, single failure
  `test-issue-162-upgrade-safety.py` (Seats exact-line rule) → repaired by `394ac518` → that suite
  standalone 27 tests OK on the repaired candidate; `./scripts/render-skills.py --check` PASS.
- Worker's own runs (reused, same candidate bytes except the repaired CHANGELOG line): 9 affected
  suites (324, 255, 259, 293, 298, 299, 302, 315, 320), 309 tests OK; each regression test fails
  with its fix removed (mutation checks). New suite `test-issue-324-wake-fixes.py` (10 tests)
  registered in both validate.sh suite lists.
- Full-inventory log `/tmp/i324-full-validate.log`; validation record
  `kaola-workflow/issue-324/.cache/final-validation.md`.

## Known failures and unverified scope

- The 73 rows the old loop already wrote stay in `maintenance-returned` until the Host retires them;
  their older evidence pointers point into pruned log space (not fixed; the pointer fix is
  forward-looking only).
- Running holders keep the old behavior until restart; CHANGELOG says `Seats: restart required`.
  No install/restart was authorized or performed in this run.
- Fallback runtime choice is in-memory: a holder restart tries the bound runtime first again.
- No live ACP smoke run in this run (no code path requires it beyond suites; restart-time adoption
  is covered by the existing 320/302 harnesses).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/webhook-wake.md
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/webhook-wake.md
- templates/orchestrator/references/sideagent-node.md
- tests/contract/test-issue-302-delegator-wake-gate.py
- tests/contract/test-issue-324-wake-fixes.py

## Follow-Up Items

- Open owner decision (relayed by `kaola-acp wake --reason needs_decision` after merge): whether an
  unbound Host should also be maintained. Today it owes nothing; maintaining it would need
  auto-binding or a looser state-tool writer check. No issue filed (no new KPR issues without owner
  direction); recorded here and in the wake.
- No run-discovered defect remains unfiled: the needs_decision and evidence-pointer defects were
  fixed in this run; the pruned-pointer history is not recoverable by new code.
- searched: duplicate probe `gh issue list --search "binding-or-recipe-unavailable"` → 1 hit (#324
  itself).

## Final readiness

Ready: candidate accepted by Host review (all five final-scope points verified in the diff),
validation recorded pass, no tag/release/install performed or required by this run.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-324/.cache/final-validation.md
- kaola-workflow/archive/issue-324/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-324/finalization-summary.md
- kaola-workflow/archive/issue-324/mission-ledger.jsonl
- kaola-workflow/archive/issue-324/workflow-state.md
