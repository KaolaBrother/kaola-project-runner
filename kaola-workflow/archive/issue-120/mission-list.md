# #120 — a dsh worker starts (or fails with an honest classified reason) inside a dsh Host

- item: reproduce dsh-in-dsh ACP initialize exit 1 under a temp HOME / isolated KAOLA_ACP_RECORD_ROOT (real ~/.dsh read-only) and pin the root cause (inheritance/env/sandbox/entry conflict); note whether cc-in-cc shares it
  status: done
  dispatched: self; findings land in kaola-workflow/issue-120/diagnosis.md
  result: diagnosis.md + evidence/ — root cause = dsh Host shell tool runs under Seatbelt workspace-write (DSH_PERMISSION_MODE default), inherited by the worker holder: nested dsh boot write to $DSH_HOME/profiles/acp/cordis.yml EPERM → exit 1; setuid /bin/ps cannot exec → holder stop crashes (holder-closed, leak). Live A/B in a real dsh Host: A reproduces #119, B (DSH_PERMISSION_MODE=danger-full-access) starts+stops the dsh worker clean. cc-in-cc is a different class (sandbox_check=0 here)
- item: Runner-side fix (or honest non-fixable classification + minimal mitigation) with contract tests: repro case (fails before) + fix case (passes after); render --write/--check
  status: done
  dispatched: self; value-neutral part = start failure facts (stderr_tail, seatbelt_confined) + ps→libproc shim for Seatbelt-confined holder/CLI; tests in tests/contract/test-issue-98-dsh-acp.py; the DSH_PERMISSION_MODE default is a value choice → HUMAN_DECISION_REQUIRED
  result: commit 6e765a0 on workflow/issue-120 — holder start_failure_facts (stderr_tail + seatbelt_confined) and run_ps libproc fallback in holder + CLI, rendered to 10 skills; 5 new tests in test-issue-98-dsh-acp.py (baseline fd909e1: 4 fail incl. holder-closed stop, control passes; candidate: 29/29 OK); render --check PASS; validate.sh rc=0 (evidence/validate-candidate.log)
- item: dsh-in-dsh starts by default — apply the owner's ruling on DSH_PERMISSION_MODE (Runner default danger-full-access as dsh's #22 skip-all, vs operator opt-in only) and correct the dsh manifest/README/#88-pinned claim that outside-workspace writes run unattended (#98 measured /tmp, a Seatbelt writable root)
  status: done
  dispatched: self (Host ruling 2026-09-22: Option 1, default danger-full-access, caller DSH_PERMISSION_MODE or --mode wins); output lands as a commit on workflow/issue-120 after 6e765a0
  result: rebased onto main e8d20a4 → b553b37 (facts + libproc) + 1bc8618 (default): agent_environment sets DSH_PERMISSION_MODE (caller --mode > caller env > danger-full-access), bypassPermissions→danger-full-access, unknown --mode refused pre-spawn, receipt config_application.mode {applied_via env, value, source}; dsh.yaml/README/#88 class DshSkipAllIsTheLaunchVariable corrected; live leg C (pure Runner default Host, DSH_HOME outside writable roots): Host shell sandbox_check 0, nested dsh worker ready, worker+Host stop stopped/residual [] (evidence/C-*)
- item: gates — validate.sh rc=0, CHANGELOG, doc-impact; delivery report (root cause, diff, evidence, acceptance)
  status: done
  dispatched: self; gate logs land in evidence/
  result: on 1bc8618: render --check PASS (budgets OK); validate.sh rc=0 (evidence/validate-1bc8618.log); test-issue-98-dsh-acp 37/37, test-issue-88 42/42; CHANGELOG two #120 entries; doc-impact = dsh.yaml + generated dsh references + README (two passages); main Skill untouched; readiness for Host acceptance — no merge/push
