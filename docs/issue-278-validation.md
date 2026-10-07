# Issue #278 review evidence (2026-10-07)

Branch: `workflow/issue-278`. Base: `41b12e85`. Workflow owns the claim,
main-checkout mission ledger and `.kw/worktrees/issue-278` child worktree.
This is a review candidate: no finalization, merge, tag, publication or production install.

## Design and compatibility

One shared path helper supplies fixed per-UID `/tmp` record/socket defaults.
Readers cover known legacy OS roots and roots identified by same-UID live
holder argv in one bounded process-table read. This finds custom legacy TMPDIRs
without a filesystem crawl, registry, daemon, lock or migration of live records.
Host uniqueness covers these roots even when a caller explicitly scopes its
record reads elsewhere. Applied legacy socket paths retain their original
spelling; new holders preserve `socket_path` on every record write.

Locator worker session presence uses ACP records for all ten platforms.
Two live records for one exact identity or an incomplete negative lookup return
`record-root-mismatch`; the failure is not a no-session receipt.

## Environment and pin constraint

macOS; Python 3.12.14; installed Bash 5.3.20 at
`/Users/ylmacstudio/.local/bin/bash`. The system Bash 3.2 invocation exited 2
with the named prerequisite refusal; subsequent runs use the installed Bash.

Direct `./scripts/render-skills.py --write` and `--check` exit 1 at the inherited
v0.9.1 pin-delta gate. The protected pin still names content commit
`3de9f61afbfa31ee99321cd5a9041dd40da43818`; even the unchanged base `41b12e85`
already differs outside the four allowed pin paths (including AGENTS.md and
architecture research documents). No original pin or Grok Bot product was changed.

The isolated QA clone at `.kw/qa-278/candidate` contains these candidate sources,
tests, platforms and templates. Only in that disposable clone, the bridge is
rendered at the existing content stage. This verifies development content and
runtime behavior; it does not establish a new saveable/release pin. Canonical
renderer worker products are copied back to this issue worktree, and every
original-worktree worker byte inventory separately matches `expected_files` /
`check_one` from the canonical renderer functions (pin validation was not changed). No generated product
was edited by hand; protected original Grok Bot products remain unchanged.

## Exact commands

From the issue worktree:

```bash
./scripts/render-skills.py --check
# exit 1: inherited protected v0.9.1 pin-delta constraint
.kw/qa-278/candidate/scripts/render-skills.py --write
.kw/qa-278/candidate/scripts/render-skills.py --check
# both exit 0: content-stage render / complete inventory and budget check
PATH="/Users/ylmacstudio/.local/bin:$PATH" /Users/ylmacstudio/.local/bin/bash \
  .kw/qa-278/candidate/scripts/validate.sh \
  --suite test-issue-278-record-root.py \
  --suite test-issue-273-list-identity.py \
  --suite test-acp-contract.py \
  --suite test-acp-sweep-contract.py \
  --suite test-issue-49-grok-bot-host.py \
  --suite test-issue-74-kaola-delegator.py \
  --suite test-issue-255-lifecycle-state.py \
  --suite test-issue-274-package-closure.py \
  --suite test-issue-266-launch-broker.py \
  --suite test-issue-266-launch-broker-composed.py \
  --suite test-issue-33-config-meta.py \
  --suite test-issue-65-steering.py \
  --suite test-issue-92-permission-wake-recovery.py \
  --suite test-acp-watch-contract.py \
  --suite test-issue-76-permission-wake.py \
  --suite test-acp-follow-contract.py \
  --suite test-zcode-heartbeat-contract.py \
  --suite test-generated-skills.py
# integrated run: exit 0
PATH="/Users/ylmacstudio/.local/bin:$PATH" /Users/ylmacstudio/.local/bin/bash \
  .kw/qa-278/candidate/scripts/validate.sh --suite test-issue-278-record-root.py
# strengthened final regression recheck: exit 0, 4 tests
python3 tests/contract/test-issue-278-record-root.py
# original-worktree strengthened regression: exit 0, 4 tests
PATH="/Users/ylmacstudio/.local/bin:$PATH" /Users/ylmacstudio/.local/bin/bash \
  .kw/qa-278/candidate/scripts/validate.sh \
  --suite test-issue-278-record-root.py \
  --suite test-issue-273-list-identity.py \
  --suite test-generated-skills.py
# final preflight / regression / inventory recheck: exit 0
```

Integrated selected run: **PASS, exit 0**, 18/89 inventory suites, 581.106 s.
The final `--suite test-issue-278-record-root.py` recheck after adding the
v0.9.1 baseline control and pre-start cleanup also **PASS, exit 0**, 4 tests.
A direct original-worktree `python3 tests/contract/test-issue-278-record-root.py`
run **PASS**, 4 tests in 8.747 s. No full-inventory coverage is claimed.

