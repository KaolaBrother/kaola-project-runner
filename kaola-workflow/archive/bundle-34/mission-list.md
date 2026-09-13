# Issue #34: per-run default/upgrade model presets with explicit Fast opt-in

Implement the frozen design from https://github.com/KaolaBrother/kaola-project-runner/issues/34
(supervising Codex owns design and final acceptance). Worktree:
`/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-34`, branch
`workflow/bundle-34`. `templates/grok-golden/` stays frozen; `skills/` is generated only.

1. item: Extend model-policy helper + platform manifests with default/upgrade preset table, Fast capability declarations, and explicit model/effort precedence (explicit model > tier model > native default; explicit effort only with preset model; encoded-effort IDs get no extra effort call).
   status: done
   dispatched: self (inline) — manifests, adapters, kaola-model-policy.py
   result: PASS — all 7 manifests carry default/upgrade preset + fast fields; helper resolves source/tier/model/effort/fast with catalog evidence; render-skills.py --check PASS on 7 Skills; test-model-policy.sh PASS (all platforms, new tier/fast/preserve cases).
2. item: Wire resolved selection into both launch paths — ACP applies model first, then effort and Fast via advertised native config IDs for all supported platforms (remove Codex-only asymmetry); PTY path uses its native mechanisms; session-scoped only, no global config writes.
   status: done
   dispatched: self (inline) — kaola-acp.py, kaola-tmux.sh, adapters
   result: PASS — ACP start applies model→effort→fast via manifest acp_*_config_id then mode skip; PTY adapters apply --model/native effort/service_tier per selection; session-scoped only (no global writes); test-acp-contract.py Issue34ModelSelectionAcpTests 9/9 PASS.
3. item: Resume/continue semantics — preserve saved native model/effort unless caller supplies tier/model/effort; keep per-run Fast off unless explicitly enabled; report limitations truthfully.
   status: done
   dispatched: self (inline) — kaola-tmux.sh resolve_model_policy, kaola-acp.py resolve_selection
   result: PASS — resume/continue without tier/model/effort resolves source=resume-preserved (no model/effort override applied); explicit tier/model/effort on resume re-applies; fast stays off unless --fast on; PTY contract cases + ACP preserve test PASS.
4. item: Receipt/reporting — selection source, requested/resolved values, configuration receipts, actual evidence and unavailable capabilities reported distinctly via existing receipt structure; unsupported Fast reported as unsupported, never claimed on/off without proof.
   status: done
   dispatched: self (inline) — kaola-acp.py config_application/fast_report, helper evidence fields
   result: PASS — receipts carry model_selection, requested_*/resolved_*/resolved_fast, config_application per-option receipts, fast report with support/effective/applied_via; rejected set_config_option recorded as limitation (session stays usable); resolved_fast=unsupported asserted in tests.
5. item: Shared template + manifest prompt guidance (agent owns selection: default unless explicit upgrade request or user-described complexity; named model wins; no inference/classifier; Fast off default) then render all seven skills; keep grok-golden frozen.
   status: done
   dispatched: self (inline) — templates/SKILL.md.tmpl, references/platform+acp templates, manifests
   result: PASS — guidance documents tiers/precedence/no-escalation/Fast opt-in/resume preservation/mismatch-as-evidence; render-skills.py --write WROTE 7 Skills + --check PASS; templates/grok-golden untouched.
6. item: Focused behavioral tests (static transport tests, no real PTY launches) covering defaults, both tiers, explicit override precedence, OpenCode zero-override, Fast off/on and unsupported, resume preservation, conflicting ID/flag reporting.
   status: done
   dispatched: self (inline) — tests/contract/test-model-policy.sh, test-adapters.sh, test-acp-contract.py, mock-acp-agent.py
   result: PASS — test-model-policy.sh PASS (7 platforms × default/upgrade/user/no-effort/unavailable/mismatch/unreadable/continue-preserve/resume-preserve/resume-tier/malicious/fast cases); test-adapters.sh PASS; test-acp-contract.py 28 tests PASS incl. ordered config application, rejection-as-limitation, strict-config mock.
7. item: Docs — README/API docs + CHANGELOG updated, contradictory old defaults eliminated.
   status: done
   dispatched: self (inline) — README.md, docs/api.md, docs/architecture.md, CHANGELOG.md
   result: PASS — platform table now lists default+upgrade presets; selection/tier/fast/preserve semantics documented in README + api.md + architecture.md; CHANGELOG Unreleased entry added; stale luna/Opus5/Adaptive/GLM defaults eliminated.
8. item: `./scripts/render-skills.py --check` and `./scripts/validate.sh` pass on final candidate.
   status: done
   dispatched: self (inline)
   result: PASS — render-skills --check: PASS (7 Skills); validate.sh exit 0 (all suites OK incl. generated Skill acceptance PASS); grok-golden untouched.
9. item: Real ACP live smoke on available authenticated platforms (no PTY/Cloud/Claude auth on this machine): actual configuration + simple send/reply + exact stop; exercise default, upgrade, explicit override, Fast off/on where supported, OpenCode no-forced-model, resume semantics; record unavailable cases honestly.
   status: done
   dispatched: self (inline) — live runs against real adapters in /tmp/kpr-34-live
   result: PASS — codex default+upgrade+fast on+resume-preserve+send/reply/stop; grok/kimi/opencode/devin/cursor start+send+stop; advertised config ids match manifests; cursor ACP rejects PTY-picker model id → reported as limitation (session usable); claude-code not tested (owner restriction). Evidence: kaola-workflow/bundle-34/evidence/acp-live-smoke-34.md.
