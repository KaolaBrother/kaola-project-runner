# Managed OpenCode transport

The Runner starts the runtime as the exact child of a managed nested-PTY relay. A pre-relay session
may still be reported as `legacy-direct`, but it cannot receive input or be stopped through this
control plane. Preserve that session until the user explicitly authorizes migration through the
runtime's continue or resume mechanism.

## Observe before mutation

```bash
scripts/runtime-tmux.sh observe --repo "$REPO" --session "$SESSION"
```

Only schema-v2 observations with `result: observed`, `relay.managed: true`, and a non-null
`snapshot_id` can authorize an action. Activity is advisory; it never substitutes for the exact
owner, platform, repository, stable pane, relay, child, TUI, editor, and snapshot checks.

Use the same unmodified repository spelling and the exact stable tmux pane identity reported by the
Runner. Do not use window or pane indexes as authority. The relay briefly quiesces and fences the
child to produce the snapshot; callers must not reproduce that sequence with raw tmux commands.

## Guarded actions

An ordinary prompt requires an empty editor and the exact fresh snapshot:

```bash
scripts/runtime-tmux.sh send --repo "$REPO" --session "$SESSION" \
  --if-snapshot "$SNAPSHOT_ID" --require-empty-editor < prompt.txt
```

Stopping, including a user-authorized force stop, also requires the exact fresh snapshot:

```bash
scripts/runtime-tmux.sh stop --repo "$REPO" --session "$SESSION" \
  --if-snapshot "$SNAPSHOT_ID"
```

The `answer` command is capability-gated. A supported adapter requires the exact decision ID,
snapshot, and `--replace-editor`; its receipt contains fingerprints, not plaintext. An adapter
without a reviewed whole-editor replacement returns `answer-unsupported`. After an answer, do not
send more input while its later-output barrier is `pending` or `output-seen`; observe again until a
later changed visible frame revision reports `satisfied`.

Every mutation reacquires the relay lease and rechecks the complete identity and snapshot immediately
before bytes are prepared, then binds the prepared editor to the requested payload and revalidates
the complete surface before Enter is submitted. The terminal fence accepts only its exact nonce
reply; any unrelated outer-PTY byte, including a separately queued next read, refuses the action and
is discarded rather than replayed. Authenticated progress checkpoints renew a bounded verification phase;
silence or disconnect still restores the exact child and pane input on the short lease. A stale
snapshot, unknown or nonempty editor, approval surface, process ambiguity, relay disconnect, or
recovery uncertainty is a refusal, not a reason to bypass the guard.

Prompt and answer payloads are text, not terminal programs. CR, ESC, DEL, other C0/C1 controls, and
embedded bracketed-paste delimiters are refused before any child PTY write. LF and TAB are accepted
only while the relay attests that the child enabled bracketed paste. Runtime descendants that escape
the original child process group remain fingerprint-tracked: guarded actions quiesce them, and force
stop does not report success until the exact tracked processes are absent.
