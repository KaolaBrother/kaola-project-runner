# Issue #278 review evidence (2026-10-07)

Branch: `workflow/issue-278`. Base: `41b12e85`. Workflow owns the claim,
main-checkout mission ledger and `.kw/worktrees/issue-278` child worktree.
This is a review candidate: no finalization, merge, tag, publication or production install.

## Host REPAIR round: record-root privacy

Review target: `527ffa6fbf6c5d9decfb90e2c8374e6a38b5b336`. The Host accepted
the path/discovery design and prior evidence, then identified a security
regression in the predictable, unverified `0755` record root. This is one repair
round in the same assignment/worktree, not a new claim or mission. The completed
candidate receipt in the main ledger remains immutable; this document and the
repair commit record the resulting engineering evidence.

Choice: retain `/tmp/kaola-<uid>` and harden it. A single stable default keeps
the accepted TMPDIR-independent lookup and socket behavior unchanged without
adding OS-specific default-selection branches. Runner start checks the selected
root with `lstat` before its start decision. Before any new session-data write,
Runner and holder share the same preparation function: create with `0700`,
reject symlink/non-directory/foreign-UID roots as `record-root-unsafe`, open with
`O_DIRECTORY | O_NOFOLLOW`, recheck owner/type by `fstat`, and use `fchmod` only
on our verified directory descriptor to tighten permissions to `0700`.
Descendants are created/opened relative to those descriptors without following
symlinks. Stale socket removal now happens after this preparation. `drain-restart`
checks the write root before stopping a live holder; an unsafe alias therefore
leaves the seat live and still readable through that alias. Standard
holder record layouts check the shared root; direct custom holder layouts check
the supplied record directory itself. Legacy lookup remains read-only.

Regression coverage adds real starts for a new caller-owned `0700` root and an
owned `0755` root tightened to `0700`; Runner and direct-holder refusal of
symlink/non-directory roots with no writes through them; a foreign-UID root
refused before open/chmod (mocked UID, no privileged chown); and a symlinked
session parent refused without redirected writes; and a refused alias-root
`drain-restart` proven to leave the same live holder answering status. The fixed-default start also
checks ownership/mode. The genuine v0.9.1 live-root test verifies that discovery
does not change its original permissions. Existing cross-TMPDIR and cross-root
Host tests remain intact.

Repair-round command receipts and results are recorded below. Prior 18-suite
evidence describes the reviewed `527ffa6f` candidate; it is not claimed as a
rerun of changed runtime bytes. The four explicitly requested affected suites
are rerun for this repair.

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

## Reviewed 527ffa6f commands and results

These are the prior reviewed candidate receipts. The security repair has its
own final verification below. From the issue worktree:

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

Source digests identify the reviewed `527ffa6f` implementation independently of the QA clone's base HEAD. Repair digests are recorded separately below.

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


## Final security-repair verification

From the issue worktree, the exact final selected invocation is:

```bash
./scripts/render-skills.py --write
./scripts/render-skills.py --check
# each exit 1: unchanged inherited protected v0.9.1 pin-delta constraint
.kw/qa-278/candidate/scripts/render-skills.py --write
.kw/qa-278/candidate/scripts/render-skills.py --check
# each exit 0: existing disposable content-stage QA setup described above
PATH="/Users/ylmacstudio/.local/bin:$PATH" /Users/ylmacstudio/.local/bin/bash \
  .kw/qa-278/candidate/scripts/validate.sh \
  --suite test-issue-278-record-root.py \
  --suite test-issue-273-list-identity.py \
  --suite test-acp-contract.py \
  --suite test-generated-skills.py
python3 tests/contract/test-issue-278-record-root.py
```

**Final repair result: PASS, exit 0**, selected 4/89 suites, 95.1004 s total.

| Selected suite | Exact outcome | Entry elapsed (s) |
| --- | --- | ---: |
| `test-issue-278-record-root.py` | PASS, 10 tests in 8.705 s | 8.762 |
| `test-issue-273-list-identity.py` | PASS, 9 tests in 1.015 s | 1.060 |
| `test-acp-contract.py` | PASS, 85 tests in 93.336 s | 93.391 |
| `test-generated-skills.py` | PASS, generated Skill acceptance | 1.832 |

The final direct original-worktree regression also **PASS, exit 0**, 10 tests
in 9.739 s. The final selected invocation included content-stage render/check,
all twelve Skill validators and Grok Bot shape verification, all PASS; cleanup
reported `residual_pids: []`, no matched holders and no unverified groups.
Original-worktree canonical worker byte inventories, original/QA runtime and
regression source equality, Python syntax and `git diff --check` also PASS.
No runtime/generated bytes changed after these checks. Docs-only outcome updates
do not alter the exercised inputs. No full inventory or native platform run is claimed.

Local raw receipts (ignored): `.kw/qa-278/validation-security-final.log`,
`regression-security-final.log`, `render-security-content-write.log`,
`render-security-content-check.log`, `render-security-original-write.log` and
`render-security-original-check.log`. Original write/check both exit 1; the
protected pin and original Grok Bot products are unchanged. The disposable
content-stage write/check both exit 0. An earlier four-suite repair run before
adding the pre-stop restart guard also passed (94.3035 s); the final run above
supersedes that runtime evidence.

Final repair source digests (QA and original-worktree runtime inputs match):

| Source | SHA256 |
| --- | --- |
| `scripts/kaola-acp-paths.py` | `8a7c6864c4eb5fc1eea6e5bba547a164940b28f40f57de7054a179a6880db321` |
| `scripts/kaola-acp.py` | `e016b255b337456253846c9b56558bbe35ac1430240f49baebbc08af5f83aee1` |
| `scripts/kaola-acp-holder.py` | `7bc65d5d59747e2b46ded1f7e13107ed4c6588f9863e12ddfec2e0114ab6cec0` |
| `tests/contract/test-issue-278-record-root.py` | `e0847de9c62bfec46c893882553fe420b583f1d229105a21bf771ce501adab42` |

Limits: existing live legacy holders remain discoverable without a permission
migration; read-only operations do not tighten their roots. The new write
protection applies on new holder construction/start and requires the already
recorded safe-boundary seat restart. It cannot retract earlier local exposure
from a readable candidate root. Foreign-UID refusal is covered with simulated
ownership, not a second-user integration run. Native paid CLI execution,
production installation and a corrected release pin remain outside this repair.

Final selected log SHA256: `dc818b0343a6e26113e31df54300686e4dd2db67e8794e048e2da8909cd8dbc5`.
