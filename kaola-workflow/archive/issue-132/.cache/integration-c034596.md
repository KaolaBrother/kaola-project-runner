# #132 integration trial over main (Host-ordered, before finalize)

- Temp detached worktree: /tmp/kpr-132-integ (not a branch; main untouched at 1ad482c)
- Merge commit c034596 = main 1ad482c + workflow/issue-132 efc9c0c (history of efc9c0c unchanged)
- Target tree: ac811be701a4625ef8a469dfad028d3ff69bfd3a
- Gates on c034596 (foreground): render-skills.py --check rc=0; validate.sh rc=0, 495 s, sweep residual_pids [] (validate-integ-c034596.log); git diff --check 1ad482c c034596 rc=0; worktree clean after validate

## Conflicts
| File | #130 (main) | #132 (efc9c0c) | Resolution |
|---|---|---|---|
| CHANGELOG.md | "Breaking: PTY retired" entry under Unreleased | "One live Host per repo" entry under Unreleased | both kept verbatim, #132 first (newer), then #130, then #133 |
| docs/api.md (Human watch paragraph) | rewrote only the `kaola-tmux.sh view` sentence (view-unsupported, exit 1, Runner wording) | inserted `--include-dead` + row-field sentence after "object of live holders" | #130's paragraph verbatim + the #132 insertion at its anchor; nothing of #130 dropped |
| skills/*/scripts/main-skill-build.json (10) | generated | generated | re-rendered with render-skills.py --write |

Auto-merged overlaps checked by hand: templates/orchestrator/SKILL.md.tmpl (#130 PTY wording; #132 Host paragraph + Hosts trim, disjoint hunks); zcode-host-dispatch.md.tmpl (#130 transport-pty-retired sentence; #132 identity-verified count, adjacent paragraphs); scripts/kaola-acp.py (#130 removed the tmux transport-mismatch probe just above the #132 identity-gated session-exists; merged code parses and passes). #130 did not touch templates/kaola-delegator/*, so handoff.md is the efc9c0c text byte-for-byte (8192/8192) — no compression needed.

## Budgets on c034596
| File | bytes | limit | headroom |
|---|---|---|---|
| skills/kaola-delegator/SKILL.md | 4093 | 4096 | 3 |
| skills/kaola-delegator/references/handoff.md | 8192 | 8192 | 0 |
| skills/kaola-project-runner/SKILL.md | 17317 | 17408 | 91 |
| references/heartbeat-skeleton.md | 8183 | 8192 | 9 |
| references/host-startup.md | 8177 | 8192 | 15 |
| references/zcode-host-dispatch.md | 7505 | 8192 | 687 |
| hosts/grok-bot/kaola-delegator.md | 2536 | 2560 | 24 |
| largest worker SKILL.md (devin) | 11517 | 12288 | 771 |

Stopped here for Host approval of the target tree; no main merge, finalize, close, or archive.
