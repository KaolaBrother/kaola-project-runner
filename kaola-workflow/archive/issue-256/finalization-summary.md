# Finalization Summary — Issue #256

## Delivered

Accepted candidate: ef76fe8c4623a41b2eafa897a7942294e1c79cdb.
Host bounded acceptance: /tmp/kpr-i256-implementation-20261004/host-ef76fe8c-verdict.md,
verified in Host comments #2565981741289 and #2555981741534.

Fresh managed OpenCode V2 launch selects a process-only build allow policy through
OPENCODE_CONFIG when no existing config or explicit contrary mode exists.
Existing native/global/project config, resume/continue and custom command defer
the default. Explicit plan maps to native ACP mode; no shared settings, model,
provider or effort override, auto-permit loop, new permission framework or holder
refactor. Benign existing config conservatively also defers the default.

Evidence is retained under /tmp/kpr-i256-implementation-20261004/:
implementation-delivery.md, final-checks.json, candidate.json,
validate-final.log, render-check.log, focused-24.log, focused-88.log,
candidate-native-acceptance.json, raw-event-inventory.json,
raw-and-redacted-inventory.json, native-cleanup-final.json, and raw/ originals.
Host independently verified all nine raw event/capture/post-stop prefix matches,
366 original hashes, nine exact stops and full validation/log hash.

Existing matching validation on the accepted frozen candidate: ./scripts/validate.sh
exit 0; ./scripts/render-skills.py --check PASS; focused #24/#88 25+42 tests PASS.
Nine real native ACP cases prove file-slot read/write/shell/reread (zero permission
events), plan write restriction, global/project/supplied config precedence,
simultaneous independent-session isolation, build-to-plan restriction and exact
held-out shell denial. Native restrictive-tool filtering/model search is distinct
from actual denied tool execution. All permission events accounted; two requests
canceled, zero answers. CLI @opencode/cli 2.0.22 / ACP protocol 1; selected
opencode-go/deepseek-v4.1-flash/default effort, no backend billing attestation.
No repeat tests whose evidence still matches. Earlier research receipts are
derived after original loss and are not candidate acceptance evidence.

All owned QA processes stopped with residual PIDs []; all 32 own native fixture
histories and all own scratch roots removed after preserving originals. No
production restart/login/installation/runtime or shared config upgrade occurred.

## Acceptance and scope

Host accepts bounded #256 and authorizes this same run's merge sink, archive,
issue closure and scoped cleanup. This is lifecycle proof, not #255 integrated QA
PASS. Integration order: #256 publishes first; #255 finishes its current native
measurement then preserves both source changes and regenerates affected products.
No #255 branch/worktree/ledger movement or writes by this owner.

Protected main owner AGENTS edit, four harness docs, archive252 and other active
state must remain untouched and unstaged. The installed mirror declines the four
untracked docs. Tracked AGENTS residue is protected with a scoped temporary main
Git assume-unchanged flag (bytes/hash and original index flags retained in
finalization/preservation-before.json), restored after the transaction. No stash,
reset or unrelated content overwrite. Only owned run records enter the archive.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/opencode.yaml
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/references/platform.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/references/platform.md
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/references/platform.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/references/platform.md
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/references/platform.md
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/references/platform.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/references/platform.md
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/references/platform.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/references/platform.md
- skills/opencode-kaola-project-runner/references/steering.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/references/platform.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- templates/grok-bot/accepted-revision.json
- templates/references/platform.md.tmpl
- tests/contract/test-issue-24-opencode-no-skip-all.py
- tests/contract/test-issue-88-permission-defaults.py

## Follow-Up Items

No newly discovered independent defect or new issue is required. Known limitations
remain: benign-config deferral, V1/older runtime compatibility and native steering
unverified; config changes after launch, remote well-known rules, arbitrary agents,
session permission edits and live resume/continue not covered by native QA.
#255 owns the already-open integrated lifecycle QA and seven owner requirements;
shared-path-hunks.json records integration overlaps. Preserve both CHANGELOG
entries and regenerate pin/worker products at its safe integration boundary.
Outer personal + same-native Opus Extra High final review and eventual release
remain Host duties; no release in this assignment.

Final readiness: accepted bounded candidate ready for authorized merge sink,
archive, verified issue closure and scoped branch/worktree cleanup. Lifecycle
transaction receipts, rather than this pre-sink readiness, own final truth.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-256/.cache/final-validation.md
- kaola-workflow/archive/issue-256/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-256/finalization-summary.md
- kaola-workflow/archive/issue-256/mission-ledger.jsonl
- kaola-workflow/archive/issue-256/workflow-state.md
