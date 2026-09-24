# Grok Bot: one bridge Skill, one device-local locator per execution target

These steps are for the owner and for Grok Bot itself. They are not a Skill. The account
receives **exactly one** small private Skill, `kaola-delegator` (Kaola-Delegator bridge,
`hosts/grok-bot/kaola-delegator.md`, 2478 bytes, stage `pinned`). Every policy,
worker, reference, and script stays in the repository and is loaded on demand from a verified
checkout on the bound execution target. Research on Grok Bot 0.51.0 found no supported automated
way to create an account Skill (`NO_SUPPORTED_PATH`), so the one native skill write below is the
only account operation; there is no Marketplace, credential, ZIP import, unofficial Sand or RPC
path, and no state hack.

## 0. Two commits: content R, then pin P

A commit cannot contain its own hash, so a delivery is two commits. The **content commit R**
holds the runtime, docs, and tests and is rendered at stage `content`: its bridge carries an
explicit "none yet" line and must not be saved. The **pin commit P** follows R and changes only
`templates/grok-bot/accepted-revision.json` (stage `pinned`, commit R, an honest label or a
release tag) plus the three regenerated files here. `render-skills.py --check --require-pinned`
at P proves R exists, is an ancestor, is not a self-pin, holds the locator and every entry
path, and that P differs from R by exactly those four files with a one-line bridge diff. Save
the bridge **from P**; check the execution target out **at R**, clean and detached. Never
rebase, squash, or amend an accepted R/P pair: if `main` moves first, create a fresh R and P
and repeat review and UAT. A release is a tag at R followed by a new P naming that tag;
rollback is a new P naming an older R. Pre-release UAT is exactly that: R is the target, P
names it, nothing is released or tagged.

## 1. One write on the account (from P only)

Save `hosts/grok-bot/kaola-delegator.md` as the account-private Skill `kaola-delegator`: `name` and
`description` from its frontmatter (`hosts/grok-bot/bridge.json` holds the already-resolved
values and `"saveable": true`; never save YAML quotes), `body` = everything after the closing
`---`. If a Skill with the same name exists, update it in place; never create a second one and
never touch any other Skill. This repository does not authorize deleting a personal account
Skill. An older `kaola-project-runner` account Skill is left in place: do not rename, restart,
or cancel in-flight work to adopt this one. A later pin changes only the accepted-revision
line; repeat this one write then.

## 2. First configuration on Local Computer (Mac): read-only, never from the cloud

The Mac already holds a `KaolaBrother/kaola-project-runner` checkout; its `main` working tree may carry untracked
Workflow records and other local files, which the locator correctly reports as `dirty`. Do not
weaken that check and do not assume any fixed path: the owner selects a clean checkout or
worktree of the existing repository, detached at R (for example
`git worktree add --detach <owner-chosen path> 2504be21b7b30feff063b8f51f15a2254c1193d3` run on the Mac), and an
owner-selected persistent directory on PATH for the locator link (`BIN` below), so the
installer-managed `--bin-links` link is left alone. The cloud Agent Computer never clones,
installs, updates, or manages anything on the Mac. In the Bot with **Execution on Local
Computer**, inside that workspace:

```bash
ROOT="$(git rev-parse --show-toplevel)"      # the owner-selected clean checkout at R
python3 "$ROOT/scripts/kaola-locate.py" register --target local --bin-dir "$BIN" --expect-revision 2504be21b7b30feff063b8f51f15a2254c1193d3
kaola-project-runner-locate --target local --expect-revision 2504be21b7b30feff063b8f51f15a2254c1193d3   # result must be "ok"
```

`register` validates origin, revision, and clean state first, then links `$BIN/kaola-project-runner-locate`
and atomically writes the registration receipt `$BIN/.kaola-project-runner-locate.json` beside it: schema,
resolved ROOT, declared target, host kernel and hashed fingerprint, accepted revision; no
hostname, username field, or credential. `--target` is the Agent's declaration, and every later
locator call compares the running `host.fingerprint` and that declaration with the receipt and
refuses on mismatch (`host-fingerprint-mismatch`, `target-mismatch`, `registration-stale`), so a
fresh conversation needs no memory of the fingerprint. A refused registration leaves an
existing locator unchanged, link and receipt alike; moving the checkout or changing R means
running `register` again. Receipts carry bounded local evidence only: ROOT and project paths on
that host (real local paths, which may include the user's home), normalised origin
(`github.com/KaolaBrother/kaola-project-runner`), HEAD, clean state. None of it enters the account Skill; link and
receipt stay device-local.

## 3. Read-only preflight UAT against the bound checkout

```bash
kaola-project-runner-locate --target local --expect-revision 2504be21b7b30feff063b8f51f15a2254c1193d3
test -f "$ROOT/skills/kaola-delegator/SKILL.md"
```

Expected: the attestation is `ok`, `ROOT/skills/kaola-delegator/SKILL.md` is present, and
nothing was started, sent, stopped, cloned, fetched, checked out, or installed. Do not load
Project Runner or `ROOT/skills/<platform id>-kaola-project-runner` from this bridge, and do
not run a worker preflight. Record that the Bot read only `ROOT/skills/kaola-delegator/SKILL.md`,
read no script source, and that the cloud Agent Computer executed nothing and accessed no Mac
file. This establishes placement only, not live use: a real-use smoke on one session is
separately authorized and is not part of installation. This repository does not claim live
Grok Bot adoption.
After UAT, remove `$BIN/kaola-project-runner-locate` and `$BIN/.kaola-project-runner-locate.json` or keep them
registered; the installer-managed link is restored with `./scripts/install-local.sh
--bin-links` from the normal checkout (it refuses to overwrite a link it does not own, so
remove a UAT link placed in its directory first) and then registered from that checkout.

## 4. Cloud Agent Computer (optional, independent)

For a project that lives on the cloud computer, that computer chooses its own persistent
directory, clones or updates its own checkout with its own existing Git or GitHub CLI
authentication (`git clone https://github.com/KaolaBrother/kaola-project-runner.git` or
`gh repo clone KaolaBrother/kaola-project-runner`, then `git checkout --detach 2504be21b7b30feff063b8f51f15a2254c1193d3`), registers its
own locator with `python3 ROOT/scripts/kaola-locate.py register --target cloud --bin-dir <its
directory on PATH> --expect-revision 2504be21b7b30feff063b8f51f15a2254c1193d3`, and passes `--target cloud` on
every call. That checkout never operates on Mac paths, CLIs, tmux, or sessions.

## 5. Update and rollback

A new pin (content R′, then pin P′) is one more account write and, on each target, a move to R′
followed by `register` again (the receipt records the accepted revision; a stale registration
is refused). Cloud: `git -C ROOT fetch origin <commit> && git -C ROOT checkout --detach
<commit>`, then `register`. A revision older than the registered one is refused
(`expect-revision-superseded`, `accepted-revision-superseded`). Rollback is a new pin commit
naming an older R: on each target remove the receipt, move to R, then `register`. Removal:
delete the account Skill the same native way it was saved, and the link and its receipt
(`rm "$BIN/kaola-project-runner-locate" "$BIN/.kaola-project-runner-locate.json"`, or `./scripts/install-local.sh --uninstall --bin-links` for the installer-managed link).

## Boundaries

- Never publish this Skill to a public or Team Marketplace; never use unofficial Sand gateways,
  hidden Bot RPCs, or account credentials; never enter, print, or pass a token.
- Never edit generated files; `python3 scripts/render-skills.py --write` regenerates them.
- No runtime copy, no per-worker account Skills, no scheduler, no daemon.
