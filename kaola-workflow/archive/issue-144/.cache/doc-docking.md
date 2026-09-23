# Documentation docking — issue-144

Candidate: workflow/issue-144 @ 6000d1e (base main 2eb336c).

| File | Result |
|---|---|
| CHANGELOG.md | Updated — Unreleased Devin entry states the final Owner mapping (upgrade = Opus 5.5 High fusion, fable = Fable 5.1 High fusion, pure claude-fable-5-1-high retired, Astra fusion documented only). |
| README.md | Updated — new sentence after the Droid tier sentence names Devin default/upgrade/fable ids. Line 531 "`--tier fable` on Devin" stays true (label unchanged, now selects the fusion). |
| docs/architecture.md:40 | No impact — `--tier fable` is a label example; Devin still declares `fable`. |
| docs/api.md:50,58 | No impact — `acp_command_<tier>` mechanism and `fable` label example unchanged and still true. |
| docs/ (full grep for fusion-claude / claude-fable-5-1-high / tier fable) | No other hits. |
| skills/devin-kaola-project-runner/* | Generated via render-skills.py --write; --check PASS. |
| AGENTS.md | No impact — no platform tier facts. |

Verdict: DOCKED
