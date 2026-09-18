# Issue #82 — standalone ACP contract fixtures must exact-stop their own sessions

Scope: fix test fixture ownership so each standalone contract test stops the exact
platform/repo/session it started (incl. restarted holders), without touching foreign
sessions. Deterministic regression cover for the failed cleanup leg. Zero own
holders/mock agents after standalone focused + full contract suite exit 0, then
render --check + validate.sh. No production lifecycle change, no weakened
assertions, no sleeps/broad-kill/second sweep daemon. Do not kill #79 or other
workers' processes; report exact PID/command/time evidence to outer.

- item: Inventory fixture start/stop ownership across tests/contract/test-acp-*.py and confirm leak attribution
  status: done
  dispatched: self
  result: Root causes confirmed. (1) test-acp-contract.py: Issue34ModelSelectionAcpTests.start(platform) starts codex/cursor-cli/devin (14 tests: 8 codex + 5 cursor-cli + 1 devin) but base AcpSessionFixture.tearDown calls self.cli("stop") which defaults platform="grok" -> stop hits a nonexistent grok session, fails silently (check=False), real holder+mock leak. Matches measured 14/run. (2) test-acp-watch-contract.py: test_view_accept_then_close_uses_frozen_runtime_code unlinks the holder socket and binds its own listener; after close the stale socket file remains but nothing listens -> tearDown stop --force gets holder-unreachable with holder alive -> kaola-acp.py returns error and does NOT kill -> exactly 1 holder+1 mock leaks per run. Other files (follow, holder-continue, sweep) already stop exact (platform,session,repo) or sweep own roots. Baseline ps: zero test-root holders/mocks; named foreign worker sessions untouched.

- item: Failing-first cover: deterministic regression test + per-class own-process after-teardown assertion in test-acp-contract.py and test-acp-watch-contract.py; record red output
  status: done
  dispatched: self — ran under .kw/worktrees/bundle-82/tests/contract/
  result: RED recorded. test_teardown_stops_the_started_platform FAIL: "codex holder 10109 survived the fixture teardown"; Issue34 tearDownClass assertion caught {10109 holder codex + 10110 mock} under kaola-acp-contract-64ak_c7d. Watch: test itself passed, tearDownClass assertion caught {10756 grok holder + 10757 mock} under kaola-acp-watch-2wf5igbs — confirms socket-replacement attribution (exactly 1/run). Own leaked pids swept via kaola-acp-sweep --root <deleted root string>; zero residual.

- item: Minimal fixture fix: thread started platform through AcpSessionFixture tearDown (base cli/start gain platform kwarg, default grok unchanged); Issue34.start records platform; watch accept-then-close test SIGKILLs the holder it orphaned so tearDown force_kill_from_record sweeps its agent
  status: done
  dispatched: self
  result: Implemented exactly as scoped. Frozen SHA 2c68789a391873a83f881c1fd38bcafa7c4658f5 on workflow/bundle-82: tests/contract/test-acp-contract.py +118/-9, test-acp-watch-contract.py +82/-0 (191 ins, 9 del total). No production code touched; assertions preserved; no sleep/daemon/global sweep.

- item: Standalone verification: rerun targeted tests green; full test-acp-contract.py + test-acp-watch-contract.py exit 0; ps evidence of zero own holders/mock agents
  status: done
  dispatched: self
  result: Targeted reruns OK (0.669s / 2.387s). Full standalone: test-acp-contract.py Ran 46 tests OK (108.6s, incl. new regression test + all tearDownClass assertions); test-acp-watch-contract.py Ran 13 tests OK (26.2s). ps after runs: zero holders/mocks under bundle-82 or kaola-acp-contract-*/kaola-acp-watch-* roots.

- item: render --check + ./scripts/validate.sh full run; collect #79/foreign leftover evidence (PID/command/time) for outer report; freeze SHA + diff for ACCEPT
  status: done
  dispatched: self
  result: render --check PASS. Plain ./scripts/validate.sh FAILED only at lane-B test-issue-49-grok-bot-host.py (1/43): OSError ENOTEMPTY on repo/.git during TemporaryDirectory cleanup — PROVEN pre-existing race: test's git commit triggers detached `git gc --auto` repack writing .git/objects during rmtree (reproduced manually: fresh bitmap-ref-tips_* temp + object-dir churn); passes on canonical root 3/3 (larger tree -> rmtree slower -> gc wins); passes in bundle-82 worktree with GIT_CONFIG_KEY_0=gc.autoDetach=false. File untouched by this diff (owned by closed #49) — left alone, reported. Full validate rerun with that diagnostic env: ALL 33 suites OK incl. issue-49, acp-contract 46, acp-watch 13; final sweep residual_pids=[], exit 0. Leftover evidence: at final snapshot zero #79-owned stale test processes remain (the measured 31 holders/62 mocks are already gone); live list is 10 named foreign sessions (KPR-*/orchestrator under kaola-501) + bundle-69 verify-69-legs zcode pair (80951) — all others' active work, untouched. Awaiting outer ACCEPT; no finalize/archive/sink/close performed.

