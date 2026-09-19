# Finalization summary — bundle-94 (Issue #94)

Branch `workflow/bundle-94`, sink `merge`, one issue: **#94** — "ZCode Host：用原生
Skill invocation 替代 AGENTS.md Compact 恢复载体".

Candidate: `2fb5419` (run records + evidence) on production code `7714d98`,
rebased onto `main` `e9c427e`. Outer review ACCEPTed `94bbb02`; the two commits
above it add only run records under `kaola-workflow/bundle-94/`, no production
bytes.

## Delivered

The ZCode Project Runner Host now enters through ZCode's own native
`/kaola-project-runner` Skill invocation, as the prompt's own first line, on
every turn-opening prompt: first handoff, resume/attach update, worker-event
notification, and the round after any compaction. The Issue #75 carrier is
gone — no durable `AGENTS.md` block is planted in consuming projects, and no
role filtering, compaction detection, or manual `SKILL.md` reread remains.

- The holder owns exactly one thing: `HOST_SKILL_ENTRY` is the
  `kaola-host-notify/1` envelope's own first line. The Host's
  `heartbeat-prompt.json` `body` never carries the entry line or Skill text.
- No identity marker and no new recovery state. The outer review's earlier
  `host_entry_session` marker and its implicit prepend were removed entirely:
  `op_steer_interrupt` resends the caller's text byte-verbatim on every
  session. Native busy `steer` is the supported Host mid-turn path; the
  composite interrupt is explicitly NOT a Host recovery entry, and a caller
  who wants one supplies `/kaola-project-runner` itself.
- Kaola-Delegator starts its ZCode Host through the same entry without copying
  the Project Runner body.
- Discovery guidance now matches the shipped runtime: the four workspace/user
  `.zcode`/`.agents` roots are DEFAULTS, and configured `skills.roots` and
  `plugins.dirs` roots are scanned too.

## Files Changed

37 files vs `main`, +1279 / −755. Authoritative surfaces:
`templates/orchestrator/` (`SKILL.md.tmpl`, `host-startup.md.tmpl`,
`zcode-host-dispatch.md.tmpl`, `heartbeat-skeleton.txt`,
`zcode-compact-recovery.md` deleted → `zcode-native-skill-entry.md` added),
`templates/kaola-delegator/references/handoff.md.tmpl`,
`scripts/kaola-acp-holder.py`, `scripts/install-local.sh`,
`scripts/validate.sh`, docs (`README.md`, `docs/zcode-host.md`, `docs/api.md`,
`docs/architecture.md`, `CHANGELOG.md`), tests, and the regenerated `skills/`
packages. `skills/` and `hosts/grok-bot/` were never hand-edited.

## Test Coverage

- `tests/contract/test-issue-94-zcode-native-skill-entry.py` — new, 30 tests.
  Pins the entry line on every turn-opening prompt type, the removal of the
  AGENTS block / role filter / manual read, heartbeat-body separation, the
  install precondition, `skills.roots` + `extraRoots`, the absence of the
  marker machinery, and the "NOT a Host entry" statement across reference,
  startup, handoff, docs and holder.
- `tests/contract/test-issue-75-zcode-compact-recovery.py` — deleted; the
  behaviour it pinned no longer exists.
- `tests/contract/test-issue-75-codex-compact-hook.py` — retained, surface
  renamed `ZcodeCompactCarrierSurface` → `ZcodeNativeEntrySurface`, 37 tests.
  Codex keeps its verified `SessionStart(compact)` hook.
- `tests/contract/test-zcode-heartbeat-contract.py` — 16/16, 324 checks,
  including a real cancel-and-resend e2e proving the resend is verbatim for a
  Host-shaped session, for caller-supplied entry text, across stop→resume, and
  for an ordinary worker.
- Unchanged suites re-run green, including `test-issue-92-permission-wake-recovery.py`
  (17/17), which shares `scripts/kaola-acp-holder.py` with this change.

## Validation

- `verdict: pass`, command
  `env -u KAOLA_PROJECT_RUNNER_CANONICAL_REPO ./scripts/validate.sh`,
  `VALIDATE_EXIT=0`, sweep `residual_pids=[]`.
  `validated_candidate_hash: cf41617c84c5d5d1f9bfff35f87a4912621c3d17f83e4ea6ab425f61554b8b76`.
  Receipt: `.cache/final-validation.md`.
- `render-skills.py --write` was a no-op after the rebase; `--check` PASS
  (budgets OK). `git diff --check` clean.
- **Why the command drops one variable.** The first run of the same suite
  failed one Kimi ACP test because this Agent's shell exports
  `KAOLA_PROJECT_RUNNER_CANONICAL_REPO`, the test inherits `os.environ`, and
  the Issue #73 guard refuses the start against the test's own throwaway repo.
  Reproduced identically on unmodified `main` `e9c427e`. All three raw captures
  are archived under `evidence/validate/`. This relaxes nothing in production:
  a real Project Runner command must still carry the KPR canonical-root
  binding. Filed as **#96** (P3).
