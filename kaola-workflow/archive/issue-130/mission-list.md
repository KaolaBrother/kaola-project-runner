# #130 Retire PTY unconditionally — ACP only, fail-closed, no dual transport (implement Fable design comment 3, owner-accepted)

Worktree: /Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-130 (branch workflow/issue-130). Out of scope: locator tmux probe → holder fact, adapter slimming/renames (design §7 follow-ons); #126/#132/#133; ~/.dsh.

1. item: Map the six #8 model-policy guarantees (test-model-policy.sh) to existing ACP coverage; add missing ACP cases before deleting the PTY suite
   status: done
   dispatched: investigator subagent (read-only mapping) → kaola-workflow/issue-130/.cache/model-policy-map.md; missing cases then authored by orchestrator in tests/contract/test-issue-130-pty-retired.py
   result: map at .cache/model-policy-map.md (c covered; a,b,d,e,f + resume+tier/model + no-prompt added as ModelPolicyOnAcp, 10/10 OK); losses L1-L4 (status provenance, actual id, true/false verified) go to CHANGELOG; test-model-policy.sh then git rm'd
2. item: Scripts — kaola-tmux.sh typed refusal transport-pty-retired before every guard + drop tmux branch; kaola-acp.py transport block {"selected":"acp"} + drop tmux collision probe; render-skills.py drop default_transport; delete relay trio + kaola-observation.py; grok-bot-verify marker
   status: done
   dispatched: self
   result: worktree edits to scripts/kaola-tmux.sh (748→~210 lines), kaola-acp.py, render-skills.py, kaola-grok-bot-verify.py; git rm relay trio, kaola-observation.py, templates/references/transport.md.tmpl
3. item: Templates, platforms/*.yaml, orchestrator templates → render --write (worker/main Skill ACP-only wording, transport.md removed)
   status: done
   dispatched: self
   result: worktree edits templates/SKILL.md.tmpl, references/{acp,platform,steering}.md.tmpl, orchestrator/{SKILL.md.tmpl,references/zcode-host-dispatch.md.tmpl,workflow-worktree.md,heartbeat-skeleton.txt}, platforms/*.yaml (default_transport removed, descriptions ACP); render --write + --check PASS, hosts/grok-bot zero diff
4. item: Tests — new test-issue-130-pty-retired.py; delete 25 PTY-only suites + fixtures; rewrite 19 mixed suites; validate.sh lanes (lane C gone)
   status: done
   dispatched: 24 PTY-only suites + tests/fixtures + tests/lib git rm'd and validate.sh lanes by self; 19 mixed suites → implementer subagent, handback kaola-workflow/issue-130/.cache/tests-handback.md; new suite test-issue-130-pty-retired.py by self; test-model-policy.sh deletion waits for mission 1
   result: crash recovery 2026-09-22 (handback never written; subagent died in the Mac reboot) — re-derived by running validate.sh on the worktree: 16 of 19 mixed suites were already rewritten and green; 3 still red, fixed by self: test-issue-73-canonical-root.py (run_cli defaulted to --transport pty; accepted starts now proven by the downstream ACP heartbeat-host-unresolved refusal, #104 N6-N6d cases absorbed by #130 suite), test-issue-51-runner-integration.py (default_transport/PTY-diagnostic/PTY skip-all checks → ACP-only), test-issue-130-pty-retired.py (red only from an inherited KPR_CANONICAL_REPO; fixed at source: kaola-tmux.sh now unsets it on entry, re-rendered). Each suite green standalone under KAOLA_*/KPR_* scrub (73: 31 OK; 51: 6/6, 119 checks; 130: 44 OK). Residual-PTY grep over tests/ shows only retirement assertions
5. item: Docs — README, AGENTS.md, docs/*, design doc git mv → superseded dated name, CHANGELOG Unreleased breaking entry
   status: done
   dispatched: doc-updater subagent → edits in worktree docs/README/AGENTS/CHANGELOG; handback summary kaola-workflow/issue-130/.cache/docs-handback.md
   result: .cache/docs-handback.md; 11 doc files + git mv design doc → docs/runner-v2-dual-transport-design-2026-09-11.md (Superseded line); orchestrator fixed CHANGELOG Claude fastMode claim and workflow-worktree.md KAOLA_PROJECT_RUNNER_REPO line
6. item: Gate — render --check + validate.sh rc=0 on the frozen candidate; live-surface grep
   status: done
   dispatched: self, foreground on the candidate commit of workflow/issue-130 → logs /tmp/i130-gate-render.log, /tmp/i130-gate-validate.log
   result: PASS on frozen candidate e42be2a (workflow/issue-130, tree = HEAD 16b42b2 + 251 files, +2800/-40639): render-skills --check rc=0 (10 workers + main + delegator + grok-bot bridge 2536 B, budgets OK); validate.sh rc=0, 39 unittest OK blocks, no FAILED/SKIPPED lines, grok-bot-verify PASS, git diff --check clean, sweep residual_pids []. Live-surface grep of skills/ + hosts/: no TMUX_BIN/capture-pane/send-keys/relay/OBSERVATION_HELPER/default_transport/--transport pty/transport.md; "tmux" only as the runtime-tmux.sh/kaola-tmux.sh entrypoint name (rename = §7 follow-on); PTY wording only as the transport-pty-retired refusal. Residual: scripts/adapters/*.sh frame helpers still name kaola-observation.py but are unreachable (kaola-tmux.sh calls only adapter_preflight) — adapter slimming §7 follow-on
7. item: Independent review of the frozen candidate; verdict held by orchestrator
   status: done
   dispatched: code-reviewer subagent (not the implementer) on e42be2a vs 16b42b2 → findings kaola-workflow/issue-130/.cache/review-e42be2a.md
   result: VERDICT ACCEPT (held by orchestrator) on e42be2a — no blocking defects; refusal ordering/shape, no residual tmux path (locator probe = §7), lanes complete, 5 suites re-run green. Non-blocking: L1 fifth declared #8 loss (status model provenance / true-false model_verified) beyond design §5's four → owner acknowledgement; L2 no test pins the KPR_CANONICAL_REPO unset; L3 "outbound text is redacted" in AGENTS.md:25 and worker Skill template overstated (only kaola-zcode-acp.py redacts). Info: case-variant/combined PTY spellings get untyped stderr refusal; leftover "default transport"/"forcing PTY" wording; two weak tests. Candidate not mutated after gate
