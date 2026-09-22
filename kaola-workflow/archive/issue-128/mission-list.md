# #128 — make test-model-policy.sh (12) and test-lifecycle-contract.py (9) green without weakening assertions; decide validate.sh mounting

1. item: Diagnose each of the 21 red cases (stale fixture / stale expectation / real regression) on worktree .kw/worktrees/issue-128 at 8819bc9
   status: done
   dispatched: self — findings land in this file's result
   result: all 21 are stale fixtures/expectations, no product regression. lifecycle 9 = EXPECTED_MARKDOWN lacks references/steering.md (#65). model-policy: kimi-cli 6 = fixture default still Kimi 2.8 Max / kimi-for-coding while #111 (d6bd56b) made default Kimi K3 Max / kimi-code/k3; opencode 5 = V2 adapter (#112) carries caller model in OPENCODE_CONFIG_CONTENT (top-level --model rejected), fake only parsed argv, so actual=saved picker; droid 1 = fake `read -r a b` word-split the --settings model literal with spaces (actual="model"). Baseline logs /tmp/lc128.log, /tmp/mp128.log.
2. item: Repair fixtures and stale expectations (no assertion weakening); fix any real regression; both suites green
   status: done
   dispatched: self — worktree .kw/worktrees/issue-128 working tree
   result: lifecycle: +steering.md, +steering.md.tmpl, +dsh roster (was 9 of 10 workers) → PASS. model-policy: kimi default fixture → K3; opencode fake reads agents.build.model ("model#variant") from OPENCODE_CONFIG_CONTENT + new check test_opencode_user_model_rides_config_not_argv; droid fake uses \x1f separator → PASS rc=0 302 s (/tmp/mp128b.log). No assertion removed or loosened.
3. item: Mount decision for validate.sh (runtime/dependency measured), CHANGELOG, doc-impact; render --write/--check + validate.sh rc=0
   status: done
   dispatched: self — validate log /tmp/kw128/validate.log, rc in /tmp/kw128/validate.rc
   result: candidate 3a2c983 on workflow/issue-128 (local, unpushed). Mounted: lifecycle in lane A, model-policy as third concurrent lane C (validate.sh picks bash for .sh; #83 harness gets python_suites_c=()). render --check PASS; validate.sh rc=0 564 s on the committed tree (base 8819bc9: rc=0 583 s), both new suites PASS in it; evidence/validate.log. Two intermediate runs under heavy external load (syspolicyd ~75% CPU + another project's cargo build) hit 4-5 timeout reds in untouched ACP suites that all pass standalone; the first candidate run exposed #101's verbatim pin of the `watched "$suite" python3` line, kept by an explicit .sh branch. CHANGELOG Unreleased entry; doc-impact: no README/docs/AGENTS surface names these suites or lane counts.
