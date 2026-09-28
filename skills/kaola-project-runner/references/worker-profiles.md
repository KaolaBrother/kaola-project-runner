# Worker profiles

Owner-defined operating classes and one-line profiles per runtime/preset,
rendered from `platforms/<id>.yaml`. A profile is selection guidance from use,
not a measured capability, price, or benchmark; it never changes a preset's
model, effort, or Fast and never gates `start`. The class attaches to the
runtime/preset, not the whole runtime. Classes are operating roles, not
benchmark claims, and they change no Host model selection.

## Classes

| Class | Responsibility | Authorization and lifecycle |
|---|---|---|
| **Expert** | Complex thinking only: difficult analysis, design, objective decomposition and review judgments. No concrete implementation or execution; not an ordinary worker seat. | Explicit user permission for each task/use. The Host judges its completion and reclaims (exact-stops) the seat. A completed task authorizes no reuse; another use needs fresh permission. Continuing turns or recovery of the same approved task need no repeated approval. |
| **Worker** | Cheaper and generally weaker; simpler, well-defined work supporting parallel throughput. | The default-authorized pool below. |
| **Elite** | Main execution workforce: primary implementation and demanding execution. | Existing explicit runtime/preset/count grants, applicable caps and seat-switch rules. A valid grant stays valid within its scope; no per-task permission. |

Expert review informs the Host; it never replaces Host acceptance or
lifecycle ownership. No Expert use follows from a listed profile, a general
grant, or an earlier approved task.

## Choosing

Decide in this order: **current authorization → class responsibility →
individual profile/task fit → available capacity and real resource limits.**
Expert contributes complex thinking only when specifically permitted; Elite
performs primary and demanding execution; Worker handles simpler bounded work.
Among eligible profiles the Host picks for efficient, precise assignments.
Listed capability never bypasses missing Expert or Elite authorization; when
it is genuinely needed, ask through the existing authorization route. Run
useful independent work in parallel and preserve real dependencies and write
ownership. No numerical ranking, complexity classifier, routing engine, fixed
QA seat, forced equal runtime distribution, or invented work to fill capacity.

## Authorized rows only

Host context holds these class meanings plus only the rows available now: the
Worker rows below minus explicit owner restrictions; each granted Elite row
with its limits; an Expert row only for its currently approved task/use. Keep
them in the existing heartbeat snapshot. Fetch a granted row by exact match,
never by reading the full [profile-catalog.md](profile-catalog.md):
`grep -F '| Codex CLI | `default` |' references/profile-catalog.md`. A later
grant or change adds or updates only the affected rows and removes superseded
availability (a finished or reclaimed Expert task, a revoked grant); do not
reinject whole tables each beat. No second profile or seat registry,
permission service, or mandatory state file.

## Worker class: the default-authorized pool

| Runtime | `--tier` | Model | Effort / parameters | Profile |
|---|---|---|---|---|
| Claude Code | `sonnet` | Sonnet | effort=max | Disciplined implementation worker; give it a detailed plan and constraints, and it excels at executing within them. |
| Codex CLI | `luna` | GPT-6 Luna | effort=max | Fast, flexible implementation worker with good reasoning for its class; relatively exploratory and suited to tasks whose implementation path is not fully predetermined. |
| Devin CLI | `default` | SWE-2 Max | effort=max (encoded in model ID) | Very low-cost, capable full-cycle engineering worker. |
| dsh | `default` | DeepSeek V4.1 Flash (OpenCode Go) | no Runner effort override | Low-cost, fast implementation worker for tasks with clear goals and boundaries; emphasizes autonomous progress, iterative validation, and self-repair. |
| OpenCode | `default` | DeepSeek V4.1 Flash (OpenCode Go) | no Runner effort override | Low-cost, fast implementation worker for tasks with clear goals and boundaries; tends to investigate deeper root causes and reduce unrelated changes. |
| ZCode | `default` | GLM 5.3 | thought=max | Autonomous engineering worker inclined to investigate, make decisions, iterate through failures, and carry substantial tasks toward completion with less hand-holding. |

Owner operating policy, not a live price comparison. For an authorized project
task these six presets need no per-seat, count, or priority approval. Their
live seats neither count toward nor are limited by the general worker
concurrency cap; no substitute cap, per-runtime seat allocation, or approval
gate applies. Membership is this exact list - being a runtime's `default` tier
does not make a preset eligible. Actual account/token/service and resource
limits and any explicit owner restriction still apply; an unspecified quota is
not unlimited. Spread suitable work across runtimes without forcing equal
counts; never create work or extra sessions, interrupt useful work, or wait
for a less suitable worker just to engage or equalize the pool. Individual
profiles keep their strengths (the GLM and SWE-2 presets carry substantial,
full-cycle tasks), while primary and demanding execution goes to an
authorized Elite seat when one is available. Every preset outside this pool
needs its class's authorization; grants already given stay valid within their
scope. The pool is dispatch authorization, not a switch grant, and it does not
extend Host model selection.

## Seat binding and model switching

A seat keeps its bound platform and preset; general dispatch authorization is
not a switch grant. Only a user's explicit grant for a particular seat lets the
Host select or switch that seat's model/preset, within the scope the user
allowed and the same agent runtime, without asking again for each switch under
that grant. Never switch across runtimes. The same seat switches only when
idle, through the existing `drain-restart --resume ID` (or `--continue`) with an
explicit `--tier`/`--model`: an exact stop and resume, not a live hot switch (a
busy seat refuses `drain-not-idle`). A new standard-named seat is a new seat,
not a switch of this one. No new flow. A switch grant never authorizes an
Expert use: an Expert preset runs only under its per-task permission above.
Record grants with the other authorization in the consuming project's run
records.
