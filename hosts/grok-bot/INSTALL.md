# Grok Bot: install or update the 8 Project Runner Private Skills from this repository

These instructions are for **Grok Bot itself**; paste them into the Bot conversation. They are
not a ninth Skill. Grok Bot reads this checkout on **Local Computer** and saves each of the
8 generated documents as one account-private Skill through its own single-Markdown
skill write (`name`, `description`, `body`). Nothing here uses a shell or API bypass, an
unofficial Sand API, an account credential, a ZIP import, or a Marketplace. The owner does not
copy any body by hand.

## 1. Verify the checkout and the candidate

Run on Local Computer, inside the checkout the owner named:

```bash
git rev-parse HEAD                                                 # must equal the candidate commit the owner named
python3 scripts/render-skills.py --check                           # render-skills: PASS (...)
python3 scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo .   # kaola-grok-bot-verify: PASS ... (generated state)
```

If any line differs, stop and report it; do not save Skills from a checkout that fails these
checks or from a commit the owner did not name. `hosts/grok-bot/private-skills.json` is the
generated fingerprint list (name, description, `file_sha256`, `body_sha256` per document); when
in doubt compare a file's `shasum -a 256` with its `file_sha256` before saving it.

## 2. Save the 8 Skills: one write per file, in this order

For each row: read the file on Local Computer; take `name` and `description` from its
frontmatter (the block between the first two `---` lines); take the **body** as everything after
the closing `---`; then save it with the Bot's private-skill write (observed in owner UAT as the
`update_state` Skill write) using **exactly** that name, description, and body. That is
8 calls, one per source file. If a private Skill with the same name already exists,
update it in place. Never create a second Skill with the same name, never rename one, and never
merge two files into one Skill.

| # | Stable Skill name | Source file (read on Local Computer) | Role |
|---|---|---|---|
| 1 | `kaola-project-runner` | `hosts/grok-bot/private-skills/kaola-project-runner.md` | main Skill (Project Runner) |
| 2 | `claude-code-kaola-project-runner` | `hosts/grok-bot/private-skills/claude-code-kaola-project-runner.md` | Claude Code worker (transport-only) |
| 3 | `codex-kaola-project-runner` | `hosts/grok-bot/private-skills/codex-kaola-project-runner.md` | Codex CLI worker (transport-only) |
| 4 | `cursor-cli-kaola-project-runner` | `hosts/grok-bot/private-skills/cursor-cli-kaola-project-runner.md` | Cursor CLI worker (transport-only) |
| 5 | `devin-kaola-project-runner` | `hosts/grok-bot/private-skills/devin-kaola-project-runner.md` | Devin CLI worker (transport-only) |
| 6 | `grok-kaola-project-runner` | `hosts/grok-bot/private-skills/grok-kaola-project-runner.md` | Grok CLI worker (transport-only) |
| 7 | `kimi-cli-kaola-project-runner` | `hosts/grok-bot/private-skills/kimi-cli-kaola-project-runner.md` | Kimi CLI worker (transport-only) |
| 8 | `opencode-kaola-project-runner` | `hosts/grok-bot/private-skills/opencode-kaola-project-runner.md` | OpenCode worker (transport-only) |

Re-running these steps is idempotent: the same 8 names are updated to the current
files, nothing else is created, and no other Skill on the account is touched. All 7
worker rows are needed; the main Skill selects a worker by the stable name in its own routing
table.

## 3. Keep a checklist; retry only the failed rows

Report one table `# | name | source file | outcome` where outcome is `created`, `updated`,
`FAILED (reason)`, or `not attempted`. A failure on one file does not undo the others: report
the cause, then repeat step 2 for the failed rows only. Partial completion is reported as
partial; do not report the install as complete until every row shows `created` or `updated`.

## 4. Verify the 8 identities, then dispatch through Project Runner

1. Settings > Plugins > Yours lists exactly these 8 private Skills, enabled:
   `kaola-project-runner`, `claude-code-kaola-project-runner`, `codex-kaola-project-runner`, `cursor-cli-kaola-project-runner`, `devin-kaola-project-runner`, `grok-kaola-project-runner`, `kimi-cli-kaola-project-runner`, `opencode-kaola-project-runner`. Record any name that is missing, duplicated, or disabled.
2. `/` in this Bot offers all 8.
3. Ask Project Runner (`kaola-project-runner`) to supervise one explicitly authorized worker, for
   example a Claude Code session. It must select that worker by the stable Skill name
   (`claude-code-kaola-project-runner`), load that Skill, and run the Local Computer script
   `${KAOLA_GROK_BOT_HOME:-$HOME/.kaola/grok-bot}/skills/kaola-project-runner/workers/claude-code/scripts/runtime-tmux.sh`
   (the runtime copy installed on this Mac by `./scripts/install-local.sh --runtime grok-bot`),
   never a script on the cloud Agent Computer.
4. Record the exact outcome or gap of every step for the owner.

## Boundaries

- Never publish or submit any of these Skills to a public Marketplace, and do not use a Team
  Marketplace for them.
- Never use unofficial Sand gateways, hidden Bot RPCs, or account credentials; only the Bot's own
  skill write and Local Computer file reads.
- Do not edit the generated files; the repository regenerates them with
  `python3 scripts/render-skills.py --write`.
- Rollback: delete or disable the 8 Skills under Settings > Plugins > Yours;
  `./scripts/install-local.sh --runtime grok-bot --uninstall` removes only the local runtime copy.
