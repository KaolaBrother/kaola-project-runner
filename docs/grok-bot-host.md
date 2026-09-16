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
`release` is a tag at R. An unverifiable pin is never written. `--require-pinned`
(renderer and verifier) is the final gate for P; R passes plain `--check` at the
content stage, so both commits are reproducible without weakening the P gate.
The label is 3–80 plain characters and states the truth ("pre-release UAT
candidate for Issue #49; not a release"); a release tag is used only once the
tag exists at R. Nothing here releases or tags.

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
`register` validates origin, the optional `--expect-revision`, the clean state,
and the link path **before** it touches anything: a foreign, dirty, or
mismatched checkout is refused and an existing locator link stays exactly as it
was (`Issue49LocatorAttestation` proves it); only a clean, matching checkout
re-registers. It never reads, prints, hashes, or forwards a credential and runs
Git with `GIT_TERMINAL_PROMPT=0`.

```bash
python3 "$ROOT/scripts/kaola-locate.py" register [--bin-dir DIR] [--expect-revision R]   # validate, then link
kaola-project-runner-locate                                          # ROOT, origin, HEAD, clean, fingerprint
kaola-project-runner-locate --target local|cloud --expect-revision <accepted> \
  --project <consumer project root> --worker <platform id> --session <exact session name>
```

The last form is the **fail-closed host-target attestation** run before each
worker dispatch. Its receipt is one JSON line (≤ 4 KB, `locator_receipt_bytes`):

| Field | Evidence |
|---|---|
| `target` | the kind **as declared** by the caller, `local` or `cloud` (required when attesting); echoed, never inferred |
| `host` | kernel and a hashed hostname fingerprint; compare it with the value recorded at that target's registration |
| `root` | ROOT path on this host (a real local path, may include the user's home), normalised origin (never the raw URL or userinfo), HEAD, `clean`, `revision_match` |
| `project` | path on this host (real local path), Git top level, normalised origin |
| `worker` | selected id, `skills/<id>-kaola-project-runner/scripts/runtime-tmux.sh`, `under_root`, `executable` |
| `session` | exact session name and whether tmux reports it present (presence only; ownership is the worker preflight's proof) |
| `result` | `ok`, or `refused` with `reasons` |

What the receipt proves is bounded and real: the command ran on the bound
target (the link is device-local), the host is the one registered there
(fingerprint), and ROOT, the consumer project, the selected worker script, and
the session all co-locate on that executing host. What it cannot prove is
physical host kind: the script does not classify Mac versus cloud, and the
docs, tests, and bridge do not claim it does. Paths in the receipt are local
evidence for that target and never enter the account Skill. Reasons:
`origin-mismatch`, `revision-mismatch`, `dirty`, `no-head`, `not-a-checkout`,
`target-required`, `expect-revision-not-40-hex`, `project-not-on-this-host`,
`project-not-a-checkout`, `worker-unknown`, `script-missing`,
`script-outside-root`, `script-not-executable`, `foreign-locator-link`,
`locator-path-occupied`. A path that does not exist on the executing host is
refused as `project-not-on-this-host` whatever target was declared; the
contract tests prove that and that the same real path is accepted under either
declaration.

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
   `---`); same-name update in place. Settings → Plugins → Yours shows exactly
   one Skill; `/` offers it. This is the only account operation (no Marketplace,
   credential, ZIP import, unofficial Sand or RPC path, or state hack). A
   content-stage bridge is never saved.
2. **First configuration on Local Computer.** On the Mac the owner selects a
   clean checkout or worktree detached at R (the existing `main` checkout may
   hold untracked Workflow records and would be `dirty`). With Execution on
   Local Computer, inside that workspace: `git rev-parse --show-toplevel` →
   ROOT, `python3 "$ROOT/scripts/kaola-locate.py" register --expect-revision R`
   (validates first, then links), then `kaola-project-runner-locate --target
   local --expect-revision R` → `ok`; record `host.fingerprint` with the target.
3. **Read-only preflight.** Attest with `--project <existing local project>
   --worker <platform id> --session <existing session>`, then run
   `ROOT/skills/<platform id>-kaola-project-runner/scripts/runtime-tmux.sh
   preflight` against that project and session. Expected: `ok` attestation
   (session presence; ownership comes from the preflight), preflight evidence,
   and nothing started, sent, stopped, cloned, fetched, checked out, or
   installed; the Bot read only the main Skill and the one selected worker
   Skill, no script source; the cloud Agent Computer executed nothing and
   accessed no Mac file.

A saved bridge is not live adoption; this read-only UAT is the boundary.
Routine-only heartbeat, takeover, `HUMAN_DECISION_REQUIRED` in this Bot
conversation, and acceptance-before-finalize stay as stated in the main Skill
and `skills/kaola-project-runner/references/grok-bot-host.md`.

## Update and rollback

A new pin (content commit R′, then pin commit P′) rewrites
`templates/grok-bot/accepted-revision.json`; `--write` then changes exactly one
line of the bridge, which is one more account write. Local: the owner moves the
Mac checkout or worktree to R′ on the Mac and the locator re-verifies. Cloud:
`git -C ROOT fetch origin <commit> && git -C ROOT checkout --detach <commit>`.
Rollback is the previous accepted revision. Removal: delete the Skill under
Settings → Plugins → Yours and remove the locator link
(`./scripts/install-local.sh --uninstall --bin-links` or `rm` the link). Do not
Reset Agent Computer; do not stop unrelated workers.

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
