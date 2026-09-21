# #125 — Droid Core is the third tier (alt_tier_label: core), not upgrade; upgrade = default = auto

1. item: Move Kimi K3 Max (kimi-k3, reasoning_effort=max) from droid upgrade_* to alt_* with alt_tier_label core; upgrade = auto (same as default); sync adapter, contract tests, docs/README/CHANGELOG prose; render --write
   status: done
   dispatched: self; output lands on branch workflow/issue-125 in .kw/worktrees/issue-125
   result: commit 72986ec (droid.yaml + adapters/droid.sh: upgrade=auto, alt core=kimi-k3/max; generated droid Skill; test-droid-acp-contract / test-issue-111-model-tiers / test-generated-skills / fake agent comment; README, docs/api.md, CHANGELOG); focused suites OK, render --check PASS
2. item: Gates — render --check and validate.sh rc=0 on the frozen candidate; record exact outcomes
   status: done
   dispatched: self; validate.sh on 72986ec, log lands in kaola-workflow/issue-125/evidence/validate.log
   result: PASS — render --check PASS; validate.sh rc=0 on 72986ec (evidence/validate.log, 0 FAIL lines, residual_pids [])
