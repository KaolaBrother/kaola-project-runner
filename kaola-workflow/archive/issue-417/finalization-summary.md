# Finalization Summary — issue-417

## Delivered
MacBook live ACP measurement of Hermes Agent v0.22.5 through the hermes Runner, recorded on `workflow/issue-417`:
- `platforms/hermes.yaml` measured fields (`acp_verified_versions`, `acp_quirks`, permission, fast, launch, and steering summaries). `acp_verified_versions` is `cli=0.22.5;agent=hermes-agent/0.22.5;protocol=1;condition=macbook-20261028-mini-unmeasured`.
- Evidence doc `docs/hermes-live-verification-20261028.md`. README Hermes capability row and `docs/architecture.md` point at that measurement.
- Re-rendered `skills/hermes-kaola-project-runner/` from the shared templates. `templates/grok-golden/` was not edited.
- Live provider read-back `deepseek:deepseek-flash` verified. Mode `dont_ask`, permission (`allow_once` on `id_ed25519`), steer refusals, cancel, and exact stop were measured.
- Mac Mini fields stay honestly deferred. No Hermes worker grant. No release or tag.

## Candidate
- `f8743e955bbe4719d94174fa98f336be6acf8d80` on `workflow/issue-417` (one commit ahead of `origin/main` `b1311844800f663536a39466fc6b335c7f549026`, fast-forward).

## Acceptance
- Host verdict: ACCEPTED. Verified independently on `workflow/issue-417` at `f8743e95`: guards clean (golden empty, `.kaola` untouched, no Hermes grant row, guard suite exit 0), `render-skills.py --check` PASS, canaries green, `acp_verified_versions` condition recorded, evidence doc present.
- No Hermes worker grant. No release, tag, or install in this close-out. Release stays with #418.

## Evidence
- Evidence doc `docs/hermes-live-verification-20261028.md` on the candidate.
- Receipts `/tmp/kpr-417-receipts`. Frames `/tmp/kpr-417-frames/wire.jsonl`. Record root `/tmp/kpr-417-records`. Throwaway repo `/tmp/kpr-417-smoke-repo`.
- Session `hermes-kaola-i417-macbook`, ACP id `local-ecb75ab5174c39bd2421bc3b5155bf9b7af218ed55bc169f196cf0442efc31aa`.
- Suites on the unchanged candidate: `test-issue-416-hermes-acp.py` Ran 21 OK; `test-generated-skills.py` PASS; `test-progressive-disclosure.py` Ran 15 OK; `test-issue-49-grok-bot-host.py` Ran 45 OK. `render-skills.py --write` and `--check` PASS.

## Known failures or unverified scope
- Mac Mini was not measured (offline, SSH denied). Placeholders stay honest.
- `test-acp-contract.py` Ran 89 FAILED 1, pre-existing: `test_codex_known_direct_model_keeps_requested_effort` expects display name GPT-6 Luna. `platforms/codex.yaml`, the test, and `scripts/kaola-acp.py` were not changed. Already filed as #420 by #416.
- Steer suites and the quota suite were not run. `native_steering` stays unknown. Quit text and `continue_syntax` were not measured.
- Exact ACP stop left `residual_pids` empty and the record stopped. A later `session/load` of the same id, the preflight id, and the bad-model id still attached. Those gateway rows were not deleted. Viewers were then stopped.
- Gateway pid 83083 (`python3 -m hermes_cli.main --profile default gateway run --quiet --idle-exit`, started 2026-10-28 23:15:23) is the owner's default-profile Hermes daemon. It idle-exited on its own before this finalize. This run did not run `hermes gateway stop` and did not touch `~/.hermes`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/architecture.md
- docs/hermes-live-verification-20261028.md
- platforms/hermes.yaml
- skills/hermes-kaola-project-runner/SKILL.md
- skills/hermes-kaola-project-runner/references/acp.md
- skills/hermes-kaola-project-runner/references/platform.md
- skills/hermes-kaola-project-runner/references/steering.md
- skills/hermes-kaola-project-runner/scripts/platform.yaml
- tests/contract/test-issue-416-hermes-acp.py

## Follow-Up Items
- #418 owns release. This run does not tag or publish.
- #420 already tracks the pre-existing acp-contract Luna failure. No new issue filed. The residual gateway rows are the measured Hermes behavior in the evidence doc.

## Readiness
Ready to archive and merge-sink. Candidate `f8743e95` stays frozen. Closure is close #417 after the merge is verified.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-417/.cache/final-validation.md
- kaola-workflow/archive/issue-417/finalization-summary.md
- kaola-workflow/archive/issue-417/mission-ledger.jsonl
- kaola-workflow/archive/issue-417/workflow-state.md
