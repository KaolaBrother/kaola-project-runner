# Finalization Summary — bundle-146 (issue #146)

Issue: #146 "Codex ACP start intermittently fails acp-session-timeout: holder's fixed 15 s session/new wait is shorter than live codex latency"
Branch: workflow/bundle-146. Candidate a5a9fa8 (fix 0d29728 + review fixes a5a9fa8) over base f5dc05f.
Delivery: sink-merge to main, no PR (Owner boundary). The Host ACCEPTED a5a9fa8 before finalize.
Naming: the claim script named the project `bundle-146`, so the archive is `kaola-workflow/archive/bundle-146/`. It covers the single issue #146, and the mission ledger is issue-146.

## Delivered
- Optional manifest key `acp_session_new_timeout`: seconds in (0, 600]. It is validated in scripts/render-skills.py and applies to the `session/new` wait in the holder for `start` and for the `preflight` probe (holder `--session-new-timeout`, default `SESSION_NEW_TIMEOUT = 15.0`).
- scripts/kaola-acp.py passes the declared wait to the holder on both spawn paths (start, preflight). It widens the client start window (`START_WAIT` 20 s) and the preflight subprocess bound (`PROBE_WAIT` 60 s) by max(0, wait − 15). An unparsable or out-of-range value falls back to 15.
- platforms/codex.yaml declares `60`, against a measured worst case of ~18.1 s (#145 probes). The other nine platforms declare nothing and keep exactly 15 s / 20 s / 60 s.
- Unchanged: no answer in time is still `acp-session-timeout`, and a late answer is still not adopted (orphan_response). No new gate, classifier, retry, or waiting layer. Redaction is untouched.

## Acceptance walk (issue #146)
- A fixed 15 s wait failed codex starts that would have come up (orphan response ~18.1 s after spawn): codex now waits 60 s, and the client window encloses it (test_codex_declares_a_wait_above_the_measured_latency, test_declared_wait_widens_the_client_start_window — ready with session/new answering ~21 s after spawn).
- Per-platform (remedy direction): manifest key, codex-only (test_undeclared_platforms_keep_the_shared_default; test_generated_codex_skill_carries_the_fact).
- Keeps "refuse only objective transport impossibility": a genuine non-answer is still `acp-session-timeout` (test_short_declared_wait_fails_start_and_the_late_answer_is_orphaned; test_short_wait_times_out_on_a_slow_session_new).
- The preflight probe gets the same wait (test_preflight_hands_the_probe_the_declared_wait — ~16 s answer admitted with a declared 20 s).
- Validation bounds (test_render_rejects_a_non_positive_or_non_numeric_wait: "", 0, -5, abc, inf, nan, 601, 1e10; test_client_window_encloses_the_declared_wait).

## Files Changed
Sources: CHANGELOG.md; docs/api.md; platforms/codex.yaml; scripts/kaola-acp-holder.py; scripts/kaola-acp.py; scripts/render-skills.py; scripts/validate.sh; templates/references/acp.md.tmpl; tests/contract/mock-acp-agent.py (MOCK_ACP_SESSION_NEW_DELAY_MS); tests/contract/test-issue-146-session-new-wait.py (new).
Generated (render-skills --write): skills/*-kaola-project-runner/{references/acp.md, scripts/kaola-acp.py, scripts/kaola-acp-holder.py} ×10, plus skills/codex-kaola-project-runner/scripts/platform.yaml.

## Test Coverage
tests/contract/test-issue-146-session-new-wait.py — 11 tests, hermetic (mock ACP agent with a delayed session/new, private record root, KAOLA_* scrubbed, force-stop registered before each start). Wired into validate.sh (python_suites_all + lane A).
Mutation proof: in a /tmp copy, reverting the client wiring (start deadline extra and preflight --session-new-timeout) turned both end-to-end tests red (start-incomplete; acp-session-timeout).
Independent code-reviewer pass on 0d29728. Findings F1 (an unbounded value overflowed threading.TIMEOUT_MAX), F3 (the client wiring was untested), and F2 (doc precision) were all fixed in a5a9fa8.

## Validation
- Final, frozen a5a9fa8: `./scripts/render-skills.py --check` PASS, budgets OK. `./scripts/validate.sh` exit=0, elapsed 567 s, 42/42 suite runs OK, 0 FAILED/SKIPPED, full footer, empty holder sweep (validate-a5a9fa8-full.log + validate-a5a9fa8-full.exit; run detached with start_new_session and its real exit code read back). `git diff --check f5dc05f a5a9fa8` clean.
- Recorded: .cache/final-validation.md, verdict pass, command `./scripts/render-skills.py --check && ./scripts/validate.sh`, validated_candidate_hash 92b4a9e746284e146f4f3260832e2f3f9190a9bb442d75024f113694aed7f443. finalize --check: ok, validation chains_green, reasons [], dirty_paths [].
- Incident record: validate-a5a9fa8-PARTIAL-KILLED.log is an earlier backgrounded run on a5a9fa8 that was killed externally (17 lines, ends "Terminated: 15"). It is partial and NOT evidence.
- Superseded: validate-0d29728.log exit=0 on 0d29728, before the review fixes.
- Host independently verified the full log and accepted.
- Not executed: a live codex start with the 60 s wait (the fix is a bound change; the latency is environmental and intermittent).

## Changed Paths
41 paths (finalize --check changed_paths): CHANGELOG.md, docs/api.md, platforms/codex.yaml, scripts/kaola-acp-holder.py, scripts/kaola-acp.py, scripts/render-skills.py, scripts/validate.sh, templates/references/acp.md.tmpl, tests/contract/mock-acp-agent.py, tests/contract/test-issue-146-session-new-wait.py, skills/{claude-code,codex,cursor-cli,devin,droid,dsh,grok,kimi-cli,opencode,zcode}-kaola-project-runner/{references/acp.md,scripts/kaola-acp.py,scripts/kaola-acp-holder.py}, skills/codex-kaola-project-runner/scripts/platform.yaml.

## Documentation Docking
DOCKED — see .cache/doc-docking.md (docs/api.md, acp.md.tmpl, CHANGELOG updated; README no impact, Host-accepted).

## Follow-Up Items
- None filed. `session/resume`, `session/load`, and `session/list` keep their 15 s waits. There is no measured evidence of slow codex resume, so this is not a defect.
- Nit, not filed: the new suite's module docstring mentions only the scaled 2.5 s delay and not the later 16 s / 21 s end-to-end cases. It was left so the validated candidate stays exact.
- Out of scope, untouched: #126 (parallel seat claude-code-KPR-i126-host).

## Status
READY — accepted, validated, docked; closes #146 on sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-146/.cache/doc-docking.md
- kaola-workflow/archive/bundle-146/.cache/final-validation.md
- kaola-workflow/archive/bundle-146/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-146/finalization-summary.md
- kaola-workflow/archive/bundle-146/mission-ledger.jsonl
- kaola-workflow/archive/bundle-146/validate-a5a9fa8-full.exit
- kaola-workflow/archive/bundle-146/workflow-state.md
