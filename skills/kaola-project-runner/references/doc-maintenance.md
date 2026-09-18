# Documentation maintenance boundary

The Runner owns documentation *judgment*, never a documentation subsystem:
no doc ledger, no second acceptance gate, no scheduled full-doc scan. The four
duties below attach to the existing main-loop steps; everything else about the
loop is unchanged.

## Dispatch — the worker judges impact

When dispatching an Issue, have the responsible worker judge which documents
the change can affect — public behavior, commands, contracts — and state the
edit and integration responsibility for shared files (`AGENTS.md`, `README.md`,
docs indexes) in the dispatch prompt. The Runner keeps supervising: this duty
grants no self-execute and no arbitrary documentation-editing authority.

## Acceptance — dock through Workflow, not a second gate

At candidate acceptance, check the affected documents against the actual code,
commands, and public behavior of the frozen candidate. Documents that need
revision travel with the candidate; documents genuinely unaffected get a
specific reason, not a keyword match. Reuse the Kaola-Workflow Finalization
documentation docking for this check — do not build a parallel doc ledger, a
second acceptance gate, or a per-file sign-off table.

## AGENTS.md — verified facts only

`AGENTS.md` carries only verified, durable project facts and stricter local
constraints. It does not copy machine-global Workflow rules, and it does not
record current quotas, sessions, or Issue history. Follow Kaola-Workflow ADR
0023: no fixed template, marker, or word-count gate; rewriting existing
owner-authored instructions needs owner authorization. This repository's old
managed marker is not a cross-project standard — do not batch-rewrite consumer
project instructions under this rule.

## After sink — verify, then sync at a safe point

After an Issue completes Workflow finalize/archive/sink/merge, verify the
target branch and remote, the Issue state, the documentation-docking evidence,
and the exact cleanup — the same close-out checks the main loop already owns.
If project instructions changed, notify in-flight Agents at a safe boundary to
sync or reload and re-verify their affected content; do not interrupt a
measurement to push the notice.

The heartbeat tracks only unfinished duties — never a per-beat full
documentation scan. Each Issue gets one impact judgment; a light entry-document
check belongs to project start and end; a full documentation review is
triggered only by a real change or an explicit task.
