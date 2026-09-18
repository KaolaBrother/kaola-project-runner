# Validation receipts — Issue #75 candidate

Candidate: this freeze on `workflow/bundle-75` (outer-review repair rounds;
issue-meaning ACCEPT at `8168621`, then rebased onto current main).
Worktree: `.kw/worktrees/bundle-75`.

## Round: docstring accuracy fix (this freeze)

Frozen SHA: **`c96e605`** on `e6403ab` (`workflow/bundle-75`).

Outer review of `e6403ab`: the module docstring claimed "Nothing here
reads, prints, or forwards a credential" — overstated, since
`load_hooks()` must read the whole existing `hooks.json` to merge and a
foreign hook command may carry a credential. The sentence now states the
accurate boundary: reading the existing file is required to merge;
nothing prints, copies, or forwards foreign content; `status` never
writes. **Docstring-only diff** — code and test semantics identical to
`e6403ab`; `docs/codex-host.md` and `CHANGELOG.md` were checked and
already state the correct boundary ("never copies"/"never echoes"), so
they are untouched.

Receipts re-run on this SHA (docstring-only):
- `python3 scripts/render-skills.py --check` → **PASS** (budgets OK).
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` →
  **37/37 PASS**.
- `python3 tests/contract/test-issue-75-zcode-compact-recovery.py` →
  **15/15 PASS**.
- `git diff --check` → clean.
- Full `scripts/validate.sh`: **not re-run on this SHA** — the diff vs
  `e6403ab` is docstring-only; see the `e6403ab` round below for the last
  full PASS (exit 0, `residual_pids=[]`).

## Round: owned-leaf symlink containment (frozen e6403ab)

Frozen SHA: **`e6403ab`** on `cd52494` (`workflow/bundle-75`).

Outer review of `cd52494`: `containment_reason` covered `hooks.json` and
the asset dir, but the three owned leaves — `compact-recovery.md`,
`kaola-codex-compact-hook.py`, `binding.json` — could each be a symlink
pointing outside the project; `read_bytes`/`read_text` follow leaf links,
so a leaf pointing out would read foreign content (writes are
atomic-replace and safe). The leaves are now part of the same
`main`-level containment check before any action touches them.

Failure-first test (`test_leaf_symlink_cannot_escape_project_root`,
isolated fake HOME/CODEX_HOME): each leaf symlinked to an outside
secret-bearing file → all five actions refuse with the outside file
untouched; a leaf symlink staying inside the project still passes
status + prepare.

Receipts on this candidate:
- `python3 scripts/render-skills.py --check` → **PASS** (budgets OK).
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` →
  **37/37 PASS**.
- `python3 tests/contract/test-issue-75-zcode-compact-recovery.py` →
  **15/15 PASS**.
- `bash scripts/validate.sh` → **PASS** (exit 0): all lanes incl. i74
  (151 assertions), i81 acp contract (46), both i75 suites, i86/i90,
  `kaola-grok-bot-verify` PASS, sweep `residual_pids=[]`.
- `git diff --check` → clean.

## Round: in-project symlink containment (frozen cd52494)

Frozen SHA: **`cd52494`** on `0e897f5` (`workflow/bundle-75`).

Outer architecture review of `0e897f5` (comment 5737384678) reproduced a
P1: a project `.codex` symlinked to the effective `CODEX_HOME` made
`prepare` write `~/.codex`-equivalent `hooks.json`/assets and could let
`uninstall` delete global content — `resolve_root` checked only the root.

Fix: `containment_reason(root)` resolves `os.path.realpath` of the managed
paths — `.codex/hooks.json` and the Runner asset dir
(`.codex/kaola-project-runner/hooks`) — before ANY action's read, write,
or delete (wired once in `main` for prepare/install/bind/uninstall/
status); a path escaping the canonical root is refused. `realpath`
resolves every symlink component, so `.codex`, `kaola-project-runner`, or
`hooks` level links are all covered; a `.codex` symlink staying inside
the project remains legal. No Git-only requirement, no transport gate,
no new state.

Failure-first test (`test_codex_symlink_cannot_escape_project_root`,
isolated fake HOME/CODEX_HOME): all five actions refuse with the fake
global byte-identical and no `kaola-project-runner` dir created inside
it; a `.codex` symlink to an in-project dir still prepares + reports.