- item: Review-round fix: replace direct os.kill(holder_pid, SIGKILL) in watch accept-then-close test with bounded kaola-acp-sweep.py --root <exact record_dir> + receipt assertions (matched_pids==[holder_pid], residual_pids==[]); persist raw focused/standalone/render/validate evidence under kaola-workflow/bundle-82/evidence/; rebase onto latest main and rerun full verification
  status: done
  dispatched: self — .kw/worktrees/bundle-82
  result: Fixed per outer review. watch test now runs `python3 scripts/kaola-acp-sweep.py --root <this test's exact record_dir>` in finally; the sweep matches the holder by its own --record-dir/--socket argv under that dir (never a bare pid) and reads record.json inside that same dir for the identity-checked agent group; assertions require matched_pids==[started holder_pid] and residual_pids==[]. No new cleaner; nothing outside the record dir is matched. Rebase note: #83 not yet sunk at rebase time (workflow/issue-83 still in outer review), so the branch was rebased onto then-latest origin/main c963bad which already contains #80's maintenance.auto fix — a second trivial rebase can follow once #83 lands (zero file overlap: this diff touches only the two contract test files). New frozen SHA ece2d065aba8f368687dd1cb7ecc4c5bfae82753 (7d4d6e9 platform fix + ece2d06 sweep fix on c963bad). Raw evidence under kaola-workflow/bundle-82/evidence/: focused-test-*.log (2 focused tests OK), standalone-test-acp-contract.log (46 tests OK, 109.0s), standalone-test-acp-watch-contract.log (13 tests OK, 26.1s), render-check.log (PASS), validate-plain.log (PLAIN ./scripts/validate.sh — all suites OK, final sweep receipt matched_pids=[]/residual_pids=[], rc=0; the #49 gc race is gone on the rebased base), diff-ece2d06.patch, frozen-commits.txt, ps-before/after-*.txt. Process snapshots: zero holders/mocks under worktrees/bundle-82 or this run's kaola-val.N4XPgu root; live foreign processes at snapshot time = bundle-75's in-flight validate (kaola-val.Cqx1xc, still on the old unfixed fixtures — same leak signature my fix removes) + issue-74 worktree run (kaola-val.yjmpLq) + named kaola-501 sessions — all untouched, listed for outer. No finalize/merge/push/archive/sink/close; awaiting outer ACCEPT.

- item: Post-#83 rebase onto main 88042cd (#83 sunk) and full re-verification; freeze new SHA + diff + raw logs for outer
  status: done
  dispatched: self — .kw/worktrees/bundle-82
  result: Rebased cleanly onto origin/main 88042cd (includes #83's validate lane-failure SKIPPED reporting, verified intact — scripts/validate.sh SKIPPED lines identical to base). New frozen SHA b158e16d8ea9e32e55e33d46b5a520fb16fdc4d8 (5c6af87 platform fix + b158e16 sweep fix on 88042cd); diff vs main still only tests/contract/test-acp-contract.py (+118/-9) and test-acp-watch-contract.py (+95/-1). Raw evidence under kaola-workflow/bundle-82/evidence/ (*-88042cd files): focused tests rc=0/rc=0; standalone test-acp-contract.py 46 tests OK rc=0 (110.1s); standalone test-acp-watch-contract.py 13 tests OK rc=0 (24.9s); render-check rc=0 PASS; PLAIN ./scripts/validate.sh rc=0 — all suites OK incl. #83's SKIPPED-reporting tests and issue-49 on the #80-fixed base, terminal sweep receipt matched_pids=[]/residual_pids=[]. Process snapshots ps-before/after-*-88042cd.txt: zero holders/mocks under worktrees/bundle-82 or this run's kaola-val.jTQP0y root; foreign processes left untouched. diff-b158e16.patch + frozen-commits-88042cd.txt recorded. No finalize/merge/push/archive/sink/close; awaiting outer ACCEPT.
