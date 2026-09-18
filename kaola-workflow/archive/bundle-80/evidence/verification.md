# Issue #80 verification — Errno 66 on repo/.git in test-issue-49-grok-bot-host.py teardown

Run: `bundle-80`, branch `workflow/bundle-80`, worktree `.kw/worktrees/bundle-80`.
Base: `f6cbe27` (main at claim). Frozen candidate: **`c4caf37`** (= `git show` output +
`git diff f6cbe27..c4caf37` in `candidate-diff.txt`; +8/−0 lines, one file), ACCEPTed by the
outer review, plus finalization CHANGELOG docking `93310eb`. After the parallel #79 sink,
the branch was rebased onto `b40813f`: test fix **`0745763`**, changelog **`08bacd1`**
(identical content; CHANGELOG Unreleased merge kept both entries). Post-rebase verification
on `08bacd1`: standalone suite OK (`Ran 43 tests`), `./scripts/validate.sh` exit 0
(`validate-final.log` is the post-rebase log; `final-validation.md` hash `1463c646…`).
Host: macOS 27.0, Python 3.14.3, git 2.54.0 (Homebrew) — same toolchain the issue measured on.

## 1. Reproduction at base

`TMPDIR=<fresh> python3 tests/contract/test-issue-49-grok-bot-host.py`, worktree at base,
fresh TMPDIR each run — failed 2/2 exactly as the issue measured:

    ERROR: Issue49PinModel.test_content_stage_is_not_saveable_and_require_pinned_refuses_it
    OSError: [Errno 66] Directory not empty: '<tmp>/repo/.git'
    tempfile._rmtree -> shutil._rmtree_safe_fd_step -> os.rmdir
    Ran 43 tests / FAILED (errors=1)   — every assertion itself passed.

## 2. Forensics — what wrote into .git

Leftover `<tmp>/repo/.git` after the failed rmtree contained only:

    info/refs          -> "fa3bf45…\trefs/heads/master"   (update-server-info output)
    objects/info/packs -> empty file                      (update-server-info output)

`GIT_TRACE2_EVENT` on a reproducing run captured the full causal chain (all times
2026-09-18T16:18:1xZ, sid chain P00016de7→df4→df7):

    git -C <repo> commit -q -m content                    10.806–10.929
      child_start  git maintenance run --auto --quiet --detach   10.922
    git maintenance run --auto --quiet --detach           10.926–11.369   (detaches, keeps running)
      child_start  git repack -d -l --cruft --write-midx  10.928
    git repack -d -l --cruft --quiet --write-midx         10.933–11.368
      pack-objects … --all --indexed-objects             10.934–11.258   wrote pack, 1345 objects
      pack-objects … --cruft                             11.258–11.304
      git multi-pack-index write --stdin-packs
          --preferred-pack=pack-1b57…pack
          --refs-snapshot=<repo>/.git/objects/bitmap-ref-tips_*  11.304–11.310
      update-server-info -> info/refs + objects/info/packs       ~11.36

So: `git commit` returns at 10.929 having spawned a **detached** maintenance child; that child
runs `repack --write-midx` + `update-server-info` inside `<tmp>/repo/.git` until ~11.37 — while the
test finishes its ~0.45 s of post-commit work (measured: render --write 82 ms, --check 89 ms,
verify 43 ms) and `TemporaryDirectory` teardown `rmtree`s the same tree. `rmdir(.git)` meets
recreated entries → Errno 66. On this host the windows overlap deterministically → 5/5 in the
issue, 2/2 here. The failing test is simply the shortest post-commit consumer; other `git_repo`
tests keep git working longer and usually win the race.

Same spawn source, second path: `LocatorFixture`'s `git push` → `git-receive-pack` on
`origin.git` → detached maintenance there too (2 spawns seen in the fix-run trace).

## 3. Knob measurements (why this fix, not the issue's guess)

Measured on probe repos with `GIT_TRACE=1` counting `maintenance run` spawns:

| gate | commit spawn | push→receive-pack spawn |
|---|---|---|
| none (control) | yes | yes |
| `-c gc.auto=0` | **yes** | — |
| `GIT_AUTO_MAINTENANCE=0` env | **yes** | — |
| `maintenance.auto=false` | **no** | **yes** (env is stripped: `run_command: unset GIT_CONFIG_COUNT GIT_PREFIX; git-receive-pack …`) |
| `receive.autogc=false` in the *bare repo's own* config | n/a | **no** |

`git push` sanitizes config-env for the remote child — the pre-receive hook sees orphaned
`GIT_CONFIG_KEY_0/VALUE_0` without `GIT_CONFIG_COUNT`, so env cannot gate receive-pack; the bare
fixture repo's own config must. `kaola-locate.py` runs only read-only git calls (rev-parse,
remote get-url, status) — no spawn path there.

## 4. The fix (candidate `c4caf37`, +8/−0 lines, `tests/contract/test-issue-49-grok-bot-host.py` only)

1. `git()` helper env gains `GIT_CONFIG_COUNT=1 / KEY_0=maintenance.auto / VALUE_0=false` —
   covers every fixture `commit`/`merge`/`rebase` (direct children see env config).
2. `LocatorFixture` bare `origin.git` gets `git config receive.autogc false` — covers the
   `git-receive-pack` spawn env cannot reach.

No `ignore_cleanup_errors`, no sleeps/timeouts, no assertion or test-logic changes
(the diff is purely additive: two config sources + comments).

## 5. Candidate verification (all on `c4caf37`)

- Standalone: `TMPDIR=<fresh> python3 tests/contract/test-issue-49-grok-bot-host.py` —
  **5/5 runs OK, 43 tests each** (one under `GIT_TRACE2_EVENT`: **0** maintenance spawns).
- `./scripts/render-skills.py --check` — PASS (budgets OK).
- `./scripts/validate.sh` — **exit 0**, zero `FAILED` lines; the Issue #80 suite logged
  `Ran 43 tests in 21.482s` inside lane B and every suite ordered after it ran and passed.
  Full log: `validate-final.log`. No interference from the parallel #79 run was observed
  during this window (its `validate.sh` was not executing; its leftover acp-holder orphans
  live under a different TMPDIR and were left untouched).
- Assertions unweakened: `git diff f6cbe27..c4caf37` touches only `git()` env and the
  LocatorFixture bare-repo config; unittest still reports `Ran 43 tests`.

## 6. Explicitly not done

- No `ignore_cleanup_errors`, no added waits — the real writer was removed, not the check.
- `run_suite_lane`'s abort-on-first-failure (which hid downstream suites) is a separate,
  pre-existing design question noted in the issue's non-binding remedy — out of this run's
  file scope, flagged for the outer review.
- No finalize/archive/sink/issue-close — awaiting outer ACCEPT.
