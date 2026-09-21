# Goal: surface ZCode output-token-max turn terminals as ACP stopReason `max_tokens`, end to end from adapter to Runner receipt (issue #113, v0.5.5 must-clear)

Scope guard (Delegator, issue #113 comment 2026-09-21). In: adapter terminal translation in
`scripts/kaola-zcode-acp.py`; verbatim persistence through `scripts/kaola-acp-holder.py` into
`record.json` `last_prompt.stop_reason` and `events.jsonl`; acceptance (a) contract-test gate and
(b) scratch-HOME live recipe; (c) drafted for the Host, not posted. Out (hard): no GLM
effort/model change, no 128K ceiling change, no vrpcadcore host handling, no writes under
`~/.dsh`, and "single-project frequent otmax" stays an unconfirmed observation.

Coordination: a parallel #112 run owns OpenCode surfaces (`platforms/opencode.yaml`,
`scripts/adapters/opencode.sh`, OpenCode contract tests). My surfaces are
`scripts/kaola-zcode-acp.py`, `scripts/kaola-acp-holder.py`,
`tests/contract/fake-zcode-app-server.py` and the already-listed
`tests/contract/test-zcode-acp-contract.py`. Shared files (`scripts/validate.sh`, `templates/`,
`templates/budgets.json`) are avoided by design; if one becomes unavoidable, stop and report.

Acceptance is not self-finalized: the Host accepts the delivery. No merge, no close.

## 1. Map the output-limit terminal surface and freeze the translation design
status: done
dispatched: self
result: kaola-workflow/issue-113/wire-contract.md — the app's own predicate is
  `finishReason === "length" || rawFinishReason in {max_tokens, max_output_tokens,
  model_context_window_exceeded}` with a 3-continuation budget, exactly as the issue states. The
  real terminal is `turn.failed` (the app-server event union has no `turn.terminal`), carrying
  `error.attribution.providerErrorCode` / `.reason` == `model_output_limit_exceeded` and
  `error.type` == `model_error`; it collapses to ACP `refusal` at kaola-zcode-acp.py:1531.
  `turn.completed` is strict and carries no finish reason, so its `error_max_*` resultTypes must
  NOT be translated. Holder stores stopReason verbatim; events.jsonl has no stop-reason-bearing
  event today, so that half is a real addition.
item: Read the live tree's collapse points in `scripts/kaola-zcode-acp.py` (`turn.completed` /
  `turn.failed` / `turn.terminal` around 1514-1536, `finish_turn` around 1574-1591) and the
  holder's stop_reason path, and establish exactly which backend payload fields carry the finish
  reason and the ModelError `providerCode`. Confirmed already: the holder stores `stopReason`
  verbatim (no whitelist) but `events.jsonl` carries NO turn-end event with a stop reason today,
  so mission 3 is a real addition, not a no-op.

## 2. Acceptance (a): the contract-test regression gate, failing first
status: done
dispatched: tdd-guide subagent (test custody, clean context), brief carrying the mission-1 wire
  contract. Output lands as edits to tests/contract/fake-zcode-app-server.py and
  tests/contract/test-zcode-acp-contract.py in the issue-113 worktree, plus the recorded baseline
  FAIL at kaola-workflow/issue-113/acceptance-a-before.txt. The production tree stays unmodified
  until it hands back, so the FAIL is a true pre-change baseline.
item: Extend `tests/contract/fake-zcode-app-server.py` with a scenario emitting a turn terminal
  that carries the `max_tokens` / `length` finish (and the ModelError
  `model_output_limit_exceeded` exhaustion variant), and assert through
  `tests/contract/test-zcode-acp-contract.py` that the resulting ACP `stopReason` is
  `max_tokens`. Record the FAIL output on the pre-change tree (it must read `end_turn`), which is
  the regression gate's proof. Test custody is separate from implementation.

## 3. Implement the translation and the verbatim persistence
status: done
dispatched: self
result: scripts/kaola-zcode-acp.py gains `is_output_limit_terminal()` (key-scoped, depth-bounded)
  plus a `terminal_stop()` helper that keeps `cancelled` first, and all three terminal branches
  now route through it. scripts/kaola-acp-holder.py appends a `turn_ended` event carrying the
  verbatim stop_reason. Gate flipped red -> green with the negative controls still holding.
  End-to-end proof through the REAL holder + fake app-server:
  kaola-workflow/issue-113/holder-persistence-check.txt — receipt `max_tokens`,
  record.json `last_prompt.stop_reason` `max_tokens`, events.jsonl
  `turn_ended{stop_reason: max_tokens}`; `failure` still refusal and `basic` still end_turn.
