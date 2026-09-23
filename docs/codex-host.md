# Codex Host (Issues #75, #97)

Codex is a first-class consuming runtime for the generated Skills and the host
whose post-compaction recovery this page adapts. It covers the Codex host
surface: skill installation and the two Runner-owned `SessionStart(compact)`
recovery entries — the **user-level** entry that `--runtime codex` installs
(Issue #97, the default) and the **project-level** bound-Host entry (Issue #75,
kept for direct Project Runner Hosts). Codex can also run as an ACP-started,
event-driven Project Runner Host (Issue #126): every turn opens with
`$kaola-project-runner`; entry and evidence are in the main Skill's
`references/host-entry-matrix.md`.

## Skill installation

`./scripts/install-local.sh --runtime codex` installs the generated Skills into
`${CODEX_HOME:-~/.codex}/skills` — `kaola-project-runner`, `kaola-delegator`
(when `zcode` is in the plan), plus the ten `<platform>-kaola-project-runner`
workers as sibling directories — and, whenever the control-plane Skills are in
the plan, the user-level recovery entry described next. `--method link|copy`
and `--bin-links` behave as documented in the installer reference. A generic
`--skills-dir` destination is never a Codex user-level install: it touches no
`hooks.json` anywhere, even when the path happens to be under `~/.codex`.

## Compact recovery: `SessionStart(source=compact)`

A Codex Agent that uses Project Runner or Kaola-Delegator runs across many
issues and worker rounds; after context compaction the previously read Skill
text cannot be assumed present. Codex fires `SessionStart` hooks with source
`compact` after a compaction — including an automatic one in the middle of a
turn — and delivers each hook's stdout as developer `additionalContext` before
the next model request (codex-cli 0.153.4 and 0.155.1 verified live;
developers.openai.com/codex/hooks). Codex discovers hooks beside every active
config layer — `~/.codex/hooks.json`, project `.codex/hooks.json`, plugins,
`config.toml` — and merges them: a higher layer never replaces a lower one.

### User-level entry (Issue #97) — the default

An outer Codex Agent that loaded the installed `kaola-delegator` delegates
projects from whatever repository it happens to be in, and may delegate several
projects in one session. A per-project hook cannot follow it, and asking the
operator to install a hook into every delegated repository is not a contract.
The installer therefore places **one** Runner-owned entry, id
`kaola-project-runner:user-compact-context`, into the official user-level
`${CODEX_HOME:-~/.codex}/hooks.json`, with private asset copies under
`${CODEX_HOME:-~/.codex}/kaola-project-runner/hooks/` (`compact-recovery-user.md`
and the emitter copy `kaola-codex-compact-hook.py`).

The entry's command runs `user-emit`, which prints the short payload
(`templates/codex-host/compact-recovery-user.md`, about 1.2 KB, far below the
default 2500-token `additionalContext` threshold) on **every**
`SessionStart(compact)`. The payload, not a session filter, carries the
condition: a session that was already using `kaola-delegator` or
`kaola-project-runner` before the compaction re-reads that installed Skill
completely from its installed directory and continues from existing records —
current authorization, the live ACP session and Runner `status` receipts, and
Git, worktree, Workflow, and Issue records — without re-intake, re-claim, a
second Host, resent prompts, or re-dispatch of in-flight work. Every other
session ignores it: no delegation or project work starts, and neither a role
nor a project is ever inferred from the working directory. The user layer keeps
no binding table, session registry, cwd map, or heartbeat.

```bash
# Installed and removed by the Codex destination of the installer:
./scripts/install-local.sh --runtime codex               # … plus "codex user hook: {…}" receipt
./scripts/install-local.sh --runtime codex --uninstall   # removes only that entry and its assets

# The same actions directly (default target ${CODEX_HOME:-~/.codex}; --codex-home overrides):
python3 scripts/kaola-codex-compact-hook.py user-status    [--codex-home DIR]   # read-only, echo-safe
python3 scripts/kaola-codex-compact-hook.py user-install   [--codex-home DIR]
python3 scripts/kaola-codex-compact-hook.py user-uninstall [--codex-home DIR]
```

- **Merge by owned id.** The entry is matched by id only. The Kaola Workflow
  user hook (`kaola-workflow:compact-context`), user-owned entries, and every
  other event list keep their JSON content untouched; the document is
  re-serialized canonically on write, so byte formatting is not preserved (and
  not claimed). Re-install is idempotent (`changed: false`, byte-identical
  file). No backup copy of `hooks.json` is ever made; `user-status` reports
  presence and counts but never any entry's `command`. A malformed
  `hooks.json` — including JSON-null `hooks` or `hooks.SessionStart` — is
  refused before any write. `user-status` also lists `install_blockers` (a
  missing payload template, a non-directory where the asset directory must
  go, a non-file at an owned leaf, an unwritable home), `user-install`
  refuses on any of them with a receipt rather than a traceback, and the
  installer plans both refusals before its first Skill write, so a broken
  user configuration aborts the whole install with nothing written.
- **Boundaries.** The Codex home must already exist; the filesystem root and
  the user home directory itself are refused, as is any managed path whose
  real path escapes the Codex home (a symlinked `hooks.json` pointing
  elsewhere). `--project-root` and `--session-id` are refused at the user
  layer; `--codex-home` is refused by the project actions. Nothing scans or
  rewrites other repositories.
- **Trust is the host owner's step, and it is not silent.** Codex requires a
  non-managed hook to be reviewed and trusted against its current definition
  before it runs; a new or changed entry is marked for review and skipped
  until trusted, and hooks load at session start. So recovery is **not**
  active before the install, not while the entry is untrusted, and not in the
  session that ran the install. Observed live on a fresh Codex home: the next
  `codex` launch shows *"Hooks need review — N hooks are new or changed"* with
  *Review hooks / Trust all and continue / Continue without trusting*, the
  `/hooks` browser lists our entry as *User config … hooks.json*, command
  `python3 …/kaola-project-runner/hooks/kaola-codex-compact-hook.py user-emit`,
  and `t` trusts it; afterwards only a *modified* entry is flagged again, and
  ours stays trusted across sessions. Until then the Skill can always be
  re-invoked explicitly. The installer prints exactly this: *review and trust
  the new entry in /hooks; it loads from the next Codex session*. Vetted
  automation may pass `--dangerously-bypass-hook-trust` for one invocation.

### Project-level entry (Issue #75) — direct Hosts, legacy

The project layer stays fully supported for a **direct Project Runner Host**
that lives in one repository: `prepare` writes the entry
`kaola-project-runner:compact-context` plus assets into
`<project_root>/.codex/hooks.json` and
`<project_root>/.codex/kaola-project-runner/hooks/` with an inert binding,
`bind`/`install` bind the exact designated Host session id, and its `emit`
prints the project payload (`templates/codex-host/compact-recovery.md`) only
for `SessionStart(compact)` on that bound session at that canonical root.

```bash
python3 scripts/kaola-codex-compact-hook.py prepare   --project-root <canonical project root>
# … start the designated Codex Host …
python3 scripts/kaola-codex-compact-hook.py bind      --project-root <root> --session-id <host session id>
python3 scripts/kaola-codex-compact-hook.py install   --project-root <root> --session-id <host session id>  # prepare+bind
python3 scripts/kaola-codex-compact-hook.py status    --project-root <root>   # read-only
python3 scripts/kaola-codex-compact-hook.py uninstall --project-root <root>   # ours only
```

Inside the Codex host's own shell, `CODEX_SESSION_ID` and `CODEX_THREAD_ID`
both carry the session identity that the hook input delivers as `session_id`
(verified live; never printed by this tooling). The id is bound only by an
explicit operator `bind`/`install`; nothing auto-claims a session and Workers
are never bound. Everything else the project layer guarantees is unchanged:
project-only writes (`--project-root` refuses the filesystem root, the home
directory, and the effective `CODEX_HOME` layer), symlink containment inside
the project root, echo-safe `status`, `prepare` never silently unbinding a live
Host, atomic refusal on malformed config, and no backup copies.

### Coexistence and migration

Both layers can be installed at once, and one compaction must not inject two
Runner blocks. The user-level `user-emit` therefore stays silent **exactly**
when the session's `cwd` holds a Runner project entry whose `binding.json`
names that very `session_id` with `cwd` as the canonical root — the same
predicate the project `emit` fires on. A bound direct Host receives only the
project block; a Worker session, a session in any other repository, a
subdirectory of the bound root, an inert (`prepare`-only) binding, a binding
that names another root, or an unreadable binding all receive the user block.
The Kaola Workflow user hook fires alongside either, untouched.

Migration is per repository and explicit — nothing is scanned or rewritten in
bulk: once the user-level entry is installed and trusted, a project whose
project-level entry is no longer wanted runs
`python3 scripts/kaola-codex-compact-hook.py uninstall --project-root <root>`
and the user layer carries that project from the next compaction on. The one
gap to know about is trust, which the emitters cannot observe: if a project
entry is bound but still unreviewed in `/hooks`, that bound session gets the
project block only after the entry is trusted (the user block yields to the
binding) — trust it or uninstall it.

## Verified boundary

- **User layer, live (evidence
  `kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/`).**
  Isolated `CODEX_HOME` (auth linked, never read) preset with the Kaola
  Workflow user hook and a user-owned entry, then the real installer
  (`--runtime codex --platform zcode`): only our entry and assets were added.
  First launch (codex-cli 0.153.4): *Hooks need review — 3 hooks are new or
  changed*; reviewed and trusted in `/hooks` (`Installed 3 / Active 3`); a
  later modification of the foreign entry flagged only that hook, ours stayed
  trusted. Real `/compact` runs, each with the `compacted` record and the
  developer `additionalContext` messages in the rollout: an ordinary session
  (0.153.4, no Skill in use) received the Workflow block and ours and answered
  that no Skill file was read, no delegation or Host started, no action taken;
  two outer Delegator sessions in two unrelated scratch repositories (0.155.1)
  received both blocks and each re-read the installed
  `<CODEX_HOME>/skills/kaola-delegator/SKILL.md` — a real `CommandExecution`
  after the `compacted` record — and contacted no Host; a Project Runner
  session (0.155.1) re-read `<CODEX_HOME>/skills/kaola-project-runner/SKILL.md`
  the same way (its final self-report was cut short by the operator's `/quit`,
  recorded as `turn_aborted`; the re-read itself is in the rollout); and in a
  repository carrying a legacy project-level entry bound to that session
  (0.155.1) the rollout holds the Workflow block plus the **project** block and
  no user block — one Runner block, none lost. Codex self-updated 0.153.4 →
  0.155.1 between the first and second live session.
- **User layer, contract** (`tests/contract/test-issue-97-codex-user-compact-hook.py`,
  `tests/contract/test-installer-runtimes.sh`): merge safety and idempotency
  against a preset Workflow + user-owned `hooks.json`, no backup copy,
  malformed/null refusal before any write, option refusals across layers,
  symlink escape refusal, `user-emit` on `SessionStart(compact)` only from any
  cwd, the deferral predicate above in every direction, payload pins, and the
  installer boundary (`--runtime codex` and the legacy default install it;
  `--no-orchestrator`, `--skills-dir`, and every other runtime never do; a
  malformed user `hooks.json` aborts before any Skill write).
- **Project layer** — mechanism and live behavior proven in the Issue #75
  isolated real `/compact` runs (`kaola-workflow/archive/bundle-75/evidence/codex-compact-live/`)
  and the contract suite `tests/contract/test-issue-75-codex-compact-hook.py`.
- Out of scope here: ZCode's compact carrier (see `docs/zcode-host.md` — its
  native `/kaola-project-runner` Skill entry, no hook), Grok Bot, and other
  native hosts.
