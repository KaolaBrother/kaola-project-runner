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
  kaola-project-runner.md   # the bridge: one single-Markdown account Skill (≈ 2 KB)
  bridge.json               # fingerprint manifest: name, description, accepted commit, sha256, bytes
  INSTALL.md                # one-write install, first configuration, read-only Mac UAT (not a Skill)
```

The bridge (`templates/grok-bot/bridge.md.tmpl` + `accepted-revision.json`)
names only: the repository `KaolaBrother/kaola-project-runner`, the expected
origin, the accepted pinned revision (40-hex commit + release; the one line that
changes on a release), the device-local locator command
`kaola-project-runner-locate`, and the two canonical entry paths
`ROOT/skills/kaola-project-runner/SKILL.md` and
`ROOT/skills/<platform>-kaola-project-runner/SKILL.md`. It carries **no**
canonical policy, transport, reference, worker text, fixed or default path,
HOME convention, username, environment variable, symlink convention, runtime
copy, per-worker account Skills, bundled references, credential handling,
private API, Sand RPC, or Marketplace. `scripts/kaola-grok-bot-verify.py` and
`tests/contract/test-issue-49-grok-bot-host.py` prove that structurally: no
sentence of any canonical Skill or reference appears in the bridge, no worker
is named (only the selected `<platform>` placeholder), a canonical edit leaves
the bridge byte-identical, and a new accepted revision changes exactly one line.

## Execution targets: bind first, never cross

Grok Bot runs **cloud Agent Computer** projects and **Local Computer** (Mac
Mini) projects. An account Skill or a checkout on the cloud computer must never
be assumed to reach the Mac filesystem, local project, local CLI, tmux, or
sessions, and vice versa. On every use the bridge:

1. binds the execution target first;
2. asks **that target's** locator `kaola-project-runner-locate` for its canonical
   repo root ROOT (normalised origin, HEAD, clean state);
3. refuses unless origin is `github.com/KaolaBrother/kaola-project-runner`,
   HEAD equals the accepted revision, and the tree is clean;
4. accepts the consumer project root as a separate path on the same target;
5. loads `ROOT/skills/kaola-project-runner/SKILL.md`, and at dispatch only the
   selected `ROOT/skills/<platform>-kaola-project-runner/SKILL.md`, running
   that directory's scripts on the same target and never reading their source.

- **Local Computer (Mac):** the Mac already holds the checkout and its local
  Skill installation. The cloud Agent Computer never clones, installs, updates,
  or manages anything on the Mac. The Mac path lives only in the Mac's locator
  link, never in the account Skill; moving the checkout means re-registering
  the locator, not rewriting any Skill.
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
service, daemon, registry, or filesystem scan; the link is the whole locator,
and re-registration from a moved checkout replaces it. It never reads, prints,
hashes, or forwards a credential and runs Git with `GIT_TERMINAL_PROMPT=0`.

```bash
python3 "$ROOT/scripts/kaola-locate.py" register [--bin-dir DIR]   # device-local registration
kaola-project-runner-locate                                          # ROOT, origin, HEAD, clean
kaola-project-runner-locate --target local|cloud --expect-revision <accepted> \
  --project <consumer project root> --worker <platform id> --session <exact session>
