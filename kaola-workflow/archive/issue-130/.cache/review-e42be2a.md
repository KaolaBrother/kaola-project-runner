# Independent review — issue #130 candidate e42be2a (base 16b42b2)

Scope: `git diff 16b42b2 e42be2a` in `.kw/worktrees/issue-130`, checked against Fable design comment 3 on #130 (fetched with gh). Worktree left unmodified (`git status` clean).

## What I established

- Refusal path, `scripts/kaola-tmux.sh:99-116`. The check reads only the parsed arguments, in this order: argument parse, adapter identity, PYTHON_BIN resolution, then the `transport-pty-retired` refusal, then the #73 guard (`:130-159`), then the ACP dispatch. No manifest read, no Git call, no tmux call remains before it. `TMUX_BIN`, the tmux branch, `default_transport` and `KPR_DEFAULT_TRANSPORT` are gone. After the refusal, dispatch goes to `kaola-acp.py` on every path (`:163-235`).
- Receipt shape, probed live. The refusal is one JSON line on exit 1 with these fields: `schema_version` 3, `result` refused, `reason` transport-pty-retired, `action`, `platform`, `session`, `repo` as given, `mutation_performed` false, `mutation_status` not_started, `detail` "...ACP-only...", and `transport` {"requested":"pty","supported":["acp"]}. It matches design §1.1 and docs/api.md:298. It also fires with no `--repo`/`--session`, and with a drifted root plus `KAOLA_ACP_DISPATCHER` (suite cases).
- No other live path reaches tmux or PTY. `kaola-acp.py` dropped its `tmux has-session` probe and `--transport-reason`. The holder and `kaola-zcode-acp.py` have no PTY code. `render-skills.py` no longer ships the relay trio or observation, and a reintroduced `default_transport` fails as `extra=` (`render-skills.py:98-101`; test-runner-v2 and test-issue-130 both pin this). The only remaining tmux calls are `kaola-locate.py:216-222` (design §7 follow-on, out of scope) and the frozen golden.
- ACP regressions. The `kaola-acp.py` edits only remove code (the transport block becomes `{"selected":"acp"}`; the probe and argparse flag are gone). No model or permission logic changed. The new shell session-name check (`kaola-tmux.sh:160-162`) duplicates `kaola-acp.py:2604-2606`, same pattern, so no previously valid call is newly refused. The `kaola-grok-bot-verify.py` marker swap leaves `hosts/grok-bot/` with zero diff, so no R/P re-pin is needed.
- validate.sh lanes, checked by script. `python_suites_all` equals lane a ∪ lane b, with no duplicates and no missing files. Every `tests/contract/test-*` file is listed. `test-issue-22-bypass-all-approvals.py` is now in the gate (it was a gap before).
- Focused suites, with all KAOLA_*/KPR_* unset: test-issue-130-pty-retired (44 OK), test-issue-73-canonical-root (31 OK), test-runner-v2 (4 OK), test-issue-22 (12 OK), test-issue-24-opencode-no-skip-all (20 OK).
- Test custody spot checks:
  - The golden sha256 freeze from the deleted test-issue-9 is still enforced (test-issue-41 GOLDEN_SHA256, test-generated-skills GROK_GOLDEN_REVIEWED_SHA256).
  - ACP capture/observe/status bounding survives in test-progressive-disclosure (BoundedAcp*). Only the observation.py cases were removed.
  - The #73 accept oracle now lands on the ACP `heartbeat-host-unresolved` refusal carrying `canonical_repo`. That is a real downstream point, not a vacuous pass.
  - #104 N6–N6d are absorbed by TypedRefusal cases.

## Findings (none blocking)

1. **Low — an #8 guarantee is declared lost, not re-homed.** Design §3.2 required each of the six #8 classes to be mapped to ACP, adding mock-agent cases for any gaps. In `tests/contract/test-issue-130-pty-retired.py` `test_e_status_reports_the_native_selection` and `test_d_...`, class (e) ("status keeps model provenance") and the computed `model_verified` true/false verdict from (d) are instead pinned as absent: `assertNotIn("requested_model_source", status)` and `model_verified == "unknown"`. These are then recorded as a loss in CHANGELOG Unreleased ("Model evidence"). The ACP behavior itself predates this candidate (kaola-acp.py model code is untouched), so nothing regresses at runtime. But design §5 lists only four capability losses, and this is a fifth one the owner has not ruled on. Needs owner acknowledgement, not a code fix.
2. **Low — the new `unset KPR_CANONICAL_REPO` has no test.** Changed at `scripts/kaola-tmux.sh:52-54`. No test in `tests/` references `KPR_CANONICAL_REPO`. I verified the behavior by hand: an inherited `KPR_CANONICAL_REPO=/leak` on `status` no longer yields `canonical_repo` in the receipt. A regression that removes the unset would pass the gate unnoticed.
3. **Low — docs claim redaction for every platform.** AGENTS.md:25 now says "outbound text is redacted (#51)", and `templates/SKILL.md.tmpl:157-158` (rendered into all ten worker Skills) lists "outbound redaction" as a transport integrity check. The #51 credential `redact()` exists only in `scripts/kaola-zcode-acp.py:353-373,1092`. The holder's `scrub()` (`kaola-acp-holder.py:427`) masks sensitive keys in records and does not redact outbound prompts. For the other nine platforms this overstates a security property.
4. **Informational — some pty spellings get a plain error instead of the typed receipt.** All stay fail-closed; none is accepted:
   - `--transport PTY` (uppercase) exits 1 with the untyped stderr `--transport must be acp`.
   - `start --transport pty --steer-mode native` hits the steer-only `die` first.
   - `--transport pty --transport acp`: the last value wins and the call runs as ACP. That is consistent with how the parser treats every repeated flag.
5. **Informational — leftover dual-transport wording.**
   - `templates/orchestrator/SKILL.md.tmpl:69` says "every platform's default transport is ACP", and `:114` says "default transport" (rendered into `skills/kaola-project-runner/SKILL.md`).
   - README.md:543 says "Neither forcing PTY nor adding a gate".
   - The usage text (`kaola-tmux.sh:21-29`) still advertises `--if-snapshot` and `--replace-editor`. These are parsed but not forwarded; docs/api.md:512 says so.
   - None of these instructs PTY use.
6. **Informational — suite weaknesses.**
   - `NoTransportOption.test_transport_acp_is_a_no_op` compares only key sets, not values. Design §3.1(4) asked for per-key equality.
   - `NoLiveOption` skips any line containing "retired" or "refused". I re-ran the regex without that filter: the only hits are refusal statements, so there is no current miss.

Unverified: live ACP smoke per platform (not run; outside this review); installer copy-mode removal of stale `transport.md` and relay scripts from existing install roots (I read only `install-local.sh`, which uses `rm -rf "$target"` replacement; not executed).

VERDICT: ACCEPT
