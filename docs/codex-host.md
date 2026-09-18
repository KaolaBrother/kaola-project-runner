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
command prints a short recovery prompt
(`templates/codex-host/compact-recovery.md`) — only when the hook input on
stdin matches the bound Host session (see the filter below). The prompt
tells the host to
confirm its role (`kaola-project-runner`, or `kaola-delegator` when that is the
installed Skill in use), completely re-read that installed Skill, then recover
the live scene from current authorization, the effective-now heartbeat, and
project run records — without re-intake, re-claim, restarting sessions, or
re-dispatching in-flight work. The hook performs no dispatch, mutates no
project state, and keeps no copy of the Skill.

### Install / uninstall

```bash
# Two-phase bootstrap — covers the FIRST Host session (hooks load at
# session start, so the entry must exist before launch; the session id can
# only be bound afterwards):
python3 scripts/kaola-codex-compact-hook.py prepare --project-root <canonical project root>
#   → writes entry + assets with an inert binding (session_id null = silent)
# … start the designated Codex Host …
python3 scripts/kaola-codex-compact-hook.py bind \
    --project-root <canonical project root> --session-id <host session id>
#   → writes ONLY binding.json; the loaded/reviewed entry is untouched

# One-shot form when the session id is already known:
python3 scripts/kaola-codex-compact-hook.py install \
    --project-root <canonical project root> --session-id <host session id>

python3 scripts/kaola-codex-compact-hook.py status    --project-root <root> # read-only
python3 scripts/kaola-codex-compact-hook.py uninstall --project-root <root> # ours only
```

Inside the Codex host's own shell, `CODEX_SESSION_ID` and `CODEX_THREAD_ID`
both carry the session identity and equal the `session_id` the hook input
delivers on stdin — verified live (the values themselves are never printed
by this tooling). The id is bound only by an explicit operator `bind`/
`install` call; nothing auto-claims the first session, and ordinary Workers
are never bound.

- Edits `<project_root>/.codex/hooks.json` — the official **project-level**
  hooks layer — only. It never writes `${CODEX_HOME}` or `~/.codex`: a single
  user-global file could hold only one project binding, so two designated
  Hosts would overwrite each other. Each repository keeps its own binding, so
  projects A and B coexist and removing B leaves A fully intact.
- **Host-only filter (required binding).** `install`/`bind` refuse without
  `--session-id`: the entry is bound to the exact designated Codex Host
  session, not to a runtime. The binding is written to
  `<project_root>/.codex/kaola-project-runner/hooks/binding.json`; the hook
  command runs a copied `emit` action that reads the binding plus the
  official hook input on stdin (`session_id`, `cwd`, `hook_event_name`,
  `source`) and prints the payload only for `SessionStart(compact)` on the
  bound session at the bound root — an ordinary Worker session, a session in
  another repository, or a non-compact source emits nothing. `codex resume`
  keeps the session id, so the binding survives resume; for a brand-new Host
  session, re-run `bind` (or `install`) with the new id — only `binding.json`
  changes, so the already-reviewed hook entry is not disturbed.
- Owns exactly one entry, id `kaola-project-runner:compact-context`, under
  `hooks.SessionStart` — matched by id, so foreign entries (Workflow-owned,
  user-owned) keep their JSON content untouched. The document is
  re-serialized canonically on write, so byte-level formatting of the file
  is not preserved (and is not claimed); entry content is. Re-install is
  idempotent; uninstall removes only that entry and our copies — a
  `hooks.json` that held nothing else is removed, and `.codex/` itself is
  left only while other content remains.
- Copies the payload to
  `<project_root>/.codex/kaola-project-runner/hooks/compact-recovery.md`, the
  emitter to `kaola-codex-compact-hook.py`, and the binding to
  `binding.json` beside them, so the hook does not depend on a checkout
  path; and keeps one content-addressed `hooks.json.kaola-backup-<sha12>`
  (atomic write, mode 0600) before rewriting an existing file. The hook
  command quotes its path with `shlex.quote`, so a project root containing
  shell metacharacters cannot change what the hook executes.
- Refuses atomically (no write of any file) on a malformed `hooks.json`,
  including JSON-null `hooks` or `hooks.SessionStart`.

### Trust and coexistence

Codex merges hook sources from all config layers (`~/.codex/hooks.json`,
project `.codex/hooks.json`, plugin-bundled, `config.toml`); our entry adds to
that set, never replaces it — the existing Workflow compact hook keeps firing
alongside it. Project-layer hooks load only while the project directory is
trusted, and entries added or changed under a trusted directory surface in
the Codex `/hooks` browser for review before they run — observed live: an
unreviewed project entry is installed but inactive. That approval is the host
owner's deliberate step, not something this installer performs; vetted
automation may instead launch Codex with `--dangerously-bypass-hook-trust`
for a single invocation without persisting trust. Two further live facts:
hooks are loaded at session start (an entry written mid-session applies from
the next session), and `codex resume` preserves the session id a binding is
tied to.

## Verified boundary

- Mechanism and live behavior proven in an isolated real `/compact` run
  against a scratch repository's project-layer `.codex/hooks.json`:
  `SessionStart(compact)` fired, the payload reached the model as
  `additionalContext` before the next reasoning turn (the model quoted
  `KPR-COMPACT-RECOVERY-V1`), and a foreign Workflow hook fired alongside
  ours. Unbound-session silence is proven by the contract suite; live it was
  additionally observed that an unreviewed project entry stays inactive —
  the trust gate, not the filter (evidence:
  `kaola-workflow/bundle-75/evidence/codex-compact-live/`).
- The installer itself performs no user-global write — the contract suite
  (`tests/contract/test-issue-75-codex-compact-hook.py`) proves merge safety,
  idempotency, two-project coexistence with local uninstall, the required
  Host binding (payload emitted only for the bound `session_id` + project
  root; silent for Worker, other repo, or non-compact sources), atomic
  refusal on malformed/null config, and payload content.
- Out of scope here: ZCode's compact carrier (see `docs/zcode-host.md` and the
  Issue #75 capability matrix — its 0.16.5 `SessionStart` has no `compact`
  call site), Grok Bot, and other native hosts.
