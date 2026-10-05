# Documentation maintenance boundary

Documentation accuracy is part of the Host's quality judgment
([qa-evidence.md](qa-evidence.md)), never a documentation subsystem or a
scheduled full-doc scan. The effective Kaola-Workflow finalize contract owns
the documentation docking, archive, sink and cleanup procedure; its docking
record is lifecycle evidence, not the Host's accuracy verdict. This file adds
only the Host's judgment duties.

## Dispatch — the worker judges impact

When dispatching an Issue, have the responsible worker judge which documents
the change can affect — public behavior, commands, profiles, contracts — and
state the edit and integration responsibility for shared files (`AGENTS.md`,
`README.md`, docs indexes) in the dispatch prompt. The Runner keeps
supervising: this duty grants no self-execute and no arbitrary
documentation-editing authority.

Write in accordance with ASD-STE100.

## Acceptance — impact travels with the candidate

At candidate acceptance, check the documents the assignment affects against
the actual code, commands, and public behavior of the frozen candidate.
Revisions travel with the candidate; documents genuinely unaffected get a
specific reason, not a keyword match. Where the installed Workflow still runs
documentation docking, it records this — no doc ledger,
second acceptance gate, or per-file sign-off table.

Shared docs touched by several issues may be integrated at their delivery
boundary. A concrete misleading instruction current users or agents rely on
is fixed when it matters.

## AGENTS.md — verified facts only

`AGENTS.md` carries only verified, durable project facts and stricter local
constraints, never machine-global Workflow rules, current quotas, sessions, or
Issue history. Follow Kaola-Workflow ADR 0023: rewriting existing
owner-authored instructions needs owner authorization, and this repository's
old managed marker is not a cross-project standard: never batch-rewrite
consumer project instructions.

## After finalize

If project instructions
changed, notify in-flight Agents at a safe boundary to sync or reload; do not
interrupt a measurement to push the notice. The heartbeat tracks only
unfinished duties, never a per-beat documentation scan or a full sweep per
issue; a broader review needs a real change, a delivery boundary that calls
for it, or an explicit task.
