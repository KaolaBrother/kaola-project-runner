# Issue #36: portable Agent Skills and runtime-neutral installation with Codex compatibility

Implement the owner-approved design from
https://github.com/KaolaBrother/kaola-project-runner/issues/36 (supervising Codex owns design and
final acceptance). Worktree:
`/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-36`, branch
`workflow/issue-36`. `templates/grok-golden/` stays frozen; `skills/` is generated only.

Parallel runs: #33 lives in `.kw/worktrees/bundle-33` (devin-kaola-observation-33) and #34/PR #35 in
`.kw/worktrees/bundle-34` (devin-kaola-model-policy). Do not touch their worktrees, branches,
records, sessions, or core model/holder logic. Integration validation follows accepted #33/#34;
v0.1.0 release belongs to those runs and must not be delayed or silently expanded by this issue.

Owned scope: installer (`scripts/install-local.sh`), standalone neutral validator, portability
templates/docs/tests. No code-generation redesign, hard gates, daemon, speculative runtime registry,
or runtime×target matrix.

1. item: Portable payload — neutralize controlling-runtime wording in the seven platform manifests
   (generic controlling-Agent `description`; keep Codex target-CLI facts and `$skill` prompt only in
   optional `agents/openai.yaml` Codex metadata); SKILL.md.tmpl + references templates invocation
   examples explicitly resolve the installed Skill's absolute script path while `--repo` stays the
   user's project; render-skills.py docstring de-Codexed; regenerate seven skills; grok-golden
   byte-identical.
   status: done
   dispatched: self (inline) — platforms/*.yaml, templates/SKILL.md.tmpl, templates/references/*.tmpl, render-skills.py docstring
   result: PASS — all 7 descriptions now read "Use when the controlling Agent should communicate..."; all invocation examples resolve "$SKILL_DIR/scripts/runtime-tmux.sh" absolutely with spaces-safe quoting and --repo for the user project; render-skills --write WROTE 7 + --check PASS; test-generated-skills.py + test-lifecycle-contract.py markers now pin the quoted absolute form (both PASS); grok-golden untouched (git status clean).
2. item: Installer contract — `--runtime codex|claude-code|cursor|devin` (aliases verified against
   installed/runtime dirs only), `--skills-dir ABS_PATH` (mutually exclusive), `--method link|copy`
   (default link), `--platform` unchanged, `--uninstall` scoped to selected target+owned Skills,
   no-arg legacy Codex default preserved, preflight-then-write, copy-mode per-install
   ownership/content receipt outside generated payload (no-op on identical owned content; replace/
   remove only unmodified owned installs; preserve edits and foreign additions; no global registry),
   staged same-filesystem replacement, literal paths with spaces, explicit `--bin-links` (default on
   only for Codex-runtime installs; uninstall leaves shared links unless explicitly requested and
   exact-owned).
   status: done
   dispatched: self (inline) — scripts/install-local.sh rewrite
   result: PASS — --runtime codex|claude-code|cursor|devin verified aliases; --skills-dir absolute (spaces ok) mutually exclusive; --method link|copy; per-Skill JSON receipts in <dest>/.kaola-install-receipts outside payload (digest = tree sha256 incl. symlinks/dirs); no-op on identical owned content; update replaces unmodified owned copy; edits/foreign/no-receipt refused; copy↔link switching via relink/copy-over-link; staged place_staged swap (no partial dirs); --bin-links on only for codex-runtime or explicit flag; uninstall leaves shared links unless explicit + exact-owned; legacy no-arg codex path and grok root migration unchanged; plan-then-execute preflight; manual smoke verified all paths incl. rc=1 refusals.
3. item: Host-neutral validation — repository-owned Agent Skills validator replaces external
   `~/.codex/skills/.system/skill-creator/scripts/quick_validate.py`; `scripts/validate.sh` runs in a
   controlled temporary HOME lacking `.codex` with `CODEX_HOME` unset and does not modify real user
   configuration; existing behavioral tests and render checks kept.
   status: done
   dispatched: self (inline) — scripts/validate-skill.py (new), scripts/validate.sh
   result: PASS — validate-skill.py is a dependency-free Agent Skills format validator (frontmatter name/description, name==dir, ≤64/≤1024 chars, allowed-field set); validate.sh drops ~/.codex quick_validate dependency, exports a mktemp HOME and unsets CODEX_HOME/CLAUDE_CONFIG_DIR/DEVIN_CONFIG_DIR for the whole suite, adds bash -n on install-local.sh; only test-acp-watch-contract.py touches HOME and sets its own env.
4. item: Portability contract tests — installer matrix coverage (named runtime, `--skills-dir`,
   platform subset, link/copy, repeated install/update/uninstall, spaces in paths, foreign path
   refusal, user-edited copy preservation, two coexisting installations with shared-link rules) plus
   neutral validator checks; update `test-generated-skills.py` for the new absolute-path invocation
   examples; wire into `validate.sh`.
   status: done
   dispatched: self (inline) — tests/contract/test-installer-runtimes.sh (new), test-generated-skills.py, test-lifecycle-contract.py, test-acp-watch-contract.py, validate.sh wiring
   result: PASS — test-installer-runtimes.sh PASS: named runtimes (claude-code/cursor/devin dirs), --skills-dir with spaces, arg validation (unknown runtime/method, mutual exclusivity, relative path), copy identical content + exec bits + receipt outside payload, no-op reinstall, update, edited-copy refuse replace+remove, clean uninstall incl. receipts dir, copy↔link switching, foreign dir refused despite .generated marker, coexistence + scoped uninstall + shared/explicit/foreign bin-links; validator accept/reject cases + all 7 generated Skills pass; test-acp-watch-contract.py updated to new shared-link contract (uninstall preserves, --bin-links removes) 13/13 PASS; both installer tests wired into validate.sh.
5. item: Runtime-neutral docs — README (runtime-neutral intro, install matrix, consuming-runtime vs
   target-platform dimensions, actual environmental requirements, authenticated-tested vs
   standard-format compatibility distinction), docs/architecture.md, docs/api.md,
   docs/conventions.md, docs/README.md, managed AGENTS.md facts, CHANGELOG entry; preserve #34 model
   tiers/Fast and #33 observation wording already on main; no stale defaults.
   status: done
   dispatched: self (inline) — README.md, docs/architecture.md, docs/api.md, AGENTS.md, CHANGELOG.md
   result: PASS — README now describes runtime-neutral Agent Skills with consuming-runtime vs target-platform terminology, full install matrix (--runtime/--skills-dir/--method/--bin-links), per-runtime discovery vs explicit SKILL.md loading, and neutral validation; architecture.md product boundary + installer paragraph updated; api.md installer contract documented; AGENTS.md purpose/install line neutralized; CHANGELOG Unreleased entry added; #34 model table and #33 stop-report wording untouched.
6. item: Offline validation battery — `./scripts/render-skills.py --check` PASS and full
   `./scripts/validate.sh` PASS both in normal env and under controlled non-Codex HOME; grok-golden
   byte-identical.
   status: done
   dispatched: self (inline) — ./scripts/render-skills.py --check; ./scripts/validate.sh
   result: PASS — render-skills --check: all 7 Skills fresh; validate.sh VALIDATE_RC=0 (neutral
   validator on all 7, installer migration + runtimes shell suites, all Python contract suites,
   generated Skill acceptance); suite ran under mktemp HOME with CODEX_HOME/CLAUDE_CONFIG_DIR/
   DEVIN_CONFIG_DIR unset; git diff -- templates/grok-golden empty.
7. item: Live end-to-end — (a) non-Codex controller (Devin, this session) explicitly loads a
   `--method copy` Skill installed to a `--skills-dir` with spaces, invokes its absolute script path
   on a scratch repo: ACP start, send, read reply, exact stop; (b) Codex controller loads the same
   portable Skill and invokes it on a scratch repo via ACP start/send/read/stop; record native
   discovery vs explicit loading separately; no PTY/Claude/Cloud auth legs; stop only exact owned
   test sessions, retain evidence; report limitations honestly where a leg is unavailable.
   status: done
   dispatched: self (inline) — /tmp/kpr36-live fixtures (paths with spaces), scratch repos under /tmp/kpr36-live
   result: PASS — Leg A (Devin controller→Codex ACP target): read
   "/tmp/kpr36-live/installed skills/codex-kaola-project-runner/SKILL.md"; preflight
   login_required:false transport:acp; start kpr36-devin-codex state:ready acp_session
   01a09ba3-5f96-7cb2-8b7a-247911a402c7 configured gpt-5.6-luna/low/agent-full-access; send
   final_text "KPR36_DEVIN_OK" end_turn completed; capture event log readable; stop stopped:true
   residual_pids:[] exit 0; status state:stopped. Evidence note: final status session_meta reports
   model currentValue gpt-5.6-sol / mode currentModeId agent while start configured_options applied
   luna/full-access — recorded as observation evidence per contract, not a blocker (#33 domain).
   Leg B (Codex consuming runtime→Grok ACP target): start kpr36-codex-ctrl via copied Skill
   state:ready; send orchestration instruction; Codex read the copied grok SKILL.md (tool_calls
   read:1) and invoked its absolute runtime-tmux.sh (execute:6) for preflight/start/send/capture/
   stop/status on kpr36-grok-target @ /tmp/kpr36-live/scratch-grok; Codex observed reply
   "KPR36_CODEX_OK", final state stopped, repo clean; controller stopped residual_pids:[]. Native
   discovery evidence: Codex session availableCommands listed $grok-kaola-project-runner et al.
   from ~/.codex/skills while the test used explicit SKILL.md loading from the spaced copy dir.
   Post-run: tmux ls shows only pre-existing foreign sessions kaola-9362e3d5 + kaola-fb9f6f4c;
   pgrep kpr36: none; unrelated bundle-28 test procs (issue6-* sessions) left untouched. No PTY or
   Claude-auth legs run per scope.
8. item: Commit candidate on `workflow/issue-36`, push, open reviewable PR, hand back exact
   SHA/PR/commands/evidence/Workflow state; stop before merge for supervising Codex review.
   status: done
   dispatched: self (inline) — git commit/push on workflow/issue-36; gh api for PR body (gh pr edit
   blocked by missing read:project token scope)
   result: PASS — commit bcbd6d8 (51 files, +1185/-304) pushed to origin/workflow/issue-36;
   PR https://github.com/KaolaBrother/kaola-project-runner/pull/38 OPEN, body updated via
   `gh api -X PATCH` to "Closes #36". Candidate stopped before merge for supervising Codex
   review; final integrated validation deferred to accepted #33/#34 per issue scope.
