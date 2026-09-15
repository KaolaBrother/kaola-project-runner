# Grok Bot host

Grok Bot is a first-class Project Runner **host**, at the same rank as Codex,
Claude Code, Cursor, and Devin. It is not an eighth CLI worker.

| Id | Meaning | Installer flag |
|---|---|---|
| `grok-bot` | Official Grok Bot desktop host | `--runtime grok-bot` |
| `grok` | Grok CLI worker (ACP `grok agent stdio`) | `--platform grok` |

`--platform grok-bot` is invalid. `--runtime grok` is not a host alias.

## Generated artifact

`./scripts/render-skills.py --write` emits `hosts/grok-bot/`: a Cursor-plugin
bundle (`.cursor-plugin/plugin.json` plus `skills/` containing
`kaola-project-runner` and the seven worker Skills). Bytes match `skills/`.
`--check` and `scripts/kaola-grok-bot-verify.py` prove that inventory.

```bash
./scripts/render-skills.py --write
./scripts/install-local.sh --runtime grok-bot
# payload: $HOME/.cursor/plugins/local/kaola-project-runner
```

`--platform` still filters workers inside the bundle. `--no-orchestrator`
omits the main Skill. Default copy; `--method link` is allowed only for the
full generated bundle.

This destination follows Cursor local-plugin layout. **Grok Bot 0.51.x UI
enablement (`/` menu, Settings → Plugins, Routine on this Bot) is release-gate
UAT.** An installer copy is not live adoption.

## Control plane on Grok Bot

The generated Skill `kaola-project-runner` owns policy. On this host:

- One Routine on **this Bot conversation** is the only heartbeat. Do not stack
  it with a Codex heartbeat or sleep.
- Takeover cancels only the previous host heartbeat. Do not stop in-flight
  exact owned worker sessions.
- `HUMAN_DECISION_REQUIRED` stays in this Bot (Needs attention / Notifications).
  Agent Computer takeover is not CLI stop.
- Exact-session stop is still the matching platform Runner `stop`.
- Mission-frontier done is review, not automatic finalize.

See `skills/kaola-project-runner/references/grok-bot-host.md`.

## Live UAT (not claimed by this change)

1. Enable the plugin in Grok Bot so `/` sees Project Runner and the seven workers, or record the exact gap.
2. A Routine fires in the same Bot conversation.
3. Local Computer can run exact `runtime-tmux.sh` / `kaola-acp` against Mac sessions.
4. Takeover from a Codex heartbeat leaves busy workers running.
5. Worker `HUMAN_DECISION_REQUIRED` surfaces as Needs attention; takeover UI is not used as stop.
6. Frontier done does not self-finalize.

## Rollback

```bash
./scripts/install-local.sh --runtime grok-bot --uninstall
```

Pause or delete the Routine; restore the previous host wake if needed. Do not
Reset Agent Computer. Do not stop unrelated workers.

## Out of scope

Unofficial Sand gateways, GrokBot RPCs, NCI, `platforms/grok-bot.yaml`, and
Grok CLI as a host (`--runtime grok`).
