# Finalization Summary — issue-206

## Delivered

Issue #206 (consolidated body + owner comments): README reorganized around usage, and the owner's
Expert / Worker / Elite preset classes carried through the canonical manifests, Host guidance and
Delegator guidance, with the Host keeping only authorized profile rows in context.

Issue parts → evidence:
- AC1 README usage path, all 20 full profiles with class/model/preset/effort, technical detail and
  history relocated → README order entry → Workflow → install → select workers (runtimes, classes,
  catalog) → authorization → responsibilities → daily use → agents → docs; generated
  `KW-README-PRESETS` region == `references/profile-catalog.md` rows (20/20; independent manifest
  re-parse: 20 presets, 0 missing); 55 links, 0 bad.
- AC2 membership/responsibility agreement → one source: `<tier>_model_class` in platforms/*.yaml
  (11 Elite / 6 Worker / 3 Expert, validated in render-skills.py); README, profile-catalog and the
  worker-profiles Worker table render from it; class meanings in the main Skill, worker-profiles,
  host-startup, qa-evidence, Delegator SKILL and host-platforms §Worker classes. No "Leader".
- AC3 scoped Host view → worker-profiles §Authorized rows only + heartbeat snapshot line; scenario
  six Worker + Codex `default` grant = 7 rows, 0 Expert; later grant fetches only its row by
  `grep -F`; Delegator relays grants, not tables; no registry/service/state file.
- AC4 Expert per-task lifecycle, Elite/Worker continuity → Expert reuse allowance removed
  ("needs no repeated permission" residue 0); same approved task continues; switch grant never
  authorizes Expert; Expert review never replaces Host acceptance; Elite grants and Worker cap
  exemption unchanged.
- AC5 decision order authorization → class → profile/task fit → capacity, no scheduling
  infrastructure → worker-profiles §Choosing, main Skill, Delegator, README.
- AC6 approved corrections → exact sentences in grok/cursor-cli/devin/codex manifests and all
  generated consumers; old wording residue 0; Sol caveat kept; 0 model/id/effort/parameters lines
  changed. Minimal Expert-profile contradiction fix ("no heavy execution" → "no concrete
  implementation or execution").
- AC7 coordination → built on re-synced main 273c1314 (#205); conflicts only in generated
  main-skill-build.json (re-rendered); two #205-dropped pinned phrases restored (test-118, test-187
  pass on the integrated tree).

Host acceptance: ZCode Host zcode-KPR-orchestrator-main (holder 626a061e) accepted candidate
5e35d924 and authorized finalize (merge sink, push, close, archive; no release/tag/install).

## Files Changed

platforms/*.yaml (10); scripts/render-skills.py; templates/orchestrator/{SKILL.md.tmpl,
references/{worker-profiles,profile-catalog,host-startup,zcode-host-dispatch}.md.tmpl,
references/{qa-evidence.md,heartbeat-skeleton.txt}}; templates/SKILL.md.tmpl;
templates/kaola-delegator/{SKILL.md.tmpl,references/host-platforms.md.tmpl}; README.md;
CHANGELOG.md; docs/architecture.md; docs/zcode-host.md; regenerated skills/**. Commits f1243180,
db9b6c73 (prior owner), 0a30b33b, 5e35d924 (merge main 273c1314).

## Test Coverage

render-skills.py --check PASS (budgets OK) on 5e35d924. Focused suites PASS on the integrated tree:
generated-skills, progressive-disclosure, 49, 52, 68, 72, 74, 75, 86, 88, 94, 111, 118, 119, 123,
147, 187, zcode-heartbeat-contract, zcode-host-contract. validate.sh rc=1 with only
test-issue-65-host-contract (2) and test-issue-162-upgrade-safety (1), identical on main 273c1314
and base db9b6c73 (introduced by #204's 4af3686b; filed #209). No live model test (out of scope).

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
- platforms/claude-code.yaml
- platforms/codex.yaml
- platforms/cursor-cli.yaml
- platforms/devin.yaml
- platforms/droid.yaml
- platforms/dsh.yaml
- platforms/grok.yaml
- platforms/kimi-cli.yaml
- platforms/opencode.yaml
- platforms/zcode.yaml
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/kimi-cli-kaola-project-runner/scripts/platform.yaml
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/SKILL.md
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/SKILL.md.tmpl
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/profile-catalog.md.tmpl
- templates/orchestrator/references/qa-evidence.md
- templates/orchestrator/references/worker-profiles.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl

## Documentation Docking

DOCKED — see .cache/doc-docking.md.

## Follow-Up Items

- filed: #209 (P2) — contract suites 65/162 fail on main after #204 budget rewording removed
  pinned phrases. Confirmed OPEN, body non-empty (1776 chars), label P2.
- Release note: next release's `platforms/` operator test reads `Seats: restart required`
  (recorded in CHANGELOG; no release in this run).
- Owner cumulative QA from v0.6.7 is Host-owned acceptance, not part of this run.

## Readiness

READY — accepted by Host; merge sink; close #206 on verified merge.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-206/.cache/doc-docking.md
- kaola-workflow/archive/issue-206/.cache/final-validation.md
- kaola-workflow/archive/issue-206/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-206/finalization-summary.md
- kaola-workflow/archive/issue-206/mission-ledger.jsonl
- kaola-workflow/archive/issue-206/workflow-state.md
