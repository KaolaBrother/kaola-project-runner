# Issue #81 — Mission 2: upstream primary-source facts for the v4 steering path

Date: 2026-09-19. Primary sources only, pinned:

- `ZhouXiaolin/zcode-provider` @ `c7d06a077a97aea7352defccd147f187b9186fe3`
  (`main` HEAD, "chore: bump version to 0.5.0"), file `extensions/zcode-provider.ts`
  (1847 lines) — fetched via raw.githubusercontent.com.
- `william0wang/zcode-acp` @ `840f9f26d72118d3ff795a7ad3842d655f3b8713`
  (`main` HEAD), file `docs/PROTOCOL.md` (1047 lines).

## 1. Same channel — v4 rides the same `app-server` stdio NDJSON pipe (VERBATIM)

zcode-provider.ts:

```ts
function request (method: string, params?: unknown): Promise {
  startServer();
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(String(id), { resolve, reject });
    proc!.stdin!.write(JSON.stringify({ id, method, params }) + "\n");
  });
}
```

```ts
// Wire protocol (ZCode Protocol v1, NDJSON over stdio), verified live:
// request: {"id": N, "method": "...", "params": {...}}
// response: {"id": N, "result": {...}} | {"id": N, "error": {...}}
// srv->cli req: {"id": "server-N", "method": "...", "params": {...}}
// notification: {"method": "...", "params": {...}}
```

Entry point (zcode-provider.ts):

```ts
const ZCODE_CJS_PATHS = [
  "/opt/ZCode/resources/glm/zcode.cjs",                          // Linux
  "/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs",    // macOS
];
… return `node ${found ?? …} app-server`;
const SERVE_CMD = process.env.ZCODE_SERVE_CMD ?? defaultServeCmd();
```

zcode-acp README: "The server launches the ZCode headless app-server
(`zcode app-server --stdio`) as a subprocess." Both `app-server` and
`app-server --stdio` forms land on the same NDJSON pipe; all inbound frames
(`session/event`, `state.updated`, `v4/conversation/frame`) are parsed from
the one `child.stdout` and fanned to listeners. **No second channel exists.**

## 2. The guide flow, verbatim (zcode-provider.ts `setupGuideMode`, lines 1150-1252)

Step A — `v4/conversation/subscribe` (lines 1194-1201):

```ts
const sub = await request<{ ack?: { logEpoch?: string } }>(
  "v4/conversation/subscribe",
  {
    topic: `conversation/${sid}`,
    connectionId: `pi-${randomUUID()}`,
    clientMode: "desktop-continuous",
  },
);
```

Step B — frames arrive as `v4/conversation/frame` notifications (lines 1173-1190):

```ts
if (m.method !== "v4/conversation/frame" || typeof m.params?.topic !== "string") return;
const frameSid = m.params.topic.startsWith("conversation/")
  ? m.params.topic.slice("conversation/".length) : undefined;
const snap = m.params.frame?.payload?.snapshot;
if (typeof snap?.revision === "number") {
  st.snapshotRevision = snap.revision;
  st.revision = Math.max(st.revision, snap.revision);
  if (snap.logEpoch) st.logEpoch ??= snap.logEpoch;
}
if (m.params.frame?.payload?.kind === "snapshot") snapshotSeen = true;
```

Step C — CAS `setFollowupMode` via `v4/command` (lines 1220-1244):

```ts
const fm = await request<{ status?: string; reasonCode?: string }>(
  "v4/command",
  {
    commandId: `pi-fm-${nextId++}`,
    clientId: "pi-bridge",
    sessionId: sid,
    type: "setFollowupMode",
    payload: { mode: "guide" },
    baseRevision: cur?.snapshotRevision ?? cur?.revision ?? 0,
    baseLogEpoch: cur?.logEpoch,
    issuedAt: Date.now(),
  },
);
if (fm?.status !== "stale") return;
// retry up to 3 attempts after waiting for a newer frame revision
```

Step D — steer input via `v4/command` `sendText` (lines 1811-1819):

```ts
await request("v4/command", {
  commandId: `pi-steer-${nextId++}`,
  clientId: "pi-bridge",
  sessionId,
  type: "sendText",
  payload: { text: event.text, attachments: [] },
  issuedAt: Date.now(),
});
return { action: "handled" };
```

