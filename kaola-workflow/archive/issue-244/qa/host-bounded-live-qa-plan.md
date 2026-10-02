# Host live QA plan — issue 244

Prepared for the Host. Do not start, send, collect, or stop from the
implementation seat. Adopt or edit this plan, then run it against `$REPO`.
Simple exact presets: the two research items skip a drafting model. The third
item is the one Sidekick synthesis.

## Variables

```bash
REPO="<canonical git root of the consumer>"
WT="<checkout that contains the rendered entry>"
ENTRY="$WT/skills/kaola-project-runner/scripts/kaola-dispatch.py"
SKILLS="$WT/skills"
AUTH="$WT/.kaola/i244-auth.json"
AVAIL="$WT/.kaola/i244-avail.json"
LIVE="$WT/.kaola/i244-live.json"
PLAN="$WT/.kaola/i244-plan.json"
INDEX="$WT/.kaola/i244-index.json"
SIDE_PLAN="$WT/.kaola/i244-sidekick-plan.json"
SESSION_A="<platform-a>-KPR-i244-research-a"
SESSION_B="<platform-b>-KPR-i244-research-b"
SESSION_S="<sidekick-platform>-KPR-i244-sidekick"
```

## Isolated candidate bytes

Shared user Skill roots stay on the released install. Do not run
`install-local.sh --runtime` or `--skills-dir` into `~/.cursor/skills`,
`~/.agents/skills`, `~/.codex/skills`, `~/.claude/skills`, `~/.zcode/skills`,
or any other released root.

The candidate checkout already contains the new holder and `kaola-acp.py`.
Each platform `runtime-tmux.sh` execs the `kaola-tmux.sh` beside it, and that
script sets `ACP_CLI` to the sibling `kaola-acp.py`. `--skills-root "$SKILLS"`
with `SKILLS="$WT/skills"` therefore starts the candidate holder. The worker
CLI may still load its released user Skill text. That text is not the holder
process. In a mixed-build state, `--skills-root` of a full Skill tree (one
that contains `SKILL.md`) refuses by design with `worker-skill-build-skew`;
the isolated route is a runner-scripts harness without `SKILL.md`, which is a
checkout-class invocation and the guard does not apply — that is what the Host
used at `/tmp/i244-qa-skills` with byte-compared candidate scripts.

```bash
export KAOLA_ACP_RECORD_ROOT="$WT/.kaola/i244-records"
mkdir -p "$KAOLA_ACP_RECORD_ROOT"
cmp "$WT/scripts/kaola-acp-holder.py" \
  "$SKILLS/zcode-kaola-project-runner/scripts/kaola-acp-holder.py"
cmp "$WT/scripts/kaola-acp.py" \
  "$SKILLS/zcode-kaola-project-runner/scripts/kaola-acp.py"
```

Export `KAOLA_ACP_RECORD_ROOT` in the same shell as `survey`, `list`,
`execute`, `collect`, the mismatch probe, and `stop`. Dispatch inherits it.
A direct `list` or `send` uses `"$WT/scripts/kaola-acp.py"`, not a copy from
a released skill root.

After the two research items are `admitted`, one wrong-holder send must
refuse without a new turn:

```bash
python3 "$WT/scripts/kaola-acp.py" <platform-a> send \
  --repo "$REPO" --session "$SESSION_A" --no-wait \
  --text "binding probe; do not edit files" \
  --expected-holder-instance-id "not-the-live-holder"
```

Expect `error.code` `holder-instance-mismatch` and `mutation_status`
`not_started`. Then continue collection. The admission send already passed
the live holder id.

Use three presets the read-only survey marks `present`. Prefer Worker-pool
defaults, for example `zcode/default` and `dsh/default` for the two research
items and `opencode/default` for the Sidekick. If a preferred preset is
absent, pick another present authorized preset. Do not substitute a silent
fallback, and do not grant Elite or Expert for this QA. Do not log in.

Prompts are read-only. They must not edit, stage, commit, or delete.

## 1. Candidate view

