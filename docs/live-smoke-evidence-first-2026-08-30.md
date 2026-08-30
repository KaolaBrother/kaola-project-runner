# Evidence-first live tmux verification — 2026-08-30

Issue #7 was exercised through the candidate generated Skills in the Issue worktree. Every test used
an exact `kpr-issue7-live-*` tmux session and the platform's generated runner script. Inputs were not
sent with raw tmux commands. The verification prompts were read-only and prohibited claim, Git,
worktree, dispatch, finalize, Issue, and forge mutations.

The acceptance question was not whether a Runner classifier called the CLI idle or safe. It was
whether the Runner could identify the exact transport, deliver the controlling agent's literal input,
read the real output, correlate changed observations without refusing them, and report durable
Workflow/forge evidence.

## Results

| Platform | Runtime | Exact session | Evidence |
|---|---|---|---|
| Grok CLI | 1.0.13, Grok 4.6 xhigh | `kpr-issue7-live-grok` | A no-snapshot transport prompt returned `KPR_GROK_TRANSPORT_OK`. A second `workflow-next` prompt used an earlier snapshot; the receipt reported `observation_changed:true` and `result:sent`, and Grok returned `KPR_GROK_WORKFLOW_NEXT_RECEIVED`. |
| Claude Code | 2.1.246 | `kpr-issue7-live-claude-code` | Both the ordinary and changed-observation prompts reached the visible editor and were submitted. Claude replied `Login expired · Please run /login`; therefore command receipt passed but authenticated Workflow execution was not claimed. |
| OpenCode | 1.18.23 | `kpr-issue7-live-opencode` | The first prompt returned `KPR_OPENCODE_TRANSPORT_OK`. The second receipt linked old snapshot `kpr-snapshot-v2:3bf3e09079274e6b1327570c1f28d0a30d593c5aff77537ae63bcf3d1f84eaae` to action-time snapshot `kpr-snapshot-v2:5ad141cf5399c856490858850086eddc9427725f4e987960e99d336fd5492a8f`, reported `observation_changed:true`, and OpenCode returned `KPR_OPENCODE_WORKFLOW_NEXT_RECEIVED`. |
| Kimi CLI | 0.39.1 | `kpr-issue7-live-kimi-key` | The candidate Runner read the native trust screen, transferred Agent-selected `up` and `enter` through the new `key` API with exact SHA-256 receipts, then sent a no-tools prompt with payload receipt `sha256:3dde8aec824b31283e733f0ec53b6397026daf9d2ab217862186372fe7260deb`. Kimi created session `session_45e48ae3-6cf3-4c5d-ba24-86a0eeb6fd76` and replied `KPR_KIMI_BIDIRECTIONAL_OK`. Ordinary stop returned `stopped`; status returned `absent`. |
| Cursor CLI | 2026.08.25-3e8eec8, Cursor Grok 4.6 Extra High, FAST off | `kpr-issue7-cursor-grok46-no-fast` | Start showed the real `cursor_x=0` surface. The Agent opened native `/model`; the selected row was `Cursor Grok 4.6 — Extra High` with no `Fast` suffix and the selector reported `Max mode: OFF`. After explicit selection, the footer remained `Cursor Grok 4.6 Extra High`. Payload fingerprint `sha256:1b048ff9b62ff0eb05e10ba3848ba7134088154248d50ab39809d81709e38273` was sent and the model replied `KPR_CURSOR_GROK46_NO_FAST_OK`; exact stop returned `stopped` and status returned `absent`. |

Grok, OpenCode, and Cursor independently read the live Issue #7 state and the main checkout's
`kaola-workflow/issue-7/workflow-state.md` and `mission-list.md`. They agreed that Issue #7 was open,
had `workflow:in-progress` plus `<!-- kw:claim project=issue-7 -->`, and belonged to the active primary
Codex run with session marker `s-67569-mtf6e9by`. They did not claim or resume it.

## What the run proves

- A supplied earlier observation is audit correlation. Normal redraw or output change is returned as
  `observation_changed:true` and does not become `stale-snapshot` refusal.
- TUI coordinates, placeholder classification, activity, visible work, approval/decision prose, Git,
  and Workflow interpretations are evidence for the controlling agent, not generic action authority.
- Exact session ownership, platform/repository binding, single-pane relay identity, literal payload
  fingerprint, and submit/recovery attestation remain mechanical transport integrity. A Runner must
  not send to a foreign target or claim a mixed/unknown payload was transferred literally.
- Native login and trust choices remain visible to the agent. Removing Runner hard gates does not
  authorize the Skill to make a user-owned persistent choice.
- Cursor model choice is also Agent-owned. The strict experiment selected non-FAST Cursor Grok 4.6
  through the CLI's own UI and proved the choice before the prompt; the Runner only transported keys,
  prompt bytes, and output evidence.

## Kimi production-history corroboration

The pinned `KaolaTerminal Routine` Codex history provides an independent real production trace from
Kimi 0.39.1. Its first `start` returned `waiting-human` on the trust screen. Because the installed
Runner then had no native-key transport and treated that evidence as a hard gate, the controlling
Agent had to bypass it with raw `tmux send-keys ... Up Enter`. Afterward status/capture returned Kimi
session `session_95a6d844-df1a-4219-bd2e-0105cce6930a`; Runner `send` delivered the full project prompt,
Kimi read it, executed Workflow, and produced observable output over the long run. Issue #7 replaces
that raw-tmux gap with the attested `key` operation; the candidate live smoke above proves the same
trust → prompt → reply path entirely through Runner commands.

## Adjacent production evidence

The exact `vrpai-grok-pr-finalizer` automation was sampled read-only and preserved. Its Grok output was
advancing, but Workflow intake reported `target_set_conflicts_active_work` because linked completed
Issues retained claim residue (`workflow:in-progress` and matching `kw:claim` markers) despite an
`ORIGIN_PR_HANDOFF`. That is evidence against adding another inferred-state gate. Issue #7 removes the
Project Runner transport gates; claim-residue lifecycle cleanup remains a Kaola Workflow lifecycle
responsibility and must be corrected at that layer.

## Shutdown and residue

All five Issue #7 smoke session names, including the later `kpr-issue7-live-kimi-key` and
`kpr-issue7-cursor-grok46-no-fast`, were checked
after their terminal disposition. Grok, Claude, OpenCode, Kimi, and Cursor smoke sessions were absent.
The pre-existing `vrpai-grok-pr-finalizer` and
all unrelated tmux sessions were not stopped or modified. The final Cursor experiment used no project
materialization; its Workflow carrier and model choice remained external to this repository.
