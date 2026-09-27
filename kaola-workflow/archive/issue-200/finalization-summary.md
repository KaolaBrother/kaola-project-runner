# Finalization summary — issue-200

## Delivered

Fresh, independent implementation of #200 from clean main (old forfeited candidate never
read, copied, or reused; its tip preserved as `abandoned/issue-200-e395f225`):

- OpenCode `--tier default` resolves to `opencode-go/deepseek-v4.1-flash` through the
  existing manifest/adapter selection path, with `default_model_effort` empty and
  parameters stated as "no Runner effort override" — no effort pin added anywhere.
- That OpenCode default pair added as the sixth default-authorized inexpensive pool
  preset in `worker-profiles.md` (source template), inheriting the same authorization and
  general-concurrency exemption; membership stays an exact six-row list.
- The six exact owner-stated worker profiles replace the prior one-line profile facts in
  `platforms/{claude-code,codex,zcode,devin,opencode,dsh}.yaml` and render into
  `worker-profiles.md`; Host SKILL, Delegator SKILL, delegator host-platforms, README,
  docs/architecture.md, and docs/zcode-host.md consistently describe six presets. No
  other preset's model, effort, or Fast parameters changed; no catalog/price/capability
  probe, route table, scheduler, cap, or eligibility logic was added.
- Affected stale-premise fixtures updated without weakening their checks:
  test-33 (two fixtures + rationale comment), test-119 H2 plain leg, test-148 emission
  fixture.
- `templates/grok-bot/accepted-revision.json` moved to content stage (mandatory pin-gate
  transition for post-release source work); v0.6.7 must create the new content/pin pair.
- CHANGELOG Unreleased entry for #200 (commit 6c28174c).

## Files Changed

Branch `workflow/issue-200` commits: 7c2d4434 (44 files, implementation + render),
006c99a1 (merge of main 968cef0a + re-render), 82daa055 (merge of main 6aaece49 +
re-render), 6c28174c (CHANGELOG). Source: 6 platform manifests, scripts/adapters/opencode.sh,
5 templates, README.md, docs/architecture.md, docs/zcode-host.md, CHANGELOG.md, 3 test
files; generated: skills/** (renderer), hosts/grok-bot/** (renderer, content stage).

## Test Coverage

- `./scripts/render-skills.py --check` PASS at every frozen head.
- Full `./scripts/validate.sh` RC=0 on 7c2d4434 (/tmp/kaola-i200-frozen-validate.log),
  RC=0 on merged head 006c99a1 (/tmp/kaola-i200-merged-validate.log), and RC=0 on final
  head 6c28174c (/tmp/kaola-i200-final-validate.log, RC as last line).
- Suites test-issue-33-config-meta.py, test-issue-119-host-entry.py,
  test-issue-148-quota-packages.py individually green on the final head (33: 9/9 OK,
  119: 11/11 tests 164 checks, 148: 16/16 OK).
- Acceptance walkthrough: six exact profile strings verified byte-exact in the six
  manifests and rendered worker-profiles.md; pool table exactly six rows; no stale
  "five-preset"/"CLI native opening"/"is unset" wording anywhere outside archives.
- Not executed: live OpenCode ACP smoke (no live session run this run; the pin rests on
  the recorded 2.0.11 round trip in docs/host-entry-evidence.md cited by the issue).

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
- platforms/devin.yaml
- platforms/dsh.yaml
- platforms/opencode.yaml
- platforms/zcode.yaml
- scripts/adapters/opencode.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/platform.md
- skills/opencode-kaola-project-runner/scripts/adapters/opencode.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-33-config-meta.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`: README, CHANGELOG, architecture, zcode-host,
conventions re-read, generated surfaces renderer-owned, no other drift.

## Follow-Up Items

- v0.6.7 release transaction must create the new grok-bot content/pin pair (release
  notes may claim #200 only after this merge; Seats line owed there).
- Host owns `abandoned/*` branch cleanup (not touched by this run).

## Readiness

All missions done; Host acceptance received on 006c99a1 with re-sync to 6aaece49
(82daa055) and CHANGELOG (6c28174c) after it; ready for the finalize transaction.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-200/.cache/doc-docking.md
- kaola-workflow/archive/issue-200/.cache/final-validation.md
- kaola-workflow/archive/issue-200/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-200/finalization-summary.md
- kaola-workflow/archive/issue-200/mission-ledger.jsonl
- kaola-workflow/archive/issue-200/workflow-state.md
