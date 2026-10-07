### Owner correction: seat counts are the authorization capacity (2026-10-06)

The authorization JSON records which runtime/tier choices or shared groups are granted and how many seats each has. Do not offer an independently writable aggregate concurrency cap such as `elite_cap`, `total_cap`, or an equivalent renamed field. This supersedes earlier language retaining an optional extra aggregate cap.

Compute available capacity from effective individual/shared grant counts and current occupancy. Shared tiers refer to one shared count, not separate additive grants. Derived totals may be shown to the user but are not another stored authorization value. Preserve model-switch scope, grant lifetime and applicable owner restrictions; keep service/quota/fault facts in their existing proper current-state locations, not an invented concurrency grant limit.

Update the existing admission and role/report projections to consume this same authority. Migration must remove obsolete standalone aggregate limits without changing individual/shared grants or interrupting active work; if legacy total-limit intent conflicts with grant counts, make that specific ambiguity actionable rather than silently inventing authority. For this run the owner explicitly revoked the old cap4: current individual/shared grants authorize six possible Elite worker seats.

Use existing affected checks to prove all granted seats can be used, shared counts are respected and excess per-grant admission remains refused. Do not substitute a huge numeric cap, another override list or a free-text capacity policy.

