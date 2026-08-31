# Managed Cursor CLI transport

The Runner starts the runtime as the exact child of a managed nested-PTY relay. A pre-relay session
may still be reported as `legacy-direct`; a running older relay remains readable but reports
`relay-upgrade-required` for mutation. The controlling agent chooses whether and when to restart only
that exact session at a safe boundary.

## Discover and give the evidence to the agent

```bash
scripts/runtime-tmux.sh observe --repo "$REPO" --session "$SESSION"
scripts/runtime-tmux.sh capture --repo "$REPO" --session "$SESSION" --lines 160
```

Read `raw_current_frame`, terminal coordinates, editor and approval observations, process/relay facts,
input/output offsets, Git facts, and any Workflow/forge evidence together. These are observations, not
Runner-owned state or authorization. The Skill does not decide whether the runtime is idle, busy,
waiting, complete, holding a draft, asking for approval, or safe to mutate. The controlling agent
decides what the evidence means and which action to take.

An observation may contain `snapshot_id` and `pane_revision` so later receipts can correlate an action
with what the agent previously saw. They are evidence identifiers, not freshness gates. A normal redraw,
new output, editor change, approval screen, process change, or Git/Workflow change is reported rather
than converted into `stale-snapshot` refusal.

Compatibility fields such as `activity_hint`, `editor_state`, `native_approval`,
`structured_decision_marker`, visible worker counts, and evidence flags may help the agent notice facts.
They never independently permit or prevent an agent-directed `send` or `stop`.

## Transfer the agent's prompt

After the agent chooses the prompt, transfer it directly:

```bash
scripts/runtime-tmux.sh send --repo "$REPO" --session "$SESSION" < prompt.txt
```

The optional legacy `--if-snapshot "$SNAPSHOT_ID"` argument only links the receipt to the earlier
observation. The compact receipt echoes it as `based_on_snapshot`; the Runner does not recapture it as
a freshness decision and still performs the requested transport when the relay can mechanically do so.

The relay performs one direct literal or bracketed-paste transfer and attests the payload fingerprint.
It does not stop the runtime child, disable pane input, acquire a lease, run a terminal fence, judge the
runtime prose, or decide whether the prompt was appropriate. Shell metacharacters remain literal input
rather than shell commands.

If the frame contains retained text, an approval, a trust/login screen, active output, or a human
decision, show it to the agent. The agent may still choose to send, use a tested whole-editor replacement,
start/resume a clean conversation, wait, or ask the user. The Skill does not turn any of those
observations into a policy gate.

## Transfer an Agent-selected native key

When a visible native selection screen needs a key, the Agent reads the screen and chooses one:

```bash
scripts/runtime-tmux.sh key --repo "$REPO" --session "$SESSION" --key up
scripts/runtime-tmux.sh key --repo "$REPO" --session "$SESSION" --key enter
```

The Runner accepts `up`, `down`, `left`, `right`, `enter`, `escape`, `tab`, `backtab`, or `space`.
It sends only the selected key bytes, adds no Enter, and attests their fingerprint. It neither infers
the option meaning nor chooses the key. Observe/capture again after every key.

## Read the response and verify durable evidence

After every transfer, observe and capture again:

```bash
scripts/runtime-tmux.sh observe --repo "$REPO" --session "$SESSION"
scripts/runtime-tmux.sh capture --repo "$REPO" --session "$SESSION" --lines 160
```

The Agent reads the real response and decides what happened. Enter or a successful transfer receipt is
not semantic success. If the Agent chose Workflow work, inspect the applicable durable Workflow, Git,
forge, validation, and cleanup evidence separately.

## Stop and capability-specific actions

An agent-directed ordinary stop does not require a snapshot and is not gated by activity, editor,
approval, decision, process-count, coordinate, prose, Git, or Workflow interpretations:

```bash
scripts/runtime-tmux.sh stop --repo "$REPO" --session "$SESSION"
```

`answer --replace-editor` is a tested whole-editor transport capability where an adapter implements it;
decision and snapshot identifiers are optional correlation evidence. An adapter that lacks that
mechanical capability reports `answer-unsupported`, after which the agent chooses another route.

The transport reports objective facts when it cannot mechanically complete the requested operation,
such as an absent exact session, unavailable or legacy relay, rejected literal input, disconnect, or
unknown transfer outcome. It reports those concrete facts without assigning semantic runtime state.

Payload and answer bytes are transferred as text, not terminal programs. If the relay cannot represent
a payload literally (for example unsupported terminal controls or multiline input without bracketed
paste), it reports that mechanical limitation before a partial write. This is a transport outcome, not
a runtime-status gate.

If a connection is lost before a direct-transfer receipt, partial mutation may be impossible to rule
out. The receipt then reports `mutation_performed:null`; it does not invent a successful recovery or
block later Agent judgment behind restoration metadata.
