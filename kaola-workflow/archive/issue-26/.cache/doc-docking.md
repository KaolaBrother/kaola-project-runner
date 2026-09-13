# Documentation docking — issue #26

Candidate: `c123d47dedd9f5d56c6b6bdb7ed9eb2fe285adea`

Transcribed from `python3 scripts/kaola-acp.py list --help`, `python3 scripts/kaola-acp.py grok view --help`, and `bash scripts/kaola-tmux.sh grok view` on that commit.

## Checked

- `README.md` — `$HOME/.local/bin/kaola-acp` and `kaola-acp-holder` owned symlinks; human `kaola-acp list [--platform P] [--repo ROOT]` (`kaola-acp-list/1`) and `kaola-acp <platform> view --repo … --session … [--since CURSOR]` (`kaola-acp-view/1`); `kaola-tmux.sh … view` is `view-unsupported`.
- `CHANGELOG.md` — Unreleased issue #26 bullet: list/view implemented; EventLog rotation reload; local-bin install; L0 keys unchanged; `view-unsupported`; #25/#27 still unimplemented.
- `docs/api.md` — ACP command list includes `view`; list/view stdout schemas and frozen runtime error codes; installer bin links.
- `docs/architecture.md` — #26 implemented; #25/#27 not.
- `docs/acp-watch/README.md` and `list-view.md` — status no longer “未实现” for #26.
- `docs/README.md`, `docs/runner-v2-dual-transport-design.md` — spectator path names implemented `list`/`view`.
- Generated Skill `references/acp.md` — humans watch with `` `list` `` / `` `view` ``; `./scripts/render-skills.py --check` PASS; no hand-edits of `skills/`.
- `templates/grok-golden/` — empty diff vs `origin/main` / this candidate.
- `AGENTS.md` documentation map — README + CHANGELOG + `docs/` cover the public watch surface.

## Verdict

DOCKED
