# Issue #393 reproduction record

Issue: <https://github.com/KaolaBrother/kaola-project-runner/issues/393>
Tree: `main@be8a1ad9` (release v0.9.23 content `a56c3fa4` + pin `0685e558`)
Run branch: `workflow/issue-393`

## Reported symptom

After `git worktree remove`, a `cwd_repaired` notice reached the dsh worker seat
`dsh-vrpai-i2067-r186` as the full Host carrier: `/kaola-project-runner`,
`kaola-host-notify/1`, the heartbeat body and the one-pass Project Runner
instruction. The worker refused it. The report expects the cwd notice and the
Host heartbeat carrier to reach only a Host.

## Result

**Not reproducible on the v0.9.23 tree.** Every current-code variant delivers
the compact `kaola-worker-notify/1` notice to a worker, Expert, Sideagent or
unknown-role holder, even when a legacy argv arms that holder with
`--host-entry`. Only a holder running the **pre-#388** bytes reproduces the
reported carrier delivery.

The reported shape is the pre-#388 holder behaviour. v0.9.23 already contains
the #388 fix, and the release notes require running seats to restart because
`scripts/kaola-acp-holder.py` changed. A worker holder that was started before
the upgrade and kept alive still runs the old bytes; its holder process ignores
the role and sends the carrier. No current-code path can produce that prompt
for `dsh-vrpai-i2067-r186`.

No product code was changed in this run.

## Current-tree variants

Each variant uses one real holder process on the scripted ACP mock, one real
linked worktree, and one out-of-band `git worktree remove`. The mock logs every
`session/prompt`; the check reads the second prompt, which is the holder's own
`cwd_repaired` self prompt.

Commands (the direct variant, abbreviated):

```bash
python3 scripts/kaola-acp-holder.py \
  --record-dir <tmp>/records/dsh/<session>/<digest> \
  --socket <tmp>/holder.sock --repo <tmp>/repo \
  --platform dsh --session <session> --command "<mock agent>" \
  --host-entry /kaola-project-runner --host-name dsh \
  --shell-cwd-persistence persistent \
  --steer-method _session/steering --native-steering supported \
  --session-role <role> --accepted-revision ""
```

The prompt turn is admitted, the linked worktree is removed, the holder repairs
the path and stages `cwd_repaired`, and the turn end delivers the self prompt.

| # | Holder bytes | Recorded role | `--host-entry` | Self-prompt first line | Carrier | Heartbeat body |
|---|---|---|---|---|---|---|
| 1 | v0.9.23 (`db475e96`) | `worker` | `/kaola-project-runner` | `kaola-worker-notify/1: dsh session ...` | no | no |
| 2 | v0.9.23 | `null` (no `--session-role`) | `/kaola-project-runner` | `kaola-worker-notify/1: dsh session ...` | no | no |
| 3 | v0.9.23 | `host` | `/kaola-project-runner` | `/kaola-project-runner` | yes | yes |
| 4 | pre-#388 (`f46e1d4e^`) | `worker` | `/kaola-project-runner` | `/kaola-project-runner` | yes | yes |

Variant 4 is the only reproducing case. It runs the holder bytes from
`f46e1d4e^`, the commit before the #388 fix:

```bash
cp -R <run-tree>/scripts /tmp/kpr-pre388
git -C <run-tree> show f46e1d4e^:scripts/kaola-acp-holder.py \
  > /tmp/kpr-pre388/kaola-acp-holder.py
# then the direct-holder command above, with --session-role worker
# and --host-entry /kaola-project-runner
```

Its CLI also appended
`--host-entry` unconditionally; its holder selected the carrier on
`self.host_entry` alone:

```python
# f46e1d4e^ scripts/kaola-acp-holder.py
text, meta = (self._heartbeat_payload(staged, overflow_ready) if self.host_entry
              else self._worker_notice_payload(staged, overflow_ready))
```

v0.9.23 has both guards:

