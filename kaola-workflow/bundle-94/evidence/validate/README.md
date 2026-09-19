# Validation runs on the rebased candidate

Three logs, in the order they happened. All three are raw captures; nothing
here is edited except this index.

## 1. `validate-rebased-env-bound-fail.log` — the first run, FAILED

```bash
./scripts/validate.sh
```

`VALIDATE_EXIT=1`. One error:
`Issue22KimiDefaultYoloAcpTests.test_public_default_start_sets_mode_yolo`,
`FileNotFoundError` on `mock-events.jsonl`.

The cause is the controlling Agent's own shell, not the candidate. This
session exports `KAOLA_PROJECT_RUNNER_CANONICAL_REPO=<the KPR checkout>`.
The test builds its subprocess environment with `dict(os.environ)`, so the
binding is inherited, and the Issue #73 guard in `scripts/kaola-tmux.sh`
refuses the start against the test's throwaway repo with
`result: refused, reason: canonical-root-mismatch` — before the mock ACP
agent ever runs, which is why its log file never exists. The start receipt
carries `reason`, not `error`, so the test's `assertIsNone(receipt.get("error"))`
passes and the failure surfaces one line later.

## 2. `main-e9c427e-same-failure-repro.log` — same failure on unmodified main

Captured in a throwaway detached worktree at `main` `e9c427e` (removed
straight afterwards), running only that one test class twice:

```bash
python3 tests/contract/test-acp-contract.py Issue22KimiDefaultYoloAcpTests
# -> FAILED, identical FileNotFoundError

env -u KAOLA_PROJECT_RUNNER_CANONICAL_REPO \
  python3 tests/contract/test-acp-contract.py Issue22KimiDefaultYoloAcpTests
# -> OK
```

So the failure exists on `main` without any Issue #94 change, and one
variable decides it.

## 3. `validate-rebased-pass.log` — the reported run, PASSED

```bash
env -u KAOLA_PROJECT_RUNNER_CANONICAL_REPO ./scripts/validate.sh
```

`VALIDATE_EXIT=0`, sweep `residual_pids=[]`. 33 unittest OK blocks;
issue-94 30 tests, zcode-heartbeat 16/16 (324 checks), issue-92 17/17,
issue-76 5, issue-74 156 assertions, issue-86 46 checks, issue-90 19,
installer migration/runtimes PASS, generated Skill acceptance PASS,
grok-bot-verify PASS.

## The rule this does NOT relax

Dropping `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` is correct **only** for the
test harness, because these contract tests start sessions against isolated
throwaway repositories that are deliberately not the canonical root. A
production Project Runner command is the opposite case: it MUST carry the
KPR canonical-root binding, and the Issue #73 refusal seen above is that
guard working as designed. Nothing in this run changes that guard, its
wording, or its scope.