| Selected suite | Result | Entry elapsed (s) |
| --- | --- | ---: |
| `test-acp-watch-contract.py` | PASS | 13.293 |
| `test-acp-sweep-contract.py` | PASS | 2.262 |
| `test-acp-contract.py` | PASS | 91.587 |
| `test-acp-follow-contract.py` | PASS | 11.667 |
| `test-issue-266-launch-broker.py` | PASS | 15.501 |
| `test-issue-266-launch-broker-composed.py` | PASS | 4.460 |
| `test-issue-33-config-meta.py` | PASS | 138.137 |
| `test-generated-skills.py` | PASS | 1.773 |
| `test-zcode-heartbeat-contract.py` | PASS | 50.407 |
| `test-issue-49-grok-bot-host.py` | PASS | 36.444 |
| `test-issue-74-kaola-delegator.py` | PASS | 9.073 |
| `test-issue-65-steering.py` | PASS | 32.625 |
| `test-issue-278-record-root.py` | PASS | 5.871 |
| `test-issue-76-permission-wake.py` | PASS | 7.870 |
| `test-issue-92-permission-wake-recovery.py` | PASS | 283.131 |
| `test-issue-255-lifecycle-state.py` | PASS | 81.384 |
| `test-issue-273-list-identity.py` | PASS | 1.072 |
| `test-issue-274-package-closure.py` | PASS | 0.458 |

The integrated cleanup receipt reports `residual_pids: []`, no matched holders
and no unverified groups. Render/check, all twelve Skill validators and the
Grok Bot shape verifier passed in the disposable content-stage copy.
`git diff --check`, Python syntax and original-worktree canonical worker byte
inventory checks also passed.

The longer feedback is localized: issue-92's absent/lost-receipt recovery tests
include existing 35-second windows and took 283.131 s; config-meta took
138.137 s. These retain distinct recovery/configuration coverage at the
integration boundary. Routine root-discovery edits can start with the bounded
issue-278/273 subset, expanding only to consumers actually affected. No timeout
was raised, no whole-inventory run was used, and no meaningful assertion was
removed for speed.

Local raw evidence (ignored QA artifacts):
`.kw/qa-278/validation-integrated.log`, `validation-strengthened.log`,
`regression-strengthened.log` and `render-original-check.log`.

Integrated log SHA256: `14f8a81ac18be18d923accb4d27bffd0a6507bb55f82a462d46a60e668ae135a`.

After the 18-suite PASS, a final two-line control-flow correction moved exact-session
lookup after the read-only preflight return. Preflight with an unavailable process
table is exercised by the final issue-278 regression. Transport lookup, socket paths,
Host uniqueness and lifecycle behavior are unchanged from the integrated PASS; their
valid evidence is reused. The final selected regression/list/generated inventory
recheck **PASS, exit 0** (3/89 suites; 7.81538 s). Issue-278: 4 tests in
5.311 s; issue-273: 9 tests in 1.075 s; generated inventory PASS. The cleanup
receipt again reports no residual processes. Raw receipt:
`.kw/qa-278/validation-preflight.log`. No other runtime bytes changed after
that integrated run.

Source digests identify the final implementation independently of the QA clone's base HEAD.

| Source | SHA256 |
| --- | --- |
| `scripts/kaola-acp-paths.py` | `8c540bb5f38c85e2cf3eb802c6fc4153cbc025261f490b7a48473b7b931c2bd4` |
| `scripts/kaola-acp.py` | `033effa21d8373a585a198ddfff5423ea50cc25be5415ad792335b27c3e236db` |
| `scripts/kaola-acp-holder.py` | `d258e870c192ae637e8d8b1715a58fada1970742a81c241fd229b97b2f5e3ad0` |
| `scripts/kaola-launchd-broker.py` | `bb91bd53e603312e05f07fef1dc04556987331fb8aeb232b0a8857b6b979f74d` |
| `scripts/kaola-locate.py` | `e3b248d36ae606b95d8b16ad9fa768e0aef27285bb76421410c7c70a98eb7d01` |

## Coverage and limits

The regression uses live new and genuine v0.9.1 holders with the existing mock
ACP agent: start under TMPDIR A, status/list/locate and send/capture under B,
cross-platform and same-named Host refusals across explicit roots, a dead
canonical shadow, fixed defaults despite XDG changes, and typed failures when
legacy process visibility is unavailable, without gating read-only preflight. The strengthened final regression
also checks the old Runner's false `no-session` as the baseline control.
Fixture stop cleanup is registered before start, and later exact-stops by holder id.

Socket-consuming fixture expectations were updated to the new path contract;
permission, identity, liveness, event-delivery and isolation assertions remain.
The validation entry explicitly puts records under its owned root so interrupted
sweeps still target only that invocation; socket paths no longer rely on TMPDIR.

Stopped records in arbitrary custom legacy roots require their original explicit
root once no live holder identifies that root. Negative discovery without process
visibility refuses and provides recovery, while explicit scoped readers remain
usable. New holder behavior requires a safe-boundary seat restart. Live records
remain readable before that restart. Actual paid/native CLI behavior across all
ten platforms, release pinning, installation and full lifecycle acceptance were
not performed or claimed by this focused bug-fix review.
