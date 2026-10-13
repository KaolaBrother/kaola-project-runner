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

## Consumer contract

The shared name and join contract is
[`tests/contract/kaola-terminal-name-contract.json`](../tests/contract/kaola-terminal-name-contract.json)
(`kaola-terminal-name-contract/1`). KaolaTerminal can vendor that file. This repository's
parser (`scripts/kaola-session-names.py`) is checked against every row. That check is not
an end-to-end verification of a consumer display. Nothing here was verified end to end
against a consumer.

The exact platform id is required. The name prefix is the manifest id derived from
`platforms/*.yaml` `session_prefix` (the `-kaola` suffix removed). `claude-code-` and
`cursor-cli-` are exact. Short aliases `claude-` and `cursor-` do not count as valid
names. `start` still succeeds for every advisory value. The field does not block, rename,
or register a session.

Join rule, which the fixture's `join_rule` repeats:

name parses AND the repo's active run claims that issue number => bound; else unbound.
Parses means classification ok: the name is `<platform>-<PROJECT>-i<ISSUE>-<purpose>` and
platform is the exact platform id derived from `platforms/*.yaml` `session_prefix` (the
id, such as `claude-code` or `cursor-cli`, not a short alias such as `claude` or
`cursor`). The repo's active run is exactly one non-archived
`kaola-workflow/<run>/workflow-state.md` in that repo's main checkout whose status is
active, whose `issue_number` equals that ISSUE, and whose `claim_repository_id` matches
the Runner record repository identity. A short alias, another platform's prefix, a
malformed name, a host, sideagent, or seat name, no active run, a repository mismatch,
and two active runs for one issue are unbound.

The Runner advisory `issue_name` `ok` is weaker than bound: it means the name parses and
at least one such active claim exists. It does not require exactly one claim, and it does
not compare `claim_repository_id` to the record. `docs/api.md` states the receipt field.
`docs/conventions.md` states that the advisory is non-blocking.
