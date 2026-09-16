# Grok Bot host

Grok Bot is a Project Runner **host**, at the same rank as Codex, Claude Code,
Cursor, and Devin. It is not an eighth CLI worker, and it is not an installer
destination: it is a **bridge host**.

| Id | Meaning | Flag |
|---|---|---|
| `grok-bot` | Grok Bot desktop/cloud host: one thin account Skill (the bridge) loads the canonical Skills from a verified checkout on the bound execution target | none (`--runtime grok-bot` is refused) |
| `grok` | Grok CLI worker (ACP `grok agent stdio`) | `--platform grok` |

`--platform grok-bot` is invalid. `--runtime grok` is not a host alias.

## Delivery shape: one thin account Skill, everything else in the repository

Research on Grok Bot 0.51.0 (Issue #49, 2026-09-16) returned
`NO_SUPPORTED_PATH`: there is no supported, automated way to create or update
an account-private Skill without the body passing through the model, and the
earlier eight-full-Markdown delivery cost ≈ 105–120 k tokens per install while
flattening references into every body. The owner therefore locked
**progressive disclosure** as a platform-neutral invariant (see
[conventions](conventions.md#progressive-disclosure)) and reduced the Grok Bot
delivery to exactly **one** very small account Skill. `./scripts/render-skills.py
--write` emits `hosts/grok-bot/`:

```text
hosts/grok-bot/
  .generated-by-kaola-project-runner
  kaola-project-runner.md   # the bridge: one single-Markdown account Skill (≈ 2.3 KB)
  bridge.json               # fingerprint manifest: stage, saveable, name, description, accepted commit, sha256, bytes
  INSTALL.md                # two-commit model, one-write install, first configuration, read-only Mac UAT (not a Skill)
```

The bridge (`templates/grok-bot/bridge.md.tmpl` + `accepted-revision.json`)
names only: the repository `KaolaBrother/kaola-project-runner`, the expected
origin, the accepted pinned revision (40-hex commit plus an honest label or
release tag; the one line that changes on a pin), the device-local locator
command `kaola-project-runner-locate`, and the two canonical entry paths
`ROOT/skills/kaola-project-runner/SKILL.md` and
`ROOT/skills/<platform>-kaola-project-runner/SKILL.md`. It carries **no**
canonical policy, transport, reference, worker text, fixed or default path,
HOME convention, username, environment variable, symlink convention, runtime
copy, per-worker account Skills, bundled references, credential handling,
private API, Sand RPC, or Marketplace. `scripts/kaola-grok-bot-verify.py` and
`tests/contract/test-issue-49-grok-bot-host.py` prove that structurally: no
sentence of any canonical Skill or reference appears in the bridge, no worker
is named (only the selected `<platform>` placeholder), a canonical or platform
manifest edit leaves all three products byte-identical, and a new pin changes
exactly one line.

## Two commits: content R, then pin P

A commit cannot contain its own hash, so an honest delivery is two commits and
`templates/grok-bot/accepted-revision.json` declares a **stage**:

| Stage | Commit | `accepted-revision.json` | Bridge line | Saveable |
|---|---|---|---|---|
| `content` | R: runtime, docs, tests; the clean detached UAT target | `{"stage": "content"}` | `Accepted revision: none yet … do not save it to any account.` | no (`bridge.json` `saveable: false`) |
| `pinned` | P: follows R; changes only this file plus the three regenerated products | `{"stage": "pinned", "commit": R, "label": "…"}` or `"release": "vX.Y.Z"` | `Accepted revision: R (label).` | yes |

At the pinned stage `render-skills.py --check`/`--write` and
`kaola-grok-bot-verify.py --repo` run the **pin gate** against the Git
checkout: R exists, is an ancestor of HEAD, is itself a content-stage commit
(never a self-pin, never another pin commit), holds
`scripts/kaola-locate.py`, `skills/kaola-project-runner/SKILL.md`, and every
selectable worker's `SKILL.md` and `scripts/runtime-tmux.sh`, and a named
`release` is a tag at R, and the **P delta** is machine-enforced: the tracked
working tree, compared directly with R (so the gate holds before P is committed
and at a clean HEAD = P alike), may differ from R only by `templates/grok-bot/accepted-revision.json` and the three
generated `hosts/grok-bot/` products, and the bridge may differ from R's bridge
by exactly one line (the content-stage placeholder replaced by the
accepted-revision line). A rebased or squashed pair, or a pair merged with an
advanced `main`, therefore fails `--require-pinned`. An unverifiable pin is
never written. `--require-pinned` (renderer and verifier) is the final gate for
P; R passes plain `--check` at the content stage, so both commits are
reproducible without weakening the P gate. The label is 3–80 plain characters,
states the truth ("pre-release UAT candidate for Issue #49; not a release"), and
may not masquerade as a release (no `vX.Y.Z` token, never beginning with
"release"); a release tag is used only once the tag exists at R. Nothing here
releases or tags.

Finalization precondition: **never rebase, squash, or amend an accepted R/P
pair**; the reviewed and UAT-tested bytes are R and P exactly. If `main` moves
before merge, create a fresh content commit R′ and pin commit P′ on top of it
and re-run review and UAT. A release is a tag placed at R followed by a new pin
commit naming that tag (`release: vX.Y.Z` at R); rollback is a new pin commit
naming an older R, followed by the same one account write and per-target
re-registration.

## Execution targets: bind first, never cross

Grok Bot runs **cloud Agent Computer** projects and **Local Computer** (Mac
Mini) projects. An account Skill or a checkout on the cloud computer must never
be assumed to reach the Mac filesystem, local project, local CLI, tmux, or
sessions, and vice versa. On every use the bridge:

1. binds the execution target first;
2. asks **that target's** locator `kaola-project-runner-locate` for its canonical
   repo root ROOT (normalised origin, HEAD, clean state, host fingerprint);
3. refuses unless the receipt's `host.fingerprint` is the one recorded when that
   target's locator was registered, origin is
   `github.com/KaolaBrother/kaola-project-runner`, HEAD equals the accepted
   revision, and the tree is clean;
4. accepts the consumer project root as a separate path on the same target;
5. loads `ROOT/skills/kaola-project-runner/SKILL.md`, and at dispatch only the
   selected `ROOT/skills/<platform>-kaola-project-runner/SKILL.md`, running
   that directory's scripts on the same target and never reading their source.

- **Local Computer (Mac):** the Mac already holds the repository. Its `main`
  working tree may carry untracked Workflow records (`kaola-workflow/…`) and
  other local files, which the locator correctly reports as `dirty`: the owner
  therefore selects a clean checkout or worktree detached at R (for example
  `git worktree add --detach <owner-chosen path> R` on the Mac); no fixed path
  is assumed and the clean-tree check is never weakened. The cloud Agent
  Computer never clones, installs, updates, or manages anything on the Mac. The
  Mac path lives only in the Mac's locator link, never in the account Skill;
  moving the checkout means re-registering the locator, not rewriting any Skill.
- **Cloud Agent Computer:** for a project that lives there, that computer may
  choose its own persistent directory, clone or update its own checkout with
  its own existing Git or GitHub CLI authentication, detach to the accepted
  revision, and register its own locator. That checkout never operates on Mac
  paths, CLIs, tmux, or sessions.

## The locator: `scripts/kaola-locate.py`

The locator is the smallest existing-repo-compatible mechanism: a symlink named
`kaola-project-runner-locate` to `<checkout>/scripts/kaola-locate.py`, placed in
the same bin directory the installer's `--bin-links` already manages (it is now
one of those links; `--bin-dir DIR` chooses any other directory on PATH). No
service, daemon, registry, or filesystem scan; the link is the whole locator.
`register --target local|cloud --expect-revision R` validates origin, the
required `--expect-revision`, the clean state, the link path, and the receipt
path **before** it touches anything: a foreign, dirty, or mismatched checkout is
refused and an existing locator link and registration receipt stay exactly as
they were (`Issue49LocatorAttestation` proves it); only a clean, matching
checkout re-registers. On success it links the command and then atomically
writes the **registration receipt** `.kaola-project-runner-locate.json` beside
the link (`kaola-project-runner-locator-registration/1`): resolved ROOT, the
declared target, host kernel and hashed fingerprint, the accepted revision
(required, so a later HEAD move is always `registration-stale`). It stores no hostname field, no username field, no credential, and no
account data (the root is a real local path and may include the user's home);
the receipt is device-local and never enters any Skill. Every later locator call
compares the running host fingerprint, the declared `--target`, the ROOT the
link resolves to, and HEAD with that receipt and fails closed
(`host-fingerprint-mismatch`, `target-mismatch`, `registration-root-mismatch`,
`registration-stale`; `locator-not-registered` when a target is declared and no
receipt exists), so a fresh conversation needs no memory of the fingerprint.
The origin is accepted only in an explicit `https://`, `ssh://`, or scp
`host:path` form and normalised without userinfo or port; a bare
`github.com/Owner/repo`, `http://`, or local-path origin is
`origin-form-unsupported`, as is a malformed value with a second `@` in its
host or a `?`/`#` query or fragment (nothing of it is echoed). It never reads, prints, hashes, or forwards a
credential and runs Git with `GIT_TERMINAL_PROMPT=0`.

```bash
python3 "$ROOT/scripts/kaola-locate.py" register --target local|cloud --expect-revision R [--bin-dir DIR]   # validate, link, write the receipt
kaola-project-runner-locate                                          # ROOT, origin, HEAD, clean, fingerprint, registration facts
kaola-project-runner-locate --target local|cloud --expect-revision <accepted> \
  --project <consumer project root> --worker <platform id> --session <exact session name>
```

The last form is the **fail-closed host-target attestation** run before each
worker dispatch. Its receipt is one JSON line (≤ 4 KB, `locator_receipt_bytes`):

| Field | Evidence |
|---|---|
| `target` | the kind **as declared** by the caller, `local` or `cloud` (required when attesting); echoed, never inferred |
| `host` | kernel and a hashed hostname fingerprint; the locator compares it with the value recorded in the registration receipt |
| `root` | ROOT path on this host (a real local path, may include the user's home), normalised origin (never the raw URL or userinfo), HEAD, `clean`, `revision_match` |
| `registration` | receipt path, `present`, recorded target and accepted revision, `fingerprint_match`, `target_match`, `root_match`, `revision_current` |
| `project` | path on this host (real local path), Git top level, normalised origin |
| `worker` | selected id, `skills/<id>-kaola-project-runner/scripts/runtime-tmux.sh`, `under_root`, `executable` |
| `session` | exact session name and whether the tmux server reachable from the locator reports it present (presence on that server only: not existence elsewhere, never ownership, which is the worker preflight's proof) |
| `result` | `ok`, or `refused` with `reasons` |

What the receipt proves is bounded and real: the command ran on the bound
target (the link is device-local), the host is the one registered there
(fingerprint), and ROOT, the consumer project, the selected worker script, and
the session all co-locate on that executing host. What it cannot prove is
physical host kind: the script does not classify Mac versus cloud, and the
docs, tests, and bridge do not claim it does. Paths in the receipt are local
evidence for that target and never enter the account Skill. Revision and clean
facts are what the executing host's own Git reports (`rev-parse`, `status
--porcelain`): index tricks such as `assume-unchanged` or `skip-worktree` and a
tampered `.git` on that trusted host are explicitly outside this boundary, and
no content hashing is attempted. Reasons: `origin-mismatch`,
`origin-form-unsupported`, `revision-mismatch`, `dirty`, `no-head`,
`not-a-checkout`, `target-required`, `expect-revision-required`, `expect-revision-not-40-hex`,
`locator-not-registered`, `locator-registration-unreadable`,
`host-fingerprint-mismatch`, `target-mismatch`, `registration-root-mismatch`,
`registration-stale`, `project-not-on-this-host`, `project-not-a-checkout`,
`worker-unknown`, `script-missing`, `script-outside-root`,
`script-not-executable`, `foreign-locator-link`, `locator-path-occupied`,
`registration-path-occupied`. A path that does not exist on the executing host
is refused as `project-not-on-this-host` whatever target was declared; a target
other than the registered one is `target-mismatch`; the contract tests prove
both, plus fresh-conversation semantics (the link alone, in a new process,
passes) and tampering (each edited receipt field is refused).

## Host adapter boundary

The bridge is produced by the `grok-bot` host adapter inside `render-skills.py`
(the delimited "Host adapter: grok-bot" section). Its inputs are exactly
`GROK_BOT_ADAPTER_INPUTS` = `templates/grok-bot/` (bridge template, guide
template, accepted revision): the adapter's product functions take no platform
manifest, read **no** canonical source, and copy nothing; the guide uses the
`<platform id>` placeholder instead of a concrete worker. Grok Bot has no
`platforms/grok-bot.yaml` and no `scripts/adapters/grok-bot.sh`. `--write` owns
the three products; `--check` and `kaola-grok-bot-verify.py --repo` reject any
drift, over-budget product, malformed stage, or unverifiable pin. See
[architecture](architecture.md#host-adapters-one-canonical-skill-system).

## Install and UAT (owner; read-only on the Mac)

`hosts/grok-bot/INSTALL.md` is the generated guide. In short:

1. **One write on the account, from P only.** Save the pinned
   `hosts/grok-bot/kaola-project-runner.md` (`bridge.json` `saveable: true`) as
   the private Skill `kaola-project-runner` (name/description from the
   frontmatter, resolved values in `bridge.json`; body after the closing
   `---`); same-name update in place. This is the only account operation (no
   Marketplace, credential, ZIP import, unofficial Sand or RPC path, or state
   hack). A content-stage bridge is never saved.
2. **First configuration on Local Computer.** On the Mac the owner selects a
   clean checkout or worktree detached at R (the existing `main` checkout may
   hold untracked Workflow records and would be `dirty`) and an owner-selected
   persistent directory on PATH for the locator link (`BIN`), so the
   installer-managed `--bin-links` link in `~/.local/bin` is left alone. With
   Execution on Local Computer, inside that workspace: `git rev-parse
   --show-toplevel` → ROOT, `python3 "$ROOT/scripts/kaola-locate.py" register
   --target local --bin-dir "$BIN" --expect-revision R` (validates first, then
   links and writes `$BIN/.kaola-project-runner-locate.json`), then
   `kaola-project-runner-locate --target local --expect-revision R` → `ok`
   (the locator itself checks the fingerprint and target against the receipt).
3. **Read-only preflight.** Attest with `--project <existing local project>
   --worker <platform id> --session <existing session>`, then run
   `ROOT/skills/<platform id>-kaola-project-runner/scripts/runtime-tmux.sh
   preflight` against that project and session. Expected: `ok` attestation
   (session presence; ownership comes from the preflight), preflight evidence,
   and nothing started, sent, stopped, cloned, fetched, checked out, or
   installed; the Bot read only the main Skill and the one selected worker
   Skill, no script source; the cloud Agent Computer executed nothing and
   accessed no Mac file. After UAT, remove `$BIN/kaola-project-runner-locate`
   and its receipt or keep them registered; the normal installer-managed link
   is restored with `./scripts/install-local.sh --bin-links` from the normal
   checkout (it refuses to overwrite a link it does not own, so remove a UAT
   link placed in its directory first) and then registered from that checkout.

A saved bridge is not live adoption; this read-only UAT is the boundary. Three
kinds of evidence stay distinct and none substitutes for another: Grok Bot's
accepted `SKILL_EXPOSURE: PASS` at `bc8592d` settles that the account holds the
loadable bridge; the locator attestation and the worker `preflight` establish
**placement** on the bound target (ROOT, registration, consumer project,
selected worker script, session presence); and **actual runtime use** is a
separately authorized scoped real-use smoke against one existing project and
session, never part of installation.

Historical note (Issue #56, recorded here only). The guide and the shared host
reference must never tell the Agent to confirm the write in Settings → Plugins →
Yours or through `/` discovery, as they once did. That account list does not
expose an account-private Skill and a 1:1 Bot chat offers no slash discovery, so
those checks were impossible: they are not installation or acceptance gates and
are never asked of the owner or the Bot again. The agent-facing guide and
reference now carry no account-UI discussion at all, because the Agent needs only
the one save, the target binding, the locator, the read-only preflight, and the
real-use boundary.

Routine-only heartbeat, takeover, `HUMAN_DECISION_REQUIRED` in this Bot
conversation, and acceptance-before-finalize stay as stated in the main Skill
and `skills/kaola-project-runner/references/grok-bot-host.md`.

## Update and rollback

A new pin (content commit R′, then pin commit P′) rewrites
`templates/grok-bot/accepted-revision.json`; `--write` then changes exactly one
line of the bridge, which is one more account write. Local: the owner moves the
Mac checkout or worktree to R′ and runs `register` again (the receipt records
the accepted revision, so a stale registration is refused). Cloud:
`git -C ROOT fetch origin <commit> && git -C ROOT checkout --detach <commit>`,
then `register`. Rollback is a new pin commit naming an older R, applied the
same way; the accepted pair itself is never rewritten. Cloud registration passes
`--target cloud --expect-revision R` exactly like Local Computer. Removal: delete
the account Skill through the same native write used to save it and remove the
locator link and its receipt (`rm "$BIN/kaola-project-runner-locate" "$BIN/.kaola-project-runner-locate.json"`,
or `./scripts/install-local.sh --uninstall --bin-links` for the installer-managed
link). Do not Reset Agent Computer; do not stop unrelated workers.

## Token cost (chars ÷ 4 … ÷ 3.5)

| Phase | Bridge (this candidate) | Eight bodies (`aba7d74`, void) |
|---|---|---|
| Install (once) | 1 write ≈ 0.6–0.7 k out + locator receipt ≈ 0.3 k in | 8 writes ≈ 52–59 k out + same in ≈ 105–120 k |
| Discovery (per turn) | ≈ 0.07 k description; worst case ≈ 0.7 k body | ≈ 0.5 k descriptions; worst case 52–59 k |
| Main activation | receipt ≈ 0.3 k + body 15.3 KB ≈ 3.8–4.4 k | 24 KB ≈ 6–7 k, references pre-flattened |
| One selected worker | 10.7 KB ≈ 2.7–3.1 k; references on demand | 26–27 KB ≈ 6.5–7.7 k; seven if injected ≈ 45–53 k |
| Update (pin) | one revision line, 1 write ≈ 0.6–0.7 k | ≈ 105–120 k |

## Out of scope

Unofficial Sand gateways, GrokBot RPCs, NCI, `platforms/grok-bot.yaml`, public
or Team Marketplace publication, ZIP or file-tree import claims, a runtime copy,
per-worker account Skills, a scheduler or update daemon, and Grok CLI as a host
(`--runtime grok`).
