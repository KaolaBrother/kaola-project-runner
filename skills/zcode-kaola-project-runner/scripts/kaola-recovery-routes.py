#!/usr/bin/env python3
"""Recovery routes for runner refusals (issue #309).

Every audited failure code maps to a route (the next command) or a self-route
(the agent decides, with the context it needs). ``stamp`` attaches one field.
An existing non-empty ``recovery`` is kept. This module does not choose when a
refusal is raised.
"""

from __future__ import annotations

from typing import Any

SUCCESS = {
    "ok", "ready", "existing", "cleaned", "configured", "delivered", "skipped",
    "removed", "absent", "written", "complete", "admitted", "collected",
}
FALLBACK = (
    "Self-route: read detail and status before any stop or start. "
    "Do not repeat the refused command unchanged and do not start a second session on a guess."
)
# Issue #318. One lost wake, not a holder timer. 401/403 and 404 replace this
# text; a non-final delivery row is not stamped with it.
WEBHOOK_LOST_WAKE = (
    "This wake was lost; run status, then observe/capture for the recorded Host "
    "and the full standard inquiry; run test once — if it delivers, nothing else "
    "is owed; otherwise stay heartbeat-only and report."
)
WEBHOOK_ROTATE_KEY = "Rotate the sender key (webhook-wake.md step 7), then test."
WEBHOOK_RECONFIGURE_URL = "Reconfigure the URL, then test."
# Issue #320. The wake child never started. This is not a dead Host session.
# ``acp-spawn-failed`` keeps the session restart. ``spawn-failed`` used to
# repeat that restart; that action is wrong for this failure.
WAKE_SPAWN_FAILED = (
    "The wake was not attempted; run delegator-webhook test; if that delivers, "
    "continue the inquiry now."
)
_WEBHOOK_DELIVERY_ERRORS = frozenset({"http-status", "connection", "timeout"})

