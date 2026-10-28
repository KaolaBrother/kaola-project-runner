# Profile catalog

Every supported runtime/preset with its owner-defined class and profile, rendered
from `platforms/<id>.yaml` (`<tier>_model_class`, `<tier>_model_profile`). Full
supported catalog, not a machine-local choice list; a listed row grants nothing. A
local row needs the runtime discovered on the bound target and its installed Runner
declaring the tier; the Host fetches only exact rows current authorization allows
([worker-profiles.md](worker-profiles.md) §Local availability and authorized rows).
A preset may set `<tier>_model_roles` to `computer-use-only` (absent means none;
unknown rejects); this table has no column for it.

Each row's **Preset ID** `<platform>/<tier>` is its stable ID (manifest id plus
declared `--tier`, e.g. `claude-code/default` vs `claude-code/opus-xhigh`, or
`cursor-cli/default` vs `grok/default`). Grants, snapshots and relays name a seat by
that exact ID; Model and parameters stay on the same row — never a second mapping.
The ID names a **configured preset**, not the running model: name and native launch
ID are declarations; installation, entitlement, applied selection and authorization
are separate facts (Droid's `auto` and Devin's ACP display both drift).
`claude-code/default` and `claude-code/opus-xhigh` both declare native launch ID
`opus`; that alias is not a preset ID. An authorization item carries
`special_requirements` only when the owner actually supplied one; absent means none.

