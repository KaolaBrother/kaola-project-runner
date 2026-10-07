# Fable final collaborative review — issue #270 (#271/#272/#273)

Reviewer: owner-appointed Claude Code Fable 5.1; thinking/review only. Corpus @97551c75. Source re-read this round: `scripts/kaola-acp.py` :888-931, :1537-1546, :1680-1693, :1759-1775, :2998-3012, :4845-4880; `scripts/kaola-record-contract.py` :39, :328-330, :1293. Root gives the final verdict; this is not acceptance.

## 1. Verbatim critique

**C1 (#273 overstates the gap; a parallel taxonomy would be redundancy).** `holder_identity` already yields four states — `verified` / `dead` / `unreachable` / `mismatch` — by PID probe plus socket handshake on `holder_instance_id` (:1680-1693). The list path already calls it (:905) and emits `identity` per row (:931). The status/root path already fails closed on `unreachable` via `holder_argv_anchor` (:4862-4873), which reads the live PID's argv and returns `False` when it is not a `kaola-acp-holder` naming that record dir (:1759-1775). The observed AI case (PIDs later held by system services) is therefore **already provably-reused on the status path**. The defect is narrower than "no distinction": (a) :923 copies persisted `agent_alive` verbatim and presents it beside live `identity`; (b) :894 filters rows by `pid_alive` instead of identity; (c) the list path does not apply the argv anchor. Minimal fix: in list rows, derive `agent_alive` from the verified holder's state reply when `identity == "verified"`, else project `null` plus `agent_alive_as_of` (receipt time); apply the anchor to `unreachable` rows as status does. **Do not add a three-state vocabulary beside the existing four.** The `:3009` consumer (`agent_alive is not True` → blocking) becomes stricter under this change and must be fixture-tested; that is the right direction (fail closed).

**C2 (#273 failure mode — identity checks are themselves time-bounded).** `LIST_IDENTITY_TIMEOUT = 2.0` (:1653): a busy holder that does not answer within 2 s reads `unreachable`. So `unreachable` is a *snapshot*, not a fact, and must stay informational (converges with #273 item 2). Also `pid_alive` returns `True` on `PermissionError` (:1544) — exactly the reused-by-root-service case; only the argv anchor disambiguates. Add one fixture case: anchor returns None (argv unreadable) frees nothing.

**C3 (#272 attribution grammar — one more form is needed).** The five QA classes answer *why the gate did not catch it* (coverage axis). Primary/contributing/UNKNOWN answers *causal role*. They are orthogonal, not corresponding, and "UNKNOWN" currently conflates *unknown role* with *unverified hypothesis*. Per separable hypothesis record a triple: `role ∈ {primary, contributing, none}`, `status ∈ {confirmed, refuted, open}`, `qa_class ∈ five`. `none` requires `refuted`. FP then becomes a **derived** verdict (every hypothesis refuted, or impact excluded), not a sixth class.

**C4 (FP operationalization).** "Impact-excluded" is operational only if its evidence kinds are enumerated: (i) symptom reproduces with KPR removed (bridge-side cause), (ii) surface unreachable on any supported path, (iii) already fixed at the pinned revision with an oracle. Absence-of-proof tension is resolved by making `open` a legitimate terminal-for-now state **held only as a forge issue** (open issues are backlog truth) — no under-investigation list, which would be the ledger the owner prohibits.

**C5 (#272 hidden second scheduler).** Stage 6 "deadline/handback owner" implies something checks at a time. Bind the watch to the **existing** post-release observation heartbeat and the issue's close condition; drop the deadline field. Stage 4 "someone other than the author-agent" must not force a seat for pure-text changes; the oracle plus render check is the independent verifier there.

**C6 (D4 old-reader is no longer fully UNKNOWN).** The current validator refuses any non-string `depends` entry (`tasks.depends array of strings`, :328-330), and tasks keys are an allowlist (:39, :199). A v0.9.1 reader therefore **refuses** a D4-shaped record rather than ignoring the key. Fail-closed, not silent — but it means reader-before-writer rollout and a migration step; D4's cost rises.

**C7 (value choice smuggled as technical detail).** #271 D2 needs two body clauses inside 58 bytes headroom (dispatch-collect at 7). If byte-neutral trims fail, a ceiling change is a user choice; state this up front rather than discovering it mid-implementation.

## 2. Convergences with root

Short-term = #271 entry contract + #273 narrow fix; behavioral evaluation is real, not word-oracle. #272 as a loop over existing structures with #267 as input. No framework migration, no forced daemon/DB, no single-incident global gates. F3's graph-fingerprint resume assertion is a mismatch-detection pattern to borrow, not a dependency (confirms §5.4a).

## 3. Disagreements

- #273 is not an "independent fix design"; it is a two-line projection fix reusing `holder_identity` + anchor (C1).
- Behavioral evaluation should validate the loop once; it is not a landing gate for D1/D2 text.
- D4 is costlier than proposed (C6); keep it behind the no-field replay test, as root says, but record the refusal fact now.

## 4. Owner choices — what the user must decide now

Genuinely now (one): **where the #271 behavioral scenario runs** — in-repo fixture / this repo as consumer (recommended) versus a live VRPAI/CAD seat. AGENTS forbids KPR-driven worker dispatch in consumers; only the owner can widen that.

Recommended and deferred (auditable defaults, no user block): 1 files+Git only until a pilot proposes a store; 2 KW untouched; 3 no resident service proposed; 4 type-level authorization-history line is a *precondition* of any event-store pilot, decided then; 5 refuse-by-default on version mismatch with an explicit degrade list (matches existing refusal style); 6 root's order; 7 pattern-only; 8 one forge read at the no-eligible boundary is negligible, measure first; D4 after replay test; D3 as a KPR prose sentence at the decision boundary, consumer owns the mechanism. Budget ceiling (C7) only if trims fail.

— End. Host records verbatim; reviewer does not self-finalize.
