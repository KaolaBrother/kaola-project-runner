# Goal: Issue #98 — dsh (DeepSeek Harness 0.1.5-rc.2) as the tenth Project Runner worker over ACP only

Run constraints, binding for every item below:

- **Never write anything under `~/.dsh/`.** Read-only observation only. dsh's own runtime writes
  under `~/.dsh/sessions/` caused by normally running the CLI are dsh behaviour, not an edit by this
  run; this run makes no hand edit to any dsh profile, patch, setting, or credential file.
- **No self-built proxy process or intermediate layer.** Bind directly to `dsh --profile acp`.
- **PTY transport out of scope.** `default_transport: acp`; PTY recorded `unsupported`.
- **R1 reference = OpenCode** (`platforms/opencode.yaml`, `scripts/adapters/opencode.sh`): the
  ACP-only, no-PTY-bypass manifest shape.
- ~~**PR-only.** Branch `workflow/issue-98`, open a PR, never merge. This run does not self-finalize;
  it stops at acceptance and reports.~~ **Superseded by the Host on 2026-09-20**, after acceptance of
  tip `45f6c68` and after PR #100 was already open: the PR-only instruction is withdrawn and delivery
  returns to the repository's normal route, Kaola-Workflow finalize plus merge-sink to `main`. PR #100
  becomes residue to settle, not the delivery. The constraint bound missions 1–7 as written and none
  of their recorded results change; only what happens after mission 7 changes.
- Anything irreversible or value-laden prints `HUMAN_DECISION_REQUIRED` and waits.

---

## 1. dsh ACP capability facts, established live

item: Establish the real ACP surface of `dsh --profile acp` on this machine by driving it directly
over JSON-RPC stdio — exact `initialize` result (protocol version, `agentCapabilities`, advertised
extras), `authenticate`, `session/new` with an absolute cwd, `session/prompt` settlement and
`stopReason`, `session/update` shapes, `session/request_permission` choice set, `session/cancel`,
`session/close`, and the `session/list` + `session/resume` pair. Confirm or refute the two shipped
README claims that drive the design: (a) `session/load` is rejected and resume is the non-standard
`session/resume`, (b) there is no `mode` config option, so no ACP skip-all. Record exact versions
and verbatim frames. Also record whether a live prompt is reachable at all with the credentials
present (a credentials-blocked prompt is a recorded fact, not a failure to hide).
status: done
dispatched: self — probe script `kaola-workflow/issue-98/evidence/probes/dsh_acp_probe.py`, raw
frames and verdicts landing in `kaola-workflow/issue-98/evidence/dsh-acp-facts.md`.
result: DONE. `evidence/dsh-acp-facts.md`, raw frames in `evidence/raw/`, probe in
`evidence/probes/dsh_acp_probe.py`. dsh 0.1.5-rc.2 serves ACP `protocolVersion: 1` as
`deepseek-harness-acp/0.0.1`; `agentCapabilities.sessionCapabilities = {close, list, resume}`,
`mcpCapabilities.http`, all `promptCapabilities` false, `authMethods: []` and `authenticate` an
immediate `{}`. Both README claims CONFIRMED: `session/load` is `-32601` and resume is
`session/resume`; there is no `mode` option and `session/set_mode` is `-32601`. Seven consequences,
each checked against the code: (1) **resume needs no holder change** — the holder already branches
on `sessionCapabilities.resume` and already tolerates the missing `sessionId` in the resume result;
proven live by resuming `e1995cb7-…` in a fresh process. (2) **`--continue` cannot work** —
`session/list` carries no `updatedAt`, so `latest_session()` answers `continue-ambiguous` even for a
single session; record continue unsupported rather than advertise a flag. (3) `set_config_option`
already sends `configId`, exactly what dsh expects; model values are JSON-encoded arrays-as-strings.
(4) **The shipped acp bundle pins the unauthenticated `deepseek-official` route** and ignores the
user's `agent-default-model`; `session/new` still succeeds and only the first prompt fails
`-32603 … no API key`. Fixed without touching `~/.dsh/` either by `DEEPSEEK_API_KEY` in the
environment or by `set_config_option` onto a credentialed route — the latter proven live:
`["opencode-go","deepseek-v4.1-flash"]` answered `PROBE-98-OK` in 2.52 s, `end_turn`. (5) **dsh ACP
is unattended by default**: zero `session/request_permission` across two tool turns, including a
bash write to `/tmp` *outside* the session workspace which succeeded. The honest line is "no
approval gate to skip", not OpenCode's "no skip-all". (6) Native steering unsupported — all four
candidate methods `-32601` — but `session/cancel` settles in **0.01 s** (`stopReason: cancelled`),
so the existing composite `--steer-mode interrupt` works at the default timeout. (7) Updates are
`agent_message_chunk` / `tool_call` / `tool_call_update` / `usage_update` only.
`~/.dsh/` integrity verified: all 16 config files byte-identical before and after
(`DSH_CONFIG_UNCHANGED`); probes ran against a throwaway `/tmp` cwd so no dsh session record was
created against this repo.

