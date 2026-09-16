# Finalization summary — bundle-51 (Issue #51)

Candidate: `58d72ac87370e238359ef3c640a17d92a13fccd7` on `workflow/bundle-51`, based on accepted #49/#50 `main` (`f9eb6e8`). Sink: merge. Closure decision: close #51 after the final delivery correction is on the issue and the transaction gates pass.

## Delivered

- Eighth generated CLI worker `zcode-kaola-project-runner`, not a Grok Bot host. Default transport is ACP; the installed ZCode 3.11.2 / bundled CLI 0.16.5 has no usable PTY TUI, per the owner's later Issue #51 correction.
- Small Runner-owned Python ACP translator for ZCode's private `app-server --stdio` protocol, shipped Skill-relative. `william0wang/zcode-acp` v0.39.0 at `80aa4e2c39909f91145dfdf6428a3867b5c61701` is a pinned Apache-2.0 protocol reference only; no upstream runtime bytes or npm dependency are vendored. It uses explicit app-bundle runtime paths, a child environment allowlist, and no remote hub, quota client, database writer or daemon.
- The adapter reads the desktop registry read-only and passes only a known enabled built-in Coding Plan provider in memory to the headless app-server; it does not persist the credential, inject an API-key environment variable, or select a pay-as-you-go/Start Plan provider. Outbound ACP messages are centrally redacted. Native permission skip-all is `yolo`.
- Shared renderer, installer, locator, ACP holder and model-policy changes plus generated Skill surfaces and docs, with progressive disclosure budgets and the frozen golden template validated.

## Files Changed

The branch adds `platforms/zcode.yaml`, `scripts/adapters/zcode.sh`, `scripts/kaola-zcode-acp.py`, the generated ZCode Skill, fake protocol harness/fixtures and `third_party/zcode-acp/UPSTREAM.md`. Shared `scripts/`, `templates/`, generated worker copies, AGENTS/README/docs/CHANGELOG and tests change only for integration and capability wording. `hosts/grok-bot/` and `templates/grok-golden/` remain generated/frozen as required. Worktree is clean at the candidate.

## Test Coverage

- Fake app-server: 24/24 ZCode ACP contract tests including lifecycle, stream/tool/user-input, model/mode, cancel, resume, concurrency, no forbidden write/network, outbound secret echo redaction and custom `-coding-plan` suffix rejection (red before the final allowlist fix, green after).
- Generated Runner: Issue #51 integration 6/6 (117 checks), installer/renderer inventory and default ACP dispatch. Existing Issue #50 and other platform suites also green in `validate.sh`.
- Live ZCode: native BigModel Coding Plan GLM-5.3 sentinel, read-only tool under `yolo`, cancel semantics, continue/resume, concurrent isolation, settings metadata identity and exact stop without residue in `uat-live-2026-09-16.md`. The controlling Agent additionally ran a final-candidate default-ACP sentinel and exact stop after commit `58d72ac`.
- Live Claude Code regression: the controlling Agent ran the same candidate's generated Claude Skill with installed Claude Code 2.1.272, Fable High and `bypassPermissions`; default ACP sentinel and exact stop both passed. Deeper Claude tool/cancel/resume coverage is archived with Issue #50.

## Validation

Consumer repository: `kaola-workflow-run-chains.js` reported `chains_config_missing` as expected; no npm workflow chains are declared. From the candidate worktree, `./scripts/validate.sh` exited 0, `./scripts/render-skills.py --check` passed, and `git diff --check origin/main..HEAD` was clean. `.cache/final-validation.md` records `verdict: pass`, `validation_command: ./scripts/validate.sh`, candidate hash `7f929d8ed55f5157f0d7de5a50b045b2931e92224223bb53cbaf9287d3ab56f8`. `finalize --check --json`: `ok=true`, `validation=chains_green`, `reasons=[]`.

## Changed Paths

`finalize --check` reported 85 `changed_paths` and `dirty_paths=[]`: `AGENTS.md`; ZCode manifest and adapter; shared installer/ACP/locator/model/tmux/renderer/validation scripts; generated Claude, Codex, Cursor, Devin, Grok, Kimi, OpenCode and ZCode worker surfaces; orchestrator Skill; shared templates; protocol fixtures and contract tests; `third_party/zcode-acp/UPSTREAM.md`. README/docs/CHANGELOG changes were separately inspected in Git's candidate diff and docked below; the transaction's `changed_paths` array is the authoritative scoped finding.

## Documentation Docking

`.cache/doc-docking.md`: DOCKED. README, API/architecture/conventions docs, CHANGELOG, AGENTS and generated Skill references state the actual ACP default and PTY limitation. No hand edits to generated Skill source.

## Acceptance legs

- Automated/local: PASS as above.
- Real ZCode Coding Plan on this Mac: PASS for ACP, with evidence boundaries in the UAT record. PTY is unsupported by the installed product, explicitly removed from the gate by the owner's later Issue #51 comment, never called PASS.
- Real Claude Code subscription on this Mac: PASS for final-candidate ACP smoke; prior #50 lifecycle evidence retained.
- Unexecuted on the final commit: a new full Claude Code lifecycle run; unchanged #50 bridge and prior accepted UAT cover it. ZCode cancel cannot be called instant interruption: the CLI acknowledges stop immediately but completes the in-flight stream before reporting cancellation.
- Issue statement deviations corrected by owner comments: Gate 2 Runner-owned translator instead of Gate 1 vendoring; read-only in-memory desktop Coding Plan bridge; ACP-only ZCode without PTY fallback. A final delivery comment restates these facts before closure.

## Follow-Up Items

No newly discovered release blocker. PTY support belongs to the ZCode product, not the Runner; do not file a Runner repair issue for it. Native cancellation latency is recorded as a protocol limitation, not disguised as instant cancellation. No unresolved human decision or conflicting worktree is known.

## Readiness

READY for the Workflow finalize transaction, archive, merge sink and Issue #51 closure after posting the final issue correction. Release/tag and installation are separate subsequent acceptance steps.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-51/.cache/doc-docking.md
- kaola-workflow/archive/bundle-51/.cache/final-validation.md
- kaola-workflow/archive/bundle-51/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-51/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-51/delivery-report.md
- kaola-workflow/archive/bundle-51/finalization-summary.md
- kaola-workflow/archive/bundle-51/mission-list.md
- kaola-workflow/archive/bundle-51/salvage-2026-09-16/MANIFEST.txt
- kaola-workflow/archive/bundle-51/salvage-2026-09-16/scripts/kaola-zcode-acp.py
- kaola-workflow/archive/bundle-51/salvage-2026-09-16/tests/contract/fake-zcode-app-server.py
- kaola-workflow/archive/bundle-51/salvage-2026-09-16/tests/contract/hooks/zcode-probe/sitecustomize.py
- kaola-workflow/archive/bundle-51/salvage-2026-09-16/tests/contract/test-zcode-acp-contract.py
- kaola-workflow/archive/bundle-51/salvage-2026-09-16/third_party/zcode-acp/UPSTREAM.md
- kaola-workflow/archive/bundle-51/uat-live-2026-09-16.md
- kaola-workflow/archive/bundle-51/workflow-state.md
