# Documentation update

verdict: pass

- `CHANGELOG.md` already records the caller-controlled scheduling contract and measured Claude Code flow in commit `f38685572e38`.
- `AGENTS.md` now contains the Documentation Update Checklist required by finalization.
- `README.md` needs no change: installation commands and package inventory did not change.
- `docs/architecture.md` and `docs/api.md` need no change: no public shell command or adapter JSON field was removed or renamed; `recurring_execution` remains a runtime-native capability fact while generated Skill prose owns the external scheduling policy.
- Claude launch flags were transcribed from local `/opt/homebrew/bin/claude --help`: `--model`, `--effort`, and `--permission-mode` with `auto` are present.