Receipts on this candidate:
- `python3 scripts/render-skills.py --check` → **PASS** (budgets OK).
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` →
  **36/36 PASS**.
- `python3 tests/contract/test-issue-75-zcode-compact-recovery.py` →
  **15/15 PASS**.
- `bash scripts/validate.sh` → **PASS** (exit 0): all lanes incl. i74
  (151 assertions), i81 acp contract (46), both i75 suites, i86/i90,
  `kaola-grok-bot-verify` PASS, sweep `residual_pids=[]`.
- `git diff --check` → clean.

## Round: three P2 hardening fixes (frozen 0e897f5)

Frozen SHA: **`0e897f5`** on `5a112f2` (`workflow/bundle-75`).

Outer review of `96707c4` (comment 5737328018) reproduced three P2s:

1. `status` echoed a same-ID entry's full config into the receipt — a
   foreign/secret-bearing `command` would leak to stdout/logs. Now the
   receipt carries safe metadata only (`entry_id`, `entry_hook_count`,
   presence/counts/paths); no entry content is ever echoed. Failure-first
   test: a `sk-fake-…` command in an our-ID entry never reaches stdout.
2. `--project-root $HOME` wrote `~/.codex/hooks.json` — user-global
   config. `resolve_root` now requires an existing directory and refuses
   before any write: the filesystem root, the user home directory, and the
   effective `CODEX_HOME` layer (the dir itself or the parent whose
   `.codex` IS that layer). Isolated-HOME test: all four paths refuse
   with zero writes. No Git-only requirement or transport gate added.
3. `install`/`bind` accepted blank/whitespace `--session-id`; `status`
   `bound` was true for any string id regardless of root. Both actions
   now refuse missing/blank ids; `bound` requires a non-empty
   `session_id` AND `project_root` equal to this project's canonical
   root. Failure-first cases cover `""`, `"   "`, tab, foreign root,
   missing root.

Receipts on this candidate:
- `python3 scripts/render-skills.py --check` → **PASS** (budgets OK).
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` →
  **35/35 PASS** (all prior + 5 new hardening tests).
- `python3 tests/contract/test-issue-75-zcode-compact-recovery.py` →
  **15/15 PASS**.
- `bash scripts/validate.sh` → **PASS** (exit 0): all lanes incl. i74
  (151 assertions), i81 acp contract (46), both i75 suites, i86/i90,
  `kaola-grok-bot-verify` PASS, sweep `residual_pids=[]`.
- `git diff --check` → clean.

## Round: final safe sync onto post-#81 main aa5fdad (frozen 5a112f2)

Frozen SHA: **`5a112f2`** on `aa5fdad990bf5f4b278853e2de0bd664a0c584b6`
(`workflow/bundle-75`, 13 commits replayed cleanly — zero conflicts).

#81 (native mid-turn steering, v4 command surface) landed on main; its
footprint (`kaola-zcode-acp.py`, generated holders, `platform.yaml`, zcode
steering reference, acp-contract tests) has zero file overlap with the #75
set. Coexistence verified item-by-item: #74 Delegator
(`templates/kaola-delegator` + `skills/kaola-delegator`), #90
(`test-issue-90-event-confirmation-race.py`), #81 steering, and all #75
Codex/ZCode compact + doc-maintenance surfaces present and tested.

Diff vs new main (`aa5fdad..5a112f2`): exactly the #75 file set —
18 files, +2176/−33 (hook script, payload template, codex/zcode host
docs, zcode-compact-recovery + doc-maintenance + host-startup refs in
template and rendered surfaces, SKILL.md/.tmpl delta, index entries,
validate.sh registrations, both contract suites). Boundary re-check:
every `.codex` path is project-relative; `${CODEX_HOME}`/`~/.codex`
appear only in "never writes" statements; no secrets in the script; no
registry/daemon/scheduler/extra gate added.

