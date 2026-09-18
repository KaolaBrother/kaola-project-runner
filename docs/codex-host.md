# Codex Host (Issue #75)

Codex is a first-class consuming runtime for the generated Skills and the only
host this issue adapts for post-compaction recovery. This page covers the Codex
host surface: skill installation and the Runner-owned compact-recovery hook.

## Skill installation

`./scripts/install-local.sh --runtime codex` installs the generated Skills into
`${CODEX_HOME:-~/.codex}/skills` — `kaola-project-runner` plus the nine
`<platform>-kaola-project-runner` workers as sibling directories. `--method
link|copy` and `--bin-links` behave as documented in the installer reference.

## Compact recovery: `SessionStart(source=compact)`

A Codex host Agent runs across many issues and worker rounds; after context
compaction the previously read Skill text cannot be assumed present. Codex
fires `SessionStart` hooks with source `compact` after a compaction and drains
the queued `additionalContext` before the next model request — the verified,
host-native re-entry point (codex-cli ≥ 0.153.x; see
developers.openai.com/codex/hooks).

The carrier is deliberately thin: one `SessionStart` matcher group whose
command `cat`s a short recovery prompt
(`templates/codex-host/compact-recovery.md`). The prompt tells the host to
confirm its role (`kaola-project-runner`, or `kaola-delegator` when that is the
installed Skill in use), completely re-read that installed Skill, then recover
the live scene from current authorization, the effective-now heartbeat, and
project run records — without re-intake, re-claim, restarting sessions, or
re-dispatching in-flight work. The hook performs no dispatch, mutates no
project state, and keeps no copy of the Skill.

### Install / uninstall

```bash
python3 scripts/kaola-codex-compact-hook.py install   # add our entry + payload
python3 scripts/kaola-codex-compact-hook.py status    # read-only report
python3 scripts/kaola-codex-compact-hook.py uninstall # remove only our entry
```

- Edits `${CODEX_HOME:-~/.codex}/hooks.json` only; `--codex-home PATH` or
  `CODEX_HOME` selects another root (isolated testing).
- Owns exactly one entry, id `kaola-project-runner:compact-context`, under
  `hooks.SessionStart` — matched by id, so foreign entries (Workflow-owned,
  user-owned) are preserved untouched. Re-install is idempotent; uninstall
  removes only that entry and our payload copy.
- Copies the payload to
  `<codex_home>/kaola-project-runner/hooks/compact-recovery.md` so the hook does
  not depend on a checkout path, and keeps one content-addressed
  `hooks.json.kaola-backup-<sha12>` before rewriting an existing file.
- Refuses (no write) on a malformed `hooks.json`.

### Trust and coexistence

Codex merges hook sources from all config layers (`~/.codex/hooks.json`,
project `.codex/hooks.json`, plugin-bundled, `config.toml`); our entry adds to
that set, never replaces it — the existing Workflow compact hook keeps firing
alongside it. Non-managed hooks require a one-time trust review in the Codex
`/hooks` browser the first time they run; that approval is the host owner's
deliberate step, not something this installer performs. Vetted automation may
instead launch Codex with `--dangerously-bypass-hook-trust` for a single
invocation without persisting trust.

## Verified boundary

- Mechanism and live behavior proven in an isolated real `/compact` run:
  `SessionStart(compact)` fired, the payload reached the model as
  `additionalContext` before the next reasoning turn, and the foreign Workflow
  hook fired alongside ours (evidence:
  `kaola-workflow/bundle-75/evidence/codex-compact-live/`).
- The installer itself performs no user-global write during tests; the
  contract suite (`tests/contract/test-issue-75-codex-compact-hook.py`) proves
  merge safety, idempotency, refusal on malformed config, and payload content.
- Out of scope here: ZCode's compact carrier (see `docs/zcode-host.md` and the
  Issue #75 capability matrix — its 0.16.5 `SessionStart` has no `compact`
  call site), Grok Bot, and other native hosts.
