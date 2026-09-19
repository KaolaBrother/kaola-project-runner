# Goal: Issue #99 — design: mechanical KAOLA_ACP_HEARTBEAT_HOST binding on the Project Runner dispatch path

Run constraints, binding for every item below:

- **Design only.** No script behaviour change, no implementation code, no finalize, no merge.
- **Never write under `~/.dsh/`.** `templates/grok-golden/` stays frozen.
- Deliverable lands under `kaola-workflow/issue-99/evidence/`; the run stops at design acceptance by the Host.

---

## 1. Design document sections a–e

item: Write `evidence/heartbeat-auto-bind-design.md` covering (a) the enforcement point split across
`scripts/kaola-tmux.sh` (rendered as `runtime-tmux.sh`), `scripts/kaola-acp.py`, the holder, and the
ZCode bridge, including how the dispatching Host's identity is determined and carried; (b) the
failure shape (code, exit code, receipt fields, what the Host sees); (c) the relation to the #70
`heartbeat_host` receipt contract, the `permission_required` → `permit` flow, the Delegator's
receipt-verification habit, and PTY transport handling; (d) compatibility for live sessions already
recorded with `heartbeat_host: null`; (e) a script-level acceptance-case list including the
negative case (a dispatch-path `start` with no binding source is refused). Cite real line numbers.
status: done
dispatched: self — output lands in `kaola-workflow/issue-99/evidence/heartbeat-auto-bind-design.md`.
result: DONE. `evidence/heartbeat-auto-bind-design.md` §0–§e and §g–§h (36.7 KB, line-cited against
main d300c7a). Mechanism: the holder names itself to its agent via one identity-only env fact
`KAOLA_ACP_DISPATCHER` (holder spawn beside `KAOLA_ACP_CHILD_RECORD`; one ZCode-bridge allowlist
entry); `kaola-acp.py start` derives the target from it, verifies the Host holder is live
(record, pid, holder_instance_id, socket), and refuses with `result: refused` / exit 1
(`heartbeat-host-unresolved`, `heartbeat-host-conflict`, `heartbeat-host-pty-unsupported`) before
anything is probed or spawned. Standalone and explicit-variable starts unchanged; live bindings
immutable (#70); pre-change Hosts must be restarted (documented residual). PTY under a ZCode Host:
refuse recommended, allow-with-`pty-no-carrier` listed as the alternative for the reviewer.
Acceptance cases N1–N8, P1–P10 plus one live smoke.

## 2. Prose-reduction inventory

item: In the same document, list per paragraph what in `templates/orchestrator/` and
`templates/kaola-delegator/` (and the docs/tests that pin those sentences) can be deleted or
shortened once the binding is mechanical, with the exact template line ranges and the test pins
that would have to move with them.
status: done
dispatched: self — same file, §f.
result: DONE. `evidence/heartbeat-auto-bind-design.md` §f.1–f.8: per-paragraph deletions/rewrites in
`templates/orchestrator/SKILL.md.tmpl:81-82`, `references/zcode-host-dispatch.md.tmpl:18-34, 36-52,
54-80, 166-167`, `references/host-startup.md.tmpl:63-65, 80-85`, `templates/kaola-delegator/
references/handoff.md.tmpl:100, 142, 154-156`, `templates/kaola-delegator/SKILL.md.tmpl:13-14, 52-53`
(~2.3 KB net deletion, no budget pressure); docs paragraphs listed; test pins that retire or move:
test-issue-65:88, test-issue-74:362-363 and :481-495; pins that stay: test-issue-65:63/96-100/141-144,
test-zcode-heartbeat-contract:1327/1337-1339/870-885, test-issue-74:261, test-generated-skills:575-579.

## 3. Owner ruling on the c.4 open item

item: Record the owner's ruling on the one open design choice (PTY transport under a ZCode Host) in
the design document without changing any other part of the design.
status: done
dispatched: self — `evidence/heartbeat-auto-bind-design.md` §c.4 and §h.
result: DONE 2026-09-19. Ruling: under a ZCode Host, `--transport pty` `start` is always refused with
`heartbeat-host-pty-unsupported`; the allow-with-`pty-no-carrier` alternative is not adopted. §c.4
now opens with the dated ruling, the alternative paragraph is marked rejected (record only), and the
§h summary line is no longer an open choice. No other design text changed; no implementation.

## 4. Owner clarification: Runner dispatch is ACP-only (general rule)

item: Apply the owner's 2026-09-19 clarification that worker dispatch on the Project Runner
instruction/Skill path is ACP-only for every Host, not only a ZCode Host; correct any design text
that scoped the PTY refusal to the ZCode case.
status: done
dispatched: self — `evidence/heartbeat-auto-bind-design.md` §b.2, §c.4, §c.5, §e (N6b–N6d), live
smoke line, §f.7, §h.
result: DONE 2026-09-19. General rule recorded: on the Project Runner path a `--transport pty`
`start` is refused with `heartbeat-host-pty-unsupported` under any Host. Mechanical trigger widened
from "dispatcher with platform zcode" to "any `KAOLA_ACP_DISPATCHER`, or orchestrator context via
`KAOLA_PROJECT_RUNNER_CANONICAL_REPO` with no dispatcher"; the earlier ZCode-only scoping is noted as
corrected. Standalone Platform Runner (neither marker) keeps both transports. Acceptance cases N6b,
N6c, N6d added. No other design text changed; no implementation.