ROUTES: dict[str, tuple[str, str]] = {
    "accepted-revision-superseded": ("route", "A newer revision is accepted. Remove the registration receipt before rolling back, then register."),
    "acp-bridge-missing": ("route", "Install the named runtime or bridge binary, then rerun. Do not start a session without it."),
    "acp-initialize-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "acp-initialize-timeout": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "acp-protocol-version-unsupported": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "acp-runtime-missing": ("route", "Install the named runtime or bridge binary, then rerun. Do not start a session without it."),
    "acp-session-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "acp-session-timeout": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "acp-spawn-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "acp-write-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "acp-unknown": ("self-route", "The sweep could not list live sessions, so the item was skipped and nothing was removed. Re-run sweep --repo REPO --dry-run when kaola-acp.py list answers. Do not remove the item by hand."),
    "agent-exited": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "agent-not-running": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "agent-system-error": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "already-recovered": ("self-route", "The same prompt was already recovered. Read status. Do not start another session for it."),
    "answer-unsupported": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "applied-empty": ("self-route", "An existing config source is in effect. Do not pass a second one. Read the receipt and keep it or replace it explicitly."),
    "applied-unreadable": ("route", "The config source cannot be read. Fix the path named in the receipt and rerun."),
    "argument-required": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "argv-binding": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "argv-empty": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "argv-incomplete": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "argv-not-holder": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "argv-shell": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "assignment-unbound": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "attempt-custody-unknown": ("route", "Rerun cleanup with --record-dir of this session so the leftover attempt can be proved gone."),
    "attempt-unresolved": ("route", "Exact-stop this session, prove the holder and native agent are gone, then rerun cleanup. Cleanup removes artifacts only."),
    "bad-request": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "batch-unverified": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "binding-superseded": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "bootstrap-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "brief-empty": ("route", "Pass non-empty text with --text or --stdin and rerun start. Nothing was started."),
    "brief-fingerprint-mismatch": ("self-route", "Read status for this session. The recorded fingerprint is not this brief, so the receipt is not a dispatch. Do not start a second session."),
    "brief-not-started": ("self-route", "The seat did not become ready, so the brief was not sent. Read the receipt reason. Do not treat a ready state as a dispatch."),
    "brief-turn-unverified": ("self-route", "Read status. If no turn exists, send the same text once to this holder. Do not start a second session and do not treat the start receipt as a dispatch."),
    "build-unrecorded": ("route", "Run ./scripts/render-skills.py --write, then start that worker again so it loads the new bytes. Do not treat the skewed skill as current."),
    "caller-env": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "caller-mode": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "cancel-turn-changed": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "canonical-root-invalid": ("self-route", "The bound canonical root is not a Git top-level. Fix KAOLA_PROJECT_RUNNER_CANONICAL_REPO to that top-level, or unset it for a standalone run. Do not start a session on the refused path."),
    "canonical-root-mismatch": ("self-route", "The requested --repo is not the bound canonical root. Re-run start with --repo set to canonical_repo, or observe and stop the existing session at its own repo. Do not start a second Host."),
    "capture-identity-unbound": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "capture-truncated": ("route", "Read status for this session, then capture --repo REPO --session SESSION --lines 200 again. Do not treat the truncated capture as the whole turn."),
    "capture-unreadable": ("route", "Read status for this session, then capture --repo REPO --session SESSION --lines 200 again. Do not treat the truncated capture as the whole turn."),
    "carrier-aborted": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "carrier-limit": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "checked-out": ("route", "The sweep skipped this branch because a worktree still has it checked out; the worktree item owns that call. Clear that worktree's own keep reasons so it is removed, then run sweep --repo REPO --dry-run again. Do not delete a branch a worktree still holds."),
    "checkout-drift": ("route", "Run ./scripts/render-skills.py --write, then start that worker again so it loads the new bytes. Do not treat the skewed skill as current."),
    "child-record-failed": ("route", "This attempt stopped its own holder. Read child_record_error. Fix the child record path and submit again. Do not adopt this attempt's session."),
    "cite-required": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "cli-drift": ("route", "Run ./scripts/render-skills.py --write, then start that worker again so it loads the new bytes. Do not treat the skewed skill as current."),
    "codex-child-path": ("self-route", "The Codex child path is not the recorded one. Start only the path on the receipt. Do not substitute a binary."),
    "collection-error": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "config-mode": ("route", "chmod 0600 the webhook config and make sure you own it, then rerun configure or status."),
    "config-option-failed": ("route", "Omit --option or pass a config id this platform advertises."),
    "config-option-timeout": ("route", "Omit --option or pass a config id this platform advertises."),
    "config-option-unavailable": ("route", "Omit --option or pass a config id this platform advertises."),
    "config-source-unreadable": ("route", "The config source cannot be read. Fix the path named in the receipt and rerun."),
    "conflict": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "connection": ("route", WEBHOOK_LOST_WAKE),
    "continue-ambiguous": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "continue-empty": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "continue-list-cursor-loop": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "continue-list-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "continue-unsupported": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "current-task-source-unavailable": ("route", "Live list failed. Rerun list --repo REPO --include-dead. Do not guess which seats are alive."),
    "cursor-range-incomplete": ("route", "Read status for this session, then capture --repo REPO --session SESSION --lines 200 again. Do not treat the truncated capture as the whole turn."),
    "cwd-occupied": ("route", "A live process cwd is inside the worktree and the worktree has uncommitted changes; that is the one hard block. Commit or stash the changes, send `cd REPO` to that session or stop that seat, then rerun `sweep --repo REPO --dry-run` (or `worktree-remove`). A live cwd without uncommitted changes proceeds with an `occupied-cwd-recoverable` warning instead."),
    "occupied-cwd-recoverable": ("route", "A live or recorded cwd is inside the worktree but the operation proceeds. Move that shell to the repo root (cd REPO) or stop that seat; the holder recreates a vanished path. Recheck with `worktree-guard --repo REPO --path PATH`."),
    "cwd-placeholder-not-empty": ("self-route", "The placeholder directory now holds content or a new worktree; the holder left it. Read `git worktree list` before touching it."),
    "cwd-relocate-failed": ("route", "The removal wrapper could not leave the worktree it was about to remove (detail names the OS error). Issue #389 treats this as a warning and the removal proceeds; the holder repairs a vanished path. An older wrapper answering this deferral needs its shell moved to the repo root and a rerun."),
    "cwd-repair-failed": ("route", "The holder could not create the placeholder (detail names the OS error). Create the parent and `mkdir -p PATH` yourself, then send `cd REPO`; the holder removes the placeholder on its own once the shell leaves."),
    "cwd-unverifiable": ("self-route", "The cwd probe is unavailable here (detail names lsof, /proc or git). The operation proceeds with a `cwd-unverifiable` warning and the holder recreates a vanished path; recheck with `worktree-guard --repo REPO --path PATH --all-user-processes`. No manual removal is required."),
    "death-wake-unrecorded": ("route", "The death wake was not recorded. Read the holder event log, then run delegator-webhook status and test. If test delivers, continue the inquiry now. Do not treat the omitted wake as delivered."),
    "delegator-field-invalid": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "delegator-migration-needed": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "dirty": ("route", "Commit or stash the checkout changes, then rerun this attest. Do not register a dirty tree."),
    "dispatch-binding-missing": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "dispatch-repo-mismatch": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "done-not-retired": ("route", "A done task record is still stored. Verify its close-out, then run the state retire command named in the detail at the current revision. Do not delete the record by hand."),
    "drain-not-idle": ("route", "Wait until the holder is idle, then rerun drain-restart. Do not kill it to force the drain."),
    "drain-restart-mode-required": ("route", "Pass --resume ID or --continue. Do not fresh-start and do not hot-replace."),
    "drain-restart-selection-unknown": ("route", "Pass the stored selection or restart a seat that stored it. Nothing was stopped."),
    "drain-stop-failed": ("route", "Prove the old holder is gone with status, then rerun drain-restart. Do not start a second holder while it remains."),
    "duplicate": ("route", "This event is already claimed. Do not POST it again."),
    "duplicate-prompt-warning": ("route", "Do not send the same prompt again. Read the live turn."),
    "entry-needs-applied-or-retained": ("self-route", "An existing config source is in effect. Do not pass a second one. Read the receipt and keep it or replace it explicitly."),
    "entry-needs-one-verb": ("route", "The checkpoint entry mixes verbs. Write that input again with exactly one of returned, applied, or retained. Do not merge verbs in one entry."),
    "entry-owned-by-other-agent": ("route", "Pass --replace-owner OLD_LABEL only after that agent's routines are retired."),
    "entry-unreadable": ("route", "The config source cannot be read. Fix the path named in the receipt and rerun."),
    "event-range-unavailable": ("route", "Read status for this session, then capture --repo REPO --session SESSION --lines 200 again. Do not treat the truncated capture as the whole turn."),
    "evidence-required": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "existing-config-source": ("self-route", "An existing config source is in effect. Do not pass a second one. Read the receipt and keep it or replace it explicitly."),
    "existing-session-ambiguous": ("route", "Attach the live holder. Do not start a second session with the same name."),
    "expect-rev-required": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "expect-revision-not-40-hex": ("route", "Pass --expect-revision as 40 lowercase hex, then rerun."),
    "expect-revision-required": ("route", "Pass --expect-revision as 40 hex, then rerun register."),
    "expect-revision-superseded": ("route", "The expected revision is behind the accepted one. Remove the registration receipt before a rollback, then register again."),
    "expected-holder-absent": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "explicit-mode-resume-or-command": ("self-route", "An existing config source is in effect. Do not pass a second one. Read the receipt and keep it or replace it explicitly."),
    "explicit-selection-unverified": ("self-route", "The Host model was not verified. Read status before trusting it. Do not assume the requested model is active."),
    "fingerprint-differs": ("self-route", "The prompt fingerprint does not match the admitted turn. Read capture and do not accept the result. Collect again after the Host identifies the turn."),
    "follow-readonly": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "follow-unsupported": ("route", "follow is not a Runner command. Run kaola-acp.py PLATFORM follow --repo REPO --session SESSION."),
    "foreign-locator-link": ("route", "The locator link points elsewhere. Do not replace it. Register in another directory."),
    "heartbeat-host-conflict": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "heartbeat-host-foreign-repo": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "heartbeat-host-unresolved": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "holder-closed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "holder-instance-mismatch": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "holder-lost": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "holder-mismatch": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "holder-not-ready": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "holder-socket-missing": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "holder-start-timeout": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "holder-unreachable": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "host-answered": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "host-closed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "host-entry-absent": ("route", "Use a Host platform whose manifest has a measured host_skill_entry. Do not select a platform with none."),
    "host-entry-unsupported": ("route", "Use a Host platform whose manifest has a measured host_skill_entry. Do not select a platform with none."),
    "host-exists": ("route", "Attach existing_host from the receipt. Do not rename it and do not start a second Host."),
    "host-fingerprint-mismatch": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "host-identity-required": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "host-model-mismatch": ("route", "Omit --model and --effort, or pass the pair the receipt requires. Do not start a second Host."),
    "host-model-unverified": ("self-route", "The Host model was not verified. Read status before trusting it. Do not assume the requested model is active."),
    "host-only": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "host-reply-invalid": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "host-turn-required": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "host-unreachable": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "host-view-too-large": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "http-status": ("route", WEBHOOK_LOST_WAKE),
    "identity-mismatch": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "identity-unavailable": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "index-unidentified": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "input-missing": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "input-required": ("route", "Pass --url-env, --stdin, or --input-file. Never put the webhook secret on the command line."),
    "input-unproven": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "install-atomic-replace-failed": ("route", "Remove the named temporary path only if it is yours, then rerun. Do not continue a partial install."),
    "install-atomic-symlink-failed": ("route", "Remove the named temporary path only if it is yours, then rerun. Do not continue a partial install."),
    "install-bin-plan-failed": ("route", "Read the refs-tool error above, fix the bin-link ledger, then rerun."),
    "install-codex-hook-blocked": ("route", "Read the named blocker, fix hooks.json or the compact-recovery entry, then rerun. Do not write Skills after this refusal."),
    "install-codex-hook-install-failed": ("route", "Read the named blocker, fix hooks.json or the compact-recovery entry, then rerun. Do not write Skills after this refusal."),
    "install-codex-hook-uninstall-failed": ("route", "Read the named blocker, fix hooks.json or the compact-recovery entry, then rerun. Do not write Skills after this refusal."),
    "install-codex-hooks-unmergeable": ("route", "Read the named blocker, fix hooks.json or the compact-recovery entry, then rerun. Do not write Skills after this refusal."),
    "install-existing-path": ("route", "Do not delete this path. Pick another --skills-dir, or uninstall only a copy this installer owns."),
    "install-foreign-directory": ("route", "Do not delete this path. Pick another --skills-dir, or uninstall only a copy this installer owns."),
    "install-foreign-directory-remove": ("route", "Do not delete this path. Pick another --skills-dir, or uninstall only a copy this installer owns."),
    "install-foreign-symlink": ("route", "Do not delete this path. Pick another --skills-dir, or uninstall only a copy this installer owns."),
    "install-foreign-symlink-remove": ("route", "Do not delete this path. Pick another --skills-dir, or uninstall only a copy this installer owns."),
    "install-method-needs-value": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-modified-copy": ("route", "Do not force-delete user edits. Review the edit, restore the recorded bytes, or remove the path by hand only if it is yours, then rerun."),
    "install-nonsymlink-remove": ("route", "Do not delete this path. Pick another --skills-dir, or uninstall only a copy this installer owns."),
    "install-platform-needs-value": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-python-missing": ("route", "Install python3 or set PYTHON_BIN to an executable, then rerun the same command."),
    "install-quarantine-failed": ("route", "Run ./scripts/install-local.sh --quarantine-stale-backups --skills-dir ROOT for the named root; it moves installer backups into the runner-owned quarantine and records each original path. Do not delete a Skill root or a backup by hand."),
    "install-quarantine-with-uninstall": ("route", "Do not combine --quarantine-stale-backups with --uninstall; run one or the other."),
    "install-render-mismatch": ("route", "Run ./scripts/render-skills.py --write in this checkout, then rerun this install. Do not install a skewed tree."),
    "install-render-missing": ("route", "Run ./scripts/render-skills.py --write in this checkout, then rerun this install. Do not install a skewed tree."),
    "install-runtime-needs-value": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-runtime-once": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-runtime-skills-dir-exclusive": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-skill-missing": ("route", "Run ./scripts/render-skills.py --write in this checkout, then rerun this install. Do not install a skewed tree."),
    "install-skills-dir-absolute": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-skills-dir-needs-value": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-skills-dir-once": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-staging-failed": ("route", "Remove the named temporary path only if it is yours, then rerun. Do not continue a partial install."),
    "install-temp-path": ("route", "Remove the named temporary path only if it is yours, then rerun. Do not continue a partial install."),
    "install-unknown-argument": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-unknown-method": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-unknown-platform": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-unknown-runtime": ("route", "Fix the named flag and rerun the same install-local.sh command. Do not continue a partial install."),
    "install-unknown-runtime-grok": ("route", "Use --platform grok for the worker, or --runtime grok-cli for a Grok CLI Host. Grok Bot has no installer destination."),
    "install-unknown-runtime-grok-bot": ("route", "Use --platform grok for the worker, or --runtime grok-cli for a Grok CLI Host. Grok Bot has no installer destination."),
    "install-verify-incomplete": ("route", "Read the per-destination failure above and rerun. Do not treat this install as complete."),
    "invalid-config": ("route", "Replace the unusable webhook config, then configure again. Do not deliver against it."),
    "invalid-config-option": ("route", "Omit --option or pass a config id this platform advertises."),
    "invalid-heartbeat-host": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "invalid-input": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "invalid-maintenance": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "invalid-payload": ("route", "The payload was not POSTed. Do not invent a wake. The next event uses a new event_seq."),
    "invalid-session-role": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "invalid-start-evidence": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "job-not-owned": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "job-occupied": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "job-running": ("route", "Exact-stop the holder (stop --repo REPO --session SESSION --expected-holder-instance-id ID), then rerun cleanup. Do not unload a running job."),
    "job-state-unknown": ("self-route", "The service manager could not be read from this process, so no job is known to be loaded or exited and this is not evidence of a stale job. Do not retry reconcile or start from the same confined shell. An auto start already degrades to direct with launch_backend_fallback_reason job-state-unknown; accept that, or exact-stop the Host and start it fresh without --resume under full access (the measured case is a dsh Host whose recorded preset is workspace-write), after which the manager is readable. If the job state is still needed, run the reconcile command once from an unconfined shell; os_state absent with reaped false means there was never a leftover."),
    "key-unsupported": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "label-foreign": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "launch-backend-unsupported": ("route", "Start the Host from an independent terminal on this target, or pass --launch-backend explicitly. Do not fall back to a silent caller spawn."),
    "launch-broker-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "launch-broker-missing": ("route", "The launch broker script is missing. Run from a complete checkout, or pass --launch-backend direct. Do not claim an outside-caller launch."),
    "launch-broker-timeout": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "launch-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "launch-in-progress": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "launch-refused": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "legacy-format": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "legacy-unreadable": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "live-session": ("route", "The sweep kept this item because the issue still has a verified live session. Exact-stop that session by its holder first, then run sweep --repo REPO --dry-run again. Do not remove the item while its session is live."),
    "live-source-unavailable": ("route", "Live list failed. Rerun list --repo REPO --include-dead. Do not guess which seats are alive."),
    "live-unidentified": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "locator-not-registered": ("route", "Run kaola-locate.py register on this host, then attest again."),
    "locator-path-occupied": ("route", "The locator path is occupied. Pick another bin directory. Do not overwrite a foreign path."),
    "locator-registration-unreadable": ("route", "The registration receipt is unreadable. Register again. Do not trust the old file."),
    "login-required": ("self-route", "The user must sign in on that platform. Do not retry credentials. Rerun start only after the user confirms the login."),
    "main-skill-build-skew": ("self-route", "The running Host loaded a different main-skill build. Reload kaola-project-runner in that Host. Do not dispatch on the skewed build."),
    "managed-build-default": ("self-route", "An existing config source is in effect. Do not pass a second one. Read the receipt and keep it or replace it explicitly."),
    "missing-host-holder-instance-id": ("route", "Rerun rebind-host from inside the replacement Host session so its verified dispatcher supplies host_holder_instance_id. Do not guess the holder id."),
    "mode-required": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "model-config-not-applied": ("self-route", "The Host model was not verified. Read status before trusting it. Do not assume the requested model is active."),
    "model-config-option-rejected": ("route", "The agent rejected the resolved model option; the session was stopped and no other model was substituted. Pass a model the agent advertises (status or observe lists its model option values), or pass --allow-unapplied-model to accept the agent's own selection, then start again. Do not start a second session with the same name until the receipt shows holder_reclaimed."),
    "mutation-ambiguous": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "mutation-unknown": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "native-config-supplied": ("self-route", "An existing config source is in effect. Do not pass a second one. Read the receipt and keep it or replace it explicitly."),
    "native-route-owned": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "no-acp-session": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "no-advertised-config-option": ("route", "Omit --option or pass a config id this platform advertises."),
    "no-compact-module": ("route", "Install the named runtime or bridge binary, then rerun. Do not start a session without it."),
    "no-head": ("route", "This checkout has no commit. Create a commit, then rerun attest."),
    "no-heartbeat-host": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "no-longer-candidate": ("self-route", "The sweep item no longer matches its rule at apply time, so nothing was removed. Run sweep --repo REPO --dry-run to see the current plan. Do not remove the item by hand."),
    "no-pending-permission": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "no-pending-reload": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "no-resolved-value": ("self-route", "An existing config source is in effect. Do not pass a second one. Read the receipt and keep it or replace it explicitly."),
    "no-result": ("self-route", "No result yet. Wait and collect again. Do not start a second session."),
    "no-session": ("route", "Confirm the name with list --repo REPO --include-dead. If the Host is stopped, exact-stop any leftover holder, attest, then start --resume NATIVE_ID. If there is no attested id or resume fails, start a fresh Host and hand it the summary from status, capture --lines 200, and delegator view. Do not invent a second live Host."),
    "node-identity-required": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "node-start-error": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "node-starting": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "node-stop-unreachable": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "not-a-checkout": ("route", "Run the locator from a complete kaola-project-runner checkout. Do not register this path."),
    "not-attempted": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "not-configured": ("route", "Run delegator-webhook configure, or stay heartbeat-only. Status does not scan a disabled entry."),
    "not-enabled": ("route", "Run delegator-webhook configure, or stay heartbeat-only. Status does not scan a disabled entry."),
    "notice-admission-unconfirmed": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "notice-host-entry-absent": ("route", "Use a Host platform whose manifest has a measured host_skill_entry. Do not select a platform with none."),
    "notice-original-work-not-successful": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "notice-write-unknown": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "origin-form-unsupported": ("route", "Set origin to https://, ssh://, or scp host:path, then rerun. Do not register another form."),
    "origin-mismatch": ("route", "This checkout origin is not the expected repository. Do not register it."),
    "original-signal-already-settled": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "output-absent": ("route", "Read status for this session, then capture --repo REPO --session SESSION --lines 200 again. Do not treat the truncated capture as the whole turn."),
    "pending-permissions-unavailable": ("route", "Live list failed. Rerun list --repo REPO --include-dead. Do not guess which seats are alive."),
    "permission-pending": ("route", "The sweep kept this session because a permission request is pending. Answer or cancel it with permit --repo REPO --session SESSION --request-id ID, then let the next sweep check it again. Do not stop the session on a guess."),
    "pgid-identity-unverified": ("self-route", "Do not exact-stop by guess. Read status residual_pids and prove the process identity, or leave the process and report it."),
    "pin-drift": ("route", "Run ./scripts/render-skills.py --write, then start that worker again so it loads the new bytes. Do not treat the skewed skill as current."),
    "preserve-unsupported": ("route", "Stop without --preserve-dispatched-workers, or upgrade the holder, then retry the same stop."),
    "prior-notice-unresolved": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "prior-turn-not-completed": ("route", "Read steer_followup.original_turn and session status. Wait until the session is idle and healthy, then send a normal prompt. Do not assume the queued text was written."),
    "prior-turn-unsuccessful": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "probe-eof": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "probe-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "project-not-a-checkout": ("route", "Pass a Git checkout. Do not attest a non-repository path."),
    "project-not-on-this-host": ("route", "Pass an absolute project directory on this host."),
    "prompt-in-progress": ("self-route", "A prompt is in progress. Steer that turn (or steer --delivery after-turn to queue for the next turn) or retry send after turn_ended. Do not start a second session."),
    "provider-error-unavailable": ("route", "No provider error could be carried out. Read status, then capture --repo REPO --session SESSION --lines 200 and the turn_ended error reason. Do not invent a provider error."),
    "queue-empty": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "rebind-host-unresolved": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "receipt-too-large": ("route", "Rerun attest with fewer selectors. Fix each remaining reason. Do not register a refused target."),
    "reconciliation-needed": ("self-route", "Reconcile the prior unknown row from its original receipts before execute or collect continues. Do not start a replacement seat on a guess."),
    "record-lost": ("route", "The session's record directory is gone but its host-registry row survives. Read the record_lost facts: if holder_pid_alive is true, run `stop --repo REPO --session SESSION --force` to sweep the argv-verified orphan; then run the start --resume command in recovery.resume. A registry that is also gone leaves no verifiable identity - never signal a guessed pid."),
    "record-lost-orphan": ("route", "A live orphan holder still owns this session and its record directory is gone. Run `stop --repo REPO --session SESSION --force` to sweep it (argv-verified), then start --resume with the recorded acp_session_id."),
    "record-missing": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "record-retired": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "record-root-mismatch": ("self-route", "Pass one private --record-root you own, or unset KAOLA_ACP_RECORD_ROOT. Do not write session files on the refused root."),
    "record-root-unsafe": ("self-route", "Pass one private --record-root you own, or unset KAOLA_ACP_RECORD_ROOT. Do not write session files on the refused root."),
    "record-versionless": ("route", "The record predates record revisions, so no record revision names it. If it is an alerts row whose inputs is an empty object (resolved), retire it directly with state retire --expect-rev 0 --evidence ORIGINAL_HANDLED_EVIDENCE. Otherwise run state migrate on this file (a read-only plan), then again with --write to assign rev 1, then retry the refused command; update and the returned-input settle still need that migration. Do not hand-edit the record."),
    "remove-failed": ("route", "The guarded removal failed (detail names the git error); the worktree is untouched. Read the original git receipt and decide."),
    "recorded-path-missing": ("route", "Run ./scripts/render-skills.py --write, then start that worker again so it loads the new bytes. Do not treat the skewed skill as current."),
    "recovery-entry-unknown": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "recovery-originals-unavailable": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "recovery-scope-conflict": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "recovery-scopes-missing": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "recovery-sources-empty": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "recovery-unavailable-unreadable": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "redirect-refused": ("route", "Reconfigure with a URL that does not redirect. Do not POST the event by hand."),
    "registration-path-occupied": ("route", "The registration path is occupied. Do not overwrite it. Pick another bin directory."),
    "registration-root-mismatch": ("route", "This link is registered to another checkout. Register again from the checkout you mean."),
    "registration-stale": ("route", "HEAD moved. Register again at the new revision before attesting it."),
    "registry-row-gone": ("self-route", "The host-registry row was removed between the scan and the wake mark, so a clean stop or a newer start already reconciled the loss. Do not POST this wake again; re-run delegator-webhook status to confirm the current state."),
    "registry-row-incomplete": ("route", "The host-registry row is missing holder_instance_id or session, so the record-loss wake cannot be keyed. Re-register the row with a clean stop --repo REPO --session SESSION --force followed by start --repo REPO --session SESSION. Do not edit .kaola/host-registry.json by hand."),
    "relay-unadmitted": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "reload-inflight": ("route", "The notice was not delivered. Read detail. Retry the notice only after the Host is idle, or leave it pending. Do not invent a delivery."),
    "reply-text-absent": ("route", "Read status for this session, then capture --repo REPO --session SESSION --lines 200 again. Do not treat the truncated capture as the whole turn."),
    "repo-mismatch": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "repo-missing": ("route", "The --repo path is not a directory. Pass the canonical project root and rerun the same command. Do not create a directory for it."),
    "request-id-required": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "restart-required": ("route", "A seat-restart file changed. Restart that running holder after the new bytes are installed. Do not treat the live seat as already running them."),
    "resume-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "resume-unsupported": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "resumed-session-permission": ("route", "The resumed dsh session keeps the permission preset recorded in its session log at creation; the launch variable does not apply. Read config_application.mode.effective for the recorded values. To gain a wider preset, exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), then start without --resume under the wanted mode. Do not resume the same id again expecting the new mode."),
    "retire-unmet": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "returned-unreadable": ("route", "The checkpoint entry's returned is empty or not a string. Write that input again with a non-empty returned reason, or settle it with applied or retained instead."),
    "revision-mismatch": ("route", "Check out the expected revision, or pass the current HEAD. Do not register a mismatch."),
    "revision-unrecorded": ("route", "Run ./scripts/render-skills.py --write, then start that worker again so it loads the new bytes. Do not treat the skewed skill as current."),
    "runner-default": ("route", "The item was admitted. Read its session with status. Do not start a second seat for the same item."),
    "runner-missing": ("route", "The platform Runner script was not found under --skills-root, the dispatch Skill root, or the checkout skills/ directory, and the bounded collect retry is exhausted. Render and install that platform Skill, then collect again with a root that holds its Runner; the next collect that resolves the Runner reads the seat. Until then the row stays runner-missing. Do not mark the item admitted."),
    "runner-python-missing": ("route", "Install python3 or set PYTHON_BIN to an executable, then rerun the same command."),
    "schema-unsupported": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "scoped-checkpoint-already-settled": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "verified-past-revision": ("self-route", "The returned input is covered by a later verified checkpoint and is settled. Read that checkpoint record; do not re-file the input or retry the same registration."),
    "wake-not-host": ("self-route", "Only the Host holder sends Delegator wakes. Re-run the wake command from the Host session (its shell or the orchestrator Skill), not from a worker or an unbound shell. Do not start a second Host for it."),
    "wake-reason-refused": ("route", "Pass --reason with one of needs_decision, question_waiting, or delivery_review. Read the receipt's allowed list; do not invent a reason string."),
    "wake-spawn-failed": ("route", WAKE_SPAWN_FAILED),
    "script-missing": ("route", "Run ./scripts/render-skills.py --write so the worker script exists, then rerun attest."),
    "script-not-executable": ("route", "Make the worker runtime-tmux.sh executable, then rerun attest."),
    "script-outside-root": ("route", "Use the worker script inside this checkout. Do not attest a script outside the root."),
    "selection-mismatch": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "send-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "session-exists": ("route", "Attach the live holder. Do not start a second session with the same name."),
    "session-gone": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "session-mismatch": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "sideagent-default-unbound": ("route", "Node mode is not bound. Run the state ensure-sideagent command named in the problem detail. The next Host boundary retries. Do not invent a preset or replace an existing binding."),
    "sideagent-receipt-unreadable": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "sideagent-unbound": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "sideagent-unreachable": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "signal-unverified": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "snapshot-unstable": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "stale-install-backup": ("route", "Run ./scripts/install-local.sh --quarantine-stale-backups --skills-dir ROOT for each named root; it moves hidden installer backups into the runner-owned quarantine, records each original path, and deletes nothing. A backup alone never blocks start."),
    "source-required": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "spawn-failed": ("route", WAKE_SPAWN_FAILED),
    "spec-foreign-owner": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "spec-missing": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "spec-nonce": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "spec-not-regular": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "spec-permissive": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "spec-required": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "spec-schema": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "start-evidence-too-large": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "start-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "start-incomplete": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "state-bloat": ("route", "The detail names the collection, id, revision, and the state retire or update command for this record. Run that command with the record's evidence; rewrite the same id in place. Do not append to it."),
    "state-exists": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "state-managed": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "state-missing": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "state-too-large": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "state-unreadable": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "status-truncated": ("route", "Read status for this session, then capture --repo REPO --session SESSION --lines 200 again. Do not treat the truncated capture as the whole turn."),
    "status-unreadable": ("route", "Read status for this session, then capture --repo REPO --session SESSION --lines 200 again. Do not treat the truncated capture as the whole turn."),
    "steer-cancel-unconfirmed": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-capability-unknown": ("self-route", "The Host model was not verified. Read status before trusting it. Do not assume the requested model is active."),
    "steer-empty": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "steer-holder-outdated": ("route", "This holder is older than steer. Exact-stop and start --resume so the new holder loads, or send after the turn is idle. Do not assume steer was delivered."),
    "steer-mode-required": ("route", "Pass --steer-mode native or interrupt and rerun steer."),
    "steer-no-response": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-prompt-failed": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-prompt-required": ("route", "The native turn already emitted its result or ended. If the holder turn is still settling (turn_active: true), queue with steer --delivery after-turn or retry send after turn_ended; if idle, send a normal prompt. Do not start a second session."),
    "steer-queued": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-rejected": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-reply-pending": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-send-failed": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-turn-changed": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-undecided": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-unrecognized-outcome": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-unsupported": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "steer-write-only-confirmation": ("route", "Read this steer receipt. Wait until the turn is idle, then send, or exact-stop the named holder if it is lost. Do not start a second session and do not assume the text was delivered."),
    "still-running": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "stopping": ("self-route", "The holder is stopping. Read status. Do not send another prompt until the stop finishes."),
    "target-mismatch": ("route", "The declared --target does not match registration. Do not reuse this receipt."),
    "target-required": ("route", "Pass --target local or cloud when attesting a project, worker, or session."),
    "tier-not-declared": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "timeout": ("route", WEBHOOK_LOST_WAKE),
    "tool-cwd-unknown": ("self-route", "The shell failed to spawn and no recorded working directory exists. Read status (`tool_cwd`) and the worktree paths removed since the last successful shell call; recreate that path as an empty directory, then send `cd REPO`. Do not restart the session."),
    "tool-cwd-vanished": ("route", "The agent's shell working directory named in detail was removed. The holder recreates it as an empty placeholder and tells the agent to `cd REPO`. If status shows `tool_cwd.placeholder` empty and `exists` false: `mkdir -p PATH`, then send `cd REPO` to the session (steer while a turn runs, send when idle), then `rmdir PATH` once status shows `tool_cwd` outside it. Do not stop or restart the session."),
    "transport-pty-retired": ("route", "Re-run without --transport (or with --transport acp)."),
    "turn-active": ("self-route", "The sweep kept this session because a turn is running. Read status; after the turn ends, the next sweep checks it again. Do not cancel or stop a running turn to clear the sweep."),
    "turn-failed": ("route", "Exact-stop this session (stop --repo REPO --session SESSION --expected-holder-instance-id ID), attest, then start --resume NATIVE_ID. If resume still fails, start a fresh Host session and hand it the summary from status, capture --lines 200, list --repo --include-dead, and delegator view (goals, decisions, in-flight tasks, live seats and holders, pending items). The new Host re-adopts live seats from that list. Do not retry the dead session. This build does not auto-reap an unowned exited job."),
    "turn-fingerprint-differs": ("self-route", "The prompt fingerprint does not match the admitted turn. Read capture and do not accept the result. Collect again after the Host identifies the turn."),
    "turn-fingerprint-unknown-or-differs": ("self-route", "The prompt fingerprint does not match the admitted turn. Read capture and do not accept the result. Collect again after the Host identifies the turn."),
    "turn-outcome-unavailable": ("route", "Read status for this session, then capture --repo REPO --session SESSION --lines 200 again. Do not treat the truncated capture as the whole turn."),
    "unmerged-or-unpushed": ("route", "The sweep kept this item because the branch head is not merged into the remote head and is not a merged-PR head. Merge or push the work first, then run sweep --repo REPO --dry-run again. Do not remove the item to silence the sweep."),
    "unknown-op": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "unknown-request": ("route", "Fix the named argument in detail and rerun the same command. Do not start a second session or bootstrap a partial job."),
    "verify-finding": ("route", "Fix the named source in templates/ or hosts/grok-bot/, rerun ./scripts/render-skills.py --write, then rerun this verifier. Do not hand-edit skills/ or hosts/grok-bot/."),
    "view-unsupported": ("route", "view is not a Runner command. Run kaola-acp.py PLATFORM view --repo REPO --session SESSION."),
    "wire-missing": ("route", "wire.jsonl was not found for this kimi-cli session. Read status, then check KIMI_CODE_HOME sessions for that repo and session at agents/main/wire.jsonl. Do not invent a provider error."),
    "wire-unreadable": ("route", "wire.jsonl for this kimi-cli session cannot be read. Read status, fix that file's path or permissions, then read it again. Do not invent a provider error."),
    "worker-event-invalid": ("route", "The worker event is invalid. Fix the payload in detail and submit it again. Do not assume the Host saw it."),
    "worker-event-queue-full": ("route", "The worker-event queue is full. Wait until it drains, then submit the same event once. Do not drop it."),
    "worker-event-unsupported": ("route", "This holder does not accept that worker event. Read status and send the result on the supported path. Do not retry the same op."),
    "worker-skill-build-skew": ("route", "Run ./scripts/render-skills.py --write, then start that worker again so it loads the new bytes. Do not treat the skewed skill as current."),
    "worker-skill-root-unreadable": ("route", "The worker skill root cannot be read. Fix the path in the receipt, then retry. Do not dispatch to an unreadable root."),
    "worker-unknown": ("route", "Pass a platform id from platforms/*.yaml. Do not invent a worker id."),
    "writer-mismatch": ("self-route", "Do not retry this target. Re-read status or the locator receipt and operate only the named session, repo, and holder_instance_id."),
    "writer-refused": ("route", "Read detail and the current revision. Run the state command detail names (init, migrate, update, or retire) with that revision. Do not write a second file or retry the same patch unchanged."),
    "zcode-runtime-invalid": ("route", "Those ZCode paths are not files on this host. Fix them, then rerun."),
    "zcode-runtime-unset": ("route", "Set KAOLA_ZCODE_ENTRY and KAOLA_ZCODE_NODE to absolute files on this host, then rerun."),
}


