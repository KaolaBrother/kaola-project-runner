# Profile catalog

Every supported runtime/preset with its owner-defined class and profile,
rendered from `platforms/<id>.yaml` (`<tier>_model_class`,
`<tier>_model_profile`). This is the full supported catalog, not a machine-local
choice list, and a listed row grants nothing. A local row needs the runtime to be
discovered on the bound execution target and its installed platform Runner to
declare the tier. The Host then fetches only exact locally available rows allowed
by current authorization
([worker-profiles.md](worker-profiles.md) §Local availability and authorized rows).

Each row's **Preset ID** `<platform>/<tier>` is its one stable ID (the manifest
platform id and its declared `--tier` word, e.g. `claude-code/default` vs
`claude-code/sonnet`, or `cursor-cli/default` vs `grok/default`): grants,
snapshots and authorization relays name a seat by that exact ID, and its Model
and parameters stay on the same row — never a second mapping. The ID names a
**configured preset**, not proof of the actually-running model: the manifest's
model name and native launch ID come from the declaration, while installation,
entitlement, applied selection and authorization remain separate facts (Droid's
`auto` and Devin's ACP display both drift from these names). An authorization
item carries `special_requirements` only when the owner actually supplied one;
absent means none.

| Class | Runtime | `--tier` | Preset ID | Model | Effort / parameters | Profile |
|---|---|---|---|---|---|---|
| Elite | Claude Code | `default` | `claude-code/default` | Opus | effort=high | All-round worker for every kind of task, especially strong at complex work, and preferred for the more complex and harder tasks. |
| Elite | Codex CLI | `default` | `codex/default` | GPT-6 Sol | effort=high | Good at exploring directions, finding problems, review, and computer use, but prone to over-engineering; set a clear scope and hold it to the minimal necessary solution. |
| Elite | Cursor CLI | `default` | `cursor-cli/default` | Grok 4.7 | effort=xhigh (encoded in model ID), fast=false | Investigates unfamiliar problems, explores solution paths, and autonomously carries them through implementation; well suited to long-running, adaptive work. |
| Elite | Cursor CLI | `opus` | `cursor-cli/opus` | Claude Opus 5.5 | effort=medium (encoded in model ID) | All-round worker for every kind of task, especially strong at complex work. |
| Elite | Devin CLI | `opus-fusion` | `devin/opus-fusion` | Opus Fusion (Opus 5.5 Medium + SWE-2 Medium) | effort=medium (encoded in model ID) | All-round worker for every kind of task, especially strong at complex work. |
| Elite | Droid | `default` | `droid/default` | Auto Model | no Runner effort override | All-round worker, balanced in every respect, suited to many kinds of tasks. |
| Elite | Droid | `opus` | `droid/opus` | Opus 5.5 | reasoning_effort=medium | All-round worker for every kind of task, especially strong at complex work. |
| Elite | Droid | `core` | `droid/core` | Kimi K3 | reasoning_effort=max | Strong at visual design and visual inspection, with good UI and design taste. |
| Elite | Grok CLI | `default` | `grok/default` | Grok 4.7 | effort=xhigh, fast=false | Suits exploratory, long-running autonomous work; give clear stage goals and exit conditions. |
| Elite | Kimi CLI | `default` | `kimi-cli/default` | Kimi K3 | thinking=max | Strong at visual design and visual inspection, with good UI and design taste. |
| Elite | Kimi CLI | `kimi-k2-8` | `kimi-cli/kimi-k2-8` | Kimi K2.8 | thinking=max | All-round implementation worker for every kind of hands-on development and implementation task. |
| Worker | Claude Code | `sonnet` | `claude-code/sonnet` | Sonnet | effort=max | Disciplined implementation worker; give it a detailed plan and constraints, and it excels at executing within them. |
| Worker | Codex CLI | `luna` | `codex/luna` | GPT-6 Luna | effort=max | Fast, flexible implementation worker with good reasoning for its class and computer-use capability; relatively exploratory and suited to tasks whose implementation path is not fully predetermined. |
| Worker | Devin CLI | `default` | `devin/default` | SWE-2 Max | effort=max (encoded in model ID) | Capable full-cycle engineering worker. |
| Worker | dsh | `default` | `dsh/default` | DeepSeek V4.1 Flash (OpenCode Go) | no Runner effort override | Fast implementation worker for tasks with clear goals and boundaries; emphasizes autonomous progress, iterative validation, and self-repair. |
| Worker | OpenCode | `default` | `opencode/default` | DeepSeek V4.1 Flash (OpenCode Go) | no Runner effort override | Fast implementation worker for tasks with clear goals and boundaries; tends to investigate deeper root causes and reduce unrelated changes. |
| Worker | ZCode | `default` | `zcode/default` | GLM 5.3 | thought=max | Autonomous engineering worker inclined to investigate, make decisions, iterate through failures, and carry substantial tasks toward completion with less hand-holding. |
| Expert | Claude Code | `fable` | `claude-code/fable` | Fable | effort=high | Design, goal definition and decomposition, issue creation, and review; only with explicit user permission for each task; no concrete implementation or execution, not a regular worker. |
| Expert | Codex CLI | `astra` | `codex/astra` | GPT-6 Astra | effort=high | Design, goal definition and decomposition, issue creation, and review; only with explicit user permission for each task; no concrete implementation or execution, not a regular worker. |
| Expert | Devin CLI | `fable` | `devin/fable` | Fable Fusion (Fable 5.1 High + SWE-2 Medium) | effort=high (encoded in model ID) | Design, goal definition and decomposition, issue creation, and review; only with explicit user permission for each task; no concrete implementation or execution, not a regular worker. |
