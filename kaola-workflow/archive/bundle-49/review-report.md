# Issue #49 independent review

- Reviewer: Fable 5.1 High main worker (acceptance-before-finalize; not the implementer)
- Candidate: branch `workflow/bundle-49`, commit `601e0045f88c8d854b29020ec505a7f0ab86239d`
  (worktree `.kw/worktrees/bundle-49`, base `ba3d14f` = `main`)
- Candidate not modified. No finalize, merge, close, or release performed.

## Verdict

**FAIL (release-blocking F1). Not PASS. Do not finalize.**

Offline mechanical acceptance items reproduce, but the candidate's central host premise is
falsified by the owner's live UAT and by read-only local and documentary evidence. Return to the
original implementer.

## Reproduced offline evidence (worktree, 2026-09-15)

| Check | Result |
|---|---|
| `python3 scripts/render-skills.py --check` | `render-skills: PASS (7 workers + kaola-project-runner + grok-bot host)` |
| `./scripts/validate.sh` | exit 0 (issue-41 23 tests, issue-49 18 tests, installer runtimes, grok-bot verifier PASS) |
| `git diff --check main..HEAD` | clean |
| `templates/grok-golden/` | 0 changed lines |
| `platforms/grok-bot.yaml` / `scripts/adapters/grok-bot.sh` | absent |
| Exec bits `skills/` vs `hosts/grok-bot/skills/` (git index and on disk) | identical (22 executables each) |
| Installer smoke in temp HOME: link full bundle, link subset refused, uninstall link, copy `--no-orchestrator --platform codex`, update to full, uninstall copy | all behaved as documented |

## Findings (bound to `601e0045f88c8d854b29020ec505a7f0ab86239d`)

### F1 — release-blocking: `~/.cursor/plugins/local` is not a Grok Bot host destination

**Claim under test.** README, `docs/api.md`, `docs/architecture.md`, `docs/grok-bot-host.md`,
`templates/orchestrator/SKILL.md.tmpl` ("Verified installer destinations: Codex, Claude Code,
Cursor, Devin, and Grok Bot"), `AGENTS.md`, and `scripts/install-local.sh` present
`--runtime grok-bot` → `$HOME/.cursor/plugins/local/kaola-project-runner` (Cursor-plugin layout
with `.cursor-plugin/plugin.json`) as the Grok Bot host install.

**Refuting evidence.**

1. Owner UAT (Grok Bot 0.51.0, this Mac): after `--runtime grok-bot` install, Settings → Plugins
   does not show Project Runner. Earlier shell / Local Computer PASS does not cover this.
2. Read-only local facts: payload exists only at `~/.cursor/plugins/local/kaola-project-runner`
   (plus `.kaola-install-receipts`). `~/.grok/plugins` does not exist. Grok CLI 1.0.30
   `grok plugin list --json` → `[]`. `grok inspect --json` sees the two Kaola skills only through
   the `~/.claude/skills` compatibility surface (as skills, not plugins) and its plugins only from
   `~/.claude/plugins/cache`.
3. Official Grok Bot docs (fetched 2026-09-15):
   - skills-routines-and-automations: "Use Settings → Plugins to discover and install supported
     connectors and packaged skills"; private skills are created by the Bot ("Save the process we
     just used as a skill") and enabled under "Settings → Plugins → Yours". No sideload path from a
     local directory or shell is documented.
   - settings-and-notifications: "Use Marketplace to discover plugins and packaged skills. Use
     Yours to review installed plugins and private skills." Agent Computer is a cloud computer
     ("Update Agent Computer rebuilds the cloud computer"); the desktop app is a client
     ("Execution on Local Computer" only controls running commands on the desktop).
   - teams-and-enterprises: apps are "thin clients for chat, review, and approvals"; "work runs in
     the hosted computer"; Team Setup runs admin install scripts on team computers, with no
     statement that installed software appears in Settings → Plugins.
4. Local Grok CLI guide `~/.grok/docs/user-guide/09-plugins.md`: plugins are installed via
   `grok plugin install <owner/repo | git URL | local path> --trust`, live in `~/.grok/plugins/`
   (auto-trusted) or project `.grok/plugins/`, or extra `[plugins].paths` in `~/.grok/config.toml`;
   manifest is `.grok-plugin/plugin.json` (or `.claude-plugin/` equivalent) and marketplace index
   `.grok-plugin/marketplace.json`. `.cursor-plugin/` is not a Grok surface.

**Root cause.** The candidate equates a Cursor IDE local-plugin path with Grok Bot plugin
registration. Grok Bot's Settings → Plugins is an account-level cloud surface (Marketplace
connectors / packaged skills / private skills); nothing in it reads the local Mac filesystem, and
Grok CLI on this Mac does not read `~/.cursor/plugins/local` either. The candidate does label UI
enablement as UAT, but the UAT has now run and failed, so the "verified destination" and
"first-class host" wording cannot ship as written.