Upstream comments documenting semantics:

- (lines 1150-1154) "Enable ZCode-native 'guide' handling on a session: v4
  conversation subscription (creates the publisher whose inputRouting drives
  the delivery decision), then setFollowupMode guide (CAS). Best-effort: on any
  failure (unsupported build, CAS revision mismatch) the session stays in queue
  mode and sendText inputs are processed after the current turn."
- (lines 1800-1805) "a message typed in pi while the ZCode turn is running is
  sent straight to the running session via the v4 command channel (sendText).
  The app-server admits it as a guide input (injected at the next tool/message
  boundary) or falls back to a queue. Returning 'handled' keeps pi from
  duplicating it into its own next turn; on any failure we fall back to pi's
  normal queueing."
- README verbatim: "A message typed while the turn is running is sent to the
  running session via the v4 `sendText` command; ZCode injects it at the next
  tool/message boundary **inside the same turn** (`turn.steerQueued` →
  `turn.steerDrained`), falling back to a queue when the turn is not steerable
  or already has queued input. pi marks the message as handled, so it is not
  duplicated into the next turn."
- Revision sources (comment, lines ~520-523): "Track session revisions from
  session-scope state.updated notifications and the initial v4 conversation
  snapshot so the CAS setFollowupMode command can present a fresh baseRevision."
  `state.updated` notifications carry `scope==="session"`, `sessionId`,
  `revision`.

**Upstream does NOT inspect the sendText result to decide injected-vs-queued** —
it returns `handled` on any non-throw. The `payload` it sends has NO
`requestedDelivery`; routing comes entirely from the session's
`followupMode=guide`. The KPR receipt contract (Mission 1) is stricter and must
read the events itself — this is a real difference, not a bug upstream.

## 3. Mode selection + fallback (verbatim)

```ts
const STEER_MODE: "queue" | "guide" = (() => {
  const env = process.env.ZCODE_STEER_MODE;
  if (env === "queue" || env === "guide") return env;
  try {
    const setting = JSON.parse(readFileSync(V2_SETTING_PATH, "utf8")) as {
      zcodeInteractionBehavior?: string;
    };
    return setting.zcodeInteractionBehavior === "guide" ? "guide" : "queue";
  } catch { return "queue"; }
})();
```

Steer sends only when `event.streamingBehavior === "steer"` AND `turnActive &&
sessionId`. On `session_shutdown`: `request("session/close", { sessionId })`
then `proc.kill()`.

## 4. zcode-acp PROTOCOL.md — the historical contract + event envelope

- (line 766-773) "### `session/steer` — removed in 0.16+ … `session/steer`
  existed up to app-server 0.15.x. The 0.16 app-server removed steering moved
  to the v4 command/conversation API. The bridge's `session/steer` ACP
  extension and the `/steer` slash command were removed accordingly. Queued
  inputs still surface as `turn.steerQueued` / `turn.steerDrained` events."
- (lines 459-478) "Steer lifecycle events … the backend emits a pair of
  lifecycle events (app-server 0.15.2+)" — shown inside the `session/event`
  envelope docs (`"type": "turn.steerQueued"`), corroborating that these types
  ride the `session/event` channel, not only v4 frames.
- (line 723-724) rewind likewise "moved to the v4 conversation API
  (`v4/conversation/fileRewindPreview` and friends)".
- The README compat table (`>= 0.16.0 | Supported | All except steer/rewind`)
  says zcode-acp does NOT implement v4 steering — it dropped steer entirely.
  zcode-provider is the only upstream reference implementation of the guide path.

## 5. What upstream does NOT establish (verified absences)

- The sendText `result` semantics for injected-vs-queued — upstream never reads
  it. Our bundle reading (evidence 03) supplies it:
  `{type:"inputAccepted", delivery:"queue"|"startNow"}` — insufficient alone.
- `docs/PROTOCOL.md` has no `v4/command` method documentation — the v4 surface
  is undocumented upstream; the bundle schemas (evidence 03) are the authority.
- Whether `turn.steerQueued`/`steerDrained` actually emit on `session/event`
  under 3.12.3 specifically — PROTOCOL.md documents the type names in the
  `session/event` envelope but payloads are `{}` placeholders. Live question.
