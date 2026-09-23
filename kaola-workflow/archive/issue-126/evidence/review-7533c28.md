# Independent review of e4f477b..7533c28 (code-reviewer subagent, 2026-09-23)

Verdict of the reviewer: no blocker, no major. Orchestrator dispositions in brackets.

- F1 minor (docs): templates/orchestrator/references/heartbeat-skeleton.txt:30 told "Codex" to use its
  own timer carrier while the new matrix note says a codex Host rewrites .kaola/heartbeat-prompt.json;
  the holder reads only that file, so a codex Host following the skeleton would lose its prompt between
  beats (fails safe: the missing-prompt report). D3 did not cover it (its beat said to overwrite the file).
  [FIXED in the follow-up commit: "ZCode Host 更新项目根" -> "Host 更新项目根", "Codex 更新其定时系统…" ->
  "非 Host 的 Codex 更新其定时系统…"; rendered 8190/8192 B; pin in test-zcode-heartbeat-contract.py updated,
  test-issue-68 pin still holds as a substring.]
- F2 nit: the codex matrix row's roots column came from #119's 1.11.0 probe, and the #126 shadow held only
  ~/.codex/skills. [FIXED: the codex note says so.]
- F3 nit: `$kaola-project-runner` is the only entry starting with `$`; inside double quotes a shell
  expands `$kaola`. The code path is safe (JSON -> argv list -> Python join). [FIXED: the codex note
  says to pass it single-quoted or via --stdin.]
- S1 suspicion (unmeasured): the Codex user-level SessionStart(compact) hook payload says to re-read the
  installed Skill, while host-startup says a Host never reads SKILL.md by hand; whether codex-acp fires
  that hook is unmeasured, and D3 had no compaction. [NOT CHANGED: unmeasured; reported to the Host as
  an open observation.]
- Pre-existing, out of scope: SKILL.md.tmpl:9/:112 say "nine platform Runner Skills" / "all nine
  platforms" (ten since #98).

Checks the reviewer ran: grep of every host_capable / HOST_SKILL_ENTRIES / --host-entry consumer; render
--check PASS; git diff --check 0; test-issue-119-host-entry 11/11 (160); the two changed zcode-heartbeat
tests; test-issue-94, test-generated-skills, test-progressive-disclosure OK. Mutation checks: a fixture
that did not empty the entry failed T1, the carrier-target row and P5, and a table-only fixture failed
the holder worker_event row, so the fixture rows are not vacuous.
