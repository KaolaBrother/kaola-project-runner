# Issue #89 — restamp OpenCode `acp_verified_versions` from the last live ACP PASS

Run facts: branch `workflow/issue-89`, worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-89`,
baseline `5dd18da` (= origin/main at claim; includes Issue #88 sink `367f43a` plus the
tracked #88 validate-log archive commit).

Scope guard (from the outer brief and the issue body): OpenCode `acp_verified_versions`
evidence stamp and the minimum docs/tests that keep the three version claims distinct.
No new schema, version ledger, or gate. No budget raise. No ACP adapter or steering
mechanism change. Do not start an OpenCode CLI this round. Do not treat an un-run
OpenCode version as live-measured. Do not touch #75 / #81 / #88 worktrees, branches,
or in-flight files. Outer ACCEPT is required before Workflow finalize / merge / close.

---

## 1. Read-only: field semantics, original records, current stamp

item: Read every `platforms/*.yaml` `acp_verified_versions`, the design/API/conventions
uses of the field, Issue #24 and #65 archive records, the 2026-09-11 live verification
doc, and the current OpenCode manifest. Classify source-audit vs live ACP vs historical
steering probe. Do not edit product files and do not start OpenCode.
status: done
dispatched: self
result: DONE. Shared meaning across all nine manifests: `acp_verified_versions` is the
live ACP stamp the Runner actually drove (CLI, negotiated `protocolVersion`, plus
adapter/bridge/agent when those were in the path). Design `docs/runner-v2-dual-transport-design.md`
§7.5: "记录已验证的 CLI 版本与协商到的 protocolVersion"; productionization `ed61666`
wrote OpenCode's value after live scenarios 1/3/4/7. `kaola-acp.py` copies it onto
`bridge.verified_versions` as a fact, not a gate. It is not a source-audit tag and not
a steering-probe version. The nine values differ only in which live components they
name, not in meaning.

OpenCode's three recorded versions, kept distinct:

| version | what the repo actually recorded | not |
|---|---|---|
| 1.18.29 | Original live ACP, 2026-09-11: `docs/acp-live-verification-2026-09-11.md` plus `kaola-workflow/archive/bundle-18-19-20-21/evidence/opencode-preflight.json` (`agent_info.version=1.18.29`, `protocol_version=1`). Introduced in `ed61666`. | Not "source audit only". Issue #24 later measured skip-all against this same 1.18.29 (`kaola-workflow/archive/bundle-24/`) and did not introduce the stamp. |
| 1.18.31 | Last live ACP PASS, Issue #65: `kaola-workflow/archive/issue-65/evidence/live-matrix/opencode-1-start.json` `transport.agent_info.version=1.18.31`, `state=ready`, `acp_session_id=ses_f4d1faf4dffeqyXDck0FxZTSBa`, `protocol_version=1`; interrupt steer `interrupted_and_resent`; stop `residual_pids []`. Stamp never updated. | Not a native-steering probe. |
| 1.18.17 | Historical native-steering probe (`-32601`, no `_meta`), calibrated by #88 as history. `native_steering: unknown`. Composite interrupt was later exercised live on 1.18.31. | Not the `acp_verified_versions` stamp. |

The issue body's hypothesis that 1.18.29 was set from #24 source audit is false about
origin, true about staleness versus the last live PASS. No OpenCode CLI was started.

## 2. Confirm main is past the #88 sink, then edit from that baseline

item: #88 was serial-sinking the same `platforms/opencode.yaml`. Wait until origin/main
has absorbed it; only then edit. If it has not moved, prepare tests but do not overwrite
in-flight files.
status: done
dispatched: self
result: DONE at claim time. origin/main and this worktree are `5dd18da` (`chore(archive):
keep the Issue #88 integration validate log as tracked evidence`), parent of #88 product
`db6bc71` and sink `367f43a`. The issue-88 worktree is gone. Current
`platforms/opencode.yaml` already carries #88's `native_steering: unknown` and the
historical 1.18.17 `steering_summary`; `acp_verified_versions` is still
`cli=1.18.29;protocol=1`. Safe to edit this file on `workflow/issue-89` without touching
#75 / #81.

## 3. RED contract: last live ACP stamp is 1.18.31, three claims stay distinct

item: Add `tests/contract/test-issue-89-opencode-verified-versions.py` that fails on the
pre-change bytes and passes after: OpenCode `acp_verified_versions` is the last live ACP
PASS (`cli=1.18.31;protocol=1`), not 1.18.29 and not 1.18.17; the 2026-09-11 live doc
still records 1.18.29 so that earlier live is not erased; the field meaning is written
once as last-live-ACP, not source-audit, not steering-probe; #88's unknown native
steering and historical 1.18.17 probe stay. Register in `scripts/validate.sh`. Prove RED
on baseline `5dd18da` before GREEN. Do not start OpenCode.
status: done
dispatched: self; tests land in the issue-89 worktree at
`.kw/worktrees/issue-89/tests/contract/test-issue-89-opencode-verified-versions.py`
and `scripts/validate.sh` registration; RED proof log at
`kaola-workflow/issue-89/evidence/red-5dd18da.log`
result: RED on baseline `5dd18da` was proven (10 tests, 7 FAIL / 3 PASS) for a
last-live restamp design. Outer then cancelled that design before GREEN. The
uncommitted test file and `scripts/validate.sh` registration stay in the
issue-89 worktree; they are not committed and are not the product change.

## 4. Restamp, retarget #88 current-stamp needles, render

item: Set `platforms/opencode.yaml` `acp_verified_versions` to `cli=1.18.31;protocol=1`
from the archived #65 live receipts. Point `steering_summary` and `docs/api.md` at that
current stamp so they still refuse to treat the 1.18.17 probe as a current-version
native result. Keep #88 semantics (historical probe vs current stamp, `native_steering:
unknown`). Write the one-sentence field meaning. CHANGELOG Unreleased. Do not rewrite
the dated 2026-09-11 live doc or the #88 CHANGELOG entry. `./scripts/render-skills.py
--write` (never hand-edit `skills/`). No new schema, ledger, gate, or budget change.
status: done
dispatched: self (not started)
result: STOPPED before any product edit. Outer cancelled the last-live restamp
design. `platforms/opencode.yaml`, `docs/`, CHANGELOG, and generated Skills were
not modified this round.

## 5. GREEN, validate, freeze for outer ACCEPT

item: Targeted GREEN, `./scripts/render-skills.py --check`, full `./scripts/validate.sh`.
Freeze the candidate SHA plus the original evidence. Stop for outer review. Do not
Workflow finalize, merge, close, or push.
status: done
dispatched: self (not started)
result: STOPPED. No GREEN, no freeze, no commit. Waiting on outer re-accept of
design. No Workflow finalize / merge / close.

## 6. Outer semantic correction — last-live is not the existing contract

item: Pause implementation, keep the uncommitted RED draft, and re-read field
docs plus all nine `acp_verified_versions` values for any actual "must be the
latest live PASS" contract. Return a short verdict: if #89's stale-defect
hypothesis is falsified, recommend an Issue comment and no production change;
if some product wording truly claims latest, cite the exact location.
status: done
dispatched: self
result: DONE, read-only. Verdict for the outer (no product edit, no commit, no
OpenCode start):

**#89's original hypothesis is falsified. No production change is justified.**

1. OpenCode `cli=1.18.29;protocol=1` is a real ACP PASS, not a source-audit
   leftover. It was written in `ed61666` (ACP productionization) after live
   scenarios 1/3/4/7: `docs/acp-live-verification-2026-09-11.md` and
   `kaola-workflow/archive/bundle-18-19-20-21/evidence/opencode-preflight.json`
   (`agent_info.version=1.18.29`, `protocol_version=1`). Issue #24 later
   measured skip-all on that same 1.18.29 and did not introduce the stamp.
2. The field name and existing contract say "verified version", not "latest
   live PASS". Design `docs/runner-v2-dual-transport-design.md` §7.5: "记录已验证的
   CLI 版本与协商到的 protocolVersion"; C-phase "写入实测版本" at the original live.
   Runtime copies the string onto `bridge.verified_versions` as a fact
   (`scripts/kaola-acp.py:214`); `verified_version_match` exists only in that
   design sketch and is not implemented, not a gate. `docs/conventions.md` and
   `README.md` do not define the field. No test requires the stamp to equal the
   most recent live CLI.
3. Later live does not obligate a restamp. Kimi stays `cli=0.41.0` after #65
   live-passed `agent_info.version=2.0.0` (`live-matrix/kimi-cli-*.json`; matrix
   even writes "Kimi Code CLI 2.0.0 (cli 0.41.0)"). OpenCode #65 live-passed
   1.18.31 and #88 kept `cli=1.18.29` while recording the 1.18.31 composite in
   `steering_summary`. Treating 1.18.29 as wrong because 1.18.31 also passed
   would invent a nine-platform maintenance duty the repo does not have.

Recommend an Issue #89 comment: 1.18.29 was truly verified; this is not a stale
defect; close or re-scope without a restamp. Do not write last-live policy into
conventions, tests, or the manifest.

Product wording that uses "current" is #88's native-steering calibration, not a
latest-stamp rule: `platforms/opencode.yaml` `steering_summary` ("not a
measurement of the `acp_verified_versions` 1.18.29 build; the current version
has not been re-probed") and `tests/contract/test-issue-88-permission-defaults.py`
("currently verified version"). In context "current" means the stamped 1.18.29
native surface, and the same summary already names 1.18.31 for composite
interrupt. That is not a last-live contract. Leave it unless the outer wants a
later, separate wording pass.

Uncommitted issue-89 worktree still holds the withdrawn RED draft
(`tests/contract/test-issue-89-opencode-verified-versions.py`, `scripts/validate.sh`
registration). Not committed. No OpenCode CLI started. #75/#81 untouched.
