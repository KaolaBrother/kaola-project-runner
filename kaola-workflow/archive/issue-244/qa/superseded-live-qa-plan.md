# Superseded live QA plan (issue 244, first candidate)

This file is the run's earlier Host plan. It was not executed. Absolute paths
below are historical evidence from that draft. The current Host plan is
`host-bounded-live-qa-plan.md` in this directory. The consumer guide is
`docs/dispatch-collect.md`. The checkout-only isolated-bytes note is
`isolated-candidate-bytes.md` in this directory.

# Issue #244 live QA plan

Host-owned. The implementation worker does not start, send, or stop these
sessions. Adopt or adjust this plan, then run it with the canonical `--repo`.
Simple exact presets: skip the Sidekick.

## Guardrails

- Canonical `--repo`: `/Users/ylmacstudio/Workspace/kaola-project-runner`
- Worktree that contains this entry: `/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-244`
- Do not log in, relogin, or repair credentials.
- Do not stage, modify, or delete `docs/harness-acp-compat-2026-10-01.md` or
  `docs/harness-acp-reverify-2026-10-01.md`.
- Prompts are read-only. They must not edit the repository or commit.
- Presets are Worker-pool defaults only. Do not grant Elite or Expert for this
  QA, and do not substitute a preset that survey did not mark present.
- Exact-stop every session this plan starts. `residual_pids` must be `[]`.

## 1. Confirm the loaded entry

From the worktree, after `./scripts/render-skills.py --write`:

```bash
WT="/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-244"
REPO="/Users/ylmacstudio/Workspace/kaola-project-runner"
ENTRY="$WT/skills/kaola-project-runner/scripts/kaola-dispatch.py"
SKILLS="$WT/skills"
```

The Host's loaded Project Runner guidance should name `dispatch-collect.md`,
the capability summary, and explicitly scoped Sidekick light work. Record the
installed-or-worktree path actually loaded.

## 2. Availability

Use the existing read-only survey. Do not authenticate.

```bash
python3 "$WT/scripts/kaola-acp.py" survey
```

Mark a preset `present` only when that survey reports the runtime present.
Suggested pool presets, in order, if present:

1. `zcode/default` — session `zcode-KPR-i244-qa1`
2. `dsh/default` — session `dsh-KPR-i244-qa2`

If only one is present, run the single-item plan. If neither is present, do
not substitute; record the survey and stop this QA without a start.

## 3. Project the candidates

Write `/tmp/kpr-i244-auth.json` with the run's durable grants. For this QA the
Worker pool needs no Elite grant and no Expert grant. Exclusions stay as the
current authorization actually records them.

Write `/tmp/kpr-i244-avail.json` with `present` and `absent` from the survey.

```bash
python3 "$ENTRY" project \
  --authorization /tmp/kpr-i244-auth.json \
  --availability /tmp/kpr-i244-avail.json \
  --platforms "$WT/platforms"
```

Expect `zcode/default` and, when present, `dsh/default` in `candidates` with
catalog profiles, and `capability_summary.classes.Expert` false unless the
current authorization already has a present Expert grant. Do not treat unknown
availability as a mismatch.

## 4. Adopted plan

`/tmp/kpr-i244-plan.json`, scope `research`, repo the canonical root. One item
if only ZCode is present; both items when both runtimes are present. No
`seat_cap` (pool seats are not capped here). No shared writes, desktop,
account, or ports.

```json
{
  "scope": "research",
  "repo": "/Users/ylmacstudio/Workspace/kaola-project-runner",
  "items": [
    {
      "item_id": "qa1",
      "preset": "zcode/default",
      "session": "zcode-KPR-i244-qa1",
      "prompt": "Read-only. Do not edit, stage, commit, or delete anything. Do not touch docs/harness-acp-compat-2026-10-01.md or docs/harness-acp-reverify-2026-10-01.md. Reply with exactly: KPR-i244-qa1-ok"
    },
    {
      "item_id": "qa2",
      "preset": "dsh/default",
      "session": "dsh-KPR-i244-qa2",
      "prompt": "Read-only. Do not edit, stage, commit, or delete anything. Do not touch docs/harness-acp-compat-2026-10-01.md or docs/harness-acp-reverify-2026-10-01.md. Reply with exactly: KPR-i244-qa2-ok"
    }
  ]
}
```

Drop `qa2` when DSH is not present.

```bash
python3 "$ENTRY" execute \
  --plan /tmp/kpr-i244-plan.json \
  --authorization /tmp/kpr-i244-auth.json \
  --availability /tmp/kpr-i244-avail.json \
  --platforms "$WT/platforms" \
  --skills-root "$SKILLS" \
  --index /tmp/kpr-i244-index.json
```

## 5. Evidence to record

From `/tmp/kpr-i244-index.json`:

- each item `status` is one of `returned`, `failed`, `unknown`, `not-run`
- `correlation_only` is true
- for a `returned` item: `preset`, `session`, `holder_instance_id`, `repo`,
  `prompt_fingerprint`, `dispatch_event_cursor`, and `selection` showing
  requested `zcode/default` or `dsh/default` with `--tier default` (no
  substituted tier)
- `selection.comparison` may be `unknown` when the runtime does not echo a
  model; that is not a mismatch and not a reason to relogin
- coverage lists every item

Then, on the Host's later beat, `observe` / `capture` the same session from
the dispatch cursor and confirm the reply marker. That observation is the
Host's, not a second execute.

## 6. Reclamation

For each session this plan started, exact-stop with that platform's Runner
and the canonical repo. Record the stop receipt. `residual_pids` must be
`[]`. Do not stop sessions this plan did not start.

```bash
"$SKILLS/zcode-kaola-project-runner/scripts/runtime-tmux.sh" stop \
  --repo "$REPO" --session zcode-KPR-i244-qa1
"$SKILLS/dsh-kaola-project-runner/scripts/runtime-tmux.sh" stop \
  --repo "$REPO" --session dsh-KPR-i244-qa2
```

Run the second command only if qa2 was started.

## Correction

The implementation worker prepared this plan and did not run it. An earlier
brief had asked that worker to drive live sessions; the Host correction moved
start, send, and stop here.
