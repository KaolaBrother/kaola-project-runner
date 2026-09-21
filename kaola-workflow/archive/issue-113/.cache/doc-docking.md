# Documentation docking — issue-113 (candidate 7c237c5)

Changed public behaviour:
1. The ZCode adapter now reports ACP stopReason `max_tokens` for the output-token-limit terminal.
2. The holder appends a `turn_ended` line to `events.jsonl`.

Checked against the AGENTS.md documentation map:

- CHANGELOG.md — FIXED in the candidate. The entry is the last item under `## 0.5.5 — unreleased`,
  and #112's entry is still first.
- docs/runner-v2-dual-transport-design.md — no impact. It already specifies stop_reason as a
  verbatim pass-through whose values include `max_tokens` (:110, :291, :303), and says `max_tokens`
  is not task completion (:321). The change makes ZCode conform to it.
- docs/api.md — no impact. It documents receipt fields (stop_reason passes through unchanged) and
  never lists events.jsonl kinds, so the additive `turn_ended` kind invalidates no sentence in it.
- docs/zcode-host.md, docs/acp-watch/{list-view,follow}.md — no impact. They reference specific
  kinds (worker_event_confirmed, process_exited, the follow NDJSON kinds), not an exhaustive list.
  The follow/view projection ignores unknown kinds, per the code review.
- README.md, templates/**, generated skills/ prose — no impact. No stop-reason or event-kind
  enumeration exists there. `render-skills.py --check` PASS with budgets OK; only the script copies
  were re-rendered.
- Setup, environment, architecture, examples — unchanged.

DOCKED
