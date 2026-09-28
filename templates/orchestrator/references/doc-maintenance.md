# Documentation maintenance boundary

The Runner owns documentation *judgment*, never a documentation subsystem or a
scheduled full-doc scan. The effective Kaola-Workflow finalize contract owns
the documentation docking, archive, sink and cleanup procedure; this file adds
only the Host's judgment duties.

## Dispatch — the worker judges impact

When dispatching an Issue, have the responsible worker judge which documents
the change can affect — public behavior, commands, contracts — and state the
edit and integration responsibility for shared files (`AGENTS.md`, `README.md`,
docs indexes) in the dispatch prompt. The Runner keeps supervising: this duty
grants no self-execute and no arbitrary documentation-editing authority.

## Acceptance — impact travels with the candidate

At candidate acceptance, check the affected documents against the actual code,
commands, and public behavior of the frozen candidate. Documents that need
revision travel with the candidate; documents genuinely unaffected get a
specific reason, not a keyword match. The worker's Workflow documentation
docking records it — no doc ledger, second acceptance gate, or per-file
sign-off table.

## AGENTS.md — verified facts only

`AGENTS.md` carries only verified, durable project facts and stricter local
constraints, never machine-global Workflow rules, current quotas, sessions, or
Issue history. Follow Kaola-Workflow ADR 0023: rewriting existing
owner-authored instructions needs owner authorization, and this repository's
old managed marker is not a cross-project standard: never batch-rewrite
consumer project instructions.

## After finalize

Verify the delivery results main Skill step 4 names. If project instructions
changed, notify in-flight Agents at a safe boundary to sync or reload; do not
interrupt a measurement to push the notice. The heartbeat tracks only
unfinished duties, never a per-beat documentation scan; a full documentation
review needs a real change or an explicit task.