Receipts on this candidate:
- `python3 scripts/render-skills.py --write` → zero diff (already
  consistent); `--check` → **PASS** (9 workers + kaola-project-runner +
  kaola-delegator + grok-bot bridge; budgets OK).
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` →
  **30/30 PASS**.
- `python3 tests/contract/test-issue-75-zcode-compact-recovery.py` →
  **15/15 PASS**.
- `bash scripts/validate.sh` → **PASS** (exit 0): all lanes incl. issue-74
  (151 assertions), #81-expanded zcode-acp contract (46 tests), both i75
  suites, i86/i90, `kaola-grok-bot-verify` PASS, sweep
  `residual_pids=[]`, no env mitigation.
- `git diff --check` → clean.

Standing limitations (unchanged, honestly scoped): live evidence proves
bound-positive injection + trust gating + two-phase bootstrap + Worker
contrast; every-negative filter case is contract-proven, not each staged
live. ZCode 0.16.5 has no native compact hook — carrier is Skill-mediated.
Real-GLM automatic compaction remains pending user authorization.
`.zcode/AGENTS.md` claim corrected (user-global only; project path never
resolved). No finalize/sink/close performed; awaiting outer ACCEPT.

## Round: integration rebase onto main 745668f (frozen 96707c4→rebased)

Frozen SHA: **`96707c4`** on `745668fac17ebff98e9805ce0543f5359047c9c0`
(`workflow/bundle-75`, 13 commits: 12 replayed + 1 re-render).

Issue-meaning ACCEPT was granted at `8168621`; this round is the safe
integration rebase requested for parallel work while #81 validates
separately. 49-commit gap closed; #74 Kaola-Delegator and #90 Host event
fixes now share the tree with all #75 behavior.

Exact conflict choices (also in commit `96707c4` message):
- `149c397`: template hunks → main's #74/#90 text (my side was cosmetic in
  those regions; the old `grok-bot-host.md` reference legitimately moved
  into `templates/kaola-delegator/`); generated `skills/SKILL.md` →
  `--theirs` then re-rendered; `README.md`/`docs/README.md`/`CHANGELOG.md`
  → union; `scripts/validate.sh` → union sorted (all suites both lanes).
- `7c1b5c6`: `SKILL.md.tmpl` → main's ZCode Host paragraph +
  `zcode-compact-recovery.md` reference appended.
- `b3aa648`: `validate.sh` → union + zcode suite. Commits 8–12 clean.
- Re-render delta: `skills/kaola-project-runner/SKILL.md` only → commit
  `96707c4`.

Receipts on this candidate (post-integration tree):
- `python3 scripts/render-skills.py --write` + `--check` → **PASS**
  (renders 9 workers + `kaola-project-runner` + **`kaola-delegator`** +
  grok-bot bridge; budgets OK). Delegator proof path now asserts against
  the REAL generated `references/handoff.md` (`orchestrator-main` present).
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` →
  **30/30 PASS**.
- `python3 tests/contract/test-issue-75-zcode-compact-recovery.py` →
  **15/15 PASS** (Delegator conditional now exercises the real surface).
- `bash scripts/validate.sh` → **PASS** (exit 0): all lanes incl. issue-74
  (151 assertions), both i75 suites, i86/i90, `kaola-grok-bot-verify` PASS,
  sweep `residual_pids=[]`.
- `git diff --check` → clean.

No semantic incompatibility found — all conflicts were wording/adjacency;
no #75 semantic content was dropped (verified by the focused suites plus
the Delegator-path test running against the real generated file).

Holding for outer review; one final safe sync remains after #81 lands
before Workflow finalize. No finalize/sink performed.

## Round: strict bound-shape classification in prepare (frozen 8168621→rebased)

Frozen SHA: **`8168621`** on `2a4f04a` (`workflow/bundle-75`).

Outer-review finding on `2a4f04a`: `prepare` treated ANY string
`session_id` as a valid bound Host — including `{"session_id":"host-A"}`
with no `project_root`, empty `""`, and whitespace-only ids — and reported
`binding_preserved` while `emit` could never match, silently leaving broken
recovery.

Fix: `prepare` preserves byte-for-byte ONLY a binding holding a non-empty
non-whitespace `session_id` AND this project's canonical `project_root`
(the exact pair `emit` matches on). Every other bound-looking shape —
missing/wrong root, empty/whitespace id, non-string id, non-dict,
unparseable — refuses before any write. Inert `session_id:null` (with
matching or absent root) is still rewritten canonically; `install`/`bind`
with explicit `--session-id` unchanged.