**Provable boundary today.**

- Provable: the renderer emits a byte-identical plugin bundle; the installer copies/links it to the
  Cursor local-plugin path with receipts and refusals; the orchestrator Skill carries the Grok Bot
  Routine / HUMAN_DECISION_REQUIRED / takeover / acceptance policy text; Grok CLI already loads the
  Kaola skills via `~/.claude/skills` compatibility.
- Not provable / falsified: that any Grok product loads `~/.cursor/plugins/local/...`; that Grok
  Bot 0.51.x exposes Project Runner from a local install.

**Minimal supportable correction direction (for the original implementer; not decided here).**

1. Stop describing the Cursor local-plugin path as a Grok Bot host destination in installer help,
   README, docs, `AGENTS.md`, and the orchestrator "Hosts" section.
2. Re-target the generated bundle to a documented loader: `.grok-plugin/plugin.json` (Grok also
   accepts `.claude-plugin/`) in a plugin folder that `grok plugin install /abs/path --trust` or
   `[plugins].paths` can load, installed under `~/.grok/plugins/` only through that documented
   command or path registration, never by silent directory copy. Tests
   (`tests/contract/test-issue-49-grok-bot-host.py`, `test-installer-runtimes.sh`) follow.
3. For Grok Bot itself the only documented ingestion is Marketplace or "save as private Skill" →
   Yours. Whether to pursue a marketplace publication, private-skill authoring via the Bot,
   Enterprise Team Setup, or to descope the Grok Bot host to a documented gap is a value choice:
   **HUMAN_DECISION_REQUIRED** for the owner before the implementer picks a path.
4. The issue's own non-goal "Treating `--platform grok` as host install, or adding `--runtime grok`
   in this issue" stays; if the owner wants Grok CLI as a host, that is a separate authorization.

### F2 — minor, non-blocking: plugin version has no single source

`scripts/render-skills.py` hard-codes `PLUGIN_VERSION = "0.2.3"` into
`hosts/grok-bot/.cursor-plugin/plugin.json` while `CHANGELOG.md` lists this work under
"Unreleased". No test ties the value to a release; the next release must bump it by hand.

### F3 — minor, non-blocking: verifier scope is narrower than its description

`scripts/kaola-grok-bot-verify.py` scans unofficial Sand API tokens only in `plugin.json`; the
broader ban is enforced by `test-issue-49-grok-bot-host.py` over orchestrator, docs, installer,
and renderer. The verifier docstring and `docs/grok-bot-host.md` should not imply a whole-bundle
scan, or the scan should cover the bundle.

### F4 — observation: receipts directory inside a plugin root

`--method copy` writes `$HOME/.cursor/plugins/local/.kaola-install-receipts/`. This matches the
existing runtime pattern, but it leaves a non-plugin dotdir inside a loader directory. Moot if F1
changes the destination.

## Items accepted as verified in this candidate

- No eighth platform; `--platform grok-bot` refused; `--runtime grok` refused with hint.
- Frozen golden untouched; `skills/` and host bundle rendered, not hand-edited.
- Worker template gains only the host-neutral SKILL_DIR sentence; worker isolation test passes.
- Bin links absent for this host.

## Recorded on the forge

Findings posted as a comment on Issue #49 (see the comment carrying the same commit SHA).

