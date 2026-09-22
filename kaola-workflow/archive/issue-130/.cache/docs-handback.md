# #130 docs handback (worktree .kw/worktrees/issue-130, uncommitted)

## Files changed
- README.md, AGENTS.md, CHANGELOG.md
- docs/api.md, docs/architecture.md, docs/conventions.md, docs/zcode-host.md, docs/README.md
- docs/acp-watch/README.md, docs/acp-watch/list-view.md
- git mv docs/runner-v2-dual-transport-design.md -> docs/runner-v2-dual-transport-design-2026-09-11.md
  (the doc's own date is 2026-09-11; first added in 8c9a94c). The only change is the one
  "Superseded by #130" line at the top.

## Statement classes removed or rewritten
1. PTY as a selectable transport or fallback: `--transport acp|pty`, "explicit PTY fallback",
   "remains the explicit fallback", "both transports", "PTY and ACP share/have the same authority",
   and the "ACP or PTY" diagrams. Rewritten as ACP-only plus the `transport-pty-retired` refusal
   (README L134, api.md "Transport selection" with the full receipt JSON, architecture diagram,
   conventions Shell safety).
2. ZCode and dsh "diagnostic entry" / "PTY unsupported" wording. Removed, and the README table's
   "Default transport" column is dropped.
3. PTY-only capabilities: the Codex OS read-only statement is now a loss statement; Droid PTY
   `--skip-permissions-unsafe`/settings overlay is removed; native keys/menus/`answer
   --replace-editor` are replaced with the ACP facts (`key escape` = cancel, else
   `key-unsupported`; `answer-unsupported`). Codex `-c service_tier` and the Cursor `-fast` picker
   variants are removed from the fast-mechanism lists. Claude fast is now described as the bridge
   `fast` config option that becomes a per-turn `--settings fastMode` (vendor/claude-code-acp/src/claude-runner.ts:271).
4. Login "stays a PTY act" becomes "a human act in a native terminal, outside the Runner".
5. Relay/observation machinery: removed api.md's `relay` object paragraph, the PTY half of
   "Status compatibility" (pane/tui/process_match fields, none of which exist in kaola-acp.py),
   the relay-transfer/input-control/force-stop paragraphs (rewritten for the ACP send/key/answer
   receipts), the PTY observe bound (kaola-observation.py), and the stale overrides TMUX_BIN,
   PS_BIN, KAOLA_START_TIMEOUT, GROK_START_TIMEOUT (no longer read anywhere in scripts/). Deleted
   architecture's "Measured relay transfer" section and the session env block
   (KAOLA_PROJECT_RUNNER=1/_PLATFORM/_REPO/_MODEL_POLICY; nothing in scripts/ sets them now), and
   conventions' relay/DECRQM/tmux test rules.
6. Retired reasons `heartbeat-host-pty-unsupported` and `steer-unsupported-transport` are now
   marked retired and absorbed by `transport-pty-retired` (api.md, zcode-host.md).
7. Manifest key `default_transport` removed from api.md's field list; `DEFAULT_TRANSPORT` removed
   from the template variables; `acp_model_map` now says "catalog model IDs", not "PTY model IDs".
8. Model evidence (api.md): provenance appears only on start/preflight; `actual_*` are null and
   `model_verified` is `unknown` (verified in kaola-model-policy.py:305-308); `effective_selection`
   is on start.
9. AGENTS.md: the two requested lines (L13 Architecture, L25 Security boundary). I also fixed
   other transport facts that were stale: L11 "via tmux" -> "via ACP"; L12 Stack dropped tmux;
   L32/L33 validation dropped tmux; L80 "exact owned tmux CLI session" -> "ACP"; L86 "relay" ->
   "holder". Revert these if you want the managed region limited to the two requested lines.
10. README Requirements: tmux is no longer required (the ACP path runs no tmux command). The
    locator probe note is kept.
11. CHANGELOG: new Breaking entry at the top of Unreleased covering the refusal and receipt,
    removed keys/files/references, retired reasons, losses, model evidence and the move of the #8
    guarantees to ModelPolicyOnAcp, migration (stop with the old build or `tmux kill-session`,
    then reinstall every root because of #105/#121), and the #128 scope note. Also removed "on
    both transports" from the #125 Unreleased entry. Released sections are untouched.

## Intentional remaining PTY/tmux mentions
- `kaola-tmux.sh` / `runtime-tmux.sh` file names are identity anchors, and api.md's heading now
  says the file keeps its historical name.
- Locator `session.present` = tmux probe (README L361/L402, api.md L236, grok-bot-host.md): a real
  fact; the follow-on is deferred per design §1.2.
- `acp_login_requires_pty` / `ACP_LOGIN_REQUIRES_PTY`: the key name is kept (rename is a
  follow-on, §7).
- README L543 "Neither forcing PTY nor adding a gate is the answer" is pinned verbatim by
  test-issue-88-permission-defaults.py:264 (test_readme_routes_through_the_existing_flow_only).
  It does not offer PTY as an option, so I kept it. If you want it gone, the test needs changing
  (your side).
- Links to dated records, with link text changed to "historical PTY-era communication tests" and
  "Droid live verification (2026-09-17)"; the docs/README index descriptions of dated records are
  kept.
- The Grok Bot target text ("neither reaches ... tmux") is still an accurate boundary statement.
- docs/acp-watch/README.md L31 lists "ACP JSON into tmux/PTY" under the v1 rejected options.
- The api.md usage block still shows `--if-snapshot` / `--replace-editor`, transcribed from the
  kaola-tmux.sh usage. The text says the parser accepts them and does not forward them.

## Items for you (outside my edit scope)
- docs/poc-acp-transport-2026-09-11.md:3 (a dated record) still names
  `docs/runner-v2-dual-transport-design.md`. It is plain text, not a link, and I left it as a
  historical record.
- templates/orchestrator/references/workflow-worktree.md:14 still documents
  `KAOLA_PROJECT_RUNNER_REPO`, which no script sets any more.
- platforms/claude-code.yaml fast_summary still says "at launch"; on ACP the bridge applies it per
  turn.
- The Unreleased #128 entry still describes the lane C it added. I left it (design §4.5) and the
  #130 entry says so.

## Test results (env -u the five KAOLA_* vars)
- PASS: test-issue-74, test-issue-86, test-issue-118, test-issue-94, test-issue-50,
  test-acp-watch-contract, test-acp-follow-contract; test-issue-130 NoLiveOption.
- FAIL test-issue-88 (1): test_main_skill_keeps_the_protective_clauses wants 'never force PTY or
  add a gate' in the main Skill template. Template side, not docs. The README pins pass.
- FAIL test-issue-52 (3 failures, 1 error), all template/script/test side:
  test_guidance_forbids_a_worktree_transport_gate reads the deleted
  templates/references/transport.md.tmpl; the template pins 'Agent decisions on both PTY and ACP,
  not transport gates' and 'PTY and ACP share that authority'; the kaola-tmux.sh pin
  '--repo must name the Git root' and the tmux_git_root_ok path.
  test_docs_and_agents_state_the_same_default passes, and a manual authorizes_gate() run over
  README/architecture/conventions/api/AGENTS returns None for all of them.
