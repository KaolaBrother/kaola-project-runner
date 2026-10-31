# Lifecycle recovery and continuity

## Sideagent binding

The Host starts the Sideagent, then sets `--section sideagent`
`{"platform","session","preset","state":"active"}`; it may add
`holder_instance_id` once. To replace, the Host marks `replacing`/`failed`,
starts and binds a successor. The successor continues from state and
receipts and replays no admitted work. A stop spares workers it dispatched. A
superseded seat's late write is `binding-superseded`. The Host repairs a
failed Sideagent record; if both fail, the Delegator recovers the Host first.

## Events

`execute` records the real dispatcher (`KAOLA_ACP_DISPATCHER`) apart from the
notify target. Workers report to the live Host holder (`sideagent-host`). A
Host advertising `sideagent-relay/1` relays them to the bound Sideagent and
wakes the Host only when attention changed. A dead, failed, or cancelled turn
returns them. Delivery is at-least-once. `"mode": "node"` keeps events with
the Host ([sideagent-node.md](sideagent-node.md)). After a Host stop kept its
seats, the new Host runs `rebind-host` for that seat only. `unknown-op`:
`drain-restart` the seat at idle.

## Never-indexed Host attestation

For accepted-done tasks with every ref absent from all supplied project indices,
Host may pass `J={"kind":"refs-host-attested","bindings":[{"ref":"REF",
"session":"SESSION","locator":"LOCATOR"}]}`: one binding per distinct ref.
`L` must be a schema-valid live list. Locators are optional on the verified
route and required for every ref on the attested route. Each locator has the form `commit:path`,
an absolute path, or HTTP(S) URL; its contents are not verified. If every
session has a unique stopped/dead project row, the receipt records verified
anchors. If a session is absent, it records `attested` and every locator for
later audit, never `verified`. Active, mismatched or ambiguous rows refuse.
Sideagent returns both routes to Host. No ledger is created.

## Size

Rewriting an id replaces it; settled records leave in that write; an old
revision is `record-retired`. Never drop a duty. Host view max 64 KiB
(`host-view-too-large`). 1 MiB needs a recorded `carrier` advertising
`heartbeat-state/2`, else 64 KiB (`carrier-limit`); every write, `migrate
--write` included, uses it; only an owner stop uses the current bound. A
refusal names `$S migrate --live LIVE --write`. An unknown row with no
outcome retires on the stale-collect route (session absent or
stopped under the holder); `outcome: stopped` with `mutation_status: unknown`
retires on `stopped-collect-incomplete-turn` (Host; accepted task,
disposition, holder, platform, repo, stopped `L` rows match).
Neither writes index bytes. For `refs-host-attested` refusal, the Host checks
each task ref, live row and typed locator, then retries. An absent session
uses Host attestation; an active or ambiguous row must be resolved.

## Migration

After a Skill update run `$S migrate --index I --live L` at a safe point;
without `--write` it plans only. `--write` migrates `active`/`pending` rows,
maps `body.alerts` rows per nameable id, and keeps
`recovery.protected_untracked`. Other legacy names leave as `unverified`
locators; a critical mapping writes nothing. Migration uses that bound;
`--live` with a capable Host records `carrier`. Never write
`heartbeat-prompt.v1-<sha12>.json`. An unknown schema refuses. Repeats
report `current`. Migration grants nothing.

Live: Codex and ZCode, `rebind-host`.

## Touchpoints

Update at dispatch (`doing`), result/verdict, goal/grant/fault change, recovery
and closeout. `check` detects omissions. Link each result to its task goal and
next action or sourced blocker.
