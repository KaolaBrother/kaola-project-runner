# AST-measured function inventory (authoritative)

Source SHA: `cbe1f2ae1ca4af681e5cd6c12c224070dadbd0d0`

Counting rule (AST, exact): `ast.FunctionDef` + `ast.AsyncFunctionDef` nodes at module top level vs nested (class/method/nested). No regex. Single ownership per node.

- `scripts/kaola-dispatch.py`: top-level 208, nested (class/method/nested) 233, all 441; sha256:64fcb90de126a684
- `scripts/kaola-acp-holder.py`: top-level 51, nested (class/method/nested) 209, all 260; sha256:f455cd271d20b2f1
- `scripts/kaola-acp.py`: top-level 195, nested (class/method/nested) 207, all 402; sha256:d957f86e1efc5b26
- `scripts/kaola-record-contract.py`: top-level 68, nested (class/method/nested) 72, all 140; sha256:b5b61d8fdf4f30de

**Totals: top-level 522, all 1243.** Prior figures reconciled: draft 208/50 counted top-level `def ` only for two files; Fable's 232/201 counted a different file set with `def` anywhere (incl. nested); this AST count at the pinned SHA is the single source of truth. Any future recount re-runs this script.

Reconciliation table: 208=dispatch top-level (grep) = AST top-level; 232/201 ≈ all-node counts across file pairs under older grep; appendix 522 = 4-file grep union at 4f28f8ac (superseded by this AST count).

## Node-level assignment obligations (supersedes the earlier keyword table)

Every AST node above (1243 total) gets exactly one owner before P1: `core-identity`, `core-process`, `core-atomic`, `core-registry`, `C1`..`C8`, or `keep-in-place:<file>` with a per-node reason string. Known corrections already adopted from the Fable addendum (5 sampled disagreements): `observed_at`→core-identity (timestamp helper); `caller_dispatcher`→core-identity (holder identity recovery from env); `seatbelt_confined`→core-process; `_snapshot_file`→C7 (script digest/skew); `compact_module`→C1 (the C1→C6 loader edge). `worker_event_id`: **core-identity (single owner)**; C3 consumes it — the v1 draft's dual listing is corrected here and in design.md. `quota_module` (holder :1109): loads C5 code from the C2 catalog — the C1↔C5 cycle resolves by declaring `kaola-quota.py` **C2 catalog data** (its consumers stay C5; the holder's load is C1 mechanics reading C2 data), NOT by re-labeling to hide the edge; both the load edge (C1→C2-data) and the subprocess edge (C5→C1 via `run_runner`) are now in the DAG.

The holder's 209 nested defs (the real event loop, ~:1800-:6000) are the C1/C3 seam: P1's first assignment pass walks them class-by-class; until then they are listed `keep-in-place:kaola-acp-holder.py (event-loop interior; C1/C3 boundary walk is P1 step 1)` — an explicit, per-file reason, not a blanket.

## Machine-checkable recount
`python3 - <<'PY'` with the same AST walk above re-derives the counts from any worktree; the numbers and SHAs in this file must match or the inventory is stale.