| Class | Runtime | `--tier` | Preset ID | Model | Effort / parameters | Profile |
|---|---|---|---|---|---|---|
| Elite | Antigravity | `default` | `antigravity/default` | Gemini 4 Argon | effort=medium (encoded in model ID) | Strong implementation worker for well-scoped build tasks: features, UI and 3D, frontend and backend code, refactors, and tests. Strong language expression in English and Chinese. Sometimes reports work, files, or results that do not exist, so every output must be independently reviewed by another seat before it is accepted. Never use as a reviewer, verifier, or for acceptance decisions. |
| Elite | Antigravity | `xhigh` | `antigravity/xhigh` | Gemini 4 Argon | effort=high (encoded in model ID) | Higher-effort Argon tier for harder or larger implementation tasks; slower and uses more quota. Strong language expression in English and Chinese. Same limits: every output must be independently reviewed by another seat before it is accepted, and it must never be used as a reviewer, verifier, or for acceptance decisions. |
| Elite | Antigravity | `opus` | `antigravity/opus` | Claude Opus 5.5 | effort=high (encoded in model ID) | Strong at UI and 3D design implementation only; Opus level for UI and 3D work that needs more depth than the Argon tiers. Strong language expression in English and Chinese within UI and 3D implementation. Do not use for any other task (research, design docs, review, backend, debugging, investigation). |
| Elite | Claude Code | `default` | `claude-code/default` | Opus 5.5 | effort=high | All-round execution worker, especially strong at complex execution work and UI and 3D visual implementation. |
| Elite | Claude Code | `opus-xhigh` | `claude-code/opus-xhigh` | Opus 5.5 | effort=xhigh | Plans, designs, and reviews difficult, complex work and handles deep reasoning tasks, with particular strength in UI and 3D visual design and review; does not perform implementation. |
| Elite | Claude Code | `sonnet` | `claude-code/sonnet` | Sonnet | effort=high | All-round execution worker, especially UI and 3D visual implementation. |
| Elite | Codex CLI | `default` | `codex/default` | GPT-6.1 Sol | effort=high | Do not use to implement. Strong at exploring directions, finding problems, and review; good at UI and 3D visual work, with computer-use capability. |
| Elite | Cursor CLI | `default` | `cursor-cli/default` | Grok 4.7 | effort=high (encoded in model ID), fast=false | Investigates unfamiliar problems, explores solution paths, and autonomously carries them through implementation; well suited to long-running, adaptive work. |
| Elite | Cursor CLI | `xhigh` | `cursor-cli/xhigh` | Grok 4.7 | effort=xhigh (encoded in model ID), fast=false | Escalation level: use it when the Cursor CLI default (Grok 4.7 high) cannot solve the task. |
| Elite | Cursor CLI | `opus` | `cursor-cli/opus` | Claude Opus 5.5 | effort=high (encoded in model ID) | All-round execution worker, especially strong at complex execution work and UI and 3D visual implementation. |
| Elite | Cursor CLI | `opus-xhigh` | `cursor-cli/opus-xhigh` | Claude Opus 5.5 | effort=xhigh (encoded in model ID) | Escalation level: use it when the Cursor CLI opus preset (Claude Opus 5.5 high) cannot solve the task. |
| Elite | Devin CLI | `opus-fusion` | `devin/opus-fusion` | Opus Fusion | effort=high (encoded in model ID) | All-round execution worker, especially strong at complex execution work. |
| Elite | Droid | `default` | `droid/default` | Auto Model | no Runner effort override | All-round worker, balanced in every respect, suited to many kinds of tasks. |
| Elite | Droid | `opus` | `droid/opus` | Opus 5.5 | reasoning_effort=high | All-round execution worker, especially strong at complex execution work and UI and 3D visual implementation. |
| Elite | Droid | `core` | `droid/core` | DeepSeek V4.1 Flash 1017 | reasoning_effort=max | Fast, low-cost worker for self-contained tasks with clear goals, boundaries, acceptance criteria; strong at 3D and frontend; one-pass complete features; iterative validation, self-repair. Review each output; split long chain. |
| Elite | Grok CLI | `default` | `grok/default` | Grok 4.7 | effort=high, fast=false | Suits exploratory, long-running autonomous work; give clear stage goals and exit conditions. |
| Elite | Grok CLI | `xhigh` | `grok/xhigh` | Grok 4.7 | effort=xhigh, fast=false | Escalation level: use it when the Grok Build default (Grok 4.7 high) cannot solve the task. |
| Elite | Kimi CLI | `default` | `kimi-cli/default` | Kimi K2.8 | thinking=max | All-round implementation worker for every kind of hands-on development and implementation task. |
| Elite | Kimi CLI | `kimi-k3-1-pro` | `kimi-cli/kimi-k3-1-pro` | Kimi K3.1 Pro | thinking=max | Strong all round worker. Strong at visual design and visual inspection, with good UI and design taste. |
| Worker | Claude Code | `haiku` | `claude-code/haiku` | Claude Haiku | effort=high | Fast all-round execution worker, well suited to well-scoped work, especially UI and 3D visual implementation. |
| Worker | Codex CLI | `terra` | `codex/terra` | Codex Terra | effort=high | Computer-use and research worker: GUI/browser/desktop QA with screenshots and verdicts; not Expert design/planning, nor Elite substitute when a better Elite seat exists. |
| Worker | Devin CLI | `default` | `devin/default` | SWE-2 | effort=max via ACP option thought_level | Capable full-cycle engineering worker. |
| Worker | dsh | `default` | `dsh/default` | DeepSeek V4.1 Flash | effort=max via ACP option reasoning_effort | Fast, low-cost worker for self-contained tasks with clear goals, boundaries, acceptance criteria; strong at 3D and frontend; one-pass complete features; iterative validation, self-repair. Review each output; split long chain. |
| Worker | dsh | `commandcode` | `dsh/commandcode` | DeepSeek V4.1 Flash (Command Code) | effort=max via ACP option reasoning_effort | Fast, low-cost worker for self-contained tasks with clear goals, boundaries, acceptance criteria; strong at 3D and frontend; one-pass complete features; iterative validation, self-repair. Review each output; split long chain. |
| Worker | OpenCode | `default` | `opencode/default` | DeepSeek V4.1 Flash | effort=max via ACP option effort | Fast implementation worker for tasks with clear goals and boundaries; tends to investigate deeper root causes and reduce unrelated changes. |
| Worker | ZCode | `default` | `zcode/default` | GLM 5.3 | thought=max | Autonomous engineering worker inclined to investigate, make decisions, iterate through failures, and carry substantial tasks toward completion with less hand-holding. |
| Expert | Claude Code | `fable` | `claude-code/fable` | Fable | effort=high | Design, goal definition and decomposition, issue creation, and review; only under an explicit task or standing grant; no concrete implementation or execution, not a regular worker. |
| Expert | Codex CLI | `astra` | `codex/astra` | GPT-6 Astra | effort=high | Design, goal definition and decomposition, issue creation, and review; only under an explicit task or standing grant; no concrete implementation or execution, not a regular worker. |
| Expert | Devin CLI | `fable` | `devin/fable` | Fable Fusion | effort=high (encoded in model ID) | Non-visual design, goal definition and decomposition, issue creation, and review; not strong at UI or other visual design. Only under an explicit task or standing grant; no concrete implementation or execution, not a regular worker. |
