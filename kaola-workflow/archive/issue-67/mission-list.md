# Issue #67 — ZCode ACP tool_call updates carry no paths

Run: issue-67 · branch `workflow/issue-67` · worktree `.kw/worktrees/issue-67`
Boundary: `scripts/kaola-zcode-acp.py` translator, targeted tests, necessary docs.
Do not bundle. Do not touch issue-70/71/72 worktrees, sessions, accepted, credentials, or main.
No extra implementer/reviewer dispatch. No nine-platform matrix. No release/global install/memory.
Outer ACCEPT before finalize/merge/close/push mainline.

## 1. Measure ZCode upstream tool payload vs one other ACP platform
- item: Capture the actual ZCode app-server tool event shape (not the translated ACP view) and one other ACP platform's `tool_call` update; bind real messages to code; never guess paths or leak credentials.
- status: done
- dispatched: self; isolated adapter-stdio probe (no tmux, no other sessions). Output lands in `kaola-workflow/issue-67/evidence/`.
- result: done. Live 0.16.5 `model.streaming` `tool_call` carries `input.file_path` (sentinel marker). `tool.updated` `scheduled` omits `input` (`inputOmitted`/`inputRef`). Claude Code ACP live (issue-65) already carries `rawInput.command`. Pre-fix ZCode ACP updates were five fields only. Evidence: `evidence/MEASURED.md`, `evidence/live/*.before.json`, `evidence/compare/`.

## 2. Forward or document the measured limit
- item: If upstream already carries file/command fields, add minimal bounded credential-scrubbed forwarding in the translator. If it does not, record that limit accurately and correct verification guidance via renderer (preserve #70 host-startup semantics on integration).
- status: done
- dispatched: self, inline in worktree `.kw/worktrees/issue-67`; output lands in `scripts/kaola-zcode-acp.py`, `templates/orchestrator/references/host-startup.md.tmpl` (renderer), `third_party/zcode-acp/UPSTREAM.md`.
- result: done. Translator forwards redacted `rawInput` and path-like `locations`; does not invent paths; does not follow `inputRef`. host-startup now says those fields appear only when upstream `input` named them. #70's heartbeat-binding sentences were not taken from its worktree; merge must keep both. Live after-fix ACP cards carry `rawInput.file_path` + `locations` for the sentinel marker.

## 3. Targeted contract tests and isolation evidence
- item: Tests that distinguish forwarding vs dropping vs inventing paths; isolated evidence under `kaola-workflow/issue-67/evidence/`. Freeze SHA, render-check, validate.sh, exact outcomes for outer ACCEPT.
- status: done
- dispatched: self; tests in `tests/contract/test-zcode-acp-contract.py` + fake scenarios `read_path`/`no_input`. Evidence under `kaola-workflow/issue-67/evidence/`.
- result: done. Frozen `45d5e750436bb952978b1c2fd07425f2f0ccfd31` on `workflow/issue-67`. `test-zcode-acp-contract.py` 30/30. `render-skills.py --check` PASS. Serial replay of every `validate.sh` python suite + grok-bot-verify PASS (`evidence/validate-serial-2026-09-18.log`). Parallel `validate.sh` flaked on unrelated suites (follow, then issue-50) when a lane aborted; those suites PASS isolated. No nine-platform matrix. Awaiting outer ACCEPT; no finalize/merge/close/push mainline.

## 4. Bound rawInput to path/command evidence and prove holder events stay safe
- item: Comment 5728867515: do not forward unbounded dicts or treat arbitrary command as a full credential scrub. Keep only the path/command fields that prove a read/execute, with a small total/depth bound; one sensitive-input and one oversized/deep-nested holder-event check; still invent no path when upstream has none.
- status: done
- dispatched: self, inline in worktree `.kw/worktrees/issue-67`; output lands in `scripts/kaola-zcode-acp.py`, fake scenarios `sensitive_extra`/`huge_nested`, `tests/contract/test-zcode-acp-contract.py` holder `events.jsonl` checks, renderer host-startup, `third_party/zcode-acp/UPSTREAM.md`.
- result: done. Rebased onto `origin/main` `464c4f9` (kept `kaola-workflow/archive/issue-71`). Frozen `1ca1c18af6d6e307eaf68c161d76c036db360309`. `extract_tool_evidence` copies only top-level path/`command` (command cap 160, total 1536 B, depth 1); extra/nested blobs dropped; no path invented. `test-zcode-acp-contract.py` 33/33 including holder events for sensitive + huge. `render-skills.py --check` PASS. No finalize.

## 5. Stop persisting plaintext command; keep path/line only
- item: Outer review of `1ca1c18`: do not persist any command prefix in `rawInput`. Persist only path/line the app-server actually named. Execute keeps kind/title/status without claiming a command transcript. Add an unregistered-token-in-command holder `events.jsonl` check. Keep existing path live evidence. No generic sanitizer. No finalize.
- status: done
- dispatched: self, inline in `.kw/worktrees/issue-67`; output lands in `scripts/kaola-zcode-acp.py`, `tests/contract/test-zcode-acp-contract.py`, renderer host-startup, `third_party/zcode-acp/UPSTREAM.md`.
- result: done. Frozen `986ee3eac6d89bad63e837d72386ea7c1b072546`. `extract_tool_evidence` copies only top-level path/line; `command` is dropped. Execute cards keep kind/title/status. `test-zcode-acp-contract.py` 34/34 including holder `events.jsonl` omitting `unreg-i67-token-9f3a7c2e`. `render-skills.py --check` PASS. Path live evidence retained (`evidence/live/zcode-acp-tool-calls.json` Read `file_path`). No finalize.

## 6. Rebase onto main that includes Issue #72 without reverting its examples
- item: Outer review of `986ee3e`: core path/line behavior is acceptable, but the branch is still on `464c4f9` and would revert #72's issue-scoped host-startup examples. Rebase onto current `origin/main`, keep #72 `codex-KT-i274-parser` / issue-dispatch text and #67 path/line facts, re-render, re-run the 34 contract tests plus `render --check` and `validate.sh`, inspect generated docs, freeze a new SHA. Do not touch #70/#74/#73 live work. No finalize/push.
- status: done
- dispatched: self, rebase `workflow/issue-67` onto `origin/main` `1f87666`; output lands on the rebased branch and `kaola-workflow/issue-67/evidence/`.
- result: done. Frozen `954eb221ebc20d193b1a6481c1379459b0bc136d` on `workflow/issue-67` (3 commits ahead of `1f87666`). host-startup keeps `codex-KT-i274-parser` + issue-dispatch paragraph and #67 path/line (never command). Generated `skills/kaola-project-runner/references/host-startup.md` matches. `test-zcode-acp-contract.py` 34/34. `test-issue-72-session-naming.py` 16/16. `render-skills.py --check` PASS. `./scripts/validate.sh` PASS (`evidence/validate-rebased-954eb22.log`). #70/#74/#73 untouched. No finalize/push.
