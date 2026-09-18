# Issue #71 delivery — waiting for outer ACCEPT

Do not finalize / merge / close / push mainline until ACCEPT.

## Frozen candidate

- SHA: `c19cdde4113792bfd8ac68881c740dd1d37296f8`
- Branch: `workflow/issue-71` (not pushed)
- Worktree: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-71`
- Parent / origin/main: `b229f8419e404e9ba65353e07c87d0a447679c0e`
- Subject: `test: equal-length #49 host-invariance probe (Issue #71)`

## Actual diff (vs origin/main)

4 files, +92/−10. No template, generated Skill, host bundle, or `templates/budgets.json` edit.

- `tests/contract/test-issue-49-grok-bot-host.py`
- `docs/architecture.md`
- `docs/conventions.md`
- `CHANGELOG.md`

Raw patch: `diff-vs-main.patch`. Commit body: `commit.txt`.

`main_skill_bytes` remains **17408**. Rendered main Skill remains **17337 B** (71 B headroom against the declared ceiling, was 12 B against the hidden 17349).

## Baseline reproduction (pre-fix, temp copy, HEAD untouched)

From `baseline-repro.txt` on `b229f84`:

- declared 17408; current main Skill 17337; old append probe 59 B; hidden ceiling 17349 (12 B slack)
- pad orchestrator template to **17405 B**: `render --write` 0, `--check` 0 (`budgets OK`)
- append `"\n\nCanonical policy sentence added for the invariance test.\n"` (59 B): `--write`/`--check` 1
  - `budget: kaola-project-runner/SKILL.md is 17464 B > 17408 B (main_skill_bytes)`

This is the #68 trap: `--check` is green at 17405, the probe is red.

## After the fix

From `postfix-near-budget.txt` and `test_invariance_probe_does_not_spend_declared_main_skill_budget` on the same 17405 shape:

- equal-length canonical substitutions: size stays **17405**, `--write` 0, `--check` 0, marker `platform InvTst and has` present, host products byte-identical
- old 59 B append on that tree still fails: 17464 > 17408
- pad to declared **17408**, equal-length edit: `--write`/`--check` 0; one extra byte: `--write` 1, product not written

True invariant still fails:

- host-template append changes host products (positive control in the pin/host test)
- `RendererEnforcesBudgets` still OK
- over-budget still names `main_skill_bytes`

## Exact tests on the frozen SHA

| Command | Result |
|---|---|
| `python3 tests/contract/test-issue-49-grok-bot-host.py Issue49BridgeInvariance -v` at `c19cdde` | 3/3 OK in 3.494s |
| `python3 tests/contract/test-issue-49-grok-bot-host.py -v` (pre-commit, same bytes) | 43/43 OK in 27.620s |
| `python3 tests/contract/test-progressive-disclosure.py RendererEnforcesBudgets -v` | 1/1 OK |
| `./scripts/render-skills.py --check` at `c19cdde` | PASS, budgets OK |
| `./scripts/validate.sh` (same bytes as `c19cdde`) | exit 0 (second run, 181.52s). First run exit 1 on unrelated `test-issue-51-runner-integration.py`; isolated re-run of that suite 6/6, 119 checks |

Raw logs: `render-check-at-c19cdde.txt`, `invariance-at-c19cdde.txt`, `test-issue-49.txt`, `validate.sh-2.log`, `test-issue-51-isolated.txt`.

## Not done (by authorization)

- no finalize / archive / sink / push / issue close
- no `templates/budgets.json` number change
- no `templates/orchestrator/SKILL.md.tmpl` body (Issue #72)
- no extra implementer/reviewer agents
- no touch of `issue-70`, `issue-72`, `issue-67`, accepted checkouts, or credentials
