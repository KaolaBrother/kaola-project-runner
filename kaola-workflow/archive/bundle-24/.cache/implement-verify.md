# Issue #24 implementer verification

Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24`
Date: 2026-09-13
Quirks string: `no ACP skip-all; PTY --auto via --transport pty is the bypass`

## Production change

- `platforms/opencode.yaml`
  - `acp_quirks`: `"no ACP skip-all; PTY --auto via --transport pty is the bypass"`
  - `launch_summary` tightened to name `--transport pty` and “no skip-all” (still no ACP skip argv)
- `README.md`: OpenCode `--auto` is PTY-only via `--transport pty`
- `CHANGELOG.md`: Unreleased issue #24 note (ACP stays `opencode acp`; PTY `--auto` is the bypass)
- Generated Skills via `./scripts/render-skills.py --write` (never hand-edited `skills/`)
- `templates/grok-golden/` not modified
- Did not add OpenCode to `ACP_SKIP_MODE`, did not auto-permit, did not set `OPENCODE_PERMISSION`

## Commands and results

All commands run from the worktree root.

### 1. Render write

```
./scripts/render-skills.py --write
```

Exit 0.

```
render-skills: WROTE (6 Skills)
```

### 2. Render check

```
./scripts/render-skills.py --check
```

Exit 0.

```
render-skills: PASS (6 Skills)
```

### 3. Issue #24 contract tests

```
python3 tests/contract/test-issue-24-opencode-pty-bypass.py
```

Exit 0.

```
.............
----------------------------------------------------------------------
Ran 13 tests in 0.014s

OK
```

13 OK. No FAIL.

### 4. Full validator

```
./scripts/validate.sh
```

Exit 0.

```
render-skills: PASS (6 Skills)
Skill is valid!
Skill is valid!
Skill is valid!
Skill is valid!
Skill is valid!
Skill is valid!
.......
----------------------------------------------------------------------
Ran 7 tests in 0.029s

OK
.....
----------------------------------------------------------------------
Ran 5 tests in 0.001s

OK
...............................
----------------------------------------------------------------------
Ran 31 tests in 0.373s

OK
..............
----------------------------------------------------------------------
Ran 14 tests in 16.651s

OK
....
----------------------------------------------------------------------
Ran 4 tests in 0.003s

OK
generated Skill acceptance: PASS
.............
----------------------------------------------------------------------
Ran 13 tests in 0.015s

OK
```

`validate.sh` includes `test-issue-24-opencode-pty-bypass.py` as the last step (13 tests OK).

### 5. Frozen golden templates

```
git diff --stat templates/grok-golden
```

Exit 0. Empty output (no changes).

### 6. Worktree diff (for the record)

```
git diff --stat
```

```
 CHANGELOG.md                                                | 4 ++++
 README.md                                                   | 2 +-
 platforms/opencode.yaml                                     | 4 ++--
 scripts/validate.sh                                         | 1 +
 skills/opencode-kaola-project-runner/SKILL.md               | 2 +-
 skills/opencode-kaola-project-runner/references/acp.md      | 2 +-
 skills/opencode-kaola-project-runner/references/platform.md | 2 +-
 skills/opencode-kaola-project-runner/scripts/platform.yaml  | 4 ++--
 8 files changed, 13 insertions(+), 8 deletions(-)
```

`scripts/validate.sh` and untracked `tests/contract/test-issue-24-opencode-pty-bypass.py` are TDD registration already present; this implementer did not author them.

## What was not run

- Live tmux smoke (`start` / `observe` / `send` / `capture` / `stop`) for any platform
- Live OpenCode ACP `send --wait` against `session/request_permission`
- `./scripts/install-local.sh`
- Re-measurement of OpenCode 1.18.29 skip knobs (trusted existing `.cache/measure-opencode-acp-skip.md` and `.cache/vendor-opencode-acp-skip.md`)
- Any `OPENCODE_PERMISSION` or permission-config injection experiment
- Content inspection of `templates/grok-golden/` beyond `git diff --stat` emptiness

## Verdict

PASS. Default OpenCode ACP remains `opencode acp` with no skip. Agent-facing `acp_quirks` documents that there is no ACP skip-all and that PTY `--auto` via `--transport pty` is the bypass. Required checks are green; grok-golden is unchanged.
