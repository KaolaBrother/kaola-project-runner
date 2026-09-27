# Worker profiles

One user-defined line per runtime preset, rendered from `platforms/<id>.yaml`
(`<tier>_model_profile`). It is selection guidance from use, not a measured
capability, price, or benchmark; it never changes a preset's model, effort, or
Fast and never gates `start`. An empty profile is unset. Read the rows you need
when choosing a worker, or a preset for a seat authorized to switch; the Host
judges, nothing scores or routes.

| Runtime | `--tier` | Model | Parameters | Profile |
|---|---|---|---|---|
| Claude Code | `default` | Opus | effort=high | All-round worker, suited to taking on the more complex work. |
| Claude Code | `fable` | Fable | effort=high | Design, goal definition and decomposition, issue creation, and review; only when the user explicitly asks or permits; no heavy execution, not a regular worker. |
| Claude Code | `sonnet` | Sonnet | effort=max | Low-cost worker for tasks whose goal and boundaries are already clearly defined; default effort max. |
| Codex CLI | `default` | GPT-6 Sol | effort=high | Good at exploring directions, finding problems, review, and computer use, but prone to over-engineering; set a clear scope and hold it to the minimal necessary solution. |
| Codex CLI | `astra` | GPT-6 Astra | effort=high | Design, goal definition and decomposition, issue creation, and review; only when the user explicitly asks or permits; no heavy execution, not a regular worker. |
| Codex CLI | `luna` | GPT-6 Luna | effort=max | Low-cost worker for tasks whose goal and boundaries are already clearly defined; default effort max. |
| Cursor CLI | `default` | Grok 4.7 | effort=xhigh (encoded in model ID), fast=false | Suits exploratory, long-running autonomous work, but prone to looping; give clear stage goals and exit conditions. |
| Cursor CLI | `opus` | Claude Opus 5.5 | effort=medium (encoded in model ID) | All-round worker for every kind of task, especially strong at complex work. |
| Devin CLI | `default` | SWE-2 Max | effort=max (encoded in model ID) | Very low-cost, capable main execution worker, but somewhat slow. |
| Devin CLI | `opus-fusion` | Opus Fusion (Opus 5.5 Medium + SWE-2 Medium) | effort=medium (encoded in model ID) | All-round worker for every kind of task, especially strong at complex work. |
| Devin CLI | `fable` | Fable Fusion (Fable 5.1 High + SWE-2 Medium) | effort=high (encoded in model ID) | Design, goal definition and decomposition, issue creation, and review; only when the user explicitly asks or permits; no heavy execution, not a regular worker. |
| Droid | `default` | Auto Model | no Runner effort override | All-round worker, balanced in every respect, suited to many kinds of tasks. |
| Droid | `opus` | Opus 5.5 | reasoning_effort=medium | All-round worker for every kind of task, especially strong at complex work. |
| Droid | `core` | Kimi K3 | reasoning_effort=max | Strong at visual design and visual inspection, with good UI and design taste. |
| dsh | `default` | DeepSeek V4.1 Flash (OpenCode Go) | no Runner effort override | Low-cost, fast implementation worker for tasks with clear goals and boundaries. |
| Grok CLI | `default` | Grok 4.7 | effort=xhigh, fast=false | Suits exploratory, long-running autonomous work, but prone to looping; give clear stage goals and exit conditions. |
| Kimi CLI | `default` | Kimi K3 | thinking=max | Strong at visual design and visual inspection, with good UI and design taste. |
| Kimi CLI | `kimi-k2-8` | Kimi K2.8 | thinking=max | All-round implementation worker for every kind of hands-on development and implementation task. |
| OpenCode | `default` | CLI native opening model | no Runner model or effort override |  |
| ZCode | `default` | GLM 5.3 | thought=max | All-round worker for every kind of routine work, but not good at visual tasks. |

## Seat binding and model switching

A seat keeps its bound platform and preset; general dispatch authorization is
not a switch grant. Only a user's explicit grant for a particular seat lets the
Host select or switch that seat's model/preset, within the scope the user
allowed and the same agent runtime, without asking again for each switch under
that grant. Never switch across runtimes. The same seat switches only when
idle, through the existing `drain-restart --resume ID` (or `--continue`) with an
explicit `--tier`/`--model`: an exact stop and resume, not a live hot switch (a
busy seat refuses `drain-not-idle`). A new standard-named seat is a new seat,
not a switch of this one. No new flow. Fable, Fable Fusion, and Astra keep their explicit-permission and usage
limits; a grant that already names them needs no repeated permission. Record
the grant with the other authorization in the consuming project's run records.