item: In `kaola-zcode-acp.py` translate the output-limit terminal to `stopReason: "max_tokens"`
  across the `turn.completed` / `turn.failed` / `turn.terminal` branches and `finish_turn`,
  without disturbing `cancelled` precedence. In `kaola-acp-holder.py` persist it unchanged into
  `record.json` `last_prompt.stop_reason` and add the turn-end line to `events.jsonl`. Mission 2's
  test must go from FAIL to PASS with no weakening of its assertions.

## 4. Independent review of the frozen candidate
status: done
dispatched: code-reviewer subagent on the frozen working-tree diff; findings return to me for the
  verdict. Runs while I take mission 5's gates.
result: verdict SOUND, no behavioural defect. I re-verified its two load-bearing claims against the
  bundle myself: `Woe` builds error as {type, ...NG(error), stack} and never sets `data`; `PJs` ->
  `RJs` lift context.providerCode onto top-level `error.code`. Accepted and applied: (1) the
  finish-reason fixtures were labelled "truthful" but that shape is never emitted, so they are now
  documented as defensive coverage of the signal the issue names (kept, since the issue
  explicitly requires detecting that signal); (2) the faithful exhaustion fixture now also
  carries `code: model_output_limit_exceeded` as the real wire does. No change: the review
  confirmed no false positive on input overflow / `{"reason":"stopped"}` / message-only text, no
  deadlock or #90 impact from `turn_ended`, and precedence intact. Its note that agent-exit
  and not-started paths write no `turn_ended` is correct and intended (no model stop reason exists
  there; `process_exited` is already logged). Because these edits mutated the candidate, the
  fail-first proof was re-run on the FINAL test bytes against the HEAD adapter:
  kaola-workflow/issue-113/acceptance-a-final.txt (BEFORE FAILED failures=5, AFTER OK).
item: Have a clean context review the exact frozen diff for defects it introduces — precedence
  bugs between cancelled/max_tokens, false positives on ordinary `stop` finishes, event-log
  cursor/retention effects on the Issue #90 confirmation bookkeeping, and whether the contract
  test actually distinguishes correct from incorrect behavior. Findings return to me; I hold the
  verdict.

## 5. Project gates: render check and full validate in the foreground
status: done
dispatched: self
result: render: `--check` FAILED at first (all ten generated trees embed hashed copies of
  kaola-acp-holder.py, and zcode also embeds kaola-zcode-acp.py), so a re-render WAS genuinely
  required. After `--write`: `render-skills: PASS (... budgets OK)`. The render copied the two
  scripts only; no template, SKILL.md prose or budget file changed. validate: first run EXIT=1 on
  a single case, test-issue-73 test_acp_start_under_a_dispatcher_passes_the_shell_to_the_acp_resolver
  ('heartbeat-host-conflict' != 'heartbeat-host-unresolved'). Root cause: this session inherits
  KAOLA_ACP_HEARTBEAT_HOST (+ _SOCKET, KAOLA_CLAUDE_PROFILE_REQUIRED) from the dispatching Host
  zcode-KPR-orchestrator-dsh-acp, and my first `env -u` list missed them. Proven unrelated: the
  same case passes once they are unset, and it covers start-time heartbeat binding, which this
  diff does not touch. Final run on the final candidate, all six vars unset:
  `VALIDATE_EXIT=0`, 0 FAILED, 38 suites — kaola-workflow/issue-113/validate.log.
item: `./scripts/render-skills.py --check` with every `templates/budgets.json` budget holding
  (adapter/holder scripts are not rendered surfaces — verify rather than assume, and only run
  `--write` if a generated surface genuinely changes). Then `./scripts/validate.sh` in the
  FOREGROUND (a backgrounded run dies with the session) under `env -u` for the ZCode Host
  variables, recording the exact outcome. Retry once if the parallel #112 run's test tmux
  sessions collide.

## 6. Acceptance (b): the deterministic live recipe and its receipt
status: done
dispatched: self. Output lands at kaola-workflow/issue-113/acceptance-b-live.txt (Runner receipt,
  record.json last_prompt, events.jsonl turn_ended, and the scratch DB finish_reason rows).
  Scratch HOME and a scratch record root under /tmp, removed afterwards; every Host-inherited
  KAOLA_* var unset so the start cannot bind to or notify the live Host.