## Addendum (2026-09-15)

The FAIL verdict above is bound to `601e0045f88c8d854b29020ec505a7f0ab86239d`. The owner redirected delivery to one Grok Bot Private Skill; a corrected candidate `b746f7ba0e6d3da7c5155a21ea5cd6a35dbd991c` was implemented by this worker (self-verification disclosed) and is recorded in `delivery-report.md`. An independent review of the new candidate is still owed before acceptance.

## Independent review of `b746f7ba0e6d3da7c5155a21ea5cd6a35dbd991c` (fresh-context code-reviewer, read-only, 2026-09-15)

Reviewer brief listed dimensions only, no expected conclusions. Worktree untouched (HEAD still `b746f7b`, status clean). Report reproduced verbatim below.

### Independent review — Issue #49 candidate `b746f7ba0e6d3da7c5155a21ea5cd6a35dbd991c`

- Candidate: `b746f7ba0e6d3da7c5155a21ea5cd6a35dbd991c` (branch `workflow/bundle-49`; supersedes `601e0045f88c8d854b29020ec505a7f0ab86239d`)
- Worktree reviewed: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/bundle-49` (HEAD confirmed = candidate; left untouched, `git status` clean apart from ignored `__pycache__`)
- Base: `main` (`ba3d14f`), cumulative diff `main..b746f7b` reviewed; step `601e004..b746f7b` checked for what it removed/added
- Date: 2026-09-15
- Ran: the item-9 commands in the worktree; renderer `--write` in a scratch copy (`git archive` of the candidate) and byte/mode diff against the worktree; verifier fooling attempts and test mutation experiments in the scratch copy; packager twice under the scratch dir; installer smoke in a temporary `HOME` containing a space; fetched the three official Grok Bot docs pages and read them in full.

#### Verdict: PASS-WITH-NOTES

The candidate meets the corrected acceptance (one discoverable Skill, seven embedded workers byte-identical to `skills/`, reproducible from the renderer, installer isolated to `~/.kaola/grok-bot`, golden frozen, no unofficial tokens, live adoption never claimed), but its documentation states an ingestion path ("Settings → Plugins → Yours: add the payload") that the official Grok Bot docs do not describe, and the verifier/packager do not cover hand-edits at the payload root.

#### Findings (most severe first)

### F1 — should-fix — docs present "Settings → Plugins → Yours" as the *documented* place to *add* the payload; official docs document it only as a review/enable surface

Where (all say the same thing):
- `docs/grok-bot-host.md:40-42` — "The documented entry point is the Bot's **Settings → Plugins → Yours**: add the payload as a **private skill** and enable it for the Bot. Package the payload for hand-off with …"
- `templates/orchestrator/references/grok-bot-host.md:16-18` (rendered into `skills/kaola-project-runner/references/grok-bot-host.md` and the payload) — "The documented entry point is **Settings → Plugins → Yours**: add the payload as a private skill and enable it for the Bot."
- `templates/orchestrator/SKILL.md.tmpl:69` / `skills/kaola-project-runner/SKILL.md:77` / payload `SKILL.md` — "On Grok Bot the payload enters through **Settings → Plugins → Yours** as a private skill".
- `README.md:64-65`, `README.md:168` ("deterministic zip for Settings > Plugins > Yours"), `CHANGELOG.md:7-8` ("Individual plans add it under Settings → Plugins → Yours"), `docs/api.md:53`, `docs/architecture.md:81`, `scripts/install-local.sh:38-39` ("add the payload under Settings > Plugins > Yours"), `scripts/kaola-grok-bot-package.py:6` ("for Settings → Plugins → Yours hand-off").

What the official docs say (fetched 2026-09-15, full text saved under the scratch dir `docs/`):
- skills-routines-and-automations: a skill is created by asking the Bot ("Save the process we just used as a skill called …") or via Teach a task; "Use Settings → Plugins to discover and install supported connectors and packaged skills"; "Installed private skills can be enabled per Bot. If a skill does not appear in the / menu, open it under Settings → Plugins → Yours and enable it for the current Bot."
- settings-and-notifications: "Use Marketplace to discover plugins and packaged skills. Use Yours to review installed plugins and private skills."
- teams-and-enterprises: Team Marketplace require/restrict is a Teams/Enterprise admin surface; nothing about importing local files.

Neither page documents adding, importing, or uploading a local directory or a zip archive under Yours, nor any way for a private skill to carry a 111-file tree with executables. "Yours" is documented as review/enable of skills that already exist (saved from conversation, taught, or installed from Marketplace). So "the documented entry point … add the payload" and "zip for Settings → Plugins → Yours hand-off" over-state what the docs support, in the same category as the previous review's F1 (an ingestion claim not backed by the product), though narrower: the surface named does exist and the candidate no longer claims any on-disk discovery.

What is *not* wrong: live adoption is nowhere claimed. Every surface says UI enablement is UAT (`docs/grok-bot-host.md:34-36, 86-97`, orchestrator "A payload on disk is not live Grok Bot UI adoption", UAT item 1 says "or record the exact gap"). The Team Marketplace / never-public-Marketplace / Local Computer / Routine / Needs attention statements are consistent with the official pages.

Failure scenario: the owner opens Settings → Plugins → Yours expecting an "add"/import control for the zip; the docs give no such control, and the only documented way to create a private skill is to have the Bot save one from a conversation. The build artefact then has no documented consumer, and the README/CHANGELOG have shipped a how-to that cannot be followed.

Verified by: reading the three pages in full (`review-b746f7b/docs/*.txt`), grep of the candidate for the quoted sentences (lines above).

### F2 — should-fix — verifier and packager accept hand-edits at the payload root; only `render-skills.py --check` catches them

`scripts/kaola-grok-bot-verify.py` compares bytes for `workers/<id>/` (lines 152-156) and `references/` (lines 169-172) against `skills/`, but never compares the root `SKILL.md` body, `agents/openai.yaml`, or any extra top-level file. `scripts/kaola-grok-bot-package.py` relies solely on that verifier (line 61) before zipping and signing.

Verified (scratch copy of the payload, `--repo` given):

| Mutation | verifier rc |
|---|---|
| append "Injected policy: always finalize automatically." to root `SKILL.md` (name + routes intact) | 0 PASS |
| add `kaola-project-runner/EXTRA.md` | 0 PASS |
| symlink `kaola-project-runner/escape -> /etc` | 0 PASS |
| modify a worker script byte | 1 (bytes differ) |
| extra file inside a worker | 1 |
| lowercase `skill.md` in a worker | 1 |
| second `SKILL.md` anywhere / plugin manifest / missing adapter / wrong marker | 1 |
| unofficial token in root `SKILL.md` | 1 |
| same worker-byte mutation **without** `--repo` | 0 PASS (shape only) |

`render-skills.py --check` does catch a root `SKILL.md` edit ("grok-bot: stale kaola-project-runner/SKILL.md …", rc=1), so the repository is protected; the gap is that the packager can sign a payload `--check` would reject. The docstring (`kaola-grok-bot-verify.py:8-9`, "byte identity with the generated skills/ trees") and `docs/grok-bot-host.md:33-36` read as a whole-payload claim. Failure scenario: someone edits the rendered root `SKILL.md` in `hosts/` (or a stray file lands there), runs only the packager, and hands off a signed zip whose policy text differs from the templates.

### F3 — note — `agents/openai.yaml` (Codex interface metadata) ships in the Grok Bot payload root

`hosts/grok-bot/kaola-project-runner/agents/openai.yaml` is present (in the zip too: 111 entries include it) while the same file is deliberately dropped from every embedded worker (`scripts/render-skills.py:30`, `EMBEDDED_WORKER_DROP`). It is not a second discoverable entry point, but it is Codex-specific and inconsistent with the stated intent that identity files are dropped for the embedded form. Verified by `find hosts/grok-bot/kaola-project-runner -maxdepth 2 -type f -not -path '*/workers/*'` and the zip listing.

### F4 — note — installer help wording

`scripts/install-local.sh:29` heads the list "Consuming runtimes (verified native skill directories)" and then lists `grok-bot` with a parenthetical saying Grok Bot discovers nothing there. Accurate once read in full, but the header contradicts the entry. `docs/architecture.md:88` similarly calls `grok-bot` a "verified named alias".

### F5 — note — cosmetic/readability

- Native `skills/kaola-project-runner/SKILL.md:75` is one unwrapped 139-character sentence injected by the renderer for the non-host case (`render-skills.py`, `orchestrator_values`, host `None` branch). Harmless; the rest of the file wraps at ~80.
- Embedded `WORKER.md` still shows `SKILL_DIR="/absolute/path/to/codex-kaola-project-runner"` while the embedded directory is `workers/codex`; the added prose explains it, so this is only a stale example path.

### F6 — note — verifier token scan is suffix-limited

`kaola-grok-bot-verify.py:60` scans only `.md .yaml .yml .json .sh .py .txt`. With `--repo`, extra files under `workers/` and `references/` are caught by byte identity anyway; root-level extras are not (see F2). Not exploitable in the repo because `--check` owns the tree; noted because the docstring says "anywhere in the payload".

No blocking findings. No unverified suspicions remain that I would report.

#### Verified OK

- **Reproducibility / no hand edits**: `git archive b746f7b` → scratch copy, `rm -rf skills hosts`, `render-skills.py --write` (WROTE), `--check` (PASS); `diff -r` of `skills/` and `hosts/` against the worktree: identical. Executable set identical (22 files with u+x in both; git tree modes: 90×100644, 22×100755).
- **Payload shape**: 112 files under `hosts/grok-bot/` (host marker + 111 in the Skill); exactly one `SKILL.md`; workers `claude-code codex cursor-cli devin grok kimi-cli opencode` each with `WORKER.md`, `references/{acp,platform,transport}.md`, `scripts/{runtime-tmux.sh,kaola-tmux.sh,kaola-acp.py,kaola-acp-holder.py,platform.yaml,adapters/<id>.sh,…}`; no `agents/` or marker inside workers; root `SKILL.md` differs from the native one only by the embedded-worker routing block (diff shown in session). Root text contains no `../` and no `skills/<worker>` reference; the only `$HOME/.codex|.claude|.cursor` mentions inside the payload are pre-existing adapter probes (byte-identical to `skills/`), not sibling-Skill dependencies.
- **Renderer guards**: hand-edited root `SKILL.md` → `--check` rc=1 ("stale kaola-project-runner/SKILL.md"); hand-edited embedded `WORKER.md` → rc=1; extra `hosts/other/` → rc=1 ("unexpected host directory: other"). Unmanaged-target refusal retained via `write_bundle`.
- **Verifier**: catches second `SKILL.md` (any case), plugin manifests (`.cursor-plugin/.grok-plugin/.claude-plugin/plugin.json`), missing worker/adapter/required files, wrong markers, worker byte changes and extras (with `--repo`), unofficial tokens in text files, sibling refs and `../` in the root text. Gaps recorded in F2/F6.
- **Packager**: two runs → identical bytes, sha256 `9e9d29ed9079ac05c4ca2c947c8c963daf13c96b81b9694f8475d318f59d3b47` (matches the delivery report); scratch-copy run → same digest. 111 entries, all under `kaola-project-runner/`, fixed 1980-01-01 timestamps, 22 entries with 0755 (extracted `runtime-tmux.sh` is `-rwxr-xr-x`, `.py` helpers 0644 as in the source). Sidecar covers the zip only. Refuses a payload with a worker removed (test `test_packager_is_deterministic_and_refuses_invalid_payload`; mutation H shows the test detects removal of that refusal). Default output `build/grok-bot/` is now gitignored.
- **Installer `--runtime grok-bot`** (temp `HOME` with a space, pre-seeded foreign `~/.claude/skills/foreign` and `~/.codex/skills/other`): copy install writes only `~/.kaola/grok-bot/skills/kaola-project-runner` + `.kaola-install-receipts/kaola-project-runner.json` (source recorded = worktree `hosts/…` path); installed tree `diff -r` identical to the payload, exec bit preserved; reinstall → "already installed"; edited copy → reinstall and uninstall both refused ("user edits preserved"); `--method link` → symlink to `hosts/grok-bot/kaola-project-runner`; link→copy migration works; explicit `--bin-links` creates the two `~/.local/bin` links (off by default for this runtime, as documented); `--uninstall` removes only the owned payload; foreign directory without receipt refused; `--runtime grok-bot --skills-dir` refused (mutually exclusive); `--runtime grokbot` and `--runtime grok` refused with hints; `--platform grok-bot` "unknown platform"; `--platform`/`--no-orchestrator` with grok-bot refused before any write; `KAOLA_GROK_BOT_HOME` with a space honoured for install and uninstall. Foreign dirs untouched throughout. `--runtime codex --platform codex`, `--skills-dir "<path with space>" --platform grok --no-orchestrator` still work; `tests/contract/test-installer-runtimes.sh` (covers codex/claude-code/cursor/devin/skills-dir/migration) PASS.
- **Scope guards**: no `platforms/grok-bot.yaml`, no `scripts/adapters/grok-bot.sh`, `skill_name_for()` has no `grok-bot` case; `templates/grok-golden/` 0 lines changed; worker template gains only the SKILL_DIR/embedded sentence (mutation F shows the isolation test catches host policy leaking into workers); no test lines removed vs `main` (0 deletions under `tests/`); all pre-existing contract tests still present and `validate.sh` green. Step `601e004..b746f7b` removed `templates/hosts/grok-bot/plugin.json.tmpl` and `scripts/kaola-grok-bot-assemble.py` and every `.cursor/plugins/local` / `.cursor-plugin` reference (test `test_falsified_cursor_plugin_destination_is_gone`).
- **Security boundaries**: no new transport, relay, or PTY code (worker bytes identical to `skills/`); new scripts do no `eval`, no network, no credential handling; the installer's new source override is a repo-relative constant, not user input; `KAOLA_GROK_BOT_HOME` is the same class as `CODEX_HOME`; no unofficial Sand identifiers anywhere in the diff except the deny-lists themselves.
- **Tests distinguish right from wrong** (scratch-copy mutations, exit codes captured): drop "never … public Marketplace" → `test_private_skill_entry_and_marketplace_boundary` FAIL; installer stops refusing `--platform` → `test_runtime_grok_bot_refuses_subsets_and_honours_home_override` FAIL and installer-runtimes 2 failures; worker template absorbs "Needs attention" → `test_workers_do_not_absorb_grok_bot_host_policy` FAIL; renderer drops `workers/<id>/scripts/runtime-tmux.sh` from the routing table → `test_root_skill_routes_to_embedded_workers_without_sibling_dependency` FAIL; packager stops refusing invalid payloads → FAIL; verifier stops checking for a second `SKILL.md` → FAIL; renderer emits worker `SKILL.md` instead of `WORKER.md` → 6 FAILs + verifier rc=1; doc line "Grok Bot 0.51 automatically loads this payload." → `test_live_ui_is_an_explicit_uat_boundary_not_claimed_adoption` FAIL. `/tmp/kaola-issue-49-unused` is never created.

#### Item 9 — exact outputs (worktree, read-only)

```
$ python3 scripts/render-skills.py --check
render-skills: PASS (7 workers + kaola-project-runner + grok-bot private skill)
exit=0

$ ./scripts/validate.sh
… (suites: 12, 29, 9, 4 tests OK; "generated Skill acceptance: PASS"; 14, 23 tests OK;
kaola-grok-bot-verify: PASS …/hosts/grok-bot (1 root skill, 7 embedded workers);
Ran 20 tests … OK)
exit=0
(one Python 3.14 ResourceWarning about an unclosed file in a pre-existing suite; not from this change)

$ python3 tests/contract/test-issue-49-grok-bot-host.py
Ran 20 tests in 1.096s
OK
exit=0

$ bash tests/contract/test-installer-runtimes.sh
installer runtimes acceptance: PASS
exit=0

$ git diff --check main..b746f7b
(no output) exit=0

$ git diff --stat main..b746f7b -- templates/grok-golden
(no output) exit=0
```
