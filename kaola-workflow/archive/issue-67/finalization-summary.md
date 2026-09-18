# Finalization Summary — Issue #67

Issue: [#67 ZCode ACP tool_call updates carry no paths, so an outer Agent cannot verify which files a session actually read](https://github.com/KaolaBrother/kaola-project-runner/issues/67)
Project folder: `kaola-workflow/issue-67` · Branch: `workflow/issue-67` · Sink: merge
Candidate: **`23d231eff500e0d4ab713740d7c20db9c6971815`**, linear on `main` `3dd7e5eb5c4efe679ffbf4717307bf74866e5463`
Accepted content: outer ACCEPT of `954eb221ebc20d193b1a6481c1379459b0bc136d` (same path/line-only translator on `1f87666`); rebased onto `3dd7e5e` without content conflict.
Worktree: `.kw/worktrees/issue-67` · Canonical repository:
`https://github.com/KaolaBrother/kaola-project-runner.git`

## Delivered

ZCode ACP `tool_call` updates now carry a bounded path/line receipt when the
app-server `input` already named one. Live CLI 0.16.5 `model.streaming`
`kind: tool_call` includes `input.file_path`; the translator had cached that
object and dropped it. `extract_tool_evidence` copies only top-level path keys
and an integer line/`offset` (depth 1, 1536-byte cap). Plaintext `command` is
not forwarded. Execute cards keep `kind`/`title`/`status` without claiming a
command transcript. No path is invented when upstream has none. `inputRef` is
not followed. No generic sanitizer.

## Files Changed

| Path | Change |
|---|---|
| `scripts/kaola-zcode-acp.py` | Path/line-only evidence on ACP `rawInput`/`locations` |
| `skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py` | Generated copy |
| `templates/orchestrator/references/host-startup.md.tmpl` | Verification guidance; #72 examples kept |
| `skills/kaola-project-runner/references/host-startup.md` | Generated |
| `tests/contract/fake-zcode-app-server.py` | `read_path` / `no_input` / `sensitive_extra` / `huge_nested` / `command_token` |
| `tests/contract/test-zcode-acp-contract.py` | 34 tests including holder `events.jsonl` |
| `third_party/zcode-acp/UPSTREAM.md` | Measured input shape |
| `CHANGELOG.md` | User-visible Unreleased entries |

## Test Coverage

`tests/contract/test-zcode-acp-contract.py`, 34 tests, already wired into `./scripts/validate.sh`.

- Path on `Read` becomes `rawInput.file_path` + `locations`; nested paths are not lifted.
- Absent input invents neither `rawInput` nor `locations`.
- Extra/secret/nested blobs are dropped.
- Unregistered token in `command` is absent from ACP updates and holder `events.jsonl`.
- Execute cards remain `kind=execute` / `title=Bash` without a command transcript.

## Validation

Recorded by `kaola-workflow-validation-runner.js` from the candidate worktree (see
`.cache/final-validation.md`, `validated_candidate_hash`
`ed317c0638d791389454ff58d7e0c6c9f9c45557a688f5721af78a31080b4dd2`). This project declares no
`test:kaola-workflow:*` chains, so `run-chains.js` reported `chains_config_missing`.

| Check | Result | Artifact |
|---|---|---|
| `./scripts/validate.sh` at `23d231e` | **exit 0**, 0 FAILED | `evidence/validate-finalize-23d231e.log` |
| `python3 tests/contract/test-zcode-acp-contract.py` | **34/34** | this finalize re-run |
| `python3 tests/contract/test-issue-72-session-naming.py` | **16/16** | this finalize re-run |
| `./scripts/render-skills.py --check` | PASS, budgets OK | this finalize re-run |

Acceptance: outer Agent independently reviewed path/line-only forwarding and the
no-command rule, re-ran the 34 tests and `render --check` on `954eb22`, and
formally ACCEPTed. Rebase onto `3dd7e5e` was archive-only (Issue #65 live
isolation supplement) and did not change translator bytes.

## Changed Paths

See the finalize transaction `changed_paths`. Expected vs `origin/main`:

- `CHANGELOG.md`
- `scripts/kaola-zcode-acp.py`
- `skills/kaola-project-runner/references/host-startup.md`
- `skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py`
- `templates/orchestrator/references/host-startup.md.tmpl`
- `tests/contract/fake-zcode-app-server.py`
- `tests/contract/test-zcode-acp-contract.py`
- `third_party/zcode-acp/UPSTREAM.md`

## Documentation Docking

`.cache/doc-docking.md` — **DOCKED**.

## Follow-Up Items

None filed. Issue #70 remains the in-flight owner of `docs/zcode-host.md` and
heartbeat-binding host-startup sentences; this run kept #72's issue-scoped
examples and did not edit #70/#73/#74 live trees.

## Readiness

Ready to archive, sink-merge, close #67, remote-sync, closure-audit, and exact
cleanup of this issue only. Mainline sink is serial; `origin/main` is `3dd7e5e`
with no MERGE_HEAD.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-67/.cache/doc-docking.md
- kaola-workflow/archive/issue-67/.cache/final-validation.md
- kaola-workflow/archive/issue-67/.cache/mirror-digest.json
- kaola-workflow/archive/issue-67/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-67/evidence/MEASURED.md
- kaola-workflow/archive/issue-67/evidence/compare/claude-code-acp-issue-65-tool-calls.json
- kaola-workflow/archive/issue-67/evidence/compare/zcode-acp-issue-66-tool-calls.json
- kaola-workflow/archive/issue-67/evidence/live-sentinel/MARKER.txt
- kaola-workflow/archive/issue-67/evidence/live/00-candidate.txt
- kaola-workflow/archive/issue-67/evidence/live/candidate.diff
- kaola-workflow/archive/issue-67/evidence/live/zcode-acp-tool-calls.before.json
- kaola-workflow/archive/issue-67/evidence/live/zcode-acp-tool-calls.json
- kaola-workflow/archive/issue-67/evidence/live/zcode-upstream-events.before.json
- kaola-workflow/archive/issue-67/evidence/live/zcode-upstream-events.json
- kaola-workflow/archive/issue-67/evidence/probe/run-upstream-probe.py
- kaola-workflow/archive/issue-67/evidence/probe/sitecustomize.py
- kaola-workflow/archive/issue-67/finalization-summary.md
- kaola-workflow/archive/issue-67/mission-list.md
- kaola-workflow/archive/issue-67/workflow-state.md
