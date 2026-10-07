# Fable B-design convergence review (2026-10-07, one bounded round; review only)

Inputs: design.md/adr.md/migration.md @a706b559; my final review @cbfd92dd and AB addendum @c61383b2. Source re-read: kaola-acp.py :1552/:1695/:1774/:1925/:2210-2215; kaola-acp-holder.py :57-:163/:323/:417/:1124/:2024; kaola-dispatch.py :43/:1066/:1114/:1166/:2240/:3521/:3556/:5372; kaola-record-contract.py :21-:67/:403/:683/:781; skills/*/scripts md5. Root decides; I do not self-finalize.

## 1. Verbatim critique

**Q1 library-first vs B0.** Not files-first smuggling, with two conditions. ADR-1's library is what a resident core would host, so staging is honest. But the design inverts my B0 ranking: lifecycle+events (my first core duties) become components C1/C3 while data access becomes core. That is acceptable only if C1/C3 are cut at the holder socket `op` surface (`holder_features` :2024), not at file polling; otherwise P5 inherits a files-shaped core. P5 flip evidence must be pre-registered now, not judged by presumption at P5: (a) observed `unreachable`-on-timeout rate from the 2 s identity snapshot (C2) in VRPAI/CAD; (b) a reproduced cross-record race between per-file locks (state/index/receipts) surfacing as a `state_problems` conflict; (c) probe cost growing with session count; (d) a detected version skew between holder and dispatch copies. Any one reproduced in P1-P4 observation legitimately flips to resident; none observed means library stays. P5's "owner confirms" must not be a dead gate on a presumption either way.

**Q2 seams, with anchors.** The "core" today is scattered and partly duplicated, so P1 is not behavior-neutral:
- Process facts exist twice: holder `process_alive`/`libproc_ps` (:76/:103) versus acp.py `pid_alive`/`libproc_ps` (:1552/:1925); `pid_alive` returns True on PermissionError. P1 must pick one variant and fixture it (my C2 case: unreadable argv frees nothing).
- ADR-1 anchors are wrong: `canonical`/`normalize_id`/`worker_event_id` are holder :57-:65, not acp.py; `holder_of` is dispatch :1066; `atomic_write`/`read_state_file`/`StateLock` are dispatch :1166/:3521/:3556. `worker_event_id` is listed in both core and C3; keep it in core.
- Split kaola-record-contract.py: schema names and allowlists (:21-:67) are core registry; `aggregate_limit_blockers`/`delegator_authorization_blockers`/`authorization_blockers` (:403/:683/:781) are grant semantics and belong in C4, consistent with open decision 2 (seat_projection in C5, agreed).
- Missing DAG edge C5→C1: dispatch execute starts workers through `run_runner` (:1114) as a subprocess and discovers kaola-acp.py by glob (:2210-2215). This is the most important subtraction edge and is absent from §4.
- Missing edge C1→C6: the holder loads kaola-compact-recovery.py at :1124, dispatch at :5372. P3's "absent → inputs queue" must be asserted on the holder path, not only the dispatch path.
- No merges. C2, C7, C8 are right as drawn.

**Q3 subtraction §5.** Contract-only dependence prevents forced edits only with two rules the draft lacks. (i) Every namespace's READ path lives in C4/core; the owning component holds only writes and semantics. Otherwise retiring C6 leaves `recovery_input` rows no code can render. (ii) ADR-3 refusal cuts the wrong way at RETIRE: a registry-listed schema with no live handler must view as `retired-readonly` raw rows, never refuse, or consumers are forced to delete data. §5 also says uninstall removes "config namespace" but is silent on the data namespace; my addendum choice 3 (retain-frozen default) is still undecided.

**Q4 ADR-5 tokens.** Sufficient on one machine only if the epoch is fenced into the artifact under the held lock (read-modify-write with epoch compare); files give no compare-and-swap, and StateLock is advisory fcntl. State the lease as machine-local; "socket forwardable later" in my table would break it. §6 contradicts ADR-5: §6 says newer holder supersedes, ADR-5 says older writer keeps ownership. Resolve per artifact: sessions newer-supersedes via exact-stop; state store older-keeps until handed off.

**Q5 migration.** P1 must assert at file level, because there is no package: scripts load each other by `importlib.spec_from_file_location` beside `__file__` and ship as byte-identical copies in eleven skill directories (md5 verified). The P1 import-graph test asserts: which script file-loads which, which subprocess-calls which, no component reaching around core, every skill directory loading core from beside itself, and rendered copies identical to `scripts/`. ADR-2's 208/50 inventory is not reproducible (I count 232/201 defs); re-measure at P1 start. P3 is the cheapest subtraction proof and needs no manifest grammar; run it parallel to P1 rather than after P2. P4 is external; gate P5 on P1-P3 plus P4-or-waiver so KW coordination cannot block the pilot indefinitely.

## 2. Convergences
Library core as B0 host; eight-component coarse cut; no microservices; refuse-by-default with degrade lists; no un-handed-off dual-write; A fixes first (my choice 4, now answered); KW optional, pointers only; recipes pinned (ADR-6).

## 3. Disagreements
Open decision 1 "single python package" conflicts with the self-contained-skill invariant and byte budgets; P1 cannot be "no behavior change"; DAG omits two real edges; §6 and ADR-5 disagree on supersession.

## 4. Minimal user choices
New: (1) core packaging, vendor-per-skill copy render-enforced identical (recommended) versus one shared install path; (2) pre-register P5 flip criteria (recommended) versus ad-hoc owner call at P5. Still open from addendum: uninstall data default retain-frozen. Covered: per-user scope, holders survive core, A-before-B0.

— End.
