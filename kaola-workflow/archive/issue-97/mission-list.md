# Issue #97 — Codex user-level compact-recovery hook covering the cross-repository Delegator

Goal: `./scripts/install-local.sh --runtime codex` (and the legacy no-flag Codex default) installs one Runner-owned user-level `SessionStart(compact)` entry in `${CODEX_HOME:-~/.codex}/hooks.json` whose short conditional payload makes an outer Codex session that was already using `kaola-delegator` or `kaola-project-runner` re-read that installed Skill after a real compaction and continue from existing records, from any repository, without a project-level hook; ordinary sessions do nothing. Merge-safe by owned id, idempotent, coexists with the Kaola Workflow user hook and legacy project-level entries (no double injection for a bound Host), `--skills-dir` never installs it. User instruction (2026-09-19): no follow-up issues — fix everything found here; after close-out cut a minor release (v0.5.0).

## 1
item: Production change — `scripts/kaola-codex-compact-hook.py` gains `user-install`, `user-uninstall`, `user-status`, `user-emit` (CODEX_HOME target, containment, refusals, no foreign copy/echo, deferral to a bound legacy project entry) plus the short conditional payload `templates/codex-host/compact-recovery-user.md`.
status: done
dispatched: self — worktree .kw/worktrees/issue-97, branch workflow/issue-97; output lands as a commit on that branch
result: commit 4991925 on workflow/issue-97 — user-install/user-uninstall/user-status/user-emit + templates/codex-host/compact-recovery-user.md (1191 B); smoke: merge by id keeps Workflow + user-owned entries, reinstall changed:false, user-emit fires on compact only, silent for a bound legacy project entry, emits for another session; refusals for $HOME, missing dir, malformed JSON, stray --project-root/--session-id/--codex-home; test-issue-75 suite 37/37 OK

## 2
item: Installer wiring — `scripts/install-local.sh` installs/uninstalls the user-level hook for `--runtime codex` and the legacy Codex default when control-plane Skills are in the plan; `--skills-dir`/generic and `--no-orchestrator` never touch it; malformed user hooks.json aborts before any Skill write; `tests/contract/test-installer-runtimes.sh` fixture and cases updated.
status: done
dispatched: self — worktree .kw/worktrees/issue-97; output lands as a commit on workflow/issue-97
result: commit 5788ae3 — install-local.sh plans user-status before any write (malformed refusal aborts), runs user-install/user-uninstall after Skill placement for codex runtime + legacy default when control-plane Skills are in the plan; fixtures updated; test-installer-migration.sh PASS, test-installer-runtimes.sh PASS (new test_user_hook_* cases)

## 3
item: Contract suite `tests/contract/test-issue-97-codex-user-compact-hook.py` (isolated CODEX_HOME with preset Workflow + user hooks: install/reinstall/status/uninstall change only Runner-owned content; foreign preserved; malformed refused before write; user-emit fires for compact only; silent for a bound legacy project entry, emits for unbound/other repo; payload teaches conditional reload + no cwd guessing) registered in `scripts/validate.sh` lanes.
status: done
dispatched: self — tests/contract/test-issue-97-codex-user-compact-hook.py + scripts/validate.sh lane registration, commit on workflow/issue-97
result: commit e6616b0 — tests/contract/test-issue-97-codex-user-compact-hook.py 18/18 OK (sandbox HOME); registered in validate.sh python_suites_all + lane A

## 4
item: Live Codex verification in an isolated CODEX_HOME (auth linked, never read): real `/compact` in two unrelated scratch repos running the outer Delegator scenario → model quotes the user marker and re-reads the installed Delegator; third ordinary session compact → no delegation; single-project Project Runner scenario recovers; legacy project-level entry bound in one repo → exactly one Runner block, none lost; record trust-review and new-session facts. Evidence under `kaola-workflow/issue-97/evidence/codex-user-compact-live/`.
status: done
dispatched: self — isolated CODEX_HOME under the session scratchpad (codex-live/home, auth.json symlinked, never read), scratch repos A–E, tmux-driven real codex sessions; evidence lands in kaola-workflow/issue-97/evidence/codex-user-compact-live/ (main root) and is committed with the docs
result: kaola-workflow/issue-97/evidence/codex-user-compact-live/ (FINDINGS.md + 00–58 captures/rollout extracts) — trust flow captured (3 new → reviewed/trusted; later only the modified foreign hook flagged); C ordinary: both blocks, no action; A/B Delegator in two unrelated repos: real re-read of installed kaola-delegator SKILL.md after compacted, no Host; D Project Runner: real re-read of kaola-project-runner SKILL.md (final self-report cut by operator /quit, turn_aborted); E bound legacy project entry: KW + KPR-COMPACT-RECOVERY only, no user block. Codex self-updated 0.153.4→0.155.1 mid-run (operator Enter landed on the update prompt); zero writes to ~/.codex

## 5
item: Documentation docking — `docs/codex-host.md` (user-level primary, project-level legacy + migration, trust/new-session caveats, no promise of silent activation), `README.md` installer section, `docs/api.md` installer reference, `docs/README.md` index, `CHANGELOG.md` entry; re-render skills if any template changed.
status: done
dispatched: self — docs commits on workflow/issue-97
result: commit 6e8d6eb — docs/codex-host.md rewritten (user-level default, project-level legacy, coexistence/migration, trust caveats, live boundary), README installer paragraph + hook pointer, docs/api.md installer paragraph, docs/README.md index, CHANGELOG Unreleased entry; no Skill template changed so no re-render needed (render-skills --check PASS)

## 6
item: Frozen-candidate review (correctness, trust boundary, test custody) by an independent clean context; findings return for verdict; full `./scripts/validate.sh` PASS on the final candidate.
status: done
dispatched: code-reviewer subagent on frozen candidate 6e8d6eb (handback inline: 0 blocker/major, 2 minor, 3 nit — install failures other than malformed JSON surfaced after Skill writes; asset-path collision traceback; empty --codex-home accepted; emit stray options; weak shell no-backup assertion); all five fixed in c675835 (install_blockers in user-status + installer planning, OSError→receipt, empty home refused, emit silent on stray options, exact sibling-list assertion, --skills-dir-under-CODEX_HOME + abort-before-write cases); validate run 1 on 6e8d6eb PASS (exit 0); validate run 2 on c675835 PASS (exit 0, 0 FAILED/SKIPPED; log archived at kaola-workflow/issue-97/evidence/validate-c675835.log)
result: verdict ACCEPT — candidate c675835 (5 commits on workflow/issue-97); reviewer findings read and fixed, exact-candidate validate PASS, worktree clean; ready for /kaola-workflow-finalize issue-97
