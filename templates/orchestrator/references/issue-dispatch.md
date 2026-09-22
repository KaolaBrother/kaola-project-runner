# Issue-scoped dispatch names and one issue per run

Control-plane scheduling policy for issue-backed ACP worker dispatch. It is not a transport
gate, a second validator, or a new lifecycle record.

## The name

Every **new issue-backed ACP worker** dispatch decides its issue before anything starts. The
consuming project's rendered heartbeat declares one stable ASCII short code (`KT` for
KaolaTerminal) beside its canonical repository identity, so the code is project policy, not
a per-session guess.

The Runner `--session` name is then, in this exact field order:

```text
<platform>-<PROJECT>-i<ISSUE>-<unique-purpose>
droid-KT-i274-parser
kimi-cli-KT-i274-review-2
```

`platform` equals the selected Runner platform id, `PROJECT` is the heartbeat's code,
`ISSUE` is the decimal GitHub issue number, and the final token keeps simultaneous
same-issue sessions distinct. The complete name must still satisfy the Runner's existing
1-80-character session syntax (`^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$`), which the transport
already enforces; this contract adds no second validator. Keep the literal `i` delimiter and
the field order, and never infer an issue from an arbitrary substring or from the purpose
token.

Record the constructed name and verify it in the start receipt. The same rule applies on
later heartbeat dispatches and when restarting a stopped worker for the same issue. A worker
reassigned to a different issue is exact-stopped and a new-named session is started - never
a live rename and never a chained prompt. **Otherwise existing active session names are left
alone** - never stop or restart a live session solely to rename it, and the native ACP
session id is unchanged by this rule.

The outer orchestrator Host itself is not an issue-backed worker. Transport-only diagnostics
and genuinely issue-less tasks have no mission ledger and must never be given one by name.
Do not fabricate an issue number; project work that is meant to appear with ledger progress
selects its real open issue before dispatch.

## One issue per run

One Workflow run claims one real GitHub issue. Do not use bundle/multi-issue mode to combine
several issues into one worker claim, branch, child worktree, mission ledger, or Runner
session. Different issues need separate runs, names, and claims; that does not prohibit safe
parallel work on independent issues.

Several ACP workers may collaborate on the **same** issue. They share that issue run's
ledger read-only while keeping distinct Runner names and distinct native sessions.

Before issue-level progress is shown, the claimed `workflow-state.md` `issue_number` must
equal the dispatch name's `ISSUE` under the same repository identity. Runs already in flight
under the older bundle mode are grandfathered for safe close-out: do not rename them, restart
them, or rewrite completed Mission results to retrofit this rule.

## The mission ledger

Path: `<canonical-root>/kaola-workflow/.ledger/issue-<N>.jsonl`. `canonical-root` is the main
checkout the Runner binds with `--repo`; `N` is the issue number in the session name and in the
run's `workflow-state.md` `issue_number`. The folder is gitignored and exists only in the main
checkout, never in a child worktree. One JSON object per line, one line per mission, keys
exactly `n`, `name`, `details`, `status` ∈ `todo | in-flight | done | failed | blocked`. The
run's Workflow Main Orchestrator is the only writer. The Runner never writes.

The Host reads it read-only. Absent file → no live Workflow run has recorded missions for this
issue (`unknown`). Present → progress = `done` lines / total lines; per-mission status by `n`.
Read only the `{n,status}` projection and open `details` only to decide one mission:

```bash
python3 -c 'import json,sys;r=[json.loads(l) for l in open(sys.argv[1]) if l.strip()];print(sum(x["status"]=="done" for x in r),"/",len(r),[ (x["n"],x["status"]) for x in r if x["status"] in ("failed","blocked")])' "$ROOT/kaola-workflow/.ledger/issue-$N.jsonl"
```

`todo` / `in-flight`: wait; never send a second worker to the same mission. `done`: counts
toward progress. `failed`: one dispatch has one result; the run's orchestrator decides any new
mission, the Host may redispatch a worker and never edits the line. `blocked`: escalate
authorization or `HUMAN_DECISION_REQUIRED`, or supply the missing authorization so the worker
returns to `in-flight`. On Workflow archive the file moves to
`kaola-workflow/archive/<project>/mission-ledger.jsonl`, so presence under `.ledger/` means a
live run. Session facts stay in Runner receipts and run facts in `workflow-state.md`.

## What the name does not decide

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
