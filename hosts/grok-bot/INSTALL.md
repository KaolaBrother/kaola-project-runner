# Grok Bot: one bridge Skill, one device-local locator per execution target

These steps are for the owner and for Grok Bot itself. They are not a Skill. The account
receives **exactly one** small private Skill, `kaola-project-runner` (Project Runner bridge,
`hosts/grok-bot/kaola-project-runner.md`, 2317 bytes, stage `content`). Every policy,
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
at P proves R exists, is an ancestor, is not a self-pin, and holds the locator and every entry
path. Save the bridge **from P**; check the execution target out **at R**, clean and detached.
Pre-release UAT is exactly that: R is the target, P names it, nothing is released or tagged.

## 1. One write on the account (from P only)

Save `hosts/grok-bot/kaola-project-runner.md` as the account-private Skill `kaola-project-runner`: `name` and
`description` from its frontmatter (`hosts/grok-bot/bridge.json` holds the already-resolved
values and `"saveable": true`; never save YAML quotes), `body` = everything after the closing
`---`. If a Skill with the same name exists, update it in place; never create a second one and
never touch any other Skill. Verify: Settings > Plugins > Yours lists exactly one Skill
`kaola-project-runner`, enabled, and `/` offers it. A later pin changes only the accepted-revision
line; repeat this one write then.

## 2. First configuration on Local Computer (Mac): read-only, never from the cloud

The Mac already holds a `KaolaBrother/kaola-project-runner` checkout; its `main` working tree may carry untracked
Workflow records and other local files, which the locator correctly reports as `dirty`. Do not
weaken that check and do not assume any fixed path: the owner selects a clean checkout or
worktree of the existing repository, detached at R, for example
`git worktree add --detach <owner-chosen path> <accepted commit>` run on the Mac. The cloud
Agent Computer never clones, installs, updates, or manages anything on the Mac. In the Bot with
**Execution on Local Computer**, inside that workspace:

```bash
ROOT="$(git rev-parse --show-toplevel)"                       # the owner-selected clean checkout at R
python3 "$ROOT/scripts/kaola-locate.py" register --expect-revision <accepted commit>   # validates origin/revision/clean first; links kaola-project-runner-locate into the installer's bin directory (--bin-dir DIR for another directory on PATH)
kaola-project-runner-locate --target local --expect-revision <accepted commit>   # result must be "ok"
```

Record the `host.fingerprint` from the `register` receipt with the target: `--target` is the
Agent's declaration, and comparing that fingerprint on every later receipt is what ties a
receipt to the bound target. The receipt carries bounded local evidence only: target as
declared, host kernel and hashed fingerprint, ROOT and project paths on that host (real local
paths, which may include the user's home), normalised origin (`github.com/KaolaBrother/kaola-project-runner`), HEAD,
clean state. None of it enters the account Skill; moving the checkout means running `register`
again, and a refused registration leaves an existing locator unchanged.

## 3. Read-only preflight UAT against an existing local project and session

```bash
kaola-project-runner-locate --target local --expect-revision <accepted commit> \
  --project /path/of/the/existing/local/project --worker <platform id> --session <existing-session-name>
"$ROOT/skills/<platform id>-kaola-project-runner/scripts/runtime-tmux.sh" preflight --repo /path/of/the/existing/local/project --session <existing-session-name>
```

Expected: the attestation is `ok` (project on this host, script under the same ROOT, a tmux
session of that exact name present; ownership is proven by the worker preflight, not by the
locator), the worker preflight returns its evidence, and nothing was started, sent, stopped,
cloned, fetched, checked out, or installed. Record that the Bot read only
`ROOT/skills/kaola-project-runner/SKILL.md` and `ROOT/skills/<platform id>-kaola-project-runner/SKILL.md`,
read no script source, and that the cloud Agent Computer executed nothing and accessed no Mac
file.

## 4. Cloud Agent Computer (optional, independent)

For a project that lives on the cloud computer, that computer chooses its own persistent
directory, clones or updates its own checkout with its own existing Git or GitHub CLI
authentication (`git clone https://github.com/KaolaBrother/kaola-project-runner.git` or
`gh repo clone KaolaBrother/kaola-project-runner`, then `git checkout --detach <accepted commit>`), registers its
own locator with `python3 ROOT/scripts/kaola-locate.py register`, records its own fingerprint,
and passes `--target cloud`. That checkout never operates on Mac paths, CLIs, tmux, or sessions.

## 5. Update and rollback

Local: the owner moves the Mac checkout or worktree to the new R on the Mac; the locator
re-verifies. Cloud: `git -C ROOT fetch origin <commit> && git -C ROOT checkout --detach <commit>`.
Rollback is the previous accepted revision. Removal: delete the Skill under Settings > Plugins >
Yours and remove the locator link (`./scripts/install-local.sh --uninstall --bin-links` or `rm`
the link).

## Boundaries

- Never publish this Skill to a public or Team Marketplace; never use unofficial Sand gateways,
  hidden Bot RPCs, or account credentials; never enter, print, or pass a token.
- Never edit generated files; `python3 scripts/render-skills.py --write` regenerates them.
- No runtime copy, no per-worker account Skills, no scheduler, no daemon.