result: BLOCKED — kaola-workflow/issue-113/acceptance-b-live.txt. The prescribed lever does not
  make the installed build hit its output ceiling, so no live max_tokens could be induced.
  RUN 1 (scratch config.json GLM-5.3 limit.output=256): receipt end_turn; scratch DB `stop|9186`
  output tokens in ONE request, i.e. the 256 cap never reached the model. RUN 2 (+ scratch
  provider_config.json manualProviderModelRules optionSpecs.maxOutputTokens.max=256): receipt
  end_turn; DB `stop|9137`. Cause, from the code: on ZCode 3.12+ the adapter registers the plan via
  `provider/updateAccountConfig`, which carries only `builtinModelIds`; `limit.output` ->
  `maxOutputTokens` (kaola-zcode-acp.py:469-470) flows ONLY through the pre-3.12 `runtimeModel`
  overlay. Stopped after one extra lever: each attempt costs ~3 min and ~9K real Coding Plan
  tokens, and further guessing is the overengineering loop AGENTS.md forbids. Making the cap
  effective would mean forwarding maxOutputTokens on the 3.12 path — a change to how the output
  ceiling is set, outside the Delegator's observability-only scope, so it is the Host's call, not
  mine. What the live run DID prove: the new events.jsonl `turn_ended` line and record.json
  `last_prompt.stop_reason` record the real app-server's stop faithfully (end_turn, twice), so the
  persistence plumbing is live-proven; only the max_tokens trigger is unexercised live. The
  max_tokens path is proven hermetically through the REAL holder on the exact `turn.failed`
  payload transcribed from the bundle (holder-persistence-check.txt). Cleanup verified: session
  stopped, 0 leftover procs, scratch (credential copies) deleted, real config.json still 128000,
  real provider_config manual rules still [], ~/.dsh untouched, kaola-ae2f524c untouched.
item: In a scratch `HOME`, set `limit.output=256` for the GLM-5.3 entry in the scratch
  `~/.zcode/v2/config.json`, start a ZCode session through the adapter, and request a text-only
  answer longer than 256 tokens. Capture the Runner receipt showing `stop_reason: max_tokens`;
  ZCode-side `finish_reason='length'` rows are corroborating, not the gate. User config stays
  read-only; nothing is written under `~/.dsh`; foreign tmux sessions are untouched.

## 7. Acceptance (c): draft the closing-comment paragraph for the Host
status: done
dispatched: self. Output lands at kaola-workflow/issue-113/acceptance-c-draft.md; read-only sqlite
  against the real ~/.zcode/cli/db/db.sqlite only.
result: kaola-workflow/issue-113/acceptance-c-draft.md — four exact `sqlite3 -readonly` commands
  (window/ceiling, finish_reason distribution, per-project output-limit finishes joined on
  session.directory, per-project exhaustion ModelError) plus the explanation, measured 2026-09-21:
  3,773 rows 2026-09-16..21, ZERO output-limit finishes, ZERO exhaustion errors, ZERO
  context_exceeded; max 14,558 output tokens = 11.4% of 128K. Schema read from the live DB, not
  guessed (model_usage.session_id -> session.id, project = session.directory). Not posted: the
  Host places it in the closing comment at finalize time.
item: Write the exact read-only sqlite count commands and the current-zero-occurrence explanation
  as a draft paragraph, delivered to the Host for placement at finalize time. Do not post to the
  issue.

## 8. Acceptance (b) rescue round (Host follow-up): find the app-level output-cap knob, rerun recipe v3
status: done
dispatched: self, on the Host's bounded brief (static reading first, at most two more live runs,
  no code change, no touch to the adapter's 3.12 registration path). Output lands at
  kaola-workflow/issue-113/acceptance-b-live-v3.txt.
result: PASS — kaola-workflow/issue-113/acceptance-b-live-v3.txt. Knob, cited from zcode.cjs: the
  per-request baseline is `lka` `_ = o.optionSpecs.maxOutputTokens.max` (line 14644) fed to
  `KJ = rwa(x) ?? twa(32000)` (line 14607). The model config comes from
  `aA.composeEffective(zcodeBuiltinModelRules, personalModels)` (line 71), which appends the
  personal exact rules LAST. So a scratch `$HOME/.zcode/v2/provider_config.json`
  `providerModelRules` entry {account:bigmodel-individual-coding-plan, GLM-5.3,
  optionSpecs.maxOutputTokens.max:256} overrides bundled `modelRules[6]` (128000). One live run
  (111.6 s, 1,024 output tokens) gave: receipt stop_reason `max_tokens`, record.json
  last_prompt.stop_reason `max_tokens`, events.jsonl turn_ended `max_tokens`, scratch DB 4×
  `length`@256. Mission 6's BLOCKED result stands as recorded: the prescribed config.json lever
  and the manual-rule variant really did not cap. Cleanup verified (session stopped, scratch
  deleted, real config/personal rules/~/.dsh untouched).

## 9. Correct the (c) draft with the recipe-v3 evidence
status: done
dispatched: self. Output lands at kaola-workflow/issue-113/acceptance-c-draft.md (v1 preserved as
  acceptance-c-draft.v1.md).
result: recipe v3 showed the exhaustion ModelError writes NO model_usage error row (all four
  capped rows are status=completed), so v1's error_code/error_message query would read 0 forever.
  I replaced it with the observed signature: per-project turns with >= 4 `length` rows (the first
  request + 3 auto-continues). Checked read-only on the real DB: turn_id is populated in 3816/3816
  rows, and the query returns zero turns today. Not posted.