## 2. Repo-side integration surface and the resume gap

item: Read the repo's ACP integration surface — `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`,
`scripts/render-skills.py` manifest schema and validation, `scripts/kaola-tmux.sh`,
`scripts/adapters/opencode.sh`, `platforms/opencode.yaml` — and produce the concrete integration
design for dsh: every manifest key with its dsh value and its evidence, the adapter's launch line,
and a decision on resume. Specifically: does the holder's resume path hardcode `session/load`, and
if so is the right answer for this issue a dsh-specific resume branch or recording resume
`unsupported` for dsh this round? Prefer the smaller change; a speculative generalisation is not
authorised by this issue.
status: done
dispatched: self — design notes landing in `kaola-workflow/issue-98/evidence/integration-design.md`.
result: DONE. `evidence/integration-design.md`. The resume question is answered and the answer is
**no change**: the holder already branches on `sessionCapabilities.resume`, already sends `configId`,
and already negotiates protocol 1, so this issue is a registration change plus one manifest and one
adapter — no transport code. Registration surface inventoried from the Droid precedent: 11 source
files carry a hardcoded roster, and `kaola-model-policy.py::probes_for` is a bare dict lookup whose
omission is a `KeyError`, not a default. Every manifest key has a measured value; three depart from
the OpenCode template on evidence — `continue_syntax: unsupported` (no `updatedAt` in `session/list`
makes `latest_session()` permanently ambiguous), an `acp_model_map` (dsh's model values are
JSON-arrays-as-strings that no caller would type, and it is the escape hatch for the credential
problem), and the permission line, where copying OpenCode's "no skip-all; PTY --auto is the bypass"
would be wrong in both halves. `templates/budgets.json` is per-class, so no new budget entry — but
the new worker Skill must fit `worker_skill_bytes: 12288`.

## 3. Implement the platform

