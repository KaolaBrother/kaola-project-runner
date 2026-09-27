# Documentation docking — issue-200 (candidate 6c28174c)

Checked against the branch's changed public behavior (OpenCode default preset pin,
sixth default-authorized pool preset, six worker-profile wordings, rendered surfaces):

- README.md — updated: preset-table OpenCode row now `DeepSeek V4.1 Flash
  (opencode-go/deepseek-v4.1-flash), no effort pin`; "OpenCode's is unset" parenthetical
  removed; four five→six-preset pool mentions. No further impact.
- CHANGELOG.md — Unreleased entry for #200 added (commit 6c28174c), stating the preset
  change, pool membership, profile rewording, non-empty release operator test, and the
  content-stage bridge pending the v0.6.7 pin. Seats-restart line is owed by the v0.6.7
  release section, per existing convention.
- docs/architecture.md, docs/zcode-host.md — five→six-preset wording updated. No other
  drift found.
- docs/conventions.md — re-read; release pin/operator-test conventions unaffected (the
  CHANGELOG entry states the operator test is non-empty).
- docs/host-entry-evidence.md — historical evidence, intentionally unchanged; it already
  records the OpenCode 2.0.11 round trip this pin uses as its ID basis.
- AGENTS.md managed snapshot — states platform count, not pool size or OpenCode default
  model; no impact.
- Generated skills/** and hosts/grok-bot/** — renderer output, `render-skills.py --write`
  then `--check` PASS; never hand-edited.
- No API, setup, environment, or example surface changed.

DOCKED
