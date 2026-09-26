# Documentation Docking — Issue #186

Status: DOCKED

Checked against `AGENTS.md`'s documentation checklist for changed public behavior.

| Surface | Decision | Reason |
|---|---|---|
| `templates/orchestrator/references/host-startup.md.tmpl` | **Updated** (via template) | The per-platform native-id paragraph now names Claude Code: its native UUID arrives in `native_session_identity` from turn one; a fresh seat's `acp_session_id` is process-local and unresumable, while a seat resumed by `--resume U` has `acp_session_id` = U; the newest `nativeSessionId` wins. Rendered `skills/kaola-project-runner/references/host-startup.md` = 8188 B within the 8192 B `reference_bytes` budget. |
| `platforms/claude-code.yaml` | **Updated** (manifest) | `acp_quirks` records the process-local fresh `acp_session_id`, the `nativeSessionId` resume path, and the cancelled-fallback announced-id preference. |
| `vendor/claude-code-acp/UPSTREAM.md` | **Updated** | Local-modification item 4 records the new `native_session_identity` emission and the empty-id guard; the upstream-hash inventory table is unchanged (its hashes are upstream values). |
| `CHANGELOG.md` | **Updated** | One `## Unreleased` entry names the observable behaviour: claude-code seats publish `native_session_identity` on the first turn; `--resume` uses the newest `native_session_identity.nativeSessionId`. No release section, no `Seats:` line (release-section-only per `AGENTS.md`). |
| `docs/api.md` | No change this run — recorded as a deferred optional | Line 339 documents the ZCode adapter's `native_session_identity` contract. A parallel clause for the Claude Code bridge would be additive, not corrective: nothing in `docs/api.md` is made wrong by this change. The owner recorded the addition as an optional follow-up (not this run). |
| `docs/architecture.md` | No change this run — recorded as a deferred optional | Line 138 names `native_session_identity` in the ZCode context; the bridge architecture description is unchanged, so no wording here became false. Owner-deferred optional follow-up. |
| `docs/zcode-host.md`, `docs/conventions.md`, `docs/codex-host.md` | No change | ZCode-specific flows; no ZCode behaviour changed. The seat-restart convention's operator test is unaffected: `scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`, and `platforms/` changed only in `platforms/claude-code.yaml` (`acp_quirks` text); no protocol, holder, or bridge-pinned surface moved. |
| `AGENTS.md` | No change | No command, installation step, validation policy, or constraint changed. `vendor/claude-code-acp/` is already covered by the existing "generated surfaces / vendored bridge" notes. |
| `README.md` | No change | No setup, usage, or entry-tier behaviour changed. |
| `docs/harness-acp-compat-2026-09-2*.md` | No change (out of scope) | Untracked operator files, explicitly excluded by the run boundary. |

Public behaviour documented: the CHANGELOG entry names the observable outcome (a
credential-free `native_session_identity` event per seat first turn), the resumable id
(`nativeSessionId`), and the fresh-seat `acp_session_id` unrecoverability.

No invented fields, signatures, or schema were transcribed.
