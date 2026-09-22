# Finalization Summary — issue-130

## Delivered
#130 "Retire PTY unconditionally — ACP only; fail-closed; no dual transport" per Fable design
comment 3 (owner-accepted). kaola-tmux.sh refuses any `--transport pty` on every command with the
typed `transport-pty-retired` receipt before #73/#104/manifest/Git and before any process or
record; tmux branch, relay trio, kaola-observation.py, transport.md, default_transport removed;
#104 PTY gate absorbed; #8 model-policy guarantees re-homed to ACP (ModelPolicyOnAcp); inherited
KPR_CANONICAL_REPO dropped on entry.

Accepted candidate e42be2a (Host ACCEPT with disclosure). Integrated by merge commit 84b5938
(tree 42db26ad; Host ruling A): main 428e7bb (#133) merged with mechanical resolutions
(CHANGELOG both entries, README, validate.sh suite union, regenerated main-skill-build.json) plus
removal of the trailing blank line e42be2a left at EOF of templates/references/steering.md.tmpl.

## Files Changed
e42be2a vs 16b42b2: 251 files, +2800/-40639 (scripts, templates, platforms, generated skills,
tests, docs). 84b5938 adds the integration resolution only.

## Test Coverage
New tests/contract/test-issue-130-pty-retired.py (44 tests: typed refusal matrix all platforms x
commands, ordering, ModelPolicyOnAcp 10/10). Mixed suites rewritten ACP-only (incl.
test-issue-73 31 OK, test-issue-51 6/6). 24 PTY-only suites + fixtures + tests/lib deleted;
validate.sh lane C removed.

## Validation
- final: `./scripts/render-skills.py --check` rc=0 and `./scripts/validate.sh` rc=0 on 84b5938
  (tree 42db26ad): 40 unittest OK blocks, no FAILED/SKIPPED, grok-bot-verify PASS; logs
  .cache/final-render-84b5938.log, .cache/final-validate-84b5938.log; record .cache/final-validation.md
  (validated_candidate_hash 7c506343f9db7b2299147aa8ccf7b88f597541c55d91e34d9d8377df36dbaf0c)
- candidate gate on e42be2a: render rc=0, validate rc=0 (mission 6)
- independent review: code-reviewer VERDICT ACCEPT on e42be2a (.cache/review-e42be2a.md);
  Host independently re-checked and accepted with disclosure
- unexecuted: live ACP smoke per platform; installer copy-mode removal of stale transport.md /
  relay scripts from existing install roots

## Changed Paths
(finalize transaction output recorded below when it runs)

## Documentation Docking
DOCKED — .cache/doc-docking.md

## Follow-Up Items
- L5 (owner acknowledgement pending): fifth declared #8 loss — status/observe no longer carry
  model provenance and model_verified true/false verdict (always unknown); design §5 listed four
- L2: `unset KPR_CANONICAL_REPO` in kaola-tmux.sh has no test pin
- L3: "outbound text is redacted" claim in AGENTS.md / worker template overstated (only
  kaola-zcode-acp.py redacts)
- §7 follow-ons: adapter slimming (unreachable frame helpers naming kaola-observation.py),
  locator tmux probe → holder fact, entrypoint rename
- Gate gap: validate.sh `git diff --check` only inspects uncommitted changes, so committed
  whitespace errors (the steering.md.tmpl EOF blank line) pass the gate
- Not filed as forge issues in this finalize (Host directed recording them on the #130 closure
  comment)

## Status
READY — accepted, validated on the integrated head; closure: close #130.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-130/.cache/doc-docking.md
- kaola-workflow/archive/issue-130/.cache/docs-handback.md
- kaola-workflow/archive/issue-130/.cache/final-validation.md
- kaola-workflow/archive/issue-130/.cache/merge-resolution-428e7bb.patch
- kaola-workflow/archive/issue-130/.cache/mirror-digest.json
- kaola-workflow/archive/issue-130/.cache/model-policy-map.md
- kaola-workflow/archive/issue-130/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-130/.cache/review-e42be2a.md
- kaola-workflow/archive/issue-130/finalization-summary.md
- kaola-workflow/archive/issue-130/mission-list.md
- kaola-workflow/archive/issue-130/workflow-state.md
