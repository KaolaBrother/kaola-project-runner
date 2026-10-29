# Document docking of issue #420
- format: kpm.workflow-doc-docking/1.0
- issue: 420
- candidate: d5392ea72b0c7972be1f8dbd28ebc21bc08bcc1c
- checked_by:
- checked_at:
- verdict:

## Impact
- docs/api.md | model-display direct-model examples now use `--model gpt-6.1-terra` with effort max and display name Codex Terra
- tests/contract/test-acp-contract.py | known direct model starts `gpt-6.1-terra --effort max` and expects display name Codex Terra; preset id, effort, and components stay null
- tests/contract/test-issue-244-dispatch.py | admitted receipts use catalog `gpt-6.1-terra` / effort high; the effort override stays max; intentional mismatches stay
- CHANGELOG.md | no release section this run
- scripts/kaola-acp-holder.py | unchanged
- scripts/kaola-compact-recovery.py | unchanged
- templates/grok-golden/ | unchanged
- skills/ and hosts/grok-bot/ | `render-skills.py --write` then `--check` passed with no tree diff

## Docking
