# Documentation docking — bundle-27 / issue #27

Status: DOCKED

Transcribed from `python3 scripts/kaola-acp.py grok follow --help` (command `follow` is a choice; flags `--since`, `--format {json,text}`) and `bash scripts/kaola-tmux.sh grok follow …` stdout `{"error":{"code":"follow-unsupported","message":"follow is not a pty/tmux command; use kaola-acp"},"kind":"error"}` rc=1.

## Checked

| File | Result |
|---|---|
| `README.md` | Updated: `kaola-acp follow --since --format json\|text` NDJSON kinds; tmux `follow-unsupported`. |
| `docs/api.md` | Already named follow CLI, read-only FD, 256-line drop, eof/holder-lost, tmux guard. Matches argparse + holder. |
| `docs/architecture.md` | `#27` marked implemented. |
| `docs/acp-watch/README.md` | `#25/#26/#27` implemented; follow NDJSON named. |
| `docs/acp-watch/follow.md` | Status 已实现; behavior/acceptance unchanged from the frozen design. |
| `docs/README.md` | Index no longer says #27 not implemented. |
| `CHANGELOG.md` | Unreleased bullet for local follow. |
| `templates/references/acp.md.tmpl` | Humans watch with list, view, and local follow. Rendered into six Skills. |
| `templates/grok-golden/` | No diff. |
| Examples in README tmux block | Unchanged; follow is kaola-acp-only, not a tmux example. |

## No-impact

- Adapter docs, PTY send/stop contract, L0 receipt keys: follow is a watch surface, not an L0 command.
- Live smoke reports: not this issue.

## Fixes this pass

`README.md` and `docs/README.md` still described list/view only / “#27 not”; aligned to the implemented CLI.
