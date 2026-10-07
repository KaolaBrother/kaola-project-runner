## 5. Owner A/B decision addendum

Reviewer: Fable (continuation seat); review only. Continues `docs/research/i270-fable-final-review.md` @cbfd92dd. Inputs: owner A/B decision, root §3/§4, stage critique R1–R9, `kaola-acp-holder.py` :1815/:5801-5830/:5976-5992.

### 5.1 Re-evaluation under the A/B split

**Stands.** C1–C7 are A-line, unchanged; A ships without waiting for B. §3's claim that consistency is a mechanism property, not topology, grounds §5.2. R1 (no scheduler vocabulary in a core), R2 (KW as pointers), R5 (embedded DB = dual-write), R7 (type-level authorization-history exclusion), R9/choice 5 (refuse-by-default plus degrade list) hold for both lines. C6 becomes a B migration fact: readers before writers.

**Changes.** (a) §3 ③ ("a service to operate — a design cost") ranked ① first by omission, which the owner forbids, as they forbid using Host-on-demand exit to negate a service; ③ gets the nine-axis comparison below. (b) §3 omitted a verified fact: KPR already runs N resident processes — one holder per session with a 0600 Unix socket and a JSON `op` surface (`state/prompt/steer/wait/capture/worker_event/...`), plus the launchd broker. B's question is "N uncoordinated per-session daemons + files" versus "one core with holders as modules", not "daemon vs none". (c) Original §4 deferred defaults 1 (files+Git until a pilot) and 3 (no resident service) remain A defaults and are withdrawn as B defaults. (d) O-options re-sorted: O4 → A-line; O2 → data-access facet of either B option; O3 → B's subtraction primitive; O1 → B-line, generated-only limit stands.

### 5.2 Lightweight resident core vs no-daemon

**L (core).** One per-user, per-machine `kaola-core`, auto-started by the first CLI call, idle-exit at zero sessions and subscribers (compatible with Host-on-demand; a property, not a denial). Reuses holder socket framing and permissions. Duties: (1) **lifecycle** — adopts holders by `holder_instance_id` handshake or supervises new ones; single liveness/identity authority (removes the #273 class structurally). (2) **events** — holders push `events`; core serves `subscribe(kinds, after_seq)` with catch-up (T3 EventSink pattern); authorization kinds excluded by type. (3) **data access** — serializes typed records through the existing validator onto the same `StateLock`+`os.replace` files: Git evidence unchanged, no dual-write. (4) **module loading** — manifests (O3), three states (R3). Agents keep planning/acceptance (R1). The core is itself removable: absent core → CLIs fall back to N.

**N (no-daemon).** Per-session holders; file locks; callers probe each holder; polled events; modules bound at render.

| Axis | L | N |
|---|---|---|
| Cross-process consistency | one serializer, same files | per-file locks; cross-record races remain |
| Query/subscription | push + catch-up | poll per holder (2 s snapshots, C2) |
| Crash recovery | lose subscriptions only; re-adopt on restart | nothing central to lose |
| Upgrade/migration | one negotiated version | per-script skew, undetected |
| In-flight ownership | holder owns ACP; core records adoption | inferred from PID (#273) |
| Single point of failure | coordination yes, sessions no | none |
| Permission/secret boundary | one socket, one redaction point (R8) | N sockets, per-script |
| Cross-machine | socket forwardable later | unavailable |
| Ops cost | +1 process/log/version | +0, probe cost grows with sessions |

**Recommendation.** L, staged: **B0** = duties (1)+(2), files untouched; (3)/(4) after B0 shows measured wins on identity and subscription. Not recommended: an embedded DB inside the core (R5), per-project daemons, holders as core children.

### 5.3 Subtraction-first contract (B-line)

- **Manifest**: id, contract version, provides/requires as capabilities (not module ids), owned namespaces, `on_absent` rule, retire procedure.
- **Dependency release**: removal fails only consumers whose required capability has no remaining provider, as a named refusal at use time — never a forced synchronized consumer edit.
- **Retire → uninstall**: retire = installed-inactive, namespace kept and marked; uninstall only after explicit data disposition: migrate to a named successor, retain frozen with an owner, or delete by explicit choice (never default).
- **Ownership**: one owning module per namespace; KW artifacts as pointers (R2).
- **Version compat**: refuse-by-default plus degrade list; field removal reader-first (tolerate, then drop), per C6.
- **Verification**: render+validate with the module absent must pass; a module's suite leaves with it (`--suite` is already per-inventory).
- **Middle layers**: the core obeys the same contract.

### 5.4 New minimal user choices

1. Core scope: per-user-per-machine (recommended) vs per-project.
2. Core death: holders survive core (recommended) vs holders as children.
3. Uninstall data default: retain-frozen (recommended) vs migrate-required.
4. Sequencing: A's #273 fix first on `holder_identity`, B0 later replaces its callers (recommended) vs B0 first.

— End. Host records verbatim; reviewer does not self-finalize.