```bash
python3 "$WT/scripts/kaola-acp.py" survey
```

Write `$AVAIL` with `present` and `absent` from that survey. `$AUTH` records
the Worker pool as already authorized: no Elite grant, no Expert grant, no
extra `elite_cap`. Exclusions stay as the current authorization records them.

```bash
python3 "$ENTRY" project \
  --authorization "$AUTH" --availability "$AVAIL" --platforms "$WT/platforms"
```

Record `capability_summary.text` and the three chosen candidates' exact ids,
Class, and selection. Unknown availability stays in `candidates` and is not a
mismatch. A present Expert must not appear unless this authorization already
granted it.

## 2. Two independent research outputs

`$PLAN` scope is `research`, repo is `$REPO`, and there is no `seat_cap`.
The two items do not share a write path, desktop, account, or port.

```json
{
  "scope": "research",
  "repo": "$REPO",
  "items": [
    {
      "item_id": "research-a",
      "preset": "<present pool preset A>",
      "session": "$SESSION_A",
      "prompt": "Read-only. Do not edit files. From templates/orchestrator/references/dispatch-collect.md, write at most eight lines: how an execute admission differs from a collected result, and who accepts. Stop there."
    },
    {
      "item_id": "research-b",
      "preset": "<present pool preset B>",
      "session": "$SESSION_B",
      "prompt": "Read-only. Do not edit files. From templates/orchestrator/references/dispatch-collect.md, write at most eight lines: which receipt fields are applied selection evidence, and what a timeout or an unapplied value must be reported as. Stop there."
    }
  ]
}
```

Fresh live facts, then admit:

```bash
python3 "$WT/scripts/kaola-acp.py" list --repo "$REPO" > "$LIVE"
python3 "$ENTRY" execute \
  --plan "$PLAN" --authorization "$AUTH" --availability "$AVAIL" \
  --platforms "$WT/platforms" --skills-root "$SKILLS" \
  --index "$INDEX" --live "$LIVE"
```

Expect both items `in-flight`, reason `admitted`, `acceptance` `pending`.
Record each `holder_instance_id`, `prompt_fingerprint`, `dispatch_event_cursor`,
and `selection.source`. Do not treat this index as a finished report.

## 3. Collection

On a later beat, without waiting for the slower item to be the gate:

```bash
python3 "$ENTRY" collect --index "$INDEX" --skills-root "$SKILLS"
```

A finished branch becomes `returned` / `collected` with `result.excerpt` and
evidence pointers. `acceptance` stays `pending`. The other branch may still
be `in-flight`. Repeat `collect` once the slower branch has a completed turn.
Idle or an ack with no completed turn stays `in-flight` / `no-result`.

Record both excerpts. The Host decides they answer the two prompts. The entry
does not accept them.

## 4. Sidekick synthesis

After both excerpts exist, adopt one new one-item plan. Paste the two
excerpts into the prompt. Do not ask the Sidekick to start workers.

```json
{
  "scope": "report",
  "repo": "$REPO",
  "items": [
    {
      "item_id": "sidekick",
      "preset": "<present sidekick preset>",
      "session": "$SESSION_S",
      "role": "sidekick",
      "prompt": "Read-only. Do not edit files. Using only the two excerpts below, write at most ten lines: what a later collect must show before the Host can accept, and what must stay unknown. Excerpts: <paste research-a and research-b>. Stop there."
    }
  ]
}
```

`execute` that plan into the same index or a second index, then `collect`
until the Sidekick item is `returned` / `collected`. `acceptance` stays
`pending` until the Host accepts the ten lines.

## 5. Reclamation

Exact-stop each of the three sessions with its platform Runner, `$REPO`, and
the holder from that item. Do not stop any other session.

```bash
"$SKILLS/<platform>-kaola-project-runner/scripts/runtime-tmux.sh" stop \
  --repo "$REPO" --session "$SESSION" \
  --expected-holder-instance-id "$HOLDER"
```

Record the three stop receipts. `residual_pids` for those sessions must be
`[]`.
