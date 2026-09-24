# Finalization summary — issue-154

Pure investigation (read-only, evidence-first) for Issue #154 "Investigate: Studio ZCode 3.14.3 vs
pin CLI 0.16.9 + ACP adapter fitness (Pink)". Verdict **A — no pin/adapter change**, Host-accepted
2026-09-24. No release cut, no CLI upgrade, `~/.dsh` untouched, Host session untouched, no
follow-up Delivery issue under A.

## Delivered

- **A/B/C verdict: A** with live + upstream evidence, posted as the issue verdict comment
  https://github.com/KaolaBrother/kaola-project-runner/issues/154#issuecomment-5805849171
  and recorded in the gitignored local receipt `.kaola/diag-zcode-acp-2026-09-24.md`.
- Four desk surfaces concluded: (1) compact busy windows — adapter's concurrent-prompt refusal
  (Issue #65 guard) live-verified (`prompt-in-progress`, `active_turn_request_id` preserved); no
  queue layer needed for Agent-driven transport; (2) `usage_update` — live-measured both backend
  shapes (per-request `session.updated`, turn-cumulative `turn.completed` with
  `modelRequestCount`); the #228 conflation class exists on the recorded stream but the holder's
  occupancy consumer (`used`/`size`) reads nulls — no consumer misled, no meter rendered;
  (3) boot-resume handshake — upstream TUI/Hub surfaces N/A-by-design for the headless adapter;
  ACP-equivalent early-return-settle invariant holds (every prompt path responds); resume
  live-verified via continue picker (`sess_527c8eed-…`, model preserved); (4) standing re-verify —
  turn attribution PASS, model lists PASS, history/list PASS-with-note, permission replies remain
  contract-tested only (yolo raises none) — standing item.
- Upstream/channel evidence: `william0wang/zcode-acp` latest **v0.47.10** (npm
  `zcode-acp-server@0.47.10`, no 0.48.x); verbatim 0.47.0–0.47.10 notes + PR bodies
  (#244 `c5cbac1`, #247 `cb496f7`, #255 `58fbbe5`, #257 `11c3688`/#228, #249 `a22d206`,
  #259 `83bd091`); no newer ZCode CLI than 0.16.9 exists; App 3.14.1→3.14.3 moved at constant CLI
  0.16.9; App update feed base found (`cdn-zcode.z.ai/zcode/electron/releases`), no public
  channel manifest (NoSuchKey/403) — recorded unverified.
- Digest-path discrepancy recorded: the desk-named digests were absent at dispatch
  (Host-verified); during the run #153 finalized and merged (`7d8bce7`, sink `e147059`), so the
  KPR copy now exists in main; KW copy still absent. Cross-referenced read-only; no #153-scope
  file edited.
- Live probe receipts preserved: diagnostic session `zcode-KPR-diag-acp-probe` (no issue number)
  at scratch repo `/tmp/kpr-i154-diag-repo`; record root `/tmp/kaola-i154-diag/` (events log
  `zcode/zcode-KPR-diag-acp-probe/72c8bb3e46051b59/events.jsonl`, 18010 B; raw outputs
  `/tmp/kaola-i154-diag/*.out`); exactly stopped twice, `residual_pids []`, no strays.

## Files Changed

None. Zero repo file changes; the finalize transaction reports `changed_paths: []` and
`implementation_commit: not_applicable`. The empty run branch `workflow/issue-154` was
fast-forwarded to the validated main tip `e147059` (no commits created or rewritten) so the
validation receipt binds a passing tree. The `.kaola` receipt is gitignored local evidence by
design.

## Test Coverage

No production bytes changed, so no new tests are owed. Existing coverage that guards the surfaces
this investigation examined: `tests/contract/test-zcode-acp-contract.py` (adapter translation
contract against the fake app-server), `test-issue-65-host-contract.py` / steering and lifecycle
suites — all green in this run's full `./scripts/validate.sh` (281 rows ok, 0 FAILED/ERROR,
machine prerequisites missing → named skip receipts per #151). Live probe evidence covers the
desk surfaces directly (see Delivered).

## Validation

Candidate: `workflow/issue-154` == main tip `e147059` (main == origin/main), worktree
`.kw/worktrees/issue-154`, clean. Validation receipt:
`kaola-workflow/issue-154/.cache/final-validation.md` — `verdict: pass`,
`validated_candidate_hash 4d0d89e4eae4fe9227fe825db3677a96a24e442f7379593d10d0e31b1b595dbc`,
command `./scripts/render-skills.py --check (rc=0)` and `./scripts/validate.sh (rc=0)` run
separately from the worktree. Logs preserved: `/tmp/kaola-i154-diag/validate-issue154-aligned.log`
(validate rc=0, 281 rows ok) and the render receipt inline. Honest caveat: at the pre-ff base
`db54017` both commands exited rc=1 solely on the grok-bot pin gate (post-pin content
`kaola-workflow/release/validate-v0600.log` beyond R `2504be21`) — a pre-existing release-cycle
state unrelated to this run's zero changes, cleared by #153's content-stage reset on main.

## Changed Paths

(none — finalize transaction `changed_paths: []`)

## Documentation Docking

DOCKED — see `kaola-workflow/issue-154/.cache/doc-docking.md`. No public behavior changed; no
README/CHANGELOG/docs surface requires an update. The verdict record lives on the issue comment
(forge) and the gitignored `.kaola` receipt (local evidence), per the issue's acceptance.

## Follow-Up Items

Standing items (recorded on the issue comment; no follow-up issue required under A unless the
desk asks): (1) real compact-window live trigger — future live probe, next zcode long-run owner;
(2) permission-mode live probe (`interaction/requestPermission` replies live) — future live probe;
(3) App channel manifest — unverified from this network, no action. No defects filed.

## Measured

- App 3.14.3 / CLI 0.16.9 / adapter 0.3.3 — measured 2026-09-24 at main `e147059` era via
  `defaults read … CFBundleShortVersionString`, `node zcode.cjs --version`, and probe preflight
  receipts (`/tmp/kaola-i154-diag/*.out`).
- Probe wire facts — measured on the live session by the probe receipts above (usage shapes,
  busy refusal, steer drain evidence, resume identity).
- Upstream release facts — measured 2026-09-24 via authenticated `gh api
  repos/william0wang/zcode-acp/{releases,pulls,issues}` and `npm view`.

## Hypothesis

(none — no unconfirmed attribution is carried; the two semantic gaps vs upstream 0.47.x are
recorded as verified facts about the Runner adapter's design, not as suspected defects)

## Readiness

Ready: accepted (Host acceptance granted), validated (receipt above), archived by the finalize
transaction, issue closed referencing the verdict comment and the `.kaola` receipt. Sink not
applicable (empty branch, Host-directed no sink-merge).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-154/.cache/doc-docking.md
- kaola-workflow/archive/issue-154/.cache/final-validation-record.json
- kaola-workflow/archive/issue-154/.cache/final-validation.md
- kaola-workflow/archive/issue-154/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-154/finalization-summary.md
- kaola-workflow/archive/issue-154/mission-ledger.jsonl
- kaola-workflow/archive/issue-154/workflow-state.md
