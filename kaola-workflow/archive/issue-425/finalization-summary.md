# Finalization Summary — issue-425

## Delivered

KPR L1 PREVENT writer invariants per the adopted dual-Expert settle
(`owner-hb-prevent-dual-expert-settle-20261029`; settle §2 wording, §4 matrix):

- **P1** — the state writer never stores `stage: done`. The Host terminal
  write (verdict `accepted`/`cancelled` + exactly one `--cite` evidence
  reference) DELETES the row in the same revision; the receipt keeps outcome
  and cite; no tombstone or audit store. Live-list precondition (live seat or
  unreadable list refuses and changes nothing); missing historical dispatch
  refs are listed `unknown` without index reconstruction; real closeout duties
  are retained; `keep_open` gives no exemption.
- **P3 + A2** — every decoded string value in task/hold/alert/decision rows is
  bounded to 512 UTF-8 bytes (nested object values and array string elements
  included; `project`/`authorization` exempt). Over-limit touches return
  `field-too-large` with path, actual bytes, limit and a correction direction;
  no truncation, no overflow store; the writer and the read-only checker share
  the constant and field scope. Touch tracking follows **value identity
  through `union_dispatch`** into merged positions — a touched field must land
  in bounds; untouched legacy offenses stay read-only-check findings.
- **A1** — a `dispositions` key must name an entry in the same task's
  `dispatch`; the check runs on the MERGED relation and refuses an orphan this
  write introduces or re-asserts (`disposition-orphan`); a null repair removes
  keys; settling an item removes ref and disposition in the same write. The
  mechanical rule is the orphan relation only — no sham classifier (judgment
  stays with the Host/Delegator per settle J).
- **P5** — enforcement independent of maintenance state; row-scoped validation
  (a legacy invalid row blocks neither other rows' writes nor its own repair
  or terminal deletion); no grandfathered PASS; receipts carry operation
  outcome, not a full snapshot; no global gate, scanner or truncation.

Agreed removals honored: no separate P2 code, no P4 migration (load does not
rewrite rows), no R1/R3/R4 extras, no caps, no classifier. Docs aligned
(`templates/orchestrator/references/lifecycle-state.md`, `heartbeat-skeleton`);
CHANGELOG Unreleased updated; contract suite
`tests/contract/test-issue-425-prevent-invariants.py` (26 tests) registered in
both validate.sh groups; rendered copies in-commit.

## Candidate

- Branch `workflow/issue-425`: `9e3684a2` (initial) → `9a87190c`/`94e686c3`
  (docs) → `adbb9ad9` (Host rebase onto #427) → `6cef8702` (four settle
  deviations closed) → `5e639a7a` (docs pointer) → `28887fa0` (union
  value-identity touch tracking). Base lineage: main `e709bd39` → `46629e47`.

## Evidence

- Suites on `28887fa0`: 425:26 / 427:21 / 426:53 / 421:45 / 412:31 / 372:13 /
  397:27 all exit 0; `render-skills --check` exit 0.
- Expert review (codex/astra), three bounded rounds: round 1 FAIL (four
  settle deviations), round 2 FAIL (one union-index regression), round 3
  **PASS** — the three repro rows correct, 10 probes, preview consistency,
  duplicates dedup, no-op early return. One owner escalation per task-failure
  (grok seat after two repair verdicts → devin completed the union fix).
- Live P1 proof during closeout: this run's own acceptance write was first
  refused by the new invariant (stage done not storable) and completed through
  the terminal-delete path with a real cite — the mechanism works on its own
  run.

## Known failures / unverified scope

- Reviewer residual limitations (intentional per settle): untouched legacy
  offenses remain permitted until repaired or terminally deleted; disk
  persistence inspected, not executed, under read-only review.
- Installed-skill enforcement and KPM-side mirrors are separate adoption
  steps (KPM #903–#906 dual-linked; Muse's P6 operates read-only meanwhile).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/kaola-record-contract.py
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/test-issue-372-stale-collect-retire.py
- tests/contract/test-issue-397-retire-deadlocks.py
- tests/contract/test-issue-412-maintenance-owed-retire.py
- tests/contract/test-issue-421-retire-recovery.py
- tests/contract/test-issue-425-prevent-invariants.py
- tests/contract/test-issue-426-retire-legacy-seats.py
- tests/contract/test-issue-427-collect-binding.py

## Follow-Up Items

- #421 (L2 cleanup home) — KPR-side close-out follows this merge (serialized
  writer order honored: #427 → #425 → #421).

## Final readiness

Ready: mission ledger closing with this summary; candidate frozen at
`28887fa0`; issue #425 acceptance basis met (settle §2 conformance over three
review rounds, §4 writer rows covered by the 26-test suite, final check PASS);
sink = merge to main, close #425, archive/sink on -dev.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-425/.cache/final-validation.md
- kaola-workflow/archive/issue-425/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-425/doc-docking.md
- kaola-workflow/archive/issue-425/finalization-summary.md
- kaola-workflow/archive/issue-425/mission-ledger.jsonl
- kaola-workflow/archive/issue-425/workflow-state.md
