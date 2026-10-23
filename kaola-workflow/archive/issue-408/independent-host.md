# Independent check of issue #408 — Host seat

- checker: host
- checked_at: 2026-10-23T03:43:00Z
- candidate_checked: 80c4db0b72089150fff28ed148b7401b96f526db
- verdict: ACCEPTED

## Evidence
- Reproduction: /tmp/kpr-408-repro/EVIDENCE.md plus probe*.py; the reviewer
  independently reproduced the pre-fix counter-proof (bound seat, raw
  same-UID socket prompt admitted and normalized to delegator).
- Host verification receipts: /tmp/kpr-408-verify/ on the Host machine —
  locator named in the verdict message; not present on this device.
- Implementation gate: 13 focused suites exit 0
  (test-issue-408-bound-seat-socket-auth 28/28), render-skills --write +
  --check PASS, prior full-inventory evidence (165 suites, exit 0) verified
  equal to 6b346dbe and reused per the stated evidence-reuse rule.

## Findings verified hands-on (Host verdict)
- Recovery-route catalog entries for unauthenticated,
  holder-instance-required and invalid-token each name a working recovery.
- Token self-heal live: a deleted auth.token reappeared on the holder's
  15 s watchdog tick.
- stop --force stops a tokenless bound seat through the argv-verified
  signal path; residuals empty.
- A non-ASCII auth_token produces the typed invalid-token refusal; the
  connection thread stays alive.
- CHANGELOG wording corrected: admitted socket prompts keep delegator
  source by design; unbound includes Host-role seats; upgrade-order note
  (restart the Host holder first, then refresh copy installs) present.
- The bound-seat wrong-instance refusal now stamps the same
  socket_op_refused event kind as the other gate refusals.
- kaola-launchd-broker reads the token through
  acp_paths.read_auth_token.