New deterministic cases in `test_prepare_refuses_ambiguous_binding`:
`{"session_id":"host-A"}` (no root), `{"session_id":""}`, whitespace-only
id — each refuses pre-write with the file untouched and no `hooks.json`
created. `test_prepare_preserves_existing_binding` still proves the valid
shape stays byte-identical and same-session emit still fires.

Receipts on this candidate:
- `python3 scripts/render-skills.py --check` → **PASS** (budgets OK).
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` →
  **30/30 PASS**.
- `python3 tests/contract/test-issue-75-zcode-compact-recovery.py` →
  **15/15 PASS**.
- `bash scripts/validate.sh` → **PASS** (exit 0): all lanes,
  `kaola-grok-bot-verify` PASS, sweep `residual_pids=[]`.
- `git diff --check` → clean.

Integration note (per outer review): this branch is 49 commits behind main
and predates #74 Delegator generation; no current-integration claim is
made from this old-base render. Rebase onto then-fresh main (after #81
sink), re-render, re-validate, and verify both generated Skills is a
post-ACCEPT step before Workflow finalize.

## Round: prepare-must-never-unbind + no config backup copies (frozen 2a4f04a)

Frozen SHA: **`2a4f04a`** on `b16f4b3` (`workflow/bundle-75`).

Two release-blocking findings on `930df9a` (comment 5736936715):

1. `prepare → bind Host-A → prepare` silently rewrote `binding.json` back to
   `session_id:null`, unbinding a live Host. Now `prepare` classifies any
   existing `binding.json` BEFORE any write: a valid bound binding for this
   project is preserved byte-for-byte (`binding_preserved` in the receipt);
   an unparseable, non-dict, non-string-id, or other-project binding is
   refused; `install`/`bind` with an explicit `--session-id` still overwrite
   by operator choice.
2. `write_backup` copied the whole foreign `hooks.json` into
   `hooks.json.kaola-backup-<sha12>` — duplicating possibly credential-
   bearing config into an unignored residue file that survived uninstall.
   Mechanism removed entirely (atomic mkstemp+replace remains the only
   write); no backup copy is ever made. `hashlib` import and all
   backup claims removed from script/docstring/docs/CHANGELOG.

Regression coverage (`test_no_backup_copy_of_config_is_made`,
`test_prepare_preserves_existing_binding`,
`test_prepare_refuses_ambiguous_binding`): secret-bearing foreign config is
preserved in-place with zero copies after install/re-install/uninstall;
bound `prepare` keeps `binding.json` byte-identical and the same bound
session still emits; all malformed/ambiguous binding shapes refuse before
any write.

Receipts on this candidate:
- `python3 scripts/render-skills.py --check` → **PASS** (budgets OK).
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` →
  **30/30 PASS** (all prior coverage plus the three new regression tests).
- `python3 tests/contract/test-issue-75-zcode-compact-recovery.py` →
  **15/15 PASS**.
- `bash scripts/validate.sh` → **PASS** (exit 0): all lanes incl. both i75
  suites, `kaola-grok-bot-verify` PASS, sweep `residual_pids=[]`, no env
  mitigation.
- `git diff --check` → clean.

## Round: outer-review P1s → project-layer + two-phase bootstrap

Scope (three review findings absorbed into the in-flight item):

1. Global `CODEX_HOME/hooks.json` entry injected Runner recovery into ANY
   Codex session → replaced by per-project `<repo>/.codex/hooks.json` +
   project-private assets (`<repo>/.codex/kaola-project-runner/hooks/`:
   payload, emitter, `binding.json`). Host-only filter: emit prints the
   payload only for `SessionStart(compact)` whose stdin `session_id` +
   realpath `cwd` match the binding.
2. Single global binding could not hold two projects (B install overwrote
   A; B uninstall stripped A) → project layer removes the shared file
   entirely; nothing writes `${CODEX_HOME}`/`~/.codex`.
3. First-session bootstrap cycle (hooks load at session start; id only
   knowable after start) → two-phase `prepare` (inert `session_id:null`
   binding before launch) + `bind` (writes ONLY `binding.json`; hooks.json
   byte-identical). `install` remains the one-shot prepare+bind.
   `CODEX_SESSION_ID`/`CODEX_THREAD_ID` inside the Codex host shell
   verified equal to the rollout/hook-stdin `session_id` (live, masked).
- Null-shape validation unchanged: `hooks`/`SessionStart` JSON-null refused
  before ANY write (install/prepare/bind/uninstall/status alike).

