# Issue #71 — stop the undeclared 59 B main-Skill budget deduction

Run: `issue-71` · branch `workflow/issue-71` · worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-71`
Canonical repository: `https://github.com/KaolaBrother/kaola-project-runner.git`
(main root `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner`).
Project short code: **KPR**. Implementer: this Grok Build session (grok-4.6 xhigh, Fast off,
ACP-only, Workflow on). No extra implementer/reviewer dispatch.

Goal: the #49 pin/host invariance probe in
`tests/contract/test-issue-49-grok-bot-host.py` must not silently spend product
budget. Prefer equal-length real canonical edits so `templates/budgets.json`
(`main_skill_bytes` 17408, unchanged) is the ceiling `render-skills.py --check`
already reports. Prove the edit landed, do not weaken host/pin invariants, do
not add a second budget system, do not raise budgets, and do not edit Issue #72
surfaces (`templates/orchestrator/SKILL.md.tmpl` body, heartbeat skeleton,
workflow-worktree reference).

Hard constraints:
- Single-issue run; no bundle. Co-active: `issue-70`, `issue-72`, `bundle-67`.
  Touch none of their folders, branches, worktrees, sessions, accepted checkouts,
  or credentials.
- Templates go through the renderer; never hand-edit `skills/` or `hosts/grok-bot/`.
- Outer ACCEPT before finalize/merge/close/push to mainline.

1. **item**: Reproduce the hidden deduction on a near-declared-budget tree: pad
   the orchestrator template so rendered `SKILL.md` sits under 17408 (the #68
   17405 B shape), show `--check` green, then apply the current 59 B append and
   show `render --write` red. Store raw command output under
   `kaola-workflow/issue-71/evidence/`.
   **status**: done
   **dispatched**: self; output lands in `kaola-workflow/issue-71/evidence/baseline-repro.txt`
   **result**: PASS. worktree `b229f84`, main Skill 17337 B, declared 17408, old
   probe 59 B, hidden ceiling 17349 (12 B slack). Temp copy padded to 17405 B:
   `--check` exit 0 (`budgets OK`). Same tree + 59 B append: `--write`/`--check`
   exit 1, `budget: kaola-project-runner/SKILL.md is 17464 B > 17408 B`. Worktree
   HEAD and index untouched.

2. **item**: Replace the append probe with equal-length canonical substitutions
   (orchestrator body, worker template, transport reference, grok-bot-host
   reference) so rendered sizes do not grow; keep the manifest rename; assert the
   new text appears in the matching products and host products stay byte-identical;
   add a live counterexample that a real host-template edit does change host
   products. Do not change #72 body or `templates/budgets.json` numbers.
   **status**: done
   **dispatched**: self; output lands in worktree
   `tests/contract/test-issue-49-grok-bot-host.py` on `workflow/issue-71`
   **result**: PASS. Append probe replaced with `CANONICAL_INVARIANCE_EDITS`
   equal-length spans; main Skill size asserted unchanged and content asserted
   changed; host products byte-identical; host-template append is a live
   counterexample. `Issue49BridgeInvariance` 3/3. No template/budget/#72 body
   edits. Diff: 4 files, +92/−10.

3. **item**: Prove the repaired probe still passes at the declared ceiling
   (pad to `main_skill_bytes`, equal-length edit, `--write`/`--check` 0) and
   that true violations still fail (one extra byte over the declared budget;
   host-product leakage).
   **status**: done
   **dispatched**: self; output lands in
   `kaola-workflow/issue-71/evidence/postfix-near-budget.txt` and the new
   `test_invariance_probe_does_not_spend_declared_main_skill_budget`
   **result**: PASS. Pad to 17405: `--check` 0. Equal-length edits: size stays
   17405, marker present, host unchanged, `--write`/`--check` 0. Old 59 B
   append on that same tree: 17464 B > 17408, exit 1. New test also pads to
   declared 17408 then equal-length (exit 0) and +1 byte (exit 1, product not
   written). `RendererEnforcesBudgets` still OK. Full
   `test-issue-49-grok-bot-host.py` 43/43 in 27.620s.

4. **item**: Dock one-sentence explanation in the existing budget docs
   (`docs/architecture.md`, `docs/conventions.md`) and CHANGELOG, then
   `./scripts/render-skills.py --check` and `./scripts/validate.sh` on the frozen
   candidate. Record SHA, actual diff, exact test results, and raw evidence for
   outer ACCEPT. Do not finalize until ACCEPT.
   **status**: done
   **dispatched**: self; docs already edited in the worktree; output of
   `--check` and `validate.sh` lands in `kaola-workflow/issue-71/evidence/`
   **result**: PASS. Frozen `c19cdde4113792bfd8ac68881c740dd1d37296f8` on
   `workflow/issue-71` (not pushed). `render --check` PASS at that SHA;
   `Issue49BridgeInvariance` 3/3; full #49 suite 43/43; `validate.sh` exit 0
   on the same bytes. Delivery package:
   `kaola-workflow/issue-71/evidence/delivery.md`. Waiting for outer ACCEPT;
   no finalize/merge/close/push.
