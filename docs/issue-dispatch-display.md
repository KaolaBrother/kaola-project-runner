# Issue-scoped names: consumer display and non-goals (Issue #72)

Moved out of the loaded reference
`skills/kaola-project-runner/references/issue-dispatch.md` (source
`templates/orchestrator/references/issue-dispatch.md`) by Issue #157 (PR-R4): it is display
guidance for a third-party consumer, not something a dispatching Agent needs on every beat. The
loaded reference keeps the naming grammar, the one-issue-per-run rule, the mission-ledger reading
rules, and one line: the name is a scheduling and display fact, never overrides repository
identity or `issue_number`, and `--resume` stays same-issue. The text below is unchanged from the
reference as of `26cee00`.

## What the name does not decide (consumer display)

The name is a scheduling and display fact. A consumer joining on it verifies the Runner
record's repository identity together with the host-local active Workflow state's
`claim_repository_id` and `issue_number`, archived runs excluded, and then shows one bar:
**issue-run progress - `done` ledger lines over total** - shared by every verified
session on that host, repository, and issue. It never predicts when one ACP process will
finish, and `all missions done` does not by itself mean review, finalize, merge, or issue
close-out happened. A missing or malformed name, a repository mismatch, no active run, an
absent ledger, or two active runs for one issue each fall back to unknown; no mtime, newest-file, `session_marker`,
worktree location, or native ACP id may override a conflict.

Whether any consumer displays that bar is outside this repository. Nothing here was verified
end to end against a consumer.

## Non-goals

Do not add a blocking classifier, a registry, a daemon, or a new Workflow state field. Do not
change exact ownership, default ACP, native session ids, authorization, the Workflow claim,
or stop/resume semantics; `--resume` stays same-issue recovery only. Do not rename or restart a running session to adopt this rule, and
do not let a name override the repository and `issue_number` facts it is checked against.