def lookup(code: str) -> tuple[str, str]:
    """Return ``(kind, text)`` for a known code, or a self-route that names it."""
    found = ROUTES.get(code)
    if found is not None:
        return found
    return ("self-route", f"{code}: {FALLBACK}")


def webhook_delivery_route(error: str | None, http_status: object, final: bool) -> str | None:
    """Class split for one failed webhook delivery row (#318).

    ``None`` means stamp from the error code. ``""`` means a non-final
    ``connection`` or ``http-status`` row: the sender is still retrying, so
    the row gets no route. A non-empty string is the route and replaces stamp.

    Final 401 and 403 rotate the sender key. Final 404 reconfigures the URL.
    A final connection, timeout, or any other final HTTP status uses the table
    text (the lost-wake route). That includes 400, 408, 429, 5xx, and any
    other final 4xx. ``redirect-refused`` and config or payload errors are
    not this split. There is no holder-side re-offer timer.
    """
    if error not in _WEBHOOK_DELIVERY_ERRORS:
        return None
    if not final:
        return ""
    if error == "http-status" and http_status in (401, 403):
        return WEBHOOK_ROTATE_KEY
    if error == "http-status" and http_status == 404:
        return WEBHOOK_RECONFIGURE_URL
    return None


def _already(payload: dict[str, Any]) -> bool:
    if isinstance(payload.get("recovery"), str) and payload["recovery"].strip():
        return True
    if isinstance(payload.get("route"), str) and payload["route"].strip():
        return True
    return isinstance(payload.get("self_route"), str) and bool(payload["self_route"].strip())