```

The last form is the **fail-closed host-target attestation** run before each
worker dispatch. Its receipt is one JSON line (≤ 4 KB, `locator_receipt_bytes`):

| Field | Evidence |
|---|---|
| `target` | declared kind, `local` or `cloud` (required when attesting) |
| `host` | kernel and a hashed host fingerprint (no hostname, no user) |
| `root` | ROOT path on this host, normalised origin (never the raw URL or userinfo), HEAD, `clean`, `revision_match` |
| `project` | path on this host, Git top level, normalised origin |
| `worker` | selected id, `skills/<id>-kaola-project-runner/scripts/runtime-tmux.sh`, `under_root`, `executable` |
| `session` | exact session name and whether tmux reports it present |
| `result` | `ok`, or `refused` with `reasons` |

Reasons: `origin-mismatch`, `revision-mismatch`, `dirty`, `no-head`,
`not-a-checkout`, `target-required`, `expect-revision-not-40-hex`,
`project-not-on-this-host`, `project-not-a-checkout`, `worker-unknown`,
`script-missing`, `script-outside-root`, `script-not-executable`. A cloud path
handed to a Local Computer dispatch, or a Mac path handed to a cloud dispatch,
does not exist on the executing host and is refused as
`project-not-on-this-host`; the contract tests prove both directions.

## Host adapter boundary

The bridge is produced by the `grok-bot` host adapter inside `render-skills.py`
(the delimited "Host adapter: grok-bot" section). Its inputs are exactly
`GROK_BOT_ADAPTER_INPUTS` = `templates/grok-bot/` (bridge template, guide
template, accepted revision): the adapter reads **no** canonical source and
copies nothing. Grok Bot has no `platforms/grok-bot.yaml` and no
`scripts/adapters/grok-bot.sh`. `--write` owns the three products; `--check`
and `kaola-grok-bot-verify.py --repo` reject any drift, over-budget product, or
non-40-hex revision. See
[architecture](architecture.md#host-adapters-one-canonical-skill-system).

## Install and UAT (owner; read-only on the Mac)

`hosts/grok-bot/INSTALL.md` is the generated guide. In short:

1. **One write on the account.** Save `hosts/grok-bot/kaola-project-runner.md`
   as the private Skill `kaola-project-runner` (name/description from the
   frontmatter, resolved values in `bridge.json`; body after the closing
   `---`); same-name update in place. Settings → Plugins → Yours shows exactly
   one Skill; `/` offers it. This is the only account operation (no Marketplace,
   credential, ZIP import, unofficial Sand or RPC path, or state hack).
2. **First configuration on Local Computer.** With Execution on Local Computer,
   inside the local workspace the owner names: `git rev-parse --show-toplevel`
   → ROOT (the existing checkout, never a clone), `python3
   "$ROOT/scripts/kaola-locate.py" register`, then
   `kaola-project-runner-locate --target local --expect-revision <accepted>`
   → `ok`.
3. **Read-only preflight.** Attest with `--project <existing local project>
   --worker <id> --session <existing session>`, then run
   `ROOT/skills/<id>-kaola-project-runner/scripts/runtime-tmux.sh preflight`
   against that project and session. Expected: `ok` attestation, preflight
   evidence, and nothing started, sent, stopped, cloned, fetched, checked out,
   or installed; the Bot read only the main Skill and the one selected worker
   Skill, no script source; the cloud Agent Computer executed nothing and
   accessed no Mac file.

A saved bridge is not live adoption; this read-only UAT is the boundary.
Routine-only heartbeat, takeover, `HUMAN_DECISION_REQUIRED` in this Bot
conversation, and acceptance-before-finalize stay as stated in the main Skill
and `skills/kaola-project-runner/references/grok-bot-host.md`.

## Update and rollback

A release rewrites `templates/grok-bot/accepted-revision.json`; `--write` then
changes exactly one line of the bridge, which is one more account write. Local:
the owner updates the Mac checkout on the Mac and the locator re-verifies. Cloud:
`git -C ROOT fetch origin <commit> && git -C ROOT checkout --detach <commit>`.
Rollback is the previous accepted revision. Removal: delete the Skill under
Settings → Plugins → Yours and remove the locator link
(`./scripts/install-local.sh --uninstall --bin-links` or `rm` the link). Do not
Reset Agent Computer; do not stop unrelated workers.

## Token cost (chars ÷ 4 … ÷ 3.5)

| Phase | Bridge (this candidate) | Eight bodies (`aba7d74`, void) |
|---|---|---|
| Install (once) | 1 write ≈ 0.6 k out + locator receipt ≈ 0.3 k in | 8 writes ≈ 52–59 k out + same in ≈ 105–120 k |
| Discovery (per turn) | ≈ 0.07 k description; worst case ≈ 0.6 k body | ≈ 0.5 k descriptions; worst case 52–59 k |
| Main activation | receipt ≈ 0.3 k + body 15.3 KB ≈ 3.8–4.4 k | 24 KB ≈ 6–7 k, references pre-flattened |
| One selected worker | 10.7 KB ≈ 2.7–3.1 k; references on demand | 26–27 KB ≈ 6.5–7.7 k; seven if injected ≈ 45–53 k |
| Update (release) | one revision line ≈ 0.6 k | ≈ 105–120 k |

## Out of scope

Unofficial Sand gateways, GrokBot RPCs, NCI, `platforms/grok-bot.yaml`, public
or Team Marketplace publication, ZIP or file-tree import claims, a runtime copy,
per-worker account Skills, a scheduler or update daemon, and Grok CLI as a host
(`--runtime grok`).