Receipts on this candidate:
- `python3 scripts/render-skills.py --check` → **PASS** (budgets OK).
- `python3 -m pytest tests/contract/test-issue-75-codex-compact-hook.py` →
  **27/27 PASS** (incl. two-phase bootstrap, bind-only binding write,
  A/B coexistence + local uninstall, Host/Worker/other-repo emit filter,
  null/malformed atomic refusal, metachar quoting, 0600 backup).
- `python3 -m pytest tests/contract/test-issue-75-zcode-compact-recovery.py`
  → **15/15 PASS**.
- `bash scripts/validate.sh` → **PASS** (exit 0): all lanes incl. both i75
  suites, `kaola-grok-bot-verify` PASS, sweep `residual_pids=[]`, no env
  mitigation.
- `git diff --check` → clean.
- Live: two-phase bootstrap proven in real Codex 0.153.4 on scratch repo —
  see `codex-compact-live/FINDINGS.md` Round 3 (inert first compact → KW
  only; bind; second compact same session → KW+KPR; Worker session → KW
  only).

## Round: Delegator-path proof detail (frozen b16f4b3 on 930df9a)

Outer-review defect: the reusable ZCode durable block allowed
`kaola-delegator` as the installed Skill but ordered the Host to quote a
marker inside `references/zcode-compact-recovery.md` — a file only
`kaola-project-runner` ships (generated `kaola-delegator` carries SKILL.md +
`references/handoff.md` + agents yaml). Fixed generically: the durable block
and the per-send carrier now ask for the checkable detail that exists for
the Skill in use — `KPR-SKILL-RELOAD-V1` in
`references/zcode-compact-recovery.md` for `kaola-project-runner`, or the
Host naming convention (`zcode-<PROJECT_CODE>-orchestrator-main`) inside
`references/handoff.md` for `kaola-delegator`. Codex payload needed no
change (no marker-file claim). No consuming `AGENTS.md` written.