def _codes(payload: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    err = payload.get("error")
    if isinstance(err, dict) and isinstance(err.get("code"), str):
        codes.append(err["code"])
    elif isinstance(err, str) and err in ROUTES:
        codes.append(err)
    if codes:
        return codes
    reason = payload.get("reason")
    if isinstance(reason, str) and (reason in ROUTES or "-" in reason or reason in {"dirty", "stopping", "conflict", "timeout", "connection"}):
        codes.append(reason)
    skip = payload.get("skip_reason")
    if isinstance(skip, str) and skip in ROUTES and skip not in codes:
        if payload.get("result") in {"refused", "error", "failed"}:
            codes.append(skip)
    for item in payload.get("reasons") or []:
        if isinstance(item, str) and item not in codes:
            codes.append(item)
    return codes


def _failure(payload: dict[str, Any]) -> bool:
    result = payload.get("result")
    if result in {"refused", "error", "failed"}:
        return True
    if payload.get("kind") == "error":
        return True
    if payload.get("scan") in {"skipped", "incomplete"} and isinstance(payload.get("reason"), str):
        return True
    # Issue #320: a death-wake dict reports failure as ``sent: false``.
    # ``already-recovered`` is one of those and keeps its own self-route.
    if payload.get("sent") is False and result not in SUCCESS:
        return True
    if payload.get("delivered") is False and isinstance(payload.get("reason"), str):
        return True
    if payload.get("status") in {"unknown", "failed", "not-run"} and isinstance(payload.get("reason"), str):
        return True
    err = payload.get("error")
    if isinstance(err, dict) and isinstance(err.get("code"), str) and result not in SUCCESS:
        return True
    reasons = payload.get("reasons")
    return result == "refused" and isinstance(reasons, list) and bool(reasons)


def stamp(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach ``route`` or ``self_route``. Idempotent. Does not drop ``recovery``."""
    if not isinstance(payload, dict):
        return payload
    # Issue #320: a failed wake is nested under the start/stop receipt and
    # under each status-scan wake. Walk those before the parent success check.
    for key in ("holder_lost", "delegator_death_wake"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            payload[key] = stamp(nested)
    wakes = payload.get("wakes")
    if isinstance(wakes, list):
        payload["wakes"] = [stamp(item) if isinstance(item, dict) else item for item in wakes]
    if _already(payload) or not _failure(payload):
        return payload
    codes = _codes(payload)
    if not codes:
        payload["self_route"] = FALLBACK
        return payload
    parts: list[str] = []
    kinds: list[str] = []
    for code in codes:
        kind, text = lookup(code)
        kinds.append(kind)
        parts.append(f"{code}: {text}" if len(codes) > 1 else text)
    field = "route" if kinds and all(kind == "route" for kind in kinds) else "self_route"
    payload[field] = " ".join(parts)
    return payload


def fit_locate(receipt: dict[str, Any], limit: int) -> dict[str, Any]:
    """Stamp a refused attest receipt without dropping its reasons to fit ``limit``."""
    import json as _json
    stamped = stamp(dict(receipt))
    def size(doc: dict[str, Any]) -> int:
        return len(_json.dumps(doc, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    if size(stamped) <= limit:
        return stamped
    reasons = [item for item in (stamped.get("reasons") or []) if isinstance(item, str)]
    if not reasons:
        reasons = ["receipt-too-large"]
    kind, short = lookup("receipt-too-large")
    field = "route" if kind == "route" else "self_route"
    shrunk: dict[str, Any] = {
        "schema": receipt.get("schema"),
        "result": "refused",
        "reasons": reasons,
        field: short,
    }
    while reasons and size(shrunk) > limit:
        reasons = reasons[:-1]
        shrunk["reasons"] = reasons or ["receipt-too-large"]
    if size(shrunk) > limit:
        shrunk = {
            "schema": receipt.get("schema"),
            "result": "refused",
            "reasons": ["receipt-too-large"],
            field: short,
        }
    return shrunk

