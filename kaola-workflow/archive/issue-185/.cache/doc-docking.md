# Documentation docking — issue #185

Candidate: `d98bebe429cf22e87a52ebc0eba0d263de3455d4` (`workflow/issue-185`).
Verdict: **DOCKED**.

Reviewed AGENTS.md's documentation checklist against the changed public behavior
(Droid `model_verified` now verified from the agent's own current-model echo, and
the launch-argv comparison uses the agent's echoed `advertised_model`).

| Surface | Checked | Action | Reason |
|---|---|---|---|
| `docs/api.md` (`## Model evidence` / model paragraph) | yes | **updated** | Added the Droid-echo exception, the launch-argv `advertised_model` comparison line, and the `acp-config-echo` provenance source. Field names read from `scripts/kaola-acp.py` (`echo_model_verification`, `effective_selection`) and the live probe receipt, not invented. |
| `CHANGELOG.md` (Unreleased) | yes | **updated** | The #185 entry now states the launch-argv comparison rule; keeps `Seats: restart not required`. No release section created. |
| `README.md` | yes | no impact | README's model coverage is the preset table and tier wording; `model_verified` values are not described there. Reviewed the Droid lines (Auto Model default, core tier) — unchanged. |
| `docs/architecture.md` | yes | no impact | Describes transport and control-plane architecture; the change is a receipt-field verdict, not an architectural surface. |
| `docs/conventions.md` | yes | no impact | The operator restart test over holder/bridge/quota/adapters/platforms is empty for this change, so the stated convention is already satisfied. |
| `docs/host-entry-matrix.md`, `docs/zcode-host.md`, host references | yes | no impact | The verdict gate is `ECHO_VERIFIED_PLATFORMS = {"droid"}`; no Host/entry behavior changes. |
| Receipt/schema docs (`docs/api.md` schema-3 fields) | yes | updated above | No new top-level key: `actual_runtime_model_id`, `actual_parameters`, `model_verified`, `model_mismatch_reason`, `model_evidence_provenance` already existed; only their values change for droid. |
| Environment / setup | yes | no impact | No new env var or dependency. |
| Examples / templates | yes | no impact | No user-selection CLI form changes. |
| `skills/**` (generated) | yes | regenerated | `render-skills.py --write` + `--check` PASS; the ten worker copies of `scripts/kaola-acp.py` carry the same change. |

## Accuracy

Every transcribed field name and value was read from `scripts/kaola-acp.py` and the
live `droid 0.225.1` probe receipts (`effective_selection.effective_model = "auto"`,
`model_verified = true`, `model_evidence_provenance.actual.source = "acp-config-echo"`),
never invented.

DOCKED