item: Add `platforms/dsh.yaml` and `scripts/adapters/dsh.sh` following the OpenCode shape, plus the
minimum renderer/holder change mission 2 justified. Then `./scripts/render-skills.py --write` and
`--check`, with budgets OK and `templates/grok-golden/` + `hosts/grok-bot/` byte-unchanged.
status: done
dispatched: self, inline in the candidate worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-98`; the
delivery landed in commit `cb689a7` on `workflow/issue-98`.
result: DONE — recorded late, during finalize reconciliation on 2026-09-20; the outcome itself was
delivered in `cb689a7` and is what missions 4, 5 and 6 then re-counted, validated live and reviewed.
`platforms/dsh.yaml` (5330 B) and `scripts/adapters/dsh.sh` (4623 B) follow the OpenCode ACP-only
shape with the three evidence-driven departures mission 2 justified (`continue_syntax: unsupported`,
an `acp_model_map`, and the no-approval-gate permission line). The minimum shared change was nine
files, and only one of them is transport behaviour: `kaola-acp-holder.py` (+46/-8, grouped select
options expanded one level in `config_option_choices()`), `kaola-acp.py` (the `acp_value_params`
guard for JSON-array descriptor values), and seven pure roster registrations
(`render-skills.py`, `kaola-model-policy.py`, `kaola-tmux.sh`, `install-local.sh`, `validate.sh`,
`kaola-locate.py`, `kaola-grok-bot-verify.py`). `./scripts/render-skills.py --write` produced
`skills/dsh-kaola-project-runner/` (SKILL.md 11964 B, under the 12288 B `worker_skill_bytes`
budget); `--check` PASS at the run tip with `10 workers + kaola-project-runner + kaola-delegator`
and budgets OK. `templates/grok-golden/` and `hosts/grok-bot/` are byte-unchanged against `main`
(empty diff).

## 4. Reconcile the nine-worker roster to ten

item: Update the roster/inventory contract suites and the prose that counts workers:
`tests/contract/test-generated-skills.py`
(`test_generated_skill_inventory_is_nine_workers_orchestrator_and_external`),
`tests/contract/test-installer-migration.sh`, `tests/contract/test-issue-78-heredoc-deadlock.py`,
`tests/contract/test-issue-88-permission-defaults.py`, `AGENTS.md`, `README.md`, `CHANGELOG.md`.
Change the count, not the assertions' intent.
status: done
dispatched: self
result: DONE, and it was wider than the issue predicted. Roster literals: five test files carried
their own `WORKER_IDS` (`test-issue-41`, `-49`, `-52`, `-72`, `test-progressive-disclosure`), and
two installer suites built fixtures from a hardcoded id list — those fixtures were the first
failures, because a missing `skills/dsh-kaola-project-runner` made the installer refuse. Counts:
`test-issue-78` 9→10 generated copies, `test-issue-50-runner-integration` 10→11 other packages,
`test-issue-65` 9→10 usable steering paths, `test-generated-skills` gained a dsh expectation block
and its inventory check is now `..._is_ten_workers_...`, and two test names that encoded the old
count were renamed (`test_install_all_nine`→`_ten`,
`test_orchestrator_is_not_a_tenth_platform`→`_an_eleventh_platform`). No assertion's intent was
weakened. `test-issue-88`'s derived set genuinely changed meaning: dsh joins
`NO_ADVERTISED_ACP_SKIP_ALL`, but for the opposite reason to Cursor/Grok/OpenCode, so README now
says that explicitly instead of lumping dsh under "a permission request may still arise". Docs:
`README.md` (counts, a dsh table row, and a dsh paragraph carrying the no-login / no-continue /
credential / profile-precondition facts), `AGENTS.md`, `docs/api.md`, `docs/architecture.md`, and a
`CHANGELOG.md` Unreleased entry.

## 5. Validate, and prove the worker live through its own generated Skill

item: `./scripts/validate.sh` to exit 0, then a live tmux ACP smoke against the real binary through
the generated `dsh-kaola-project-runner` Skill's own scripts in an exact session this run owns:
start → observe → send → capture → stop, ending with `residual_pids []`. Only sessions this run
created are touched. Record exact outcomes including any FAIL or unverified capability; never
report green for something not proven.
status: done
dispatched: self — `./scripts/validate.sh` plus a live smoke through
`skills/dsh-kaola-project-runner/scripts/runtime-tmux.sh` in a session this run owns; receipts land
in `kaola-workflow/issue-98/evidence/live/`.
result: DONE. `evidence/live-smoke.md`, receipts `evidence/live/01..08`, suite log
`evidence/validate-final.txt`. `./scripts/validate.sh` **exit 0**; `render-skills.py --check` PASS
with budgets OK. Live through the generated Skill in one owned session `dsh-KT-i98-smoke`:
preflight reported protocol 1 / `deepseek-harness-acp/0.0.1` / `login_required false` /
`load_session false`; `start --model opencode-go/deepseek-v4.1-flash` reached `state: ready` with
the picker id mapped to `["opencode-go","deepseek-v4.1-flash"]` and applied; `send` settled
`end_turn` and `capture` carried exactly `OPAL-98-OK`; a `--no-wait` long turn was steered
`interrupted_and_resent` / `cancel-confirmed` (turn 5 cancelled → turn 6) and the steered turn
answered exactly `OPAL-98-STEER`, proving the same ACP session kept its context; `stop` returned
`residual_pids []` with no surviving holder, `dsh --profile acp`, or background `sleep`. The steer
run also showed why `side_effects_possible` matters on dsh specifically: it answered by starting a
**background job** and ending its turn, so cancelling the turn did not cancel the work — only the
stop did. **One defect found and fixed inside this mission** (same promised outcome, no new
mission): the first preflight reported the grouped `model` option as `"values": [null, null]`; dsh
is the first platform with grouped select options, and the probe read `value` off the group entry.
`kaola-acp-holder.py::config_option_values()` now expands one level and the re-run lists all eight
routes. **One pre-existing failure reported, not fixed**: with `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE`
exported (as in this shell) `test-zcode-acp-contract.py::test_resolve_runtime_fails_closed` fails
because it does not clear them — reproduced on the clean `main` checkout at d300c7a, so it is not
this change; the exit-0 run used `env -u` for exactly those two variables. `~/.dsh/` config
byte-identical throughout: 16/16.

## 6. Independent review of the frozen candidate

item: Freeze the candidate SHA and have a clean context review the exact diff for defects it
introduces — manifest/adapter correctness against the mission-1 evidence, the resume decision, the
permission-default honesty (no implied skip-all, no implied PTY bypass), and whether any roster test
was weakened rather than re-counted. Findings return here for the verdict.
status: done
dispatched: two `code-reviewer` subagents on frozen candidate
`cb689a7321f6e84f5d0a3b1e006e9edb9e65b1fc` (branch `workflow/issue-98`, baseline `main` d300c7a),
cut two ways — (a) correctness: manifest vs measured evidence, adapter shell, the two shared-code
behaviour changes (`acp_value_params` guard, `config_option_values`), and any roster list still
missing `dsh`; (b) custody/honesty: whether any edited assertion was weakened rather than
re-counted, and whether any user-facing claim outruns the evidence, especially the
no-permission-gate fact. Findings return to this list for the verdict.
result: DONE — reviews collected, verdict held here, every finding dispositioned, repairs made
inside this mission (same promised outcome, custody unchanged). Both reviewers finished their full
cut. **Correctness: PASS with 7 findings** (D1/D2 "blocking-lite", 5 non-blocking). **Custody:
PASS on the literal question — no assertion was weakened** — with 4 custody gaps; **claim honesty:
6 findings**, 3 blocking. The two shared-code changes were cleared explicitly by the correctness
reviewer, who checked `config_option_values` against the real ACP schema
(`SessionConfigSelectOptions` is a list of options *or* a list of groups, so nesting is exactly one
level) and confirmed Cursor's `acp_model_map` values never begin with `[`, so the
`acp_value_params` guard is unreachable for the only platform using descriptors.

**The two convergent evidence findings were real and are fixed by measuring, not rewording.** I had
probed all ten `-32601` methods and read dsh's profile-template registry, but preserved neither, so
the manifest asserted more than `evidence/raw/` could show. Added probe phase `methods` →
`evidence/raw/method-surface.txt` (all ten, every one `-32601`, including the four the reviewers
flagged as unprobed) and `evidence/raw/profile-templates.txt` (shipped templates are exactly
`acp, headless, sdk, sdk-minimal, web`; **no `tui`** — the `--profile tui` in `dsh --help` names a
*custom* profile). Claims unchanged; the artifacts now back them, and `dsh-acp-facts.md` no longer
parks PTY under "not established" while the docs assert no terminal UI.

Repaired: **B-1** README "Nine Platform Runners" → Ten; **B-2/D3** `docs/api.md` platform-ID list
gains `dsh`; **B-3/D5** two stale "not a tenth platform" → "eleventh"; **D4**
`docs/architecture.md` core-accepts list gains `dsh`; **B-4** the README dsh operator brief now
leads with the no-approval-gate fact instead of burying it 374 lines away; **B-7** the CHANGELOG no
longer claims "transport code is untouched" and now documents the holder change and its
every-platform receipt effect; **A-2/A-4** stale nine-member docstrings; **D6** `dsh` added to
`test-issue-9-contract.py`'s roster (a suite validate actually runs).

**D7 was a real receipt regression and is fixed and proven live.** The helper had been applied to
the probe site only, so a grouped platform silently lost `value_name`/`value_description` from its
selection receipt — visible in this run's own `02-start.json`. Refactored into
`config_option_choices()` used by both sites; `evidence/live/09-start-after-d7-fix.json` now carries
`value_name: "deepseek-v4.1-flash"`, and that session stopped with `residual_pids []`.

**A-1 and A-3 were the sharpest findings and both are now closed with RED evidence.** A-1: the
existing roster check is satisfied by the word "dsh" appearing anywhere in README, so the reviewer
demonstrated that softening the paragraph into OpenCode's weaker "no skip-all" shape kept the suite
green. New class `DshHasNoApprovalGateAtAll` in `test-issue-88-permission-defaults.py` pins the
claim on all three surfaces, requires it inside the operator brief itself, and rejects OpenCode's
shape near `dsh`; mutation-proven — the reviewer's exact softening now fails 2 tests and the real
text passes 41/41. A-3: the two changed shared functions had **zero** test references repo-wide.
New suite `tests/contract/test-issue-98-dsh-acp.py` (24 tests, wired into `validate.sh`) covers
both functions, the dsh manifest against the measured frames, every roster registration, and that
the adapter never writes under `$DSH_HOME`; proven **RED with 15 failures** against the pre-fix
implementations and green with them.

Declined, with reasons: a full fake-agent contract suite on the Droid model (the two shared
functions and the dsh facts are now covered directly, and a fake dsh peer would re-test the shared
holder, not dsh); and the observation that `--transport pty --continue` is silently accepted on the
diagnostic PTY path (ACP is the real transport and refuses it honestly as `continue-ambiguous`,
and `continue_syntax: "unsupported"` documents it).

**No blocking item remains.** One pre-existing, non-dsh failure stands and is reported, not
hidden: `test-zcode-acp-contract.py::test_resolve_runtime_fails_closed` fails whenever
`KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE` are exported, reproduced on clean `main` at d300c7a. Repairs committed as `45f6c68` on `workflow/issue-98`
(tip after candidate `cb689a7`); `./scripts/validate.sh` → `VALIDATE_EXIT=0`, 680 tests, zero
FAILED/RED/SKIPPED; `render-skills.py --check` PASS, budgets OK.

## 7. Open the PR

item: Push `workflow/issue-98` and open a PR against `main` describing the change, the evidence, and
what is explicitly unproven. Do not merge. Authorised by the user's explicit PR-only delivery
instruction.
status: done
dispatched: self — `git push -u origin workflow/issue-98`, then `gh pr create --base main`.
result: DONE, on the Host's explicit go-ahead after acceptance of 45f6c68. Branch pushed as a new
remote branch (no force, no rebase). **PR #100** —
https://github.com/KaolaBrother/kaola-project-runner/pull/100 — `workflow/issue-98 -> main`, OPEN,
not a draft, MERGEABLE, 85 files +10915/-149, tip 45f6c68. The body carries Issue #98, the
ACP-only tenth-platform scope, the four measured facts that depart from the OpenCode template, the
two shared receipt fixes, the full verification block (VALIDATE_EXIT=0, 680 tests, zero
FAILED/RED/SKIPPED, render PASS with budgets OK, live smoke with `residual_pids []`, RED-before-
GREEN for both new test groups), and both flags stated as open rather than resolved — the
unreproduced intermittent `install-local.sh` hang and the external `~/.dsh/` change. Issue #98
stays OPEN. **Not merged, not finalized, not archived, not sunk** — those remain the Host's
transaction.
