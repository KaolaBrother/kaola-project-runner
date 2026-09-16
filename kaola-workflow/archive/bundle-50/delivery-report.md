# Issue #50 delivery report (bundle-50) — acceptance candidate after the #49 ordering gate

Branch `workflow/bundle-50`, worktree `.kw/worktrees/bundle-50`, now based on `main` =
`origin/main` = `4a705f3` (Issue #49 sunk: R3 `bc8592d`, P3 `db4b0d5`, archive `4a705f3`; that
history is untouched and is an ancestor of the candidate).
Candidate: `8095611` — five content commits, the first four rebased from the pre-reconcile tip
`fa25281` (saved as `refs/kaola/bundle-50-pre-reconcile`): `e5dd527` Mission 1, `4a1ea1f`
Mission 2, `8a6ddac` Mission 3, `46c7492` Mission 4 review-1 fixes, `8095611` Mission 4 review-2
fixes. Tree clean; `git diff --check main HEAD` clean; `render-skills.py --check` PASS at the tip
and at each rebased commit; `./scripts/validate.sh` exit 0 on `8095611` (bridge harness 10/10 =
203 checks, Runner harness 6/6 = 107 checks; the suite now also runs `git diff --check`).
`git diff --stat main HEAD`: 74 files, +43397/−111 (the vendored bundle and lock dominate).

Reconcile facts: real conflicts were (1) `templates/grok-bot/accepted-revision.json` and the three
`hosts/grok-bot/` products — main carries P3's pinned stage; a content commit after P3 must return
to the content stage (the pin gate rejects any tracked delta beyond the four pin files), so the
file is `{"stage": "content"}` and the host products re-rendered to the content-stage bytes;
(2) `CHANGELOG.md` — both #49 R3 and #50 added an Unreleased entry; both kept, #50's first.
`scripts/kaola-acp.py` and `docs/api.md` merged automatically (R3's bounding hunks and #50's
token/env/facts hunks are disjoint); the generated `kaola-acp.py` copies were re-rendered at each
step. The six non-Claude workers differ from main only in `scripts/kaola-acp.py`.

## What the candidate delivers against the issue's acceptance

| Acceptance item (issue #50) | Where | Evidence |
|---|---|---|
| Vendored `vendor/claude-code-acp/` at `6c20f280…`, `LICENSE` verbatim, `UPSTREAM.md` with URL, commit, MIT, modification list | `e6e937b`, `c1a9b91` | harness `test_provenance` (hashed 43-file upstream inventory) |
| Lock-consistent, offline-reproducible build or proven committed `dist` | `kaola-dist.py --check` | inputs re-hashed, rebuild byte-identical (12 inputs) |
| Renderer ships the bridge only in the Claude Code Skill; `--check` inventories the bytes | `b251ca5` | `render-skills.py --check` PASS; Runner harness `test_manifest_and_generated_skill` (other seven packages carry no `vendor/`) |
| Bridge: exact binary, never PATH | fork `src/config.ts`, `src/claude-runner.ts` | bridge harness `test_missing_binary_fails_closed`; Runner harness `test_fail_closed_without_exact_binary_or_bridge` |
| model/effort config options, `--permission-mode` mapping, Fast pin, every subprocess | fork `src/agent.ts`, `src/claude-runner.ts` | bridge harness `test_turns_flags_env_cwd_logs`; Runner harness start receipt + fake argv |
| `session/new` cwd = repo, `listSessions`/`--continue`/`--resume`, process-group cancel | fork | both harnesses (`--continue`/`--resume` land in one native session; cancel kills claude + grandchild) |
| `sanitizeEnv` strips API creds, inherits the rest; logs mask; no Settings access | fork | harness canary/credential checks; live UAT Settings metadata identical |
| Temp `mcp.json` removed on stop, zero residue | fork | harness `test_stop_during_turn_cleans_everything`; live: 0 temp dirs, `residual_pids=[]` |
| Manifest facts (`acp_command` without `npx`/registry name, pin, versions, config ids, allowlist, login PTY, quirks) | `platforms/claude-code.yaml` | `test-runner-v2.py`, Runner harness |
| `default_transport` flips only after live UAT | `c1a9b91` | `uat-live-2026-09-16.md` |
| Docs: README, api, architecture, design §12.5 superseded, CHANGELOG | `b251ca5`, `c1a9b91` | text present; no registry references (harness guard) |

## Live UAT (release gate) — summary

See `uat-live-2026-09-16.md`. All six gates recorded; gate 3's permit half could not be
exercised because the CLI produced no permission request on this machine; recorded as a fact.
One live finding (cancel on a `--resume` turn re-run as a fresh conversation, CLI exit 143)
was repaired in the fork, reproduced offline, and re-verified live.

## Deviations and facts to carry into closure

1. The six other worker Skills changed in exactly one file each (`scripts/kaola-acp.py`, the
   shared ACP runtime copy); behavior for them is unchanged (no token, no bridge env entry).
2. The Grok Bot host at #49 R2/P2 embeds no worker; its three products are byte-identical.
3. Two `claude-acp-mcp-*` directories in the user's TMPDIR predate the fork's cleanup and were
   left untouched; UAT transcripts under `~/.claude/projects/-private-tmp-kaola-uat50-repo/` and
   one bridge store entry in `~/.claude-code-acp/sessions.json` are the user's own data and were
   left in place.
4. `docs/acp-live-verification-2026-09-11.md` is a historical record of the superseded wrapper
   probe and was not rewritten.

## Independent review

Round 1 (`review-50-r1`, clean context, on `df8b85e..c1a9b91`): PASS-with-notes, ten findings.
Orchestrator verdicts and dispositions in `review-report.md`: F1 (acceptance `git diff --check`
on the rendered bundle), F2, F3, F4, F7 fixed in `fa25281`; F5, F6, F8, F9, F10 recorded as
facts. The reviewer's PASS covers the unchanged bytes; the re-run suite covers the changed ones.

## Ordering gate (Mission 4) — met

#49 CLOSED and sunk (main `4a705f3`); `workflow/bundle-50` rebased onto it without rewriting
#49's commits; full validation re-run on the composed tip; live subscription consistency check
re-run on the composed bundle (see `uat-live-2026-09-16.md`, post-reconcile section: preflight
on the manifest default `acp`, bridge sha equal to the tip's vendored dist, Fable High sentinel,
native model `claude-fable-5-1`, cancel on a resume turn, continue into the same conversation,
zero residue, Settings metadata identical). Review round 2 on the rebased candidate (`46c7492`):
PASS-with-notes, four nits — N2 (discriminating escape shape) and N4 (changelog wording) fixed in
`8095611`; N1 and N3 recorded in `review-report.md`. The final tip differs from the reviewed
`46c7492` only in one harness string and the changelog entry; validate.sh re-run on the tip.
Not done by instruction: finalize, merge, close, release. bundle-51 untouched.
