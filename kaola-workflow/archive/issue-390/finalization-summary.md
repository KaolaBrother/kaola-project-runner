# Finalization Summary — issue-390

## Delivered

`platforms/antigravity.yaml` carries the owner-approved Argon profiles verbatim. L22
`default_model_profile` and L29 `xhigh_model_profile` were replaced with the exact issue #390 text:
general implementation work (features, UI and 3D, frontend and backend code, refactors, tests),
the explicit warning that Argon sometimes reports work, files or results that do not exist, the
rule that every output must be independently reviewed by another seat before acceptance, and the
rule that the Argon tiers are never reviewers, verifiers or acceptance authorities. The profile is
the dispatch guidance: `kaola-dispatch.py project` projects it into `candidates[].profile`, and the
#218 suite asserts that projection on `antigravity/default` and `antigravity/xhigh`.

Both Argon classes stay `Elite`. `antigravity/opus` is untouched: its row keeps the #343
`UI and 3D design implementation only` wording, and its exact-text assertion remains in both
Antigravity suites. The #343 pins for the two Argon tiers were replaced, not weakened; the
unrelated presets, model IDs, efforts, ACP fields and quota are unchanged.

`./scripts/render-skills.py --write` and `--check` pass. The new text appears in the generated
Antigravity worker manifest (`skills/antigravity-kaola-project-runner/scripts/platform.yaml`), the
profile catalog (`skills/kaola-project-runner/references/profile-catalog.md`) and the README preset
region. The catalog grew by 244 B from the mandated text, so its preamble was tightened by 256 B:
the catalog is 8116 B, inside the unchanged 8192 B `reference_bytes` budget and the #351 8130 B
pin. No budget value was raised. `CHANGELOG.md` Unreleased carries `Fixes #390` and the
`Seats: restart required` entry; the historical 0.9.16 #343 release note stays as history.

## Candidate

Branch `workflow/issue-390`. The accepted pre-rebase commit is `ab3bb26b` (Host acceptance in
conversation, 2026-10-20). It was rebased onto current main `150613a6` (which carries merged #388);
the candidate is now `aa54d4d1` (`Widen Antigravity Argon profiles to general implementation, never
a reviewer (#390)`). The only rebase conflict was `CHANGELOG.md` (both `Fixes #388` and
`Fixes #390` kept); `platforms/antigravity.yaml` auto-merged with no conflict. `render-skills.py
--write` was rerun on the rebased tree and `--check` is PASS, so the generated build records match
the union tree. `git diff --check` is clean.

## Evidence

- Byte-level match: a script parsed the two fenced blocks from `gh issue view 390 --json body` and
  compared them with the YAML values; both report `MATCH` (not a hand-copied comparison). The Host
  independently verified the same L22/L29 text byte-for-byte at `ab3bb26b` before acceptance.
- Host acceptance of `ab3bb26b`: L22/L29 verbatim, Elite kept, `antigravity/opus` untouched,
  render `--check` PASS, the catalog-preamble budget handling accepted, #218/#323 updates accepted,
  and the two full-inventory runs accepted as evidence. Argon was not used for any review,
  verification or acceptance.
- Affected batch 1 on `ab3bb26b`, exit 0: `test-generated-skills.py`,
  `test-issue-218-preset-ids.py`, `test-issue-323-antigravity-acp.py`,
  `test-progressive-disclosure.py`, `test-issue-41-orchestrator.py`,
  `test-issue-351-dsh-profile.py`.
- Affected batch 2 on `ab3bb26b`, exit 0: `test-issue-111-model-tiers.py`,
  `test-issue-119-host-entry.py`, `test-issue-215-install-truthfulness.py`,
  `test-installer-runtimes.sh`, `test-issue-237-model-display.py`,
  `test-issue-345-worker-pool.py`.
- Full inventory on `ab3bb26b`: the first `./scripts/validate.sh` run hit one unrelated timing
  flake in `test-issue-341-agent-initiated-turn.py` case f2 (10 s wait for a second wake); that
  suite passed alone in 28 s. The second full run was green: FULL INVENTORY 144 suites, exit 0,
  total wall 2229.71 s.
- Rebased candidate `aa54d4d1`: `./scripts/render-skills.py --check` PASS and seven focused suites
  exit 0 (total wall 31.2 s): `test-generated-skills.py`, `test-issue-218-preset-ids.py`,
  `test-issue-323-antigravity-acp.py`, `test-progressive-disclosure.py`,
  `test-issue-41-orchestrator.py`, `test-issue-351-dsh-profile.py`,
  `test-issue-388-role-carrier.py`. The last covers the merged #388 code on the union tree.
- Final validation record: `kaola-workflow/issue-390/.cache/final-validation.md` (written by the
  validation recorder for `aa54d4d1`).

## Known failures or unverified scope

- Validation on the rebased union candidate is diff-scoped (seven suites), not whole-inventory.
  Whole-inventory evidence remains the green 144-suite run on `ab3bb26b`; #388 carried its own
  affected-suite evidence before merge. The Host will run the final full gate after landing.
- No live Antigravity/agy smoke was run for this text-only profile change; the contract suites read
  the manifest and generated surfaces. No antigravity session was started.
- `Seats: restart required`: `platforms/` and the generated guidance are in the operator restart
  set, so a running Host keeps the old profile wording until it restarts. This finalize does not
  install, restart another Host, tag or release.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- platforms/antigravity.yaml
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/antigravity-kaola-project-runner/scripts/platform.yaml
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/profile-catalog.md.tmpl
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-323-antigravity-acp.py

## Follow-Up Items

None. No run-discovered defect needs a separate issue.

## Readiness

Ready for the merge sink: candidate `aa54d4d1`, rebased onto `150613a6`, focused validation green,
Host acceptance recorded, no unresolved issue work.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-390/.cache/final-validation.md
- kaola-workflow/archive/issue-390/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-390/finalization-summary.md
- kaola-workflow/archive/issue-390/mission-ledger.jsonl
- kaola-workflow/archive/issue-390/workflow-state.md
