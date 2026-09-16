# Grok Bot: one bridge Skill, one device-local locator per execution target

These steps are for the owner and for Grok Bot itself. They are not a Skill. The account
receives **exactly one** small private Skill, `kaola-project-runner` (Project Runner bridge,
`hosts/grok-bot/kaola-project-runner.md`, 2039 bytes). Every policy, worker, reference, and
script stays in the repository and is loaded on demand from a verified checkout on the bound
execution target. Research on Grok Bot 0.51.0 found no supported automated way to create an
account Skill (`NO_SUPPORTED_PATH`), so the one native skill write below is the only account
operation; there is no Marketplace, credential, ZIP import, unofficial Sand or RPC path, and no
state hack.

## 1. One write on the account

Save `hosts/grok-bot/kaola-project-runner.md` as the account-private Skill `kaola-project-runner`: `name` and
`description` from its frontmatter (`hosts/grok-bot/bridge.json` holds the already-resolved
values; never save YAML quotes), `body` = everything after the closing `---`. If a Skill with
the same name exists, update it in place; never create a second one and never touch any other
Skill. Verify: Settings > Plugins > Yours lists exactly one Skill `kaola-project-runner`, enabled, and
`/` offers it. A release changes only the accepted-revision line (`ba3d14f0c4f35bfc96004435d1ef053713d323ec`,
release v0.2.3); repeat this one write then.

## 2. First configuration on Local Computer (Mac): read-only, never from the cloud

The Mac already holds the `KaolaBrother/kaola-project-runner` checkout and its local Skill installation. The cloud
Agent Computer never clones, installs, updates, or manages anything on the Mac. In the Bot with
**Execution on Local Computer**, inside the local workspace the owner names:

```bash
ROOT="$(git rev-parse --show-toplevel)"                       # the existing checkout, not a clone
python3 "$ROOT/scripts/kaola-locate.py" register              # links kaola-project-runner-locate into the installer's bin directory (--bin-dir DIR for another directory on PATH)
kaola-project-runner-locate --target local --expect-revision ba3d14f0c4f35bfc96004435d1ef053713d323ec   # result must be "ok"
```

The locator receipt carries only: target kind, host kernel and hashed fingerprint, ROOT,
normalised origin (`github.com/KaolaBrother/kaola-project-runner`), HEAD, clean state. The Mac path lives only in that
device-local link; it never enters the account Skill. Moving the checkout means running
`register` again; the bridge is unchanged.

## 3. Read-only preflight UAT against an existing local project and session

```bash
kaola-project-runner-locate --target local --expect-revision ba3d14f0c4f35bfc96004435d1ef053713d323ec \
  --project /path/of/the/existing/local/project --worker claude-code --session <existing-session-name>
"$ROOT/skills/claude-code-kaola-project-runner/scripts/runtime-tmux.sh" preflight --repo /path/of/the/existing/local/project --session <existing-session-name>
```

Expected: the attestation is `ok` (project on this host, script under the same ROOT, session
present), the Claude Code preflight returns its evidence, and nothing was started,
sent, stopped, cloned, fetched, checked out, or installed. Record that the Bot read only
`ROOT/skills/kaola-project-runner/SKILL.md` and `ROOT/skills/claude-code-kaola-project-runner/SKILL.md`, read no
script source, and that the cloud Agent Computer executed nothing and accessed no Mac file.

## 4. Cloud Agent Computer (optional, independent)

For a project that lives on the cloud computer, that computer chooses its own persistent
directory, clones or updates its own checkout with its own existing Git or GitHub CLI
authentication (`git clone https://github.com/KaolaBrother/kaola-project-runner.git` or
`gh repo clone KaolaBrother/kaola-project-runner`, then `git checkout --detach ba3d14f0c4f35bfc96004435d1ef053713d323ec`), registers its
own locator with `python3 ROOT/scripts/kaola-locate.py register`, and passes
`--target cloud`. That checkout never operates on Mac paths, CLIs, tmux, or sessions.

## 5. Update and rollback

Local: the owner updates the Mac checkout on the Mac; the locator re-verifies. Cloud:
`git -C ROOT fetch origin <commit> && git -C ROOT checkout --detach <commit>`. Rollback is the
previous accepted revision. Removal: delete the Skill under Settings > Plugins > Yours and
remove the locator link (`./scripts/install-local.sh --uninstall --bin-links` or `rm` the link).

## Boundaries

- Never publish this Skill to a public or Team Marketplace; never use unofficial Sand gateways,
  hidden Bot RPCs, or account credentials; never enter, print, or pass a token.
- Never edit generated files; `python3 scripts/render-skills.py --write` regenerates them.
- No runtime copy, no per-worker account Skills, no scheduler, no daemon.