- Live acceptance, real ZCode 3.12.3 + real GLM over ACP, adapter 0.3.3
  (receipts under `evidence/zcode-acp-live/`): `/kaola-project-runner`
  produced a native `Skill` `tool_call` pending → in_progress → completed and
  returned a marker that exists only in the Skill body; a real manual
  `/compact` then produced a NEW `Skill` tool call; the dollar form followed by
  trailing text invoked the Skill and processed the text; exact stop
  `agent_exit_code=0`, `residual_pids=[]`.
- Bounded auto-compaction leg: scratch-HOME ZCode with a mock provider at a
  declared 8192 context window produced real `trigger:"auto"` compactions, and
  post-compact requests still carried the skill metadata on the wire.
- **Not executed / not claimed**, and stated as such in the shipped docs: real
  GLM automatic compaction was never forced; the mock provider proves discovery
  and wire metadata, never model behaviour; ACP has no compact-specific event.
- **Fresh-install byte identity** was satisfied by construction rather than by
  a separate install step: the live legs ran the repository's own generated
  package (`skills/zcode-kaola-project-runner/`), whose adapter SHA-256 is
  recorded in the matrix, and the installer migration/runtimes acceptances pass
  in the recorded validate run. The separately-tested user-installed 0.3.0
  adapter is recorded as FAILing against ZCode 3.12.3 — that is a stale local
  install, not a candidate defect.

## Changed Paths

Reported by the finalize transaction (source-scoped; documentation files are
not listed by that scope):

```
scripts/install-local.sh
scripts/kaola-acp-holder.py
scripts/validate.sh
skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
skills/kaola-delegator/references/handoff.md
skills/kaola-project-runner/SKILL.md
skills/kaola-project-runner/references/heartbeat-skeleton.md
skills/kaola-project-runner/references/host-startup.md
skills/kaola-project-runner/references/zcode-compact-recovery.md
skills/kaola-project-runner/references/zcode-host-dispatch.md
skills/kaola-project-runner/references/zcode-native-skill-entry.md
skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
templates/kaola-delegator/references/handoff.md.tmpl
templates/orchestrator/SKILL.md.tmpl
templates/orchestrator/references/heartbeat-skeleton.txt
templates/orchestrator/references/host-startup.md.tmpl
templates/orchestrator/references/zcode-compact-recovery.md
templates/orchestrator/references/zcode-host-dispatch.md.tmpl
templates/orchestrator/references/zcode-native-skill-entry.md
tests/contract/test-installer-runtimes.sh
tests/contract/test-issue-74-kaola-delegator.py
tests/contract/test-issue-75-codex-compact-hook.py
tests/contract/test-issue-75-zcode-compact-recovery.py
tests/contract/test-issue-94-zcode-native-skill-entry.py
tests/contract/test-zcode-heartbeat-contract.py
```

`dirty_paths: []`.

## Documentation Docking

`DOCKED` — see `.cache/doc-docking.md`. README, CHANGELOG, `docs/zcode-host.md`,
`docs/api.md`, `docs/architecture.md` and the `install-local.sh --help` text were
all corrected; `docs/codex-host.md` and `docs/grok-bot-host.md` are no-impact.
The Issue #92 documentation merged from `main` was preserved verbatim.

## Evidence archived with this run

`evidence/NATIVE-SKILL-LIVE-MATRIX.md` (verbatim, all three addenda),
`evidence/zcode-acp-live/` (ten ACP receipts), `evidence/skill-discovery-wire.md`
(distilled wire extract), `evidence/validate/` (three raw validation captures),
and `evidence/README.md`, which records provenance, the credential scan, and the
run's real gaps — including that mission 6 leg (a), session
`zcode-kaola-kpr-i94-entry-a`, left no receipt files on disk. That gap is
recorded, not papered over.

## Follow-Up Items

- **#96** (P3, filed this finalization) — contract suites inherit
  `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` and are refused against their own
  throwaway repos. Confirmed to exist with a non-empty body.
- A correction comment was posted on #94 before closure: the issue body names
  the workspace `.zcode/skills` as *the* discovery form, and this run proved it
  is one of four defaults plus configured roots.
- No deferred work, no partial mission, no unresolved conflict. The rebase
  content conflicts were resolved by keeping both sides and are recorded in
  mission 11.

## Readiness

READY — all eleven missions done, validation pass recorded, documentation
docked, follow-up filed, issue correction posted. Proceeding to closure,
archive, and merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-94/.cache/doc-docking.md
- kaola-workflow/archive/bundle-94/.cache/final-validation.md
- kaola-workflow/archive/bundle-94/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-94/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-94/evidence/NATIVE-SKILL-LIVE-MATRIX.md
- kaola-workflow/archive/bundle-94/evidence/README.md
- kaola-workflow/archive/bundle-94/evidence/skill-discovery-wire.md
- kaola-workflow/archive/bundle-94/evidence/validate/README.md
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/capture-after-e.json
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/capture-dollar-f.json
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/capture-project-after-compact-e.json
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/send-after-e.json
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/send-before-e.json
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/send-compact-e.json
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/send-dollar-f.json
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/send-project-after-compact-e.json
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/start-e.json
- kaola-workflow/archive/bundle-94/evidence/zcode-acp-live/stop-e.json
- kaola-workflow/archive/bundle-94/finalization-summary.md
- kaola-workflow/archive/bundle-94/mission-list.md
- kaola-workflow/archive/bundle-94/workflow-state.md