```python
# scripts/kaola-acp.py, command_start
if role == "host":
    holder_argv += ["--host-entry", args.manifest.get("host_skill_entry") or ""]

# scripts/kaola-acp-holder.py, _deliver_worker_events
carrier = self.host_entry and self.session_role == "host"
```

## CLI start variants

The same route through the current `kaola-acp.py` start seam (fixture dsh
manifest with `shell_cwd_persistence: persistent`):

- fresh worker `start --tier default`: record `session_role: worker`,
  `host_skill_entry: ""`; cwd-repair self prompt is compact;
- `start --resume <acp_id>` with no tier/model/effort (resume-preserved):
  record `session_role: worker`, `host_skill_entry: ""`; compact;
- `drain-restart --resume <acp_id>` with the recorded selection: record
  `session_role: worker`, `host_skill_entry: ""`; compact.

These are pinned by `tests/contract/test-issue-393-cwd-carrier.py` and pass in
the focused suite run (see `validation.md`).

## Path audit

- `host_session()` accepts only `<platform>-<project>-orchestrator-<purpose>`
  names and excludes `-i<N>-` names. `dsh-vrpai-i2067-r186` cannot be a Host by
  name, so `session_role_value()` returns the selected preset class (`Worker`
  for the dsh default) or null.
- `record_start_evidence` sends only `session_role`; it never changes
  `host_entry`. A resume-preserved start with an unknown role is spawned with no
  `--host-entry`; the later inherited role cannot arm a carrier.
- `rebind-host` moves `heartbeat_host` only; it does not change the role or add
  an entry.
- The holder does not re-read `session_role` from its record to arm a carrier.
- `status` reports `stale: true` and `restart_files` when a recorded
  restart-required file (`kaola-acp-holder.py` included) changed on disk after
  the holder started. This is the existing signal that a live seat needs the
  restart the release notes require.

## Supporting local evidence

A read-only scan of the local ACP record root (`/tmp/kaola-501`) found 105
`worker_event_delivered` records that carried a staged `cwd_repaired` and a
`heartbeat_fingerprint`:

- 104 were delivered by holder build `55072ca6c5e7` (pre-#388), with recorded
  roles `worker`, `expert`, `elite` and `sideagent`;
- 1 was delivered by holder build `db475e966dc8` (v0.9.23), and its recorded
  role was `host`.

This is local corroboration, not vrpai evidence: the vrpai worker's
`runner_build` was not available in the issue. It matches the reproduction
above: the carrier route is reachable only from pre-#388 holder bytes.

## What was tried

1. Fresh dsh worker, real linked worktree removed, self prompt inspected.
2. Resume-preserved worker after `stop`, then the same removal and delivery.
3. `drain-restart` of a worker, then the same removal and delivery.
4. Direct holder with worker role and a legacy `--host-entry`.
5. Direct holder with no role and a legacy `--host-entry`.
6. Direct Host holder as the positive control.
7. The same direct worker route on the pre-#388 holder bytes (historical
   control; the only reproducing variant).
8. Record and event scan of the local ACP sessions for pre-#388 vs current
   carrier deliveries.

## Host check before closing

The one fact that decides the incident is the vrpai worker holder's build:

- If the worker record says `runner_build: db475e966dc8` (v0.9.23 holder),
  `session_role: worker`, `host_skill_entry: /kaola-project-runner`, and
  `status` reports `stale: false`, then this non-reproduction is incomplete:
  capture that record and its cwd-repair events before closing.
- If the record says an older build (local pre-#388 seats report
  `55072ca6c5e7`), or `status.stale` is true with
  `restart_files: ["kaola-acp-holder.py"]`, the incident is the known
  live-seat condition: restart the worker seat so it loads the role-gated
  holder, and confirm the next `cwd_repaired` self prompt is
  `kaola-worker-notify/1`.

## Conclusion

The current tree does not reproduce #393. The report is consistent with a live
worker holder that was started before #388 and not restarted after the v0.9.23
holder change. The correct recovery is the one the release already names:
restart the seat so it loads the role-gated holder. Under the repro-first rule
this run changes no product code; it adds regression coverage for the route and
records the non-reproduction for the Host.
