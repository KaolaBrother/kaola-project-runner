# Issue #76 — ZCode Host: immediate permission_required worker event while the ACP worker turn is still active

Run: bundle-76 · branch `workflow/bundle-76` · worktree `.kw/worktrees/bundle-76`
Boundary: extend the existing holder→ZCode-Host worker_event carrier with one new kind
`permission_required`, its worker-side trigger on `session/request_permission`, and the
shortest Host prompt guidance. No polling, daemon, second approval queue, auto-approve, or
change to Droid/Cursor native authorization semantics. Unbound/standalone/non-ZCode behavior
unchanged. Never carry raw tool input, commands, options, or credentials in the event. Do not
touch the issue-70/73/74/bundle-69 runs' files or branches; no finalize/push/close before an
outer ACCEPT.

## 1. Contract tests that distinguish permission-pending from turn-end, failing on the baseline
- item: New `tests/contract/test-issue-76-permission-wake.py` proving: a bound worker whose
  agent raises `session/request_permission` while `turn_active=true` produces one
  `permission_required` worker event on the ZCode Host (idle Host → immediate delivery; busy
  Host → staged then flushed at the next completed turn boundary); the staged event and the
  delivered payload carry only locating metadata (kind/platform/session/repo/reason/
  event_cursor/request_id) — never title/options/raw tool input/secrets; a retransmitted
  request with the same id sends no second carrier; `permit` settles it, the turn ends, and
  the ordinary `idle` event still arrives; an unbound worker sends nothing and is otherwise
  unchanged; `worker_event` validation accepts `permission_required` and rejects a malformed
  `request_id`. Record the baseline failures.
- status: done
- dispatched: self, inline in worktree `.kw/worktrees/bundle-76`; output lands in
  `tests/contract/test-issue-76-permission-wake.py` on branch `workflow/bundle-76`.
- result: done. 5 tests, ~90 checks; baseline fails exactly at the missing wake
  (`timeout: permission_required event reaches the idle host and delivers`) —
  `kaola-workflow/bundle-76/evidence/00-baseline-failure.log`.

## 2. Worker-side trigger and carrier extension in `scripts/kaola-acp-holder.py`
- item: Add `permission_required` to `WORKER_EVENT_KINDS`; on a NEW `session/request_permission`
  pending key send one carrier event with `request_id` (raw JSON-RPC id, non-sensitive) as
  optional structured metadata; extend `_notify_heartbeat_host_now` with an `extra` param;
  accept optional `request_id` in `op_worker_event` validation and carry it into the staged
  event and `_heartbeat_payload` serialization (omitted when absent, so idle/terminated
  payloads are byte-identical). Sources only — `skills/` stays generated.
- status: done
- dispatched: self, inline in worktree `.kw/worktrees/bundle-76`; output lands in
  `scripts/kaola-acp-holder.py` + generated `skills/*/scripts/kaola-acp-holder.py`.
- result: done. All of the above landed; the emitted locator is the *normalized* pending key
  (`normalize_id(request_id)` == `str(request_id)`), so it equals the `pending_permissions`
  receipt key exactly and `7`/`"7"` collapse to one wake — same dedup domain as the pending
  map itself. `op_worker_event` still accepts str|int `request_id` and rejects bool/nested.
  Focused suite re-run green: 5 tests, 77 checks.

## 3. Minimal Host guidance in templates + docs
- item: `templates/orchestrator/references/zcode-host-dispatch.md.tmpl`: document
  `permission_required` where `idle`/`terminated` are defined — it is a wake, not idle and not
  turn end; `observe`/`status` the worker for `pending_permissions`; `permit` only inside
  existing authorization, otherwise report the decision to the user; a gone request is
  already resolved — ignore idempotently; the turn-end `idle` still arrives later. Fit the
  8192 B reference budget (trim redundancy, net bytes must not rise past the cap). One compact
  clause in `heartbeat-skeleton.txt` step 2 naming the permission wake as a worker question.
  Update the `docs/zcode-host.md` Events bullet. Render `--write`, `--check` PASS.
- status: done
- dispatched: self, inline in worktree `.kw/worktrees/bundle-76`; output lands in
  `templates/orchestrator/references/{zcode-host-dispatch.md.tmpl,heartbeat-skeleton.txt}`,
  `docs/zcode-host.md`, and the rendered `skills/kaola-project-runner/` copies.
- result: done. Dispatch ref carries the new kind beside the pinned `idle`/`terminated`
  sentence under the 8,192 B cap after trimming only unpinned prose — every
  Issue #65/#70 contract-pinned fragment verified restored
  (`test-issue-65-host-contract.py` 13/13, `test-issue-70-binding-fact.py` 6/6).
  Skeleton step 2 instructs: read the worker's `pending_permissions`, ignore settled
  requests idempotently, `permit` only inside existing authorization else escalate,
  event approves nothing, turn-end `idle` still arrives. `render-skills.py --check` PASS.

## 4. Full validation, isolated real-path probe, freeze, and outer-review handoff
- item: `render-skills.py --check` + `validate.sh`; probe whether a real ACP permission path
  can be reproduced in isolation on this machine (installed droid/cursor/zcode binaries);
  if not, record live-unverified honestly. Freeze the candidate SHA; assemble actual diff +
  raw test/evidence receipts under `kaola-workflow/bundle-76/evidence/`; hand to the outer
  reviewer. No finalize/push/close before outer ACCEPT.
- status: done
- dispatched: self, inline; probe script at `kaola-workflow/bundle-76/evidence/20-real-droid-probe.py`.
- result: done. `render-skills.py --check` PASS; `validate.sh` full run PASS (all lanes,
  including the post-commit canonical-drift check and the issue-65/issue-70 fragment
  contracts). REAL ACP approval path VERIFIED on this machine for the worker side:
  real `droid` 0.220.0 in `--mode manual` raised a genuine `session/request_permission`
  (`request_id: 0`), stayed `turn_active`, the bound Host got a confirmed
  `permission_required` delivery carrying only the locator, `permit` settled it, and the
  ordinary `idle` then `terminated` events followed — `evidence/20-*.log|py`,
  `21-*.jsonl`, `22-*.jsonl`. The Host-side agent process was the fake zcode app-server
  (no real zcode binary exists — stated limitation); every holder/carrier/permit path
  was real code. Rebased at the safe point onto the post-#73 main `249fc20`
  (both sides' semantics verified present: the #73 op_stop instance pre-check,
  canonical-repo skeleton clause, and the #76 carrier all coexist; generated
  outputs re-rendered identical). Full `validate.sh` re-run PASS post-rebase.
  Candidate frozen: `4f7d83dc907fc844d1422302b890612ea1ab07d5` (supersedes the
  pre-rebase `30f17b0`; diff base for review is `249fc20`).
  Diff + receipts in `kaola-workflow/bundle-76/evidence/`. Awaiting outer reviewer;
  no finalize/push/close performed.