Receipts on this candidate:
- `./scripts/render-skills.py --write` + `--check` → **PASS** (budgets OK).
- `pytest tests/contract/test-issue-75-codex-compact-hook.py` → **28/28**
  (new `test_proof_detail_exists_for_each_installed_skill`: durable block +
  carrier name `references/handoff.md`/`orchestrator-main` for the Delegator
  and never `kaola-delegator's references/zcode-compact-recovery.md`;
  runner path verified against the rendered surface; Delegator file
  existence asserted whenever the generated `kaola-delegator` surface is
  present on the branch — it lands via main's #74/#86).
- `pytest tests/contract/test-issue-75-zcode-compact-recovery.py` → 15/15.
- `bash scripts/validate.sh` → **PASS** (exit 0, `residual_pids=[]`, no env
  mitigation). One earlier run hit a flaky
  `test-acp-follow-contract.py` timing failure (`prompt` on follow FD
  answered `delta` not `error`); the suite is unrelated to this diff and
  passed 12/12 standalone plus in the re-run — recorded as flake.
- `git diff --check` → clean.

## Fix round on d727e1f → 78a0dfe (outer-review findings)

- `hook_entry` command was `cat "{path}"` — a metacharacter-bearing
  `CODEX_HOME` could be reinterpreted by the shell at hook execution. Now
  `cat {shlex.quote(str(payload_path))}`.
- `backup.write_bytes` inherited umask (0644 risk for mirrored config). Now
  `write_backup()` reuses the atomic mkstemp+replace writer at mode 0600.
- "byte-for-byte" corrected everywhere it appeared: entries keep their JSON
  content; the file is re-serialized canonically (script docstring,
  `docs/codex-host.md`, `CHANGELOG.md`, test docstring, this file).
- New contract tests: `test_metachar_home_command_quotes_and_only_reads`
  (install under `odd "q" $(touch PWNED)'s`, asserts the stored command is
  the shlex-quoted path, runs it via `/bin/sh -c`, asserts stdout equals the
  payload and no `PWNED` exists anywhere under the fixture) and
  `test_backup_is_written_0600` (install + uninstall backup paths).

## Receipts on 78a0dfe

- `python3 scripts/render-skills.py --check` → **PASS**.
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` → **12/12 PASS**
  standalone and inside the gate.
- `bash scripts/validate.sh` → **PASS** (exit 0): all lanes completed,
  `kaola-grok-bot-verify` PASS, `git diff --check`/`--cached` clean, sweep
  `residual_pids=[]`. Same env-only `GIT_CONFIG gc.autoDetach=false`
  invocation as below — see flake (b); the #49 teardown race remains a
  pre-existing base issue, not claimed green without the mitigation.

## Receipts on d727e1f (superseded, kept for history)

- `python3 scripts/render-skills.py --check` → **PASS** (9 workers +
  kaola-project-runner + grok-bot bridge; budgets OK; main SKILL.md 17392/17408 B,
  references/doc-maintenance.md 2501/8192 B).
- `python3 tests/contract/test-issue-75-codex-compact-hook.py` → **10/10 PASS**
  (install, idempotency `changed:false`, foreign-entry JSON preservation, malformed
  refusal, uninstall, payload content, generated doc-maintenance surfaces, budgets).
- `bash scripts/validate.sh` → **PASS** (exit 0): render --check, 11× validate-skill,
  bash -n, installer migration + runtimes, all 34 contract suites replayed,
  `kaola-grok-bot-verify` PASS, `git diff --check`/`--cached` clean,
  Issue #63 sweep `residual_pids=[]`.
  Invocation carried env-only `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=gc.autoDetach
  GIT_CONFIG_VALUE_0=false` — see flake (b) below. No repo file was changed for it.

## Rebase record

- Worktree was 26 commits behind / 0 ahead; fast-forwarded `3dd7e5e → f6be8a3`,
  then `f33a377` committed, then rebased onto `f6cbe27` after #78's sink landed.
- One conflict: `CHANGELOG.md` (both entries wanted the Unreleased top) — resolved
  newest-first, both entries kept verbatim. `scripts/validate.sh` auto-merged
  (#78 added its heredoc suite to lane A/B/all; #75 added its suite to lane B/all —
  disjoint insertions, both present).

## Pre-existing flakes A/B-proven against the base (not caused by #75)

(a) `test-issue-50-runner-integration.py` `test_pty_fallback_stays_explicit` —
    60 s timeout on `runtime-tmux.sh status --transport pty`, observed only while
    the worktree carried the pre-#78 `kaola-tmux.sh` (heredoc body >512 B pipe
    deadlocking `write()` under macOS pipe pressure — the exact bug #78 fixed).
    After rebase onto `f6cbe27`: **7/7 tests, 182 checks PASS** standalone and
    inside the full gate.

(b) `test-issue-49-grok-bot-host.py` —
    `Issue49PinModel.test_content_stage_is_not_saveable_and_require_pinned_refuses_it`
    errors in `TemporaryDirectory` teardown: `OSError [Errno 66] Directory not
    empty` on `<fixture>/repo/.git` during `rmtree`. Cause: the fixture copies the
    whole project, so its `git add`/`commit` crosses the auto-gc threshold; git's
    default `gc.autoDetach=true` leaves a detached `git gc --auto` still writing
    `.git` while `rmtree` runs. Reproduces **identically on main `f6cbe27` without
    the #75 diff** (3/3 standalone runs) and 0/3 with env `gc.autoDetach=false`.
    Reported here for the outer review/repo owner — the fix (set `gc.autoDetach`
    false in test env or wait-for-gc in teardown) belongs to #49's suite, outside
    the #75 frontier.

## Candidate scope vs main (`git diff main --stat` at 78a0dfe: 12 files, +788/-27)

CHANGELOG.md, README.md, docs/README.md, docs/codex-host.md (new),
scripts/kaola-codex-compact-hook.py (new), scripts/validate.sh (+2 registrations),
skills/kaola-project-runner/SKILL.md (generated), skills/kaola-project-runner/
references/doc-maintenance.md (generated, new), templates/codex-host/
compact-recovery.md (new), templates/orchestrator/SKILL.md.tmpl,
templates/orchestrator/references/doc-maintenance.md (new),
tests/contract/test-issue-75-codex-compact-hook.py (new).

## Round: ZCode live carrier + rebase onto latest main (frozen at 7c1b5c6)

Rebase: replayed onto `b40813f` (#79), then `c963bad` (#80 — its
`maintenance.auto=false` fixture fix resolves the #49 teardown race
documented above; the env-only mitigation is no longer needed), then
`88042cd` (#83 — lane-failure visibility; both `python_suites_all`
registrations kept). CHANGELOG conflicts resolved keeping every entry,
#75 newest-first. Final gate on `88042cd` rerun: `render --check` PASS,
i75 suite 15/15, `validate.sh` PASS exit 0 with **no env mitigation** —
unqualified green.

Live experiment (isolated scratch repo `/tmp/kpr-i75-zcode/repo`, adapter
0.3.3 on ZCode 3.12.3/CLI 0.16.5, yolo): real `/compact` via session/prompt
-> `context_compaction`/`compaction` part rows (`trigger:"manual"`,
`auto:false`, `cmp_d814b072`) committed synchronously; counterfactual probe
recalled `ZEBRA-991` (summary preserves facts); carrier prompt -> real `read`
on planted SKILL.md -> `KPR-SKILL-RELOAD-7931`. Compaction invisible in
observe/capture/context_usage (detection premise revised). Exact stop:
`residual_pids=[]`. Evidence: `zcode-compact-live/`.

Post-change gate (all lanes):
- `render-skills.py --check` PASS (SKILL.md 17393/17408; new reference
  3104/8192; host-startup 7899/8192).
- `test-issue-75-codex-compact-hook.py` **15/15** (incl. new
  ZcodeCompactCarrierSurface: rendered carrier markers, host-startup
  pointer, budget).
- `test-progressive-disclosure.py` 21/21 — caught and fixed: every
  reference must be linked from SKILL.md; added the
  `](references/zcode-compact-recovery.md)` pointer funded by ~86 B of
  wording trims.
- `test-issue-41-orchestrator.py` 23/23 — caught and fixed: trims must not
  remove the pinned phrase "no suitable authorized work is executable"
  (restored; funded elsewhere).
- ZCode suites: test-zcode-acp-contract OK, test-zcode-host-contract 47
  checks, test-issue-65-host-contract OK, test-zcode-heartbeat-contract 166
  checks.
- `bash scripts/validate.sh` **PASS** on the final base `88042cd` (exit 0,
  all lanes incl. lane-B i75 suite, #83's new suite, grok-bot verify, sweep
  `residual_pids=[]`) — **no env mitigation, unqualified green**. Earlier
  runs for the record: `b40813f` PASS with `GIT_CONFIG gc.autoDetach=false`
  (pre-#80 flake), `c963bad` PASS unmitigated.

## Round 2 — native UserPromptSubmit hook (frozen `8b8abbc` on `88042cd`)

Isolated experiment, no worktree code changes beyond `docs/zcode-host.md`
wording (round-2 verdicts). Fixture: `/tmp/kpr-i75-native/` (scratch repo +
project `plugins.dirs` plugin + hook script + direct app-server driver
reusing the adapter's backend/auth helpers). User `cli/config.json` kept
`hooks:{}` throughout; no credentials copied/decrypted/logged.

Live results (evidence: `zcode-compact-live/FINDINGS-native-hook.md`,
`hook-invocations.jsonl`, `rpc-compact-events.jsonl`):
- `UserPromptSubmit` fires on every normal prompt — 7 invocations,
  3 sessions (`sess_194d7421`, `sess_8287b1f4`, `sess_25e3d20d`).
- Detection: read-only `MAX(time_created)` `part` query + hook-private
  cursor under `$ZCODE_PLUGIN_DATA`; injected once per episode
  (`inject:true` after each compaction, `false` otherwise); `/compact`
  itself bypasses the hook.
- Injection reaches the model: real `read` of planted SKILL.md +
  `KPR-SKILL-RELOAD-8842` quoted — after typed `/compact` AND after
  programmatic `session/compact` RPC (`compact_started`,
  `operationId compact_c3390f77`, summarization call, `turn.completed`;
  identical `trigger:"manual"` part records).
- Runtime auto compaction NOT triggered at bounded cost: GLM-5.3 climbed
  to 494,040 input tokens with zero compaction parts; live
  `contextWindow:1,000,000` (threshold ~966k+ => ~8M provider tokens);
  GLM-5.3-Flash (also 1M) absorbed 288,926 tokens. `trigger:"auto"`
  coverage inferred (same schema, trigger-agnostic read), not observed.
- Exact stop: `stopped:true` x2, `residual_pids:[]`, scratch repo clean.

Post-change gate (docs-only diff):
- `render-skills.py --check` PASS.
- `test-issue-75-codex-compact-hook.py` 15/15.
- `bash scripts/validate.sh` PASS (all lanes, sweep `residual_pids=[]`,
  no env mitigation).

## Round 3 — durable AGENTS-prefix carrier (frozen `e2a8316` on `88042cd`)

Isolated experiment, worktree delta limited to `docs/zcode-host.md`
(round-3 verdicts). Fixture: `/tmp/kpr-i75-native/repo` + planted
`AGENTS.md` (`KPR-AGENTS-DURABLE-5520` + standing instruction
`KPR-PREFIX-CARRIER-V1`); session `kpr-i75-agents` / `sess_4f59f76d`,
GLM-5.3, yolo. No user-global writes; no credentials touched.

Live results (evidence: `zcode-compact-live/FINDINGS-durable-prefix.md`):
- P0 pre-compact: model quoted `KPR-AGENTS-DURABLE-5520` (AGENTS prefix live).
- P1 `/compact`: real compaction `cmp_918b57d0`, `trigger:"manual"`,
  `standalone_turn`, `summarySource:"model"`, pre 6630 → post 18585.
- P2 post-compact, no carrier in prompt: model still quoted
  `KPR-AGENTS-DURABLE-5520` — **AGENTS prefix is durable across compaction**.
- P3 post-compact runner prompt, no carrier: `tool_calls:{read:1}` on the
  planted SKILL.md, `final_text` quoted `KPR-SKILL-RELOAD-8842` and
  reasoned "context was compacted" — **durable-prefix carrier works
  end-to-end; trigger-agnostic by construction** (covers any compaction
  incl. the first post-compact inference; zero hooks/detection/sends).
- P4: marker quoted; conservative re-read (correct, not minimal).
- BLOCKED fact (exact): no safe `trigger:"auto"` path — 1M windows on
  both catalog models (GLM-5.3 live `contextWindow:1,000,000`), ~8M
  provider tokens for threshold pressure, registry-owned model
  properties (no caller/contextWindow lever on `session/setModel`,
  `provider/updateAccountConfig`, config file, or `session/create`),
  reactive compact needs provider overflow at the same wall.
- Exact stop: `stopped:true`, `residual_pids:[]`, repo `dirty:false`.

Post-change gate (docs-only diff):
- `render-skills.py --check` PASS.
- `test-issue-75-codex-compact-hook.py` 15/15.
- `bash scripts/validate.sh` PASS exit 0 (all lanes, sweep
  `residual_pids:[]`, no env mitigation).

## Round 4 — real auto-compact leg (isolated MOCK provider, scratch HOME)

Live validation on installed ZCode 3.12.3/CLI 0.16.5, unpatched; session
`sess_c46bd933-b8fd-46e9-95d1-c7983a9e4577`; provider `mock-local/mock-small`
(MOCK OpenAI-compatible endpoint 127.0.0.1:8797, declared contextWindow 8192,
fake key) — transport only, real runtime compaction machinery.

- `auto-compact-parts.jsonl`: 7 completed `trigger:"auto"` compactions
  (`auto:true`, `phase:"pre_request"`, `compactReason:"context_limit"`,
  `status:"completed"`) — first live observation of auto-compact records.
- `mock-requests.jsonl`: 16/16 conversation inferences carry the
  `# agentsMd` durable prefix (incl. every post-compact request); the only
  `false` is an off-band title-generation call. Post-compact requests carry
  the runtime continuation header while the prefix precedes it unchanged.
- Isolation: scratch `HOME` only; personal `~/.zcode` untouched
  (`hooks:{}` unchanged); no credentials copied/decrypted/logged; mock
  localhost-only; exact stop `residual_pids:[]`.
- Pairing: wire-level `trigger:"auto"` prefix survival (this leg) +
  real-GLM manual-compact Skill-read (round 3) = Candidate A coverage.

Post-change gate (docs-only diff vs e2a8316):
- `render-skills.py --check` PASS.
- `test-issue-75-codex-compact-hook.py` 15/15.
- `bash scripts/validate.sh` PASS exit 0 (all lanes, `residual_pids:[]`,
  no env mitigation).
