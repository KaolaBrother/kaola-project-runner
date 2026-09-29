# Worker profiles

Owner-defined operating classes and one-line profiles per runtime/preset,
rendered from `platforms/<id>.yaml`. A profile is owner selection guidance,
not a benchmark; it changes no model, effort, Fast setting, tool permission, or
start behavior. The class attaches to the preset, not the whole runtime.

## Classes

| Class | Responsibility | Authorization and lifecycle |
|---|---|---|
| **Expert** | Complex thinking only: difficult analysis, design, objective decomposition and review judgments. No concrete implementation or execution; not an ordinary worker seat. | Explicit user permission for each task/use. The Host judges its completion and reclaims (exact-stops) the seat. A completed task authorizes no reuse; another use needs fresh permission. Continuing turns or recovery of the same approved task need no repeated approval. |
| **Worker** | Cheaper and generally weaker; simpler, well-defined work supporting parallel throughput. | The exact five-preset pool below is default-authorized for authorized project tasks. |
| **Elite** | Main execution workforce: primary implementation and demanding execution. | Existing explicit runtime/preset/count grants, applicable caps and seat-switch rules. A valid grant stays valid within its scope; no per-task permission. |

Expert review informs the Host; it never replaces Host acceptance or
lifecycle ownership. No Expert use follows from a listed profile, a general
grant, or an earlier approved task.
A seat's confirmed limit failure is recovered by its class, never by
login: [quota-packages.md](quota-packages.md#confirmed-exhaustion). An
authentication or account-access failure instead pauses that seat and goes to
the user ([Account unavailable](quota-packages.md#account-unavailable)).

## Local availability and authorized rows

A locally selectable runtime/preset needs both facts on the bound execution
target:

- The existing `kaola-acp.py survey` reports the runtime `present` in its
  effective launch context, including its resolved explicit path or login
  environment. Outer-machine PATH or a loaded Skill does not prove
  installation on the target.
- The corresponding installed platform Runner is discovered on that target
  and its own `scripts/platform.yaml` declares the preset. A tier is the
  Runner's preset mapping, not a downloaded model. A missing native provider
  model-catalog entry does not invalidate a declared preset.

Discovery shows a declared launch mapping, not account quota, model execution,
or tool access. Do not authenticate, relogin, enumerate entitlements, or
benchmark to create a local list. At start, use the existing receipt to check
requested/applied configuration; report a known mismatch and never silently
downgrade or substitute another Worker.

Show users only rows with both facts, with Class, profile, and current
authorization stated separately. Omit missing runtimes, Runner Skills, and
presets. Keep unresolved discovery `unknown` and report the actual missing
fact separately when relevant. Installed Elite and Expert rows may be shown
for a user to grant; visibility never grants authorization.

Host working context is the intersection of local rows and current
authorization: discovered Worker pool members without owner restrictions,
granted Elite rows with their limits, and an Expert row only for its currently
permitted task. Read the exact applicable rows from
[profile-catalog.md](profile-catalog.md) after establishing availability and
authorization; never load the full catalog just to discard rows. The heartbeat
`authorization` carries these rows directly (exact ID, Class, catalog profile
text) plus the three Class definitions once; a pointer never replaces them
([heartbeat-skeleton.md](heartbeat-skeleton.md)). Rebuild at intake or
recovery; update only on an actual grant, profile, install, or launch-path
change; do not poll, cache a second registry, or rescan each beat. A verified
active session keeps its ownership when availability changes.

## Preset IDs in authorization

A granted, paused, or revoked seat is named by its exact catalog Preset ID
`<platform>/<tier>`; a platform word alone names no seat. Count, Class grant
lifetime, cap, quota units, seat identity and switch authorization stay
separate facts; a Worker exclusion names its exact ID. An authorization item
carries `special_requirements` only when the owner actually supplied a
deviation (`{"effort":"high"}`, `{"task_scope":"visual QA"}`); omit by
default — tier defaults, profile text, or Host judgment are
not owner requirements. Effort changes only effort; task scope only narrows
coverage; an unappliable requirement is reported, never silently fallen back
or inferred to a nearby ID. The ID is notation: `start` still takes the
declared `--tier` with its requested/applied receipt — no new flag or gate.

## Choosing

Decide in this order: **current authorization → local availability → class
responsibility → profile/task fit → capacity and known resource limits.**
Expert contributes complex thinking only for its permitted task; Elite performs
primary and demanding execution. `claude-code/default` does not perform implementation; a Claude Code Host still plans, dispatches, and accepts. Worker handles simpler bounded work. Listed
capability never bypasses missing Expert or Elite authorization; ask through
the existing authorization route when needed. Keep real dependencies and write
ownership. Do not rank models, invent a complexity classifier or routing
engine, force equal runtime distribution, create work to fill capacity, or
interrupt useful work.

The Worker pool is exactly: `codex/luna`, `devin/default`, `dsh/default`, `opencode/default`, `zcode/default`.
For an authorized project
task, these five presets need no per-seat, count, or priority approval. Their
live seats neither count toward nor are limited by the general worker
concurrency cap. A runtime's `default` is not automatically a pool member. Real account, service, and resource limits
and explicit owner restrictions still apply; an unspecified quota is not
unlimited. Default authorization is permission, not a preference over
suitable authorized Elite; never wait on a less suitable Worker. Existing grants stay valid within scope; the pool is not
a model-switch grant and does not extend Host model selection.

## Computer interaction

The owner designates exactly two presets for tasks that operate a computer:
`codex/default` (GPT-6 Sol, effort=high; Elite) and `codex/luna` (GPT-6
Luna, effort=max; Worker). Prefer Sol only when its local row is discovered,
available for the task, and covered by the user's explicit preset/seat grant.
If no eligible Sol is available, use locally available Luna under the Worker
pool rules, with no extra seat approval for an authorized project task. If
neither qualifies, report the concrete availability or authorization gap;
never silently switch tiers or substitute another preset.

Do not infer computer-operation capability from visual-design or screenshot-review profiles or class membership. Visual analysis is not computer use. Model authorization and permission to
use computer tools are separate existing facts. Profile wording grants no tool
or switch permission, and already granted tooling needs no repeated approval.

## Seat binding and model switching

A seat keeps its bound platform and preset; general dispatch authorization is
not a switch grant. Only a user's explicit grant for a particular seat lets the
Host select or switch that seat's model/preset, within the scope the user
allowed and the same agent runtime, without asking again for each switch under
that grant. Never switch across runtimes. The same seat switches only when
idle, through the existing `drain-restart --resume ID` (or `--continue`) with an
explicit `--tier`/`--model`: an exact stop and resume, not a live hot switch (a
busy seat refuses `drain-not-idle`). A new standard-named seat is a new seat,
not a switch of this one. A switch grant never authorizes an Expert use: an
Expert preset runs only under its per-task permission above. Record grants with
the other authorization in the consuming project's run records.
