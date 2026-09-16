# Issue #49 delivery report

Candidate only. Stopped before Workflow finalize, merge, issue close, release,
and live Grok Bot UI enablement (manual UAT).

- Issue: https://github.com/KaolaBrother/kaola-project-runner/issues/49
- Branch: `workflow/bundle-49`
- Worktree: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/bundle-49`
- Candidate commit: `b746f7ba0e6d3da7c5155a21ea5cd6a35dbd991c` (supersedes `601e0045f88c8d854b29020ec505a7f0ab86239d`, which failed review F1)

## Root cause corrected

The first candidate equated a Cursor local-plugin path (`~/.cursor/plugins/local`, `.cursor-plugin/plugin.json`)
with Grok Bot registration. Owner UAT on Grok Bot 0.51.0 showed nothing under Settings → Plugins; read-only
checks showed neither Grok Bot nor Grok CLI reads that path; official docs describe an account-level,
cloud-hosted plugin surface. The owner is on an individual Ultra plan with no Team Marketplace and
redirected delivery to **one Grok Bot Private Skill**.

## What landed (commit `b746f7ba0e6d3da7c5155a21ea5cd6a35dbd991c`)

- `hosts/grok-bot/kaola-project-runner/`: one discoverable root `SKILL.md` (orchestrator template plus an
  embedded-worker routing table) with the seven workers under `workers/<id>/` as supporting resources
  (`SKILL.md` → `WORKER.md`; marker and `agents/openai.yaml` dropped; all other bytes identical to `skills/`).
  Still seven platforms, not an eighth; no worker is a separately discoverable Skill.
- `scripts/render-skills.py`: renders the payload from the shared templates (`{{HOST_WORKERS}}` token);
  Cursor plugin template and `kaola-grok-bot-assemble.py` removed.
- `scripts/install-local.sh --runtime grok-bot`: local execution copy only, under
  `${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}/skills/kaola-project-runner`; `--platform` and
  `--no-orchestrator` refused; no other Skill directory read or written; bin links off.
- `scripts/kaola-grok-bot-verify.py`: exactly one `SKILL.md`, seven embedded workers with contract,
  adapter, manifest and scripts, no plugin manifest, no sibling-Skill dependency, byte identity with
  `skills/`, no unofficial Sand API tokens in any payload text file.
- `scripts/kaola-grok-bot-package.py`: deterministic zip + `.sha256` for Settings → Plugins → Yours hand-off.
  This checkout: `kaola-project-runner-grok-bot-skill.zip`, 111 files, sha256 `9e9d29ed9079ac05c4ca2c947c8c963daf13c96b81b9694f8475d318f59d3b47` (identical on repeat runs).
- Docs (README, docs/api.md, docs/architecture.md, docs/conventions.md, docs/grok-bot-host.md, docs/README.md,
  CHANGELOG.md, AGENTS.md) and the orchestrator Hosts section / `references/grok-bot-host.md`: Private Skill
  via Settings → Plugins → Yours for individuals; Team Marketplace only optional on Teams/Enterprise; never a
  public Marketplace; Local Computer execution copy; live UI enablement remains UAT.
- Worker template: SKILL_DIR note now covers the embedded `workers/<id>/` form; no host policy in workers.

## Validation (worktree, 2026-09-15)

| Check | Result |
|---|---|
| `python3 scripts/render-skills.py --write` then `--check` | `render-skills: PASS (7 workers + kaola-project-runner + grok-bot private skill)` |
| `./scripts/validate.sh` | exit 0 (includes issue-49 20 tests, installer runtimes with new grok-bot cases, verifier PASS) |
| `python3 tests/contract/test-issue-49-grok-bot-host.py` | 20 tests OK |
| `bash tests/contract/test-installer-runtimes.sh` | PASS |
| `git diff --check` | clean |
| `templates/grok-golden/` | unchanged |
| Installer smoke (temp HOME): copy, refusals, link, uninstall | as documented; only `~/.kaola/grok-bot` created |

## Not done (manual UAT, owner)

1. Add the payload (zip above or the `SKILL.md` tree) under Grok Bot Settings → Plugins → Yours as a private
   skill and enable it for the Bot; confirm `/` offers Project Runner with no separate worker Skill.
2. Routine fires in the same Bot conversation.
3. Local Computer runs `~/.kaola/grok-bot/skills/kaola-project-runner/workers/<id>/scripts/runtime-tmux.sh`
   against existing Mac sessions.
4. Takeover from a Codex heartbeat leaves busy workers running; worker `HUMAN_DECISION_REQUIRED` surfaces as
   Needs attention; frontier done does not self-finalize.

Independent review of `b746f7ba0e6d3da7c5155a21ea5cd6a35dbd991c` is pending (the earlier review verdict is bound to `601e004` only).

## Review-fix candidate `91b2e269c85ee617ec45d8ca34060c5c04662ef9` (2026-09-15)

Supersedes `b746f7ba0e6d3da7c5155a21ea5cd6a35dbd991c` as the Issue #49 candidate. Addresses only the two
should-fix findings (F1, F2) of the independent PASS-WITH-NOTES review recorded in `review-report.md`;
notes F3–F6 were not acted on. Mission List item 5 records this as a causal mission; item 4's result is
unchanged. Still a candidate: no finalize, merge, issue close, release, or Grok Bot UI operation.

### F1 — evidence boundary for the private-skill hand-off

Every surface that previously said the payload "enters through" / is "added under" Settings → Plugins →
Yours, or called that the "documented entry point", now states what the official Grok Bot docs support:
Yours is only the surface to review and enable plugins and private skills that already exist on the
account; no control to upload or import a local directory or archive is documented; the payload and zip
are a private-skill hand-off for the owner's manual UAT; no official ingestion entry point is claimed;
UAT step 1 records the exact outcome or gap. Surfaces changed: `README.md` (2 places), `CHANGELOG.md`,
`docs/README.md`, `docs/api.md`, `docs/architecture.md`, `docs/grok-bot-host.md` (new section heading,
UAT item 1, rollback), `scripts/install-local.sh` help, `scripts/kaola-grok-bot-package.py` docstring,
`templates/orchestrator/SKILL.md.tmpl` Hosts paragraph, `templates/orchestrator/references/grok-bot-host.md`,
and the regenerated `skills/kaola-project-runner/` + `hosts/grok-bot/kaola-project-runner/` copies.
New test `test_yours_is_a_review_surface_not_a_claimed_upload_entry_point` rejects the over-claim
phrasings on all of those surfaces and requires the boundary clauses; it fails on `b746f7b`.

### F2 — payload integrity against the shared generation source

- `scripts/kaola-grok-bot-verify.py --repo <checkout>` now loads that checkout's `render-skills.py`,
  re-renders `expected_grok_bot_host_files(...)` from `templates/`, `platforms/`, `scripts/`, and requires
  the whole `hosts/grok-bot/` file map (root `SKILL.md`, `agents/openai.yaml`, `references/`, every
  embedded worker resource) to match byte-for-byte: missing, unexpected, and differing files are each a
  finding. Independent of `--repo` it now also refuses any symlink and requires executable bits only on
  `.sh` files. The PASS line says `generated state` or `shape only; pass --repo to prove generated state`.
- `scripts/kaola-grok-bot-package.py` always runs the `--repo` proof before zipping and refuses with
  `refusing to package a payload that is invalid or drifts from the generated state of <repo>`; a
  successful run prints `verified: generated state of <repo>`.
- New tests (class `Issue49PayloadIntegrity`): root `SKILL.md` append, `agents/openai.yaml` edit, root
  reference edit, `WORKER.md` edit, worker script edit, adapter edit, stray root file, stray worker file,
  missing reference, symlink at root, exec-bit flips both ways, packager refusal on edited root / stray
  file, and a template edit that `--check`, the verifier, and the packager all reject. All fail on
  `b746f7b`, pass on `91b2e26`.
- Renderer unchanged except being reused; `templates/grok-golden/` untouched (0 lines vs `main`).

### Validation (worktree, committed tree `91b2e26`)

| Check | Result |
|---|---|
| `python3 scripts/render-skills.py --write` then `--check` | `render-skills: PASS (7 workers + kaola-project-runner + grok-bot private skill)` |
| `./scripts/validate.sh` | exit 0 (all suites OK; issue-49 suite now 26 tests; verifier `PASS … generated state`) |
| `python3 tests/contract/test-issue-49-grok-bot-host.py` | 26 tests OK (20 previous + 6 new) |
| new tests against `git archive b746f7b` | 6 failures, exactly the 6 new tests |
| `bash tests/contract/test-installer-runtimes.sh` | PASS |
| `git diff --check main..HEAD` | clean |
| `git diff --stat main..HEAD -- templates/grok-golden` | empty |
| `python3 scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo .` | PASS (generated state) |
| `python3 scripts/kaola-grok-bot-package.py` | sha256 `3ae76a1eed3c8d0a64abb100a6408de5b95b4a596eccb89b957724a8b52c4e55` (changed from `9e9d29ed…` because the root `SKILL.md` and `references/grok-bot-host.md` text changed) |

### Remaining manual UAT (owner; unchanged in substance, item 1 reworded)

1. Attempt to establish the payload (zip above or the `SKILL.md` tree) as a private skill on the Bot.
   Settings → Plugins → Yours is the documented review/enable surface with no documented upload control;
   record the exact outcome or gap, including whether Project Runner appears under Yours and can be enabled.
2. `/` in that Bot offers Project Runner; no separate worker Skill is needed.
3. A Routine fires in the same Bot conversation.
4. Local Computer runs `~/.kaola/grok-bot/skills/kaola-project-runner/workers/<id>/scripts/runtime-tmux.sh`
   against existing Mac sessions.
5. Takeover from a Codex heartbeat leaves busy workers running; worker `HUMAN_DECISION_REQUIRED` surfaces as
   Needs attention; frontier done does not self-finalize.

Independent re-review of `91b2e26` is the orchestrator's call; this worker self-verified only.

## Correction candidate `4133601da64d653dd831071c7bd5c449ca6b3040` (2026-09-16)

Supersedes `91b2e269c85ee617ec45d8ca34060c5c04662ef9` as the Issue #49 candidate. Mission List item 6
is the causal mission. Trigger: owner UAT of `91b2e26` returned **PARTIAL** (zip integrity, one root,
seven embedded workers PASS; `GROK_BOT_PRIVATE_SKILL_INGESTION_GAP`: a Grok Bot private skill is one
single Markdown — name, description, body — saved by the Bot's `update_state` skill write; no ZIP or
file-tree import; Settings > Plugins > Yours has no import tool). Recorded verbatim in Issue #49
(`kw:uat`), never rewritten as PASS. Three owner corrections followed (Issue #49 `kw:correction`
comments): eight standalone single-Markdown Private Skills instead of one payload (an intermediate
"one huge Markdown" direction was stopped before any write); Grok Bot installs them itself from the
repo via a bootstrap guide; one canonical Skill system with Grok Bot as a host packaging adapter.

### What landed

- `scripts/render-skills.py`: delimited **"Host adapter: grok-bot"** section (`GROK_BOT_ADAPTER_INPUTS`
  = `templates/orchestrator`, `templates/SKILL.md.tmpl`, `templates/agents`, `templates/references`,
  `platforms`, `scripts`, plus `templates/grok-bot` holding only install prose). No
  `platforms/grok-bot.yaml`, no `scripts/adapters/grok-bot.sh`. Products (all owned by `--write`,
  rejected on drift by `--check`):
  - `hosts/grok-bot/private-skills/<name>.md` — exactly eight: `kaola-project-runner` (orchestrator
    template rendered with a worker routing table by stable Skill name; two references bundled
    verbatim; no transport; no inlined worker text) and `<id>-kaola-project-runner` ×7 (canonical
    `skills/<id>-kaola-project-runner/SKILL.md` verbatim + a short adapter section with
    `SKILL_DIR="${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}/skills/kaola-project-runner/workers/<id>"`
    + `platform.md`/`transport.md`/`acp.md` bundled verbatim; no orchestrator policy). Sizes 24–27 KB.
  - `hosts/grok-bot/private-skills.json` — fingerprint manifest (name, description, role,
    platform_id, source, `file_sha256`, `body_sha256`; `skill_count` 8).
  - `hosts/grok-bot/INSTALL.md` — guide for Grok Bot itself (not a ninth Skill): verify `git rev-parse
    HEAD`, `render-skills.py --check`, `kaola-grok-bot-verify.py --repo`; read the eight files in order;
    eight skill writes with exact name/description/body; same-name update, never duplicate; idempotent;
    checklist `created/updated/FAILED/not attempted` with retry of failed rows only; verify eight under
    Yours and `/`; main dispatch by stable name to the Local Computer script; no public Marketplace, no
    unofficial API, no credentials, no ZIP import.
  - `hosts/grok-bot/kaola-project-runner/` — unchanged Local Computer runtime copy (Hosts prose
    regenerated); `--runtime grok-bot` installs only this copy (verified: temp HOME gains only
    `~/.kaola/grok-bot/skills/kaola-project-runner` + receipt; uninstall removes it).
- `scripts/kaola-grok-bot-verify.py`: eight-document shape (1+7, unique names = stems, frontmatter,
  standalone: no `../`, no sibling `skills/<name>`, every `references/` link bundled, no file-tree
  links; main routes to all seven names and carries no transport markers / `WORKER.md`; workers carry
  no orchestrator markers, state their Local Computer location and all seven operations; with
  `--repo`, each worker doc begins with its canonical contract), manifest fingerprints, guide sources
  and clauses; `--repo` whole-bundle byte identity unchanged. Packager: docstring only (zips the
  runtime copy after the `--repo` proof; not an account import).
- Templates: `templates/orchestrator/SKILL.md.tmpl` Hosts section and
  `templates/orchestrator/references/grok-bot-host.md` describe the eight-Skill delivery; new
  `templates/grok-bot/INSTALL.md.tmpl`. `templates/grok-golden/` untouched.
- Tests (`tests/contract/test-issue-49-grok-bot-host.py`, 38 tests): new `Issue49AccountPrivateSkills`
  (exactly eight, 1+7, unique names, worker = canonical + location + references, main routes by name
  without transport or inlined workers, workers absorb no policy, standalone reassembly
  name/description/body, verifier rejections: ninth doc, missing worker, duplicate name, broken
  routing, absorbed transport/policy, unbundled reference, lost location, no frontmatter, drift; guide
  content and boundaries; install isolation) and `Issue49HostAdapterBoundary` (packaging adapter not a
  platform; adapter inputs; no second hand-written body — residue of each doc after removing canonical
  contract and references is one short adapter section; manifest matches documents and verifier
  rejects a wrong sha / missing entry; canonical edits to worker template, acp reference, codex
  manifest description, orchestrator template and host reference propagate to every account product
  and `--check` flags them stale first). Existing tests updated to the new bundle shape.
- Docs: `README.md`, `CHANGELOG.md`, `docs/README.md`, `docs/api.md`, `docs/architecture.md` (new
  "Host adapters: one canonical Skill system"), `docs/conventions.md`, `docs/grok-bot-host.md`
  (rewritten: delivery shape, Grok Bot self-install, adapter principle, UAT), `AGENTS.md` snapshot,
  installer help.

### Validation (worktree, committed tree `4133601`)

| Check | Result |
|---|---|
| `python3 scripts/render-skills.py --write` then `--check` | `render-skills: PASS (7 workers + kaola-project-runner + grok-bot host: 8 private skills + runtime copy)` |
| `python3 scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo .` | `PASS … (8 private skill docs + manifest + install guide; runtime copy: 1 root skill, 7 embedded workers; generated state)` |
| `./scripts/validate.sh` | exit 0 (all suites OK; issue-49 suite 38 tests) |
| `python3 tests/contract/test-issue-49-grok-bot-host.py` | 38 tests OK |
| `bash tests/contract/test-installer-runtimes.sh` | PASS |
| new/updated tests against `git archive 91b2e26` | 14 fail (10 errors + 4 failures), all in the new/changed tests |
| `git diff --check` | clean |
| `git diff --stat main..HEAD -- templates/grok-golden` | empty |
| `platforms/`, `scripts/adapters/` | seven entries each; no grok-bot |
| `python3 scripts/kaola-grok-bot-package.py` (twice) | identical zip, sha256 `1ad06c995101a5d23af046a6111bf616abdbb4f7d87cd905ec11ef3989bf4ac0` |
| installer smoke, temp HOME | only `~/.kaola/grok-bot/skills/kaola-project-runner` (+ receipt) created; uninstall removes it |

### Not done (owner, morning UAT; nothing here is claimed)

Source for the Bot: worktree `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/bundle-49`,
branch `workflow/bundle-49`, commit `4133601da64d653dd831071c7bd5c449ca6b3040`, guide
`hosts/grok-bot/INSTALL.md`, documents `hosts/grok-bot/private-skills/*.md`, fingerprints
`hosts/grok-bot/private-skills.json`. Runtime copy on this Mac: `./scripts/install-local.sh --runtime grok-bot`.

1. Grok Bot follows `hosts/grok-bot/INSTALL.md` on Local Computer against `4133601`: verify step passes;
   eight skill writes; checklist with any FAILED rows and retries.
2. Yours lists exactly the eight names, enabled, no duplicates; `/` offers all eight.
3. Project Runner selects a worker by stable name and runs
   `~/.kaola/grok-bot/skills/kaola-project-runner/workers/<id>/scripts/runtime-tmux.sh` on Local Computer.
4. Routine same-conversation wake; takeover leaves busy workers; `HUMAN_DECISION_REQUIRED` → Needs
   attention; frontier done does not self-finalize.

Independent re-review of `4133601` is owed before finalize; this worker self-verified only. No finalize,
merge, issue close, release, or Grok Bot UI operation was performed.

## Review-fix candidate `aba7d74f1a28a58c13814b32031d6bebbc5ab619` (2026-09-16)

Supersedes `4133601da64d653dd831071c7bd5c449ca6b3040` as the Issue #49 candidate. Mission List item 6
remains the causal mission (review round, not a new mission). Trigger: the independent review of
`4133601` (Issue #49 comment 5684635088, verdict PASS offline) flagged **F3**, a cheap and UAT-relevant
ambiguity: the main document `hosts/grok-bot/private-skills/kaola-project-runner.md` carries a quoted
frontmatter scalar (`description: "Use when …"`, colon-space inside) while the seven worker descriptions
are bare, and INSTALL §2 said to take the description "exactly" from the frontmatter, so a literal reader
could save the main Skill with surrounding quotes. Only F3 is addressed; F1, F2, F4–F8 are untouched.

### What changed (3 files, +47/−2)

- `templates/grok-bot/INSTALL.md.tmpl` §2 (canonical adapter prose): the `description` value is the text
  **without YAML quotes**; for a `description: "..."` line (the main Skill's) save the text between the
  quotes, never the quotes themselves; the `description` field of the same row in
  `hosts/grok-bot/private-skills.json` is that already-resolved value and is the exact string to save.
- `hosts/grok-bot/INSTALL.md`: regenerated by `render-skills.py --write` (the only product that changed;
  the eight documents, `private-skills.json`, `skills/`, and the runtime copy are byte-identical).
- `tests/contract/test-issue-49-grok-bot-host.py` (39 tests): the guide-clause test requires the new
  sentences; new `test_quoted_main_description_is_never_saved_with_its_quotes` proves the main frontmatter
  description is a quoted scalar, every manifest description is the resolved unquoted value with no JSON
  escapes, the manifest never carries the quoted scalar verbatim, the guide points at the manifest value
  and authorizes no "with quotes" reading, and the verifier rejects a manifest whose main `description` is
  the raw quoted frontmatter string (`kaola-project-runner: description does not match the document
  frontmatter`).

### Validation (worktree, committed tree `aba7d74`)

| Check | Result |
|---|---|
| `python3 scripts/render-skills.py --write` | `render-skills: WROTE (7 workers + kaola-project-runner + grok-bot host: 8 private skills + runtime copy)`; only `hosts/grok-bot/INSTALL.md` changed |
| `python3 scripts/render-skills.py --check` | `render-skills: PASS (7 workers + kaola-project-runner + grok-bot host: 8 private skills + runtime copy)` |
| `python3 scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo .` | `PASS … (8 private skill docs + manifest + install guide; runtime copy: 1 root skill, 7 embedded workers; generated state)` |
| `python3 tests/contract/test-issue-49-grok-bot-host.py` | 39 tests OK |
| same suite file against `git archive 4133601` | 2 failures: `test_install_guide_is_repo_based_idempotent_bounded_and_not_a_ninth_skill`, `test_quoted_main_description_is_never_saved_with_its_quotes` |
| `./scripts/validate.sh` | exit 0 (validate-skill ×8 PASS, installer migration PASS, installer runtimes PASS, all Python suites OK, verifier PASS, issue-49 39 OK; 0 FAIL lines) |
| `git diff --check` (working tree and `4133601..HEAD`) | clean |
| `git diff --stat 4133601..HEAD -- templates/grok-golden` | empty |
| `git status --porcelain` before commit | exactly `hosts/grok-bot/INSTALL.md`, `templates/grok-bot/INSTALL.md.tmpl`, `tests/contract/test-issue-49-grok-bot-host.py`; clean after commit |

### Not done

- F1, F2, F4–F8 of the `4133601` review: deliberately untouched (scope).
- The `4133601` PASS review is bound to those bytes; `aba7d74` needs a delta re-review (3 files).
- Morning human Grok Bot UI UAT (source: this worktree @ `aba7d74f1a28a58c13814b32031d6bebbc5ab619`,
  guide `hosts/grok-bot/INSTALL.md`): unchanged in substance from the `4133601` section above; item 8
  of the reviewer's UAT list (how the Bot renders the main Skill's quoted description) now has an
  explicit instruction to check against.
- No finalize, merge, issue close, release, or Grok Bot UI operation was performed.

## Correction candidate `fb65c512459841ec0e7973b406affcc749acba8a` (2026-09-16, Mission 7)

Supersedes `aba7d74f1a28a58c13814b32031d6bebbc5ab619` as the Issue #49 candidate; the `aba7d74` UAT
is void (Issue #49 `kw:correction` comment 5690464167). Basis: research `NO_SUPPORTED_PATH` (comment
5690241771), the repo-direct bridge addendum (5690299109), and four owner corrections received while
Mission 7 was framed: (1) progressive disclosure locked as a platform-neutral invariant and one thin
account bridge instead of eight documents; (2) bind the execution target first, never assume Local
Computer and the cloud Agent Computer reach each other; (3) the Mac already holds the checkout and
its local install, the cloud never clones/installs/updates the Mac; (4) one account/cloud Skill
package plus a tiny device-local locator/receipt per target, path changes by re-registration.

### What landed (48 files, +1 979 / −2 336 excluding the bulk deletion of the runtime copy)

- `hosts/grok-bot/` is now exactly: marker, `kaola-project-runner.md` (the bridge, 2 039 B,
  description 261 chars), `bridge.json` (name, resolved description, accepted commit
  `ba3d14f0c4f35bfc96004435d1ef053713d323ec` = current `main`, release v0.2.3, bytes, file/body
  sha256), `INSTALL.md` (4 845 B: one account write, first configuration on Local Computer,
  read-only preflight UAT, optional independent cloud checkout, update/rollback, boundaries).
  Removed: `private-skills/` (8 docs), `private-skills.json`, the runtime copy
  `hosts/grok-bot/kaola-project-runner/` (111 files), `scripts/kaola-grok-bot-package.py`,
  `--runtime grok-bot` (now refused with a bridge/locator hint), `KAOLA_GROK_BOT_HOME`, and the
  worker template's embedded-`WORKER.md` sentence.
- Bridge (`templates/grok-bot/bridge.md.tmpl` + `accepted-revision.json`): repository, expected
  origin, exactly one 40-hex accepted revision, locator command `kaola-project-runner-locate`,
  `ROOT/skills/kaola-project-runner/SKILL.md`, `ROOT/skills/<platform>-kaola-project-runner/SKILL.md`;
  step order bind target → locator → verify (origin / revision / clean; fetch+detach only on the
  cloud target) → load main with ROOT, target, consumer project root as inputs → load only the
  selected worker and run its scripts on the same target. No canonical sentence, worker name,
  transport/orchestrator marker, path/HOME/env/symlink convention, runtime copy, or credential
  pattern (verifier + tests).
- `scripts/kaola-locate.py` (new): device-local locator and fail-closed attestation. `register
  [--bin-dir]` links `kaola-project-runner-locate` in the installer's bin directory (also added to
  `install-local.sh` `bin_specs`, so `--bin-links` and `--uninstall --bin-links` manage it); the
  receipt form prints one JSON line ≤ 4 KB with target, host kernel + hashed fingerprint, ROOT
  (path, normalised origin without userinfo, HEAD, clean, revision_match), project (path on this
  host, top level, origin), worker script under the same ROOT, session presence; refusals:
  `origin-mismatch`, `revision-mismatch`, `dirty`, `target-required`, `project-not-on-this-host`,
  `project-not-a-checkout`, `worker-unknown`, `script-missing`, `script-outside-root`, …;
  `GIT_TERMINAL_PROMPT=0`; no credential handling; no scan/daemon/registry.
- `templates/budgets.json` + `render-skills.py`: budgets measured before any write (description
  320 chars, main 16 384 B, worker 12 288 B, reference 8 192 B, bridge 2 560 B, guide 8 192 B,
  locator receipt 4 096 B, capture receipt 65 536 B); `--check`/`--write` fail with
  `budget: <surface> is N B > M B (<key>)`. Renderer host adapter rewritten: inputs
  `GROK_BOT_ADAPTER_INPUTS = ("templates/grok-bot",)`, no canonical source read; `HOST_WORKERS`
  token dropped (sibling sentence inlined in the orchestrator template).
- Bounded ordinary capture: `kaola-observation.py bound-text` (newest whole lines + marker with
  total size and sha256 of the full stream, result ≤ limit); `kaola-tmux.sh capture` pipes through it
  unless `--full`. Live `tests/contract/test-kaola-tmux.sh` PASS on the bounded path.
- Orchestrator template: Hosts section rewritten (bridge host, target binding, attestation
  command, no cross-host reach, Routine/HUMAN_DECISION unchanged) + new "Progressive disclosure"
  section; `references/grok-bot-host.md` rewritten (delivery shape, targets, attestation, UAT
  boundary). Worker template: one progressive-disclosure sentence. Main SKILL.md 15 287 B; workers
  10 450–10 945 B.
- `scripts/kaola-grok-bot-verify.py` rewritten for the bridge (shape, budgets, clauses, order,
  forbidden patterns, manifest identity, guide clauses, unofficial tokens; `--repo` = generated
  state + no canonical sentence leaked).
- Tests: `tests/contract/test-issue-49-grok-bot-host.py` rewritten (28 tests: not-an-eighth-
  platform, single bridge, invariance, locator fixtures with a bare repo and a clone in a path
  with spaces, cross-host path refusal both directions, register/re-register/foreign-link
  refusal, orchestrator semantics, adapter boundary, worker isolation); new
  `tests/contract/test-progressive-disclosure.py` (14 tests: budgets, discovery, activation
  boundaries, renderer enforcement, bounded outputs, invariant documented); installer runtimes
  suite: `--runtime grok-bot`/`grokbot` refused, locator link install/uninstall.
- Docs: README, CHANGELOG, docs/api.md (renderer, installer, new Locator section), architecture
  (generated Skills, Progressive disclosure, host adapters), conventions (source of truth +
  Progressive disclosure), docs/README.md, docs/grok-bot-host.md (rewritten, token table),
  AGENTS.md snapshot line, installer help.

### Validation (worktree, committed tree `fb65c51`)

| Check | Result |
|---|---|
| `python3 scripts/render-skills.py --write` then `--check` | `render-skills: PASS (7 workers + kaola-project-runner + grok-bot host: 1 bridge skill, 2039 B, accepted ba3d14f0c4f3; budgets OK)` |
| `python3 scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo .` | `PASS … (1 bridge skill, 2039 B, manifest, guide; no canonical content; generated state)`; without `--repo`: PASS shape only |
| `python3 -m unittest tests/contract/test-issue-49-grok-bot-host.py` | 28 tests OK |
| `python3 -m unittest tests/contract/test-progressive-disclosure.py` | 14 tests OK |
| same two files on `git archive aba7d74` (+ `templates/budgets.json`) | issue-49: FAILED (failures=7, errors=16); progressive-disclosure: FAILED (failures=9, errors=2) |
| `bash tests/contract/test-installer-runtimes.sh` / `test-installer-migration.sh` | PASS / PASS |
| `bash tests/contract/test-kaola-tmux.sh` (live tmux, bounded capture path) | `kaola tmux acceptance: PASS` |
| `./scripts/validate.sh` | exit 0 (render check, validate-skill ×8, installer suites, all Python suites OK, verifier PASS, issue-49 28 OK, progressive-disclosure 14 OK) |
| `git diff --check` (tree and cached) | clean |
| `git diff --stat main..HEAD -- templates/grok-golden` | empty (golden frozen); `platforms/` = seven ids; no `adapters/grok-bot.sh` |
| working tree after commit | clean (`git status --short` = 0 lines) |

### Token-size comparison (chars ÷ 4 … ÷ 3.5)

| Surface | `fb65c51` (bridge) | `aba7d74` (eight docs, void) |
|---|---|---|
| Account write, once | 1 write, 2 039 B ≈ 0.5–0.6 k out | 8 writes, 209 190 B ≈ 52–60 k out (+ same in) |
| Discovery per turn | 261-char description ≈ 0.07 k | 8 descriptions ≈ 0.5 k |
| Main activation | 15 287 B ≈ 3.8–4.4 k (+ locator receipt ≤ 4 KB, typically ≈ 0.2 k) | 24 111 B ≈ 6.0–6.9 k, references pre-flattened |
| One selected worker | 10 450–10 945 B ≈ 2.6–3.1 k; references (≈ 4–6 KB each) only on demand | 25 943–27 062 B ≈ 6.5–7.7 k each |
| Release update | one bridge line, 1 write ≈ 0.5–0.6 k | 8 writes ≈ 52–60 k |

### Not done (owner; read-only)

1. One native `update_state` write of `hosts/grok-bot/kaola-project-runner.md` on the account (the
   only account operation; NO_SUPPORTED_PATH for anything automated).
2. Local Computer first configuration in the owner-named workspace: `git rev-parse --show-toplevel`
   on the existing Mac checkout at the accepted revision, `python3 "$ROOT/scripts/kaola-locate.py"
   register`, `kaola-project-runner-locate --target local --expect-revision <accepted>` → `ok`.
3. Read-only attestation + one worker `preflight` against an existing local project and session;
   record that nothing was started, sent, stopped, cloned, fetched, checked out, or installed and
   that the cloud Agent Computer executed nothing.

Note: the accepted revision pinned in this candidate is the current `main` (`ba3d14f…`, v0.2.3), the
last accepted baseline; a release rewrites `templates/grok-bot/accepted-revision.json`. To UAT this
candidate's own Skills from the bridge before release, the owner may temporarily set that file to
the candidate commit and `--write` (uncommitted), or check the Mac checkout out at `main`.

Stopped before finalize, merge, issue close, release, and any Grok Bot UI/state operation.
Independent review of `fb65c51` is owed.

## Correction candidate R `381b389e127a17893ea7d8698dfe0a824a859ff3` + pin P `242747a254bdd49bbcc72a10f686a551c2c71e66` (2026-09-16, Mission 8)

Supersedes `fb65c512459841ec0e7973b406affcc749acba8a`, which failed independent review (Issue #49
`kw:review` 5691006289, verdict FAIL, security cut PASS-WITH-NOTES). The candidate is now **two
commits** on `workflow/bundle-49`, by design:

| Commit | Role | `templates/grok-bot/accepted-revision.json` | Bridge line | Saveable |
|---|---|---|---|---|
| R `381b389e127a17893ea7d8698dfe0a824a859ff3` | content: runtime, docs, tests; the clean detached UAT target | `{"stage": "content"}` | `Accepted revision: none yet … do not save it to any account.` | no |
| P `242747a254bdd49bbcc72a10f686a551c2c71e66` | pin: names R; changes only the revision file + 3 regenerated products (4 files, +17/−15) | `{"stage": "pinned", "commit": R, "label": "pre-release UAT candidate for Issue #49; not a release"}` | `Accepted revision: \`381b389e…9ff3\` (pre-release UAT candidate for Issue #49; not a release).` | yes (`bridge.json` `saveable: true`) |

No self-pin (a commit cannot contain its own hash), no dirty pin rewrite, no release, no tag.

### Findings addressed (all seven blocking + three security-cut corrections)

1. **Two-commit content/pin model** — `accepted-revision.json` declares `stage`; the renderer emits
   the `ACCEPTED_LINE` token (content placeholder or pinned line) on its own line, so content→pin
   and pin→pin each change exactly one bridge line; `bridge.json` gains `stage`, `saveable`,
   `label`; `INSTALL.md` §0 explains R/P, "save from P, check out at R". The label is 3–80 plain
   characters and must state the truth; a `release` must be a `vX.Y.Z` tag at R.
2. **Pin gate** — `render-skills.py` `pin_findings()` at the pinned stage: commit exists
   (`cat-file -e`), is an ancestor of HEAD (`merge-base --is-ancestor`), its own
   `accepted-revision.json` is at stage `content` (never a self-pin, never another pin commit),
   `ls-tree` contains `scripts/kaola-locate.py`, `skills/kaola-project-runner/SKILL.md`, and every
   worker `SKILL.md` + `scripts/runtime-tmux.sh`, and a named release tag resolves to R. An
   unverifiable pin is never written. `--require-pinned` (renderer and verifier) is the P gate;
   the verifier `--repo` runs the same `pin_findings` from outside the renderer. Tests:
   `Issue49PinModel` (content stage not saveable and refused by `--require-pinned`; gate refuses
   missing / non-ancestor / incomplete / self-or-pin-commit / mistagged; P verifies from P itself;
   `PROJECT` stage consistent with its own checkout), `Issue49BridgeInvariance` rewritten on a real
   Git fixture (canonical + platform-manifest edits leave all three products byte-identical;
   content→pin and pin→pin change exactly one line). Repo copies without `.git` in the other suites
   (`test-generated-skills.py`, `test-issue-41-orchestrator.py`, issue-49 `copy_repo`,
   progressive `RendererEnforcesBudgets`) start at the content stage, so R and P are each
   reproducible without weakening the P gate.
3. **`kaola-locate.py register` validates first** — origin, optional `--expect-revision`
   (40-hex checked), clean state, and the link path are all evaluated before any filesystem
   change; a refusal returns `locator.changed: false` and the existing link is untouched. Test
   `test_register_validates_every_fact_before_touching_an_existing_locator` (dirty, wrong
   revision, malformed revision, foreign origin from a second clone → link byte-identical; clean
   matching clone re-registers; dirty first registration links nothing).
4. **Bounded ordinary ACP capture** — `kaola-acp.py` `bound_capture_receipt()` (constant
   `CAPTURE_RECEIPT_BYTES = 65536` = `capture_receipt_bytes`) drops the oldest `events`
   (L2: `--lines`, `--since`) or `tool_calls` (L1) until the JSON line fits and adds `truncated`
   = `{list, kept, dropped, total, stream_bytes, stream_sha256, hint}` where `stream_sha256` is over
   the untruncated one-JSON-line-per-entry stream; explicit `--full` never passes through it.
   Behavioural test `BoundedAcpCapture` against `mock-acp-agent.py --scenario follow_flood` (two
   turns, 560+ events): `--full --inline` > budget with no marker; `--lines 1000` ≤ budget with
   counts, newest events kept, sha256 recomputed from the `--full` stream and equal; `--since 0`
   bounded; `--lines 5` passes through unchanged. Reference `acp.md` and the orchestrator
   "Progressive disclosure" section state the bound on both transports.
5. **Target kind honesty** — docstring, bridge, orchestrator Hosts section, host reference, docs,
   and tests now say `--target` is the Agent's declaration (echoed, never inferred; the script
   cannot classify Mac vs cloud); the real safety is device-local execution, `host.fingerprint`
   compared with the value recorded at registration, and root/project/script/session co-location
   on the executing host. The former "rejects cloud paths for a Local Computer dispatch" test is
   now `test_paths_absent_on_the_executing_host_are_refused_whatever_target_is_declared` (same
   real path accepted under either declaration). Security-cut corrections: `session.present` is
   tmux presence only (ownership = worker preflight); `root.path`/`project.path` are real local
   paths that may include the user's home, never stored in the account Skill; "no hostname, no
   user" claim removed; the bridge now requires the fingerprint comparison (verifier clause).
6. **Adapter input claim** — `bridge_values()` / `expected_grok_bot_host_files()` take no
   manifests; `FIRST_WORKER_*` tokens removed; the guide uses `<platform id>`; test asserts the
   signatures, no `manifests[0]`/runtime names in the adapter section, no worker id/runtime in
   the guide, and the manifest-edit invariance above.
7. **Tests** — drift test asserts `render --write` rc 0 and verifier PASS before each mutation
   (plus a `content-stage-revision` case); `authorizes_wrong_move` and the script-source heuristic
   exempt a sentence only where a negation immediately precedes the match (`only`/`is not`
   exemptions dropped); `CAPTURE_RECEIPT_BYTES` agreement extended to `kaola-acp.py`; shipped
   `kaola-acp.py` copies checked byte-identical. Budgets unchanged.

UAT boundary stated in `INSTALL.md`, `docs/grok-bot-host.md`, the host reference, and CHANGELOG:
the Mac `main` checkout may hold untracked Workflow records (`dirty` is correct); the owner selects
a clean checkout or worktree detached at R (`git worktree add --detach <owner-chosen path> R`);
no fixed path; clean-tree verification not weakened; nothing cloned/installed/updated on the Mac
from the cloud.

### Validation (worktree, committed trees R then P)

| Check | Result |
|---|---|
| `render-skills.py --write` / `--check` at R | `render-skills: PASS (… 1 bridge skill, 2317 B, content stage, unpinned (not saveable); budgets OK)` |
| `render-skills.py --write` / `--check --require-pinned` at P | `render-skills: PASS (… 1 bridge skill, 2280 B, pinned at 381b389e127a, pin verified; budgets OK)` |
| `kaola-grok-bot-verify.py hosts/grok-bot --repo . [--require-pinned]` | R: `PASS … stage content … generated state`; P: `PASS … stage pinned … generated state, pin verified` |
| `test-issue-49-grok-bot-host.py` | 34 tests OK at R and at P (fb65c51 baseline: FAILED failures=11, errors=3) |
| `test-progressive-disclosure.py` (incl. `BoundedAcpCapture` live mock agent) | 15 tests OK at R and at P (fb65c51 baseline: FAILED failures=4) |
| `test-installer-runtimes.sh` / `test-installer-migration.sh` | PASS / PASS (inside validate.sh at R and P) |
| `bash tests/contract/test-kaola-tmux.sh` (live tmux) | `kaola tmux acceptance: PASS` at R; `kaola-tmux.sh`, `kaola-observation.py`, adapters unchanged since fb65c51 |
| `./scripts/validate.sh` | exit 0 at R (content) and exit 0 at P (pinned; first P attempt exposed two repo-copy suites that could not verify a pin without `.git`, fixed in R before the final P) |
| `git diff --check main..P` | clean |
| `git diff --stat main..P -- templates/grok-golden` | empty (golden frozen); `platforms/` = seven ids; no `adapters/grok-bot.sh` |
| `git diff --stat R..P` | 4 files (+17/−15): `accepted-revision.json`, bridge, `bridge.json`, `INSTALL.md`; bridge diff = exactly one line |
| working tree after P | clean (`git status --short` = 0 lines) |
| `git diff --stat fb65c51..P` | 39 files, +1 567 / −350 |

Sizes: bridge 2 280 B (description 261 chars), guide 6 522 B, main SKILL.md within 16 384 B,
workers within 12 288 B, references within 8 192 B; all budgets unchanged.

### One-account-write UAT path (owner; nothing here performed)

1. From P: save `hosts/grok-bot/kaola-project-runner.md` (`bridge.json` `saveable: true`) as the
   account Skill `kaola-project-runner` (name/description resolved in `bridge.json`, body after
   the closing `---`, same-name update in place). Only account operation.
2. On the Mac, in an owner-selected clean workspace:
   `git worktree add --detach <owner-chosen path> 381b389e127a17893ea7d8698dfe0a824a859ff3`
   (or any clean checkout detached at R). With Execution on Local Computer inside it:
   `ROOT="$(git rev-parse --show-toplevel)"`,
   `python3 "$ROOT/scripts/kaola-locate.py" register --expect-revision 381b389e127a17893ea7d8698dfe0a824a859ff3`
   → `ok`; record `host.fingerprint`;
   `kaola-project-runner-locate --target local --expect-revision 381b389e127a17893ea7d8698dfe0a824a859ff3` → `ok`.
3. Read-only attestation with `--project <existing local project> --worker <platform id>
   --session <existing session>` then that worker's `runtime-tmux.sh preflight`; record that
   nothing was started/sent/stopped/cloned/fetched/checked out/installed and that the cloud Agent
   Computer executed nothing.

Stopped before UAT, finalize, merge, issue close, release, tag, and any Grok Bot UI/state
operation. Independent re-review of R+P is owed.

## Pre-UAT closure candidate R2 `bbfba65fac7667c6705e1ee0b0d53d5a735eeadd` + pin P2 `df8b85e319f2a2b46a9a63d0f1dd25a3ab5b34e5` (2026-09-16, Mission 9)

Supersedes R `381b389e127a17893ea7d8698dfe0a824a859ff3` + P `242747a254bdd49bbcc72a10f686a551c2c71e66`.
Four independent Fable High re-reviews of that pair returned PASS; their closure gaps were recorded as
one consolidated Issue #49 `kw:review` PASS-with-notes (comment 5691538023) and corrected **before**
UAT so no byte changes after UAT. Both commits are on `workflow/bundle-49`; `templates/budgets.json`
and `templates/grok-golden/` are byte-identical to P; seven platforms, no `platforms/grok-bot.yaml`,
no `scripts/adapters/grok-bot.sh`, one thin account Skill.

| Commit | Role | `accepted-revision.json` | Bridge line | Saveable |
|---|---|---|---|---|
| R2 `bbfba65fac7667c6705e1ee0b0d53d5a735eeadd` | content: runtime, docs, tests; the clean detached UAT target | `{"stage": "content"}` | `Accepted revision: none yet … do not save it to any account.` | no |
| P2 `df8b85e319f2a2b46a9a63d0f1dd25a3ab5b34e5` | pin: names R2; changes only the revision file + 3 regenerated products (4 files, +18/−16; bridge diff = 1 line) | `{"stage": "pinned", "commit": R2, "label": "pre-release UAT candidate for Issue #49; not a release"}` | `Accepted revision: \`bbfba65f…eadd\` (pre-release UAT candidate for Issue #49; not a release).` | yes |

### Notes closed (all seven)

1. **Bounded ordinary `observe`/`status` on both transports.** PTY: `kaola-observation.py bound_observation`
   applied to `build` and `status-view` (every PTY observe/status/start receipt): over `capture_receipt_bytes`
   the process tree is first cut to a 32-entry excerpt, then `raw_current_frame` keeps its newest whole
   lines, then the process excerpt is dropped; `truncated.fields` carries kept/total sizes or counts and
   the sha256 of the full frame / process stream; `snapshot_id` and `pane_revision` are computed from
   the full frame before bounding. ACP: `kaola-acp.py bound_state_receipt` applied to `observe`/`status`:
   `record`, `initial_config_options`, `session_meta`, `capabilities`, `agent_info` are replaced in turn by
   `{"omitted": true, "bytes", "sha256"}` summaries (`pending_permissions` keeps its newest entries).
   Only `capture --full` stays unbounded. Tests: `BoundedObserveAndStatus` (120 KB frame + 1 500-row
   process tree through the real helper; snapshot equals the unbounded in-process build; status-view
   keeps the original totals), `BoundedAcpObserveAndStatus` (600 native config options through the mock
   agent; sha256 recomputed from the injected list), and the **live private-tmux wrapper path** in
   `test-kaola-tmux.sh` (400×300 pane, `FILL:280:320` from the fake runtime: observe and status ≤ budget with
   marker and sha256, the bounded receipt's snapshot still drives `send --if-snapshot`, `capture --lines`
   bounded, `capture --full` unbounded, a within-budget observe untouched).
2. **Durable device-local registration receipt.** `kaola-locate.py register --target local|cloud
   [--bin-dir DIR] [--expect-revision R]` validates origin/revision/clean/link/receipt paths first, then
   links and atomically writes `.kaola-project-runner-locate.json` beside the link (schema
   `kaola-project-runner-locator-registration/1`, resolved root, declared target, host kernel + hashed
   fingerprint, accepted revision; no hostname or username field, no credential, no account data). Every
   later call (through the link, or `--bin-dir`) compares running fingerprint, declared target, resolved
   root, and HEAD with it: `locator-not-registered`, `locator-registration-unreadable`,
   `host-fingerprint-mismatch`, `target-mismatch`, `registration-root-mismatch`, `registration-stale`; a
   declared `--target` requires the receipt, plain discovery tolerates an absent one but refuses a
   mismatching one. Refused registrations leave link and receipt byte-identical (tested). Tests cover
   fresh-conversation semantics (the link alone in a new process) and tampering of every field. The
   guide names `$BIN/.kaola-project-runner-locate.json` relative to the owner-chosen link and says both
   stay device-local.
3. **Pin delta machine-enforced.** `pin_delta_findings` (renderer, and the verifier through it): the tracked
   working tree compared directly with R may differ only by `templates/grok-bot/accepted-revision.json`
   and the three `hosts/grok-bot/` products, and the bridge must differ from R's bridge by exactly the
   accepted-revision line. Refuted in `test_pin_gate_enforces_the_p_delta_and_the_one_line_bridge_diff`
   (stray tracked edit, merge with an advanced main, rebase onto it, orphan squash, stale committed bridge)
   and by hand at P2 (stray edit → refused; masquerading label → refused). Docs (INSTALL guide, host
   reference, `docs/grok-bot-host.md`, api, architecture, README): never rebase/squash/amend an accepted
   R/P pair; fresh R/P when `main` moves; release = tag at R then P after the tag; rollback = new pin
   naming an older R. A label may not look like a release tag or begin with "release".
4. **Cloud registration** now passes `--target cloud --bin-dir <dir on PATH> --expect-revision R`.
5. **Origin forms.** Only explicit `https://`, `ssh://`, or scp `host:path` origins are accepted and
   normalised without userinfo/port; bare `github.com/...`, `http://`, `git://`, `file://`, local paths →
   `origin-form-unsupported` with `origin: null` and no raw leak (tested for eight rejected forms).
6. **Honesty wording.** Session field = presence on the tmux server reachable from the locator only (not
   existence elsewhere, never ownership); `docs/api.md` documents `bridge.json` `stage`/`saveable`/`label`
   and the content-stage `null` fields; trusted-host Git-index edge cases (`assume-unchanged`,
   `skip-worktree`, tampered `.git`) stated as bounded, no content hashing.
7. **UAT installer conflict.** UAT registers into an owner-selected persistent directory on PATH (`BIN`),
   leaving the installer-managed `--bin-links` link alone; after UAT remove `$BIN/kaola-project-runner-locate`
   and its receipt or keep them; the installer-managed link is restored with
   `./scripts/install-local.sh --bin-links` from the normal checkout (it refuses to overwrite a link it
   does not own) and then registered from that checkout.

### Validation (worktree)

| Check | Result |
|---|---|
| `render-skills.py --write`/`--check` at R2 | `PASS (… 1 bridge skill, 2526 B, content stage, unpinned (not saveable); budgets OK)` |
| `render-skills.py --write`/`--check --require-pinned` at P2 | `PASS (… 1 bridge skill, 2489 B, pinned at bbfba65fac76, pin verified; budgets OK)` (before and after the P2 commit) |
| `kaola-grok-bot-verify.py hosts/grok-bot --repo . [--require-pinned]` | R2: `PASS … stage content … generated state`; P2: `PASS … stage pinned … generated state, pin verified` |
| `test-issue-49-grok-bot-host.py` | 37 OK at R2 and at P2 (baseline R `381b389`: FAILED failures=12, all new/changed locator, guide, pin-delta, and label tests) |
| `test-progressive-disclosure.py` | 17 OK at R2 and at P2 (baseline R: FAILED failures=3: PTY over-budget, ACP over-budget, helper wiring) |
| `bash tests/contract/test-kaola-tmux.sh` (live private tmux, fake runtime) | PASS at R2 and at P2 incl. `test_bounded_observe_live`, `test_bounded_status_live`, snapshot-drives-send, bounded/`--full` capture (baseline R: RED on the three bounded cases) |
| `test-installer-runtimes.sh` / `test-installer-migration.sh` | PASS / PASS (standalone at P2 and inside `validate.sh`) |
| `test-observation-contract.py`, `test-relay-pty.py`, `test-guarded-actions.sh`, `test-evidence-first-actions.sh` | OK / OK / PASS / PASS (receipt shape unchanged within budget) |
| `./scripts/validate.sh` | exit 0 at R2 (content) and exit 0 at the P2 state (pinned; the first P2 attempt exposed the Git fixture committing pinned products, fixed in R2 before P2 was committed) |
| Pin-delta refutations at P2 | stray tracked edit → `pin: P may differ from bbfba65fac76 only by …; found docs/README.md`, `--write` refused; label `release v0.3.0` → `label must not masquerade as a release` |
| `git diff --name-only R2` at P2 / `git diff --stat R2 P2` | exactly the 4 allowed files (+18/−16); bridge diff exactly the accepted-revision line |
| `git diff --check main..P2` | clean |
| `templates/grok-golden/` vs main; `templates/budgets.json` vs P and vs fb65c51 | 0 changed lines |
| working tree after P2 | clean |
| `git diff --stat P..P2` | 55 files, +2 346 / −346 |

Sizes at P2: bridge 2 489 B (description 261 chars; budget 2 560), guide 8 090 B (budget 8 192), main
SKILL.md 15 664 B (budget 16 384), host reference 7 852 B (budget 8 192), workers ≤ 10 450 B, references
≤ 6 548 B. Budgets unchanged.

### UAT path (owner; one account write; nothing performed here)

UAT artifact: `hosts/grok-bot/INSTALL.md` at P2 `df8b85e319f2a2b46a9a63d0f1dd25a3ab5b34e5` (and this section).

1. From P2: save `hosts/grok-bot/kaola-project-runner.md` (`bridge.json` `saveable: true`) as the account
   Skill `kaola-project-runner` (same-name update). Only account operation.
2. On the Mac, an owner-selected clean worktree detached at R2
   (`git worktree add --detach <owner-chosen path> bbfba65fac7667c6705e1ee0b0d53d5a735eeadd`) and an
   owner-selected persistent `BIN` on PATH; with Execution on Local Computer inside it:
   `ROOT="$(git rev-parse --show-toplevel)"`,
   `python3 "$ROOT/scripts/kaola-locate.py" register --target local --bin-dir "$BIN" --expect-revision bbfba65fac7667c6705e1ee0b0d53d5a735eeadd`
   → `ok` (link + `$BIN/.kaola-project-runner-locate.json`), then
   `kaola-project-runner-locate --target local --expect-revision bbfba65fac7667c6705e1ee0b0d53d5a735eeadd` → `ok`
   (the locator compares fingerprint and target with its receipt; no operator memory needed).
3. Read-only attestation with `--project <existing local project> --worker <platform id> --session
   <existing session>` then that worker's `runtime-tmux.sh preflight`; nothing started/sent/stopped/
   cloned/fetched/checked out/installed; the cloud Agent Computer executes nothing. Afterwards remove
   `$BIN/kaola-project-runner-locate` and its receipt or keep them; the installer-managed link is
   untouched.

Stopped before UAT, finalize, merge, issue close, release, tag, and any Grok Bot UI/state operation.
Independent delta re-review of R2+P2 is owed; the accepted pair must not be rebased or squashed.

## Final bounding-correctness candidate R3 `bc8592d323864c30010b48ae724f329f8df6753e` + pin P3 `db4b0d5813111ef71afbcf165be0fb91d9a7d976` (2026-09-16, Mission 10)

Supersedes R2 `bbfba65fac7667c6705e1ee0b0d53d5a735eeadd` + P2 `df8b85e319f2a2b46a9a63d0f1dd25a3ab5b34e5`.
The consolidated final delta review of that pair (Issue #49 `kw:review` comment 5692110310) returned
**FAIL** on one confirmed Medium/Major runtime defect; because the defect lives in content-commit bytes
and an accepted R/P pair is never amended or rebased, the correction is this fresh pair. R2/P2 stay on
the branch untouched. Mission 10 was dispatched to Fable 5.1 High, which committed R3 and left the P3
pin products in the working tree; the owner then limited Fable to a single task, so Opus 5 High took
over as sole production-write owner, verified the landed state independently, and committed P3.
Seven platforms, no `platforms/grok-bot.yaml`, no `scripts/adapters/grok-bot.sh`, one thin account
Skill; `templates/budgets.json` (unchanged since `fb65c51`) and `templates/grok-golden/` (identical to
`main`) frozen.

| Commit | Role | `accepted-revision.json` | Bridge line | Saveable |
|---|---|---|---|---|
| R3 `bc8592d323864c30010b48ae724f329f8df6753e` | content: runtime, docs, tests; the clean detached UAT target | `{"stage": "content"}` | `Accepted revision: none yet … do not save it to any account.` | no |
| P3 `db4b0d5813111ef71afbcf165be0fb91d9a7d976` | pin: names R3; changes only the revision file + 3 regenerated products (4 files, +18/−16; bridge diff = 1 line) | `{"stage": "pinned", "commit": R3, "label": "pre-release UAT candidate for Issue #49; not a release"}` | `Accepted revision: \`bc8592d3…6753e\` (pre-release UAT candidate for Issue #49; not a release).` | yes |

`git diff --shortstat P2..P3` = 44 files, +901/−353; `R2..R3` = 40 files, +890/−342.

### Blocker corrected (review F1 / Major)

`bound_observation` started a fresh `truncated.fields` on every call. The PTY status path bounds the
same receipt twice — once in `build`, then again in `status-view` once its scalar fields are added — so
when the second pass went over budget, emptying the inherited `truncated` block alone brought the line
back under the limit: neither trim loop ran, the excerpts stayed, and the original totals, counts, and
sha256 digests were silently lost. Reproduced on 200- and 399-column frames with 1 500 child processes.

1. **Idempotent, monotone bounding.** `bound_observation` now reads the existing `truncated.fields`
   first and seeds the new block from it, so every prior entry survives with its original `total`,
   `stream_bytes`, `stream_sha256`, and `total_bytes`/`sha256`; a further cut only lowers the `kept`
   figure; a still-trimmed `child_processes` entry is re-registered even when this pass does not trim
   it further; and a receipt that already fits is returned unchanged.
2. **Bound last, emit as is.** `result` (and, for grok only, `legacy_ownership`) are now added *inside*
   `status-view` through `KPR_STATUS_RESULT` / `KPR_STATUS_LEGACY` and the bound runs after them
   (`emit_status_view`). `kaola-tmux.sh` `emit_status` and the `start` success path pipe the observation
   through the helper and print the bounded line verbatim; nothing is appended afterwards, so the
   emitted status/start line stays within `capture_receipt_bytes` on a 400-column pane. The budget is
   measured on the emitted line (`_line_size` = JSON + the newline `print` writes), closing the
   few-bytes-over low note from the delta review.
3. **Same guarantee on ACP.** `bound_state_receipt` records each field's summary *before* cutting that
   field and measures the emitted line, so no summary entry can itself push the receipt over;
   `pending_permissions` updates its `kept`/`dropped` as it drops. `bound_capture_receipt` measures the
   same way. Only `capture --full` stays unbounded.
4. **Low notes folded in (same causal cut).** `kaola-locate.py register` now *requires*
   `--expect-revision` (`expect-revision-required`), and a receipt without a 40-hex accepted revision is
   `locator-registration-unreadable`, so `registration-stale` can always fire. `normalise_origin` rejects
   a host carrying a second `@` and any host or path carrying `?` or `#` as `origin-form-unsupported`,
   echoing no fragment of the raw value.

Docs (`docs/api.md`, `docs/grok-bot-host.md`, `templates/references/transport.md.tmpl`, the orchestrator
host reference, `CHANGELOG.md`) state the corrected behaviour; the seven generated worker copies of
`kaola-observation.py`, `kaola-acp.py`, `kaola-tmux.sh`, and `references/transport.md` were regenerated by
`render-skills.py --write` and are byte-identical to the canonical scripts.

### Validation (worktree, 2026-09-16, re-run by the Opus successor at the P3 byte state)

| Check | Result |
|---|---|
| `render-skills.py --check --require-pinned` | `PASS (7 workers + kaola-project-runner + grok-bot host: 1 bridge skill, 2489 B, pinned at bc8592d32386, pin verified; budgets OK)` — before and after the P3 commit |
| `kaola-grok-bot-verify.py hosts/grok-bot --repo . --require-pinned` | `PASS … 1 bridge skill, 2489 B, stage pinned, manifest, guide; no canonical content; generated state, pin verified` |
| `test-issue-49-grok-bot-host.py` | 37 OK |
| `test-progressive-disclosure.py` | 21 OK (was 17 at R2; +4 bounding regressions) |
| Baseline failure on R2 | the R3 suite run against a `git archive bbfba65` tree: `FAILED (failures=4)` — `test_repeated_bounding_merges_prior_truncation_metadata`, `test_real_build_to_status_path_keeps_evidence_and_wrapper_fields_within_budget` (`'child_processes' not found` at widths 200 and 399), `test_state_receipt_never_exceeds_the_limit_when_pending_permissions_decide`, `test_tmux_core_bounds_ordinary_capture_and_leaves_full_unbounded` |
| `bash tests/contract/test-kaola-tmux.sh` (live private tmux, fake runtime) | PASS (`kaola tmux acceptance: PASS`) |
| `./scripts/validate.sh` (full, incl. both installer suites, ACP, relay, generated-Skill acceptance) | exit 0 at the P3 byte state |
| Pin-delta refutations (fresh local clone at the P3 state; production worktree untouched) | stray `README.md` edit → `pin: P may differ from bc8592d32386 only by …; found README.md` (exit 1); pin naming `000…0` → `pin: accepted commit 000000000000 does not exist in this checkout`; label `v0.3.0` → `label must not masquerade as a release` (exit 2); extra bridge line → `grok-bot: stale kaola-project-runner.md expected=3e0e70292778 actual=a19d8a4f9b81`; self-pin after committing P → `pin: accepted commit … is not a content-stage commit (stage 'pinned')`; clean P in the clone → PASS |
| `git diff --name-only bc8592d..P3` | exactly the 4 allowed files; bridge diff exactly the accepted-revision line |
| `git diff --check main..P3` | clean |
| `templates/grok-golden/` vs `main`; `templates/budgets.json` vs `fb65c51` | 0 changed lines |
| Generated helper copies across the 7 workers + orchestrator | one distinct sha256 each for `kaola-observation.py`, `kaola-acp.py`, `kaola-tmux.sh` |
| working tree after P3 | clean |

Sizes at P3: bridge 2 489 B (budget 2 560), guide 8 090 B (8 192), main `SKILL.md` 15 664 B (16 384),
host reference 7 881 B (8 192), largest worker 10 945 B (12 288), largest worker reference 6 682 B
(8 192). Budgets unchanged.

### UAT path (owner; one account write; nothing performed here)

UAT artifact: `hosts/grok-bot/INSTALL.md` at P3 `db4b0d5813111ef71afbcf165be0fb91d9a7d976` (and this section).
Identical to the P2 path with R3/P3 substituted:

1. From P3: save `hosts/grok-bot/kaola-project-runner.md` (`bridge.json` `saveable: true`) as the account
   Skill `kaola-project-runner` (same-name update). Only account operation.
2. On the Mac, an owner-selected clean worktree detached at R3
   (`git worktree add --detach <owner-chosen path> bc8592d323864c30010b48ae724f329f8df6753e`) and an
   owner-selected persistent `BIN` on PATH; with Execution on Local Computer inside it:
   `ROOT="$(git rev-parse --show-toplevel)"`,
   `python3 "$ROOT/scripts/kaola-locate.py" register --target local --bin-dir "$BIN" --expect-revision bc8592d323864c30010b48ae724f329f8df6753e`
   → `ok` (link + `$BIN/.kaola-project-runner-locate.json`), then
   `kaola-project-runner-locate --target local --expect-revision bc8592d323864c30010b48ae724f329f8df6753e` → `ok`.
   `--expect-revision` is now required, so a registration made without it is refused rather than silently
   unstale-able.
3. Read-only attestation with `--project <existing local project> --worker <platform id> --session
   <existing session>` then that worker's `runtime-tmux.sh preflight`; nothing started/sent/stopped/
   cloned/fetched/checked out/installed; the cloud Agent Computer executes nothing. Afterwards remove
   `$BIN/kaola-project-runner-locate` and its receipt or keep them; the installer-managed link is
   untouched and is restored with `./scripts/install-local.sh --bin-links` from the normal checkout.

Stopped before UAT, finalize, merge, issue close, release, tag, and any Grok Bot UI/state operation.
An independent delta re-review of R3+P3 is owed; the accepted pair must not be rebased, squashed, or amended.

### Delta re-review of R3 + P3 (2026-09-16, Opus successor, discharging the owed re-review)

The re-review owed above is now discharged. Recorded as Issue #49 `kw:review`
[5692569301](https://github.com/KaolaBrother/kaola-project-runner/issues/49#issuecomment-5692569301),
verdict **PASS-with-notes**, superseding the R2/P2 FAIL 5692110310. Three independent Opus High
reviews (runtime bounding; locator/trust boundary; test custody, baseline honesty and records) plus
the orchestrator's own verification, all read-only; the worktree stayed byte-clean at `db4b0d5`
and every experiment ran in scratch clones or `git archive` trees.

Blocker F1 is closed in runtime bytes: a direct sweep of the R2 bytes reproduces the recorded defect
(`truncated.fields` empty at frame line widths 200 and 399 while only 32/1500 processes and ~61 KB of a
130 KB frame survive), and R3 preserves every original total, count and digest at all widths, is
idempotent on the third and fourth bound, and returns a fitting receipt by identity. The wide-pane
budget note is closed with it: the emitted line (JSON plus newline) is the yardstick and the wrapper
fields are added before the single bound, with 0 over-budget lines across a 12 600-configuration sweep.

Gates reproduced independently at the P3 byte state: `--check --require-pinned` PASS (2489 B, pinned at
`bc8592d32386`) and correctly exit 1 at R3; verifier PASS with `--repo`; pin delta exactly the 4 allowed
files with a one-line bridge diff; `git diff --check main..P3` clean; golden tree sha identical to `main`;
budgets unchanged since `fb65c51`; 21 generated worker copies byte-identical; issue-49 37 OK;
progressive-disclosure 21 OK; `validate.sh` exit 0; live `tests/contract/test-kaola-tmux.sh` PASS; four
pin-gate refutations refused with the documented reasons in a fresh clone while clean P3 passed; worktree
clean after all of it. Baseline failure on `bbfba65` is genuine (21 run, 4 failed, 0 errors) and no test
was weakened.

Note for a future pair (correcting a record in the R3+P3 section above): `validate.sh` does **not** run the
live tmux smoke — it only syntax-checks `kaola-tmux.sh` and the adapters — so
`tests/contract/test-kaola-tmux.sh` was run separately to establish that PASS.

Seven Low notes are documented in the review comment and deliberately **not** corrected here: none sits in
the content-commit runtime path that UAT exercises, and the accepted R3/P3 pair must not be rebased,
squashed, or amended. They are recorded for a future pair.

R3/P3 stand as the UAT-ready pair; the branch remains local and unpushed. Still stopped before owner UAT,
Workflow finalize, merge, issue closure, release, tag, and any Grok Bot UI/account mutation.