10. item: Commit, push `workflow/bundle-34`, open reviewable PR, and hand back exact SHA/PR/commands/evidence/limits; stop before merge for supervising Codex review.
   status: done
   dispatched: self (inline) — commit/push/PR next
   result: PASS — committed 2956bd379be65c48da85ae9686cd2d27f7746f25 (95 files, +4389/-641) on workflow/bundle-34; pushed to origin; PR https://github.com/KaolaBrother/kaola-project-runner/pull/35 OPEN (non-draft, head=2956bd3); worktree + evidence preserved for finalization; stopped before merge.

## Corrective review outcome (supervisor review of 2956bd3 — not accepted for merge)

11. item: Address supervisor review fixes: (1) cursor ACP model mapping via manifest acp_model_map (live-verified advertised values); (2) fast_report effective/applied must reflect native success — unknown on rejected fast config and unapplied fast-model, descriptor-declared fast honored, plus regression tests; (3) evidence date corrected 2026-10-10→2026-09-13 with raw record-dir receipt paths and per-session stop proof; (4) live explicit --model override + resume send/reply with preserved-model evidence.
   status: done
   dispatched: self (inline) — kaola-acp.py, kaola-acp-holder.py, cursor-cli.yaml + 6 manifests, render-skills.py, mock-acp-agent.py, test-acp-contract.py, evidence file
   result: PASS — committed 790e2ae4a7cd6e49805e1bd8618fd123dea95255, pushed to PR #35. Cursor ACP now applies model=grok-4.6[effort=high,fast=true] via map (requested_id=cursor-grok-4.6-xhigh, declared={effort:high,fast:true}), send CUROK2, stopped residual []; fast.effective reports on with conflict (descriptor-declared intrinsic fast; no false off); rejected fast config → effective=unknown, rejected fast model → applied=False/effective=unknown (2 new regression tests + 2 mapping tests, Issue34 class 13/13 PASS); preflight reports advertised_config_options; live codex --model gpt-6-astra bare (no invented effort) EXPLICITOK + stopped; resume send RESUMEDOK + stopped; acp34-resume leaked holder stopped cleanly; all bundle-34 test holders verified dead (0 residual); evidence file re-dated 2026-09-13 with per-session record-dir paths. render-skills --check PASS; validate.sh exit 0; test-acp-contract.py 32 tests PASS.
| 12 | Corrective review round 2: parameterized Cursor ACP route | done | Supervisor measured `_meta.parameterizedModelPicker` unlocking native `model`/`effort`/`fast` options; replaced rejected descriptor mapping | `acp_init_meta` wired through holder `--init-meta` in start+preflight (Cursor-only manifest field); `acp_model_map` decomposes `cursor-grok-4.6-xhigh`→`grok-4.6`, suffix→effort `xhigh`, fast→`"false"` string via `acp_fast_values`; wrong `grok-4.6[effort=high,fast=true]` map removed; `model-variant+acp-config` mechanism fixed; mock `cursor-params` cap + 7 new regression tests (init meta Cursor-only, exact order, string values, fable upgrade, fast-variant decompose, no-descriptor manifest guard); PASS: 38 acp contract tests, render --check, validate.sh; live `acp34-param-cursor` verified `VERIFIED_XHIGH_OFF`, end_turn, zero tools, stopped with `residual_pids=[]`; 114 owned test pairs killed exactly, foreign sessions preserved |
| 13 | Corrective review round 3: Claude fastMode platform fact | done | Supervisor found official docs show fastMode setting + --settings JSON; manifest wrongly claimed no mechanism | `settings` fast mechanism added to model-policy helper (`--fast-capable`/`--fast-uncapable` substring lists); claude adapter pins process-scoped `--settings '{"fastMode": ...}'` — false by default incl. unsupported/unknown, true only on explicit opt-in with fast-capable model (opus; fable stays selected + reports unsupported, no model switch, no global settings write); ACP unchanged (wrapper probe-eof, reports unsupported honestly); manifest fast_support=settings; tests: model-policy claude case (off pin, opus on, fable unsupported+pin) + adapters pin assertions; PASS: test-model-policy.sh, test-adapters.sh, render --check, validate.sh exit 0; 30 owned test pairs killed, foreign sessions preserved |
| 14 | Corrective review round 4: remove speculative Claude fast classifier | done | Supervisor: substring capability lists silently flip --fast on→off for unknown models; owner principle forbids inferred-support gates | Removed `--fast-capable`/`--fast-uncapable` args, adapter constants, and substring logic; settings mechanism now passes request verbatim — `fastMode: true` on explicit opt-in, `false` default; resolved_fast reports launch intent, effective unknown without native evidence (CLI decides support, Runner never changes the model); docs/tests corrected (explicit-model + fast-on verbatim case replaces fable-unsupported case); PASS: test-model-policy.sh, test-adapters.sh, render --check, validate.sh exit 0; 19 owned test pairs killed exactly |
