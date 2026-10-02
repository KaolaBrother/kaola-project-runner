# Issue 244 repair round

This is a run record, not a mission. Workflow Next has no amend command.
The installed writer is a full rewrite of
`kaola-workflow/.ledger/issue-244.jsonl`, and a `done` line does not change.
A repair round stays inside the same mission, so the ledger no longer has a
mission 3.

The first close of mission 1 is restored. The sentence added after that close
was: `First candidate was not accepted; the repair is mission 3.`

The mission line removed from the ledger, verbatim:

```json
{"n":3,"name":"Repair collect, selection evidence, recovery identity, authorization, and capability summary","details":"done: uncommitted on workflow/issue-244 in /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-244. scripts/kaola-dispatch.py SHA256 a725c48b77086df96216744c32efafc085acb381500d8ac56d7d864eddcc92e2. render-skills --check PASS. validate.sh exit 0, elapsed_ms 588625, 12 validate-skill PASS, grok-bot 2555 B content, residual_pids []. test-issue-244 21 OK.","status":"done"}
```

That `validate.sh` receipt and `test-issue-244` 21 OK exercise dispatch,
docs, and rendered skill bytes. They do not exercise the new
`op_prompt` holder check. The check that does is
`tests/contract/test-issue-244-holder-prompt-binding.py`.
