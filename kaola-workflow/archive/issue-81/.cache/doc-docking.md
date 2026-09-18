# Issue #81 — Documentation docking

Candidate: `8133c28` (rebased on `745668f`, post-#90 main).

Checked files against changed public behavior (native ZCode v4 steering):

- `CHANGELOG.md` — DOCKED. #81 entry added at Unreleased top (merged with
  #90/#87/#86/#85 entries during the rebase; no content dropped).
- `platforms/zcode.yaml` — DOCKED (in candidate). `native_steering:
  "supported"`, `acp_steer_method: "_session/steering"`, full
  `steering_summary` describing the v4 path, the ack trap, the evidence
  ladder, and the interrupt fallback.
- `docs/api.md` — FIXED IN COMMIT. The `steer_outcome` table listed
  `not_consumed → steer_confirmation: none, "nothing was written"`; the
  accepted queued-admission path returns `not_consumed` with
  `steer_confirmation: agent-confirmed`, `error.code: steer-queued`, and
  `mutation_performed: true`. Added one clarifying paragraph after the
  table (lines 335-338). No other row affected — every outcome the adapter
  produces (`injected`/`written`/`not_consumed`/`unsupported`/`rejected`/
  `unknown`) is still accurately covered.
- `README.md` — NO IMPACT. Its `steer` section describes the generic
  receipt contract and manifest selection, both unchanged in shape.
- `docs/zcode-host.md` — NO IMPACT. Its steer mentions are about the
  ZCode Host's worker-event path (never converted to `steer`), unrelated
  to the #81 adapter surface.
- `docs/README.md` — NO IMPACT (index page).
- `skills/zcode-kaola-project-runner/` — generated; `SKILL.md`,
  `references/steering.md`, `scripts/platform.yaml`, and both
  `kaola-*.py` copies re-rendered from the merged sources
  (`render-skills.py --write` → `--check` PASS on the rebased tree).
- `AGENTS.md` — NO IMPACT (no steer-surface facts listed there).
- `templates/` — NO IMPACT (the steer contract lives in the holder source
  and manifest; no template change was needed or made).

Verdict: **DOCKED** — one real API-doc clarification applied; everything
else confirmed accurate against the candidate.
