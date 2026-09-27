# Finalization Summary — issue-195

## Delivered

Issue #195: the five eligible inexpensive runtime/preset pairs are default-authorized
for an authorized project task, exempt from the general worker concurrency count/cap,
with explicit authorization still required for every other runtime/preset.

- One compact canonical list in `references/worker-profiles.md`
  (`## Default-authorized inexpensive presets`): Claude Code `sonnet`, Codex `luna`,
  dsh `default`, Devin `default`, ZCode `default` — exact existing model/effort bindings,
  no model/effort/Fast changes. Membership is by enumeration; a `default` tier name alone
  never qualifies.
- Pool seats need no per-seat grant, count, or priority order; they neither consume nor
  are limited by the general cap; no substitute cap, per-runtime allocation, or approval
  gate. Actual account/token/service/resource limits and prior outside-pool grants remain.
- Selection stays task-fit driven (profile, tools, idle capacity, known usage); no
  forced equal counts, no invented work or extra sessions, no interrupting useful work or
  waiting for a less suitable worker; a future explicit owner restriction wins.
- Outside-pool rules scoped consistently: `No worker authorization, no heartbeat`;
  `live N / authorized M` and N>M violation cover non-pool seats while pool seats report
  factual live seats marked exempt; heartbeat skeleton zh mirrors all of it; first-intake
  gate reads missing worker authorization.
- Delegator extraction scopes platforms/members/counts/concurrency to outside-pool
  workers and stated exclusions; Delegator carries goal/bounds/exclusions and does not
  enumerate, gate, or schedule the pool.
- Exact session binding, lifecycle, close-out ownership, and Host model authorization
  unchanged; no new scheduler, router, registry, quota engine, or state file.
- ZCode `default_model_profile` carries "Very low-cost" with routine-work and weak-visual
  characterization preserved.

Host accepted exact integrated candidate `f0561176` (merge of origin/main `48cd9cd7`
carrying #192 + #193 sinks); `98942335` adds only the CHANGELOG Unreleased entry required
by the docking checklist.

## Files Changed

Branch vs `ad73e158` (issue base): templates `orchestrator/SKILL.md.tmpl`,
`orchestrator/references/worker-profiles.md.tmpl`, `zcode-host-dispatch.md.tmpl`,
`heartbeat-skeleton.txt`, `kaola-delegator/SKILL.md.tmpl`,
`kaola-delegator/references/host-platforms.md.tmpl`; `platforms/zcode.yaml`; `README.md`;
`docs/architecture.md`; `docs/zcode-host.md`; `CHANGELOG.md`; regenerated `skills/`
outputs incl. the ten `main-skill-build.json` (merged with #192's upstream regeneration
by re-render from templates/manifests).

## Test Coverage

- `./scripts/validate.sh` rc=0, 434 checks, on `30c3c623` — policy-prose-only wording
  deltas since; every lane that pins a mutated phrase was re-run on each later commit.
- `./scripts/render-skills.py --write` and `--check` rc=0, budgets OK on `f0561176`
  (main SKILL 17388/17408, delegator 4086/4096, heartbeat-skeleton 7758/8192).
- Affected contract lanes, all green on `f0561176`: test-issue-148 (16), 86 (46),
  118 (18), 68 (7), 41 (23), 49 (45), 65 (13), 74 (187 assertions), 187 (14),
  111 (25); test-generated-skills PASS; installer migration and installer runtimes PASS.
- Two Host review rounds repaired on-branch (`6486e39e`, `d33178b9`) and re-verified.
- Not executed: a live Host intake smoke of the new wording (documentation/policy-only
  change; contract lanes cover the mutated surfaces).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/architecture.md
- docs/zcode-host.md
- platforms/zcode.yaml
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/worker-profiles.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. CHANGELOG gained the Unreleased entry; README,
`docs/architecture.md`, `docs/zcode-host.md`, generated Skills and references updated;
`docs/api.md`, `docs/conventions.md`, `AGENTS.md`, `quota-packages.md` (#192-owned),
`templates/grok-golden/` untouched by this issue.

## Follow-Up Items

- No follow-up issue filed. This run surfaced no product defect; both review rounds were
  wording repairs on this candidate.
- Protected-doc guard: the finalize residue mirror copies untracked non-`kaola-workflow/`
  files from the main checkout onto the branch (observed by #192–#194). For this finalize,
  `docs/harness-acp-compat-2026-09-25.md` and `-26.md` were temporarily listed in the main
  checkout's local untracked `.git/info/exclude` so the mirror skips them; the exclude file
  will be restored byte-identically (sha256 `321dffcb77a68a6c079d35da12944866b895b4cc9fb3b1fae72fe9468c7eafeb`)
  and the files themselves were never moved or edited.

## Status

Ready for sink: all seven missions done, Host accepted `f0561176`, validation recorded
(`verdict: pass`, candidate hash `1a65398dbe08b6d3d66c23737373226d601b166432a30d4dab55a4c2306c1a66`),
docs docked.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-195/.cache/doc-docking.md
- kaola-workflow/archive/issue-195/.cache/final-validation.md
- kaola-workflow/archive/issue-195/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-195/finalization-summary.md
- kaola-workflow/archive/issue-195/mission-ledger.jsonl
- kaola-workflow/archive/issue-195/workflow-state.md
