# Replace authoritative idle classification with observable snapshots and atomic guarded actions

- item: Design the deterministic observation, snapshot, editor, guarded-mutation, and human-answer contract against current runner architecture
  status: done
  dispatched: code-architect (heavy-reasoning tier) maps the current code and returns an implementation blueprint in /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-6/kaola-workflow-design-issue-6.md
  result: PASS — architecture freezes the model/Runner boundary, opaque evidence snapshots, fail-closed editor and hard guards, atomic compare-and-act, Claude-only proven answer replacement, advisory-only activity, Grok golden protection, and deterministic acceptance oracles.

- item: Establish independent failing acceptance for live failure fixtures, stale snapshots, editor guards, and the public answer path
  status: done
  dispatched: tdd-guide (standard-reasoning tier) owns only new/updated Issue #6 acceptance tests and sanitized fixtures in the issue worktree, proves the required behaviors fail on the current baseline, and returns exact RED receipts without editing production sources or documentation
  result: PASS — independent tests and eight sanitized Claude frames fail on baseline because observe/answer do not exist, non-Claude adapters lack explicit fail-closed answer capability, and send/stop still read activity as an authoritative gate; syntax, compilation, and diff checks pass.

- item: Implement the shared observation and compare-and-act control plane across source and generated Skills without weakening identity boundaries
  status: blocked
  dispatched: implementer (heavy-reasoning tier) owns the Issue #6 production control-plane sources, adapters, renderer/templates, and deterministic generated Skill output in the issue worktree; it must satisfy the frozen RED tests without altering their acceptance meaning, preserve frozen Grok golden bytes and prompt/task semantics, and return focused GREEN receipts
  result: BLOCKED — pure observation is GREEN, but tmux immediately SIGCONT-resumes its stopped pane leader on macOS, so the proposed direct SIGSTOP freeze cannot establish atomic compare-and-act; guarded mutation remains fail-closed at process-freeze-failed and partial work is preserved.

- item: Converge focused, full, and live-oriented validation and dock the new public contract in documentation
  status: done
  dispatched: inline by the controlling agent for README/API/architecture/conventions/CHANGELOG docking, focused-to-full validation, live five-platform tmux evidence within installed-account limits, and final renderer/Grok-golden cleanliness proof after test-carrier migration
  result: PASS — README, API, architecture, conventions, changelog, and a dated five-runtime relay smoke record dock the contract; ./scripts/validate.sh passes every renderer, Skill, lifecycle, relay, adapter, Grok, Claude, Cursor, installer, identity, and isolation surface, while live exact sessions prove the authorized prompt/approval boundaries and zero owned-session residue.

- item: Independently review the frozen candidate for correctness, transport safety, and regression coverage
  status: done
  dispatched: code-reviewer (heavy-reasoning tier) reviews correctness, regressions, frozen Grok boundary, documentation, and test coverage; security-reviewer (heavy-reasoning tier) reviews Unix-socket peer/timeout/framing safety, temp/socket ownership, payload secrecy, process-group/signal cleanup, exact session targeting, command injection, and lease recovery, both read-only against the frozen Issue #6 candidate
  result: PASS — independent review completed and found six concrete pre-finalization blockers: stale routed generated commands, prepare-time surface drift, outer-fence byte replay, placeholder ambiguity, escaped process-group descendants, and terminal-control injection. Each finding received its own failing acceptance and repair mission before the candidate could be frozen again.

- item: Revise the atomic transport design around the proven tmux pane-leader SIGCONT behavior without weakening snapshot or identity guarantees
  status: done
  dispatched: code-architect (heavy-reasoning tier) must use the reproduced tmux source/host behavior to either prove a tmux-native transaction or specify a managed pane relay/supervisor with exact child-runtime identity, in-band drain synchronization, failure recovery, migration, and testable public semantics in /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-6/kaola-workflow-design-issue-6-relay.md; no production/test/docs edits
  result: PASS — tmux-native atomicity is explicitly disproven; the minimal safe revision uses an attested nested-PTY relay, a tokenized grid-neutral DECRQM parser fence, exact child-process-group quiescence, lease recovery, schema-v2 byte revisions, legacy-direct refusal, and unchanged Grok workflow semantics. Local probes confirmed the nonce reply, grid neutrality, child freeze, and child teardown after relay SIGKILL on macOS.

- item: Establish independent RED acceptance for relay fencing, child identity/quiescence, recovery, schema-v2 staleness, and guarded public actions
  status: done
  dispatched: tdd-guide (standard-reasoning tier) revises only Issue #6 tests/fixtures to supersede the impossible direct-freeze assumptions with the relay contract, pins the tmux SIGCONT negative baseline and DECRQM fence proof, and proves current partial production remains RED without editing production/docs/generated Skills
  result: PASS — schema-v2, relay fence/PTY/identity/recovery, legacy-direct refusal, and public guarded-action tests are independently RED; live DECRQM nonce/grid-neutrality and child-query demultiplex probes pass, while current production lacks the managed relay and v2 hashes.

- item: Implement the attested nested-PTY relay, schema-v2 observation, relay-atomic actions, and deterministic five-Skill transport surface
  status: blocked
  dispatched: implementer (heavy-reasoning tier) owns production scripts/adapters/renderer/templates/generated Skills only, must make the frozen relay RED suites GREEN without editing tests/docs/Grok golden, and must stop at any fence, crash, identity, editor, or portability blocker rather than introduce a racy fallback
  result: BLOCKED — relay/fence/native/PTY surfaces reached GREEN and the public answer reached safe prepare, but two independently confirmed acceptance-carrier defects prevented truthful paste negotiation/prepared-frame verification; production preserved the fail-closed boundary and did not render stale Skills.

- item: Repair the relay PTY acceptance carrier to query pane-only tmux facts through the exact pane ID while preserving the input-off oracle
  status: done
  dispatched: tdd-guide (standard-reasoning tier) owns only the minimal test-path repair after independent tmux 3.7b proof that display-message -t =SESSION returns an empty pane_input_off while -t %PANE returns 1; acceptance semantics and production remain unchanged
  result: PASS — the test now resolves the one exact pane ID before querying pane_input_off; the unchanged relay identity/quiesce/disconnect/lease/SIGKILL oracle passes in 9.385 seconds.

- item: Repair the raw Claude acceptance TUI to truthfully negotiate bracketed paste and render prepared editor bytes before submit
  status: done
  dispatched: tdd-guide (standard-reasoning tier) owns only the fixture/test-carrier correction after proof that the current fake neither emits ?2004h nor redraws pasted editor content, while production correctly refuses unconditional paste wrapping and unverified replacement; public answer semantics remain unchanged
  result: PASS — the fake now advertises and disables bracketed paste, handles split delimiters and ordinary bytes, and redraws the prepared decision editor; public answer reaches answer-sent without relaxing production guards.

- item: Repair the schema-v2 receipt mutation oracle so integer counter premises are tested without falling through to the unknown-field failure
  status: done
  dispatched: tdd-guide (standard-reasoning tier) owns only the exclusive control-flow correction in test_observation_contract.py after the submitted_output_offset mutation was independently proven to fail in the test harness after the receipt itself passed
  result: PASS — integer counter mutations are now exclusive and the independent schema-v2 observation/receipt suite passes all 14 tests.

- item: Converge the relay public receipts, three-state output barrier, force-stop restoration, renderer packaging, and focused integration after the repaired acceptance carriers
  status: done
  dispatched: implementer (heavy-reasoning tier) resumes ownership of production scripts/adapters/renderer/templates/generated Skills only; it must repair the canonical-repo receipt, distinguish grid-neutral output-seen from satisfied, restore exact child/input state before force-stop, and make all relay plus original focused suites and renderer drift checks GREEN without editing tests/docs/Grok golden
  result: PASS — schema-v2 receipts use canonical repo facts without plaintext, grid-neutral output is output-seen until a changed fenced pane revision, exact force-stop restores relay state before killing only the owned session, Claude is a thin shared-core wrapper, and all five deterministic Skills package the relay/control overlay with frozen Grok golden bytes unchanged.

- item: Repair expected-refusal control flow in the native/legacy shell oracle so set -e cannot exit before expect_refusal inspects the required nonzero result
  status: done
  dispatched: tdd-guide (standard-reasoning tier) owns only guarded invocation of capture_command for the four expected legacy-direct refusals after xtrace proved production returned relay-required with exit 1 and the sourced set -e terminated the carrier first; refusal semantics remain unchanged
  result: PASS — all four expected refusals retain exit 1 and relay-required evidence, while the carrier now reaches expect_refusal; native/legacy acceptance passes.

- item: Migrate legacy acceptance carriers from idle-gated direct mutation calls to fresh schema-v2 observe/snapshot guarded actions without changing their ownership, literal-input, decision, or isolation assertions
  status: done
  dispatched: tdd-guide (standard-reasoning tier) owns only mechanical test-path migration in test-kaola-tmux, Claude runtime/human-decision, Grok compatibility, and Grok validation-isolation carriers, using public observe tokens and expected snapshot-required refusals while preserving all original behavioral verdicts
  result: PASS — Claude runtime/human-decision and Grok compatibility carriers use fresh public snapshots and pass; the migration preserved their original verdicts and exposed two genuine production failures in generic visible-work facts and multi-pane null-relay observation.

- item: Make multi-pane and other non-relay observations return typed fail-closed schema-v2 evidence instead of dereferencing a null relay object
  status: done
  dispatched: inline by the controlling agent in the shared core, with the existing unexpected-pane-count acceptance as the fixed verdict
  result: PASS — null relay state is normalized before identity/process lookup, so multi-pane observation reaches the typed unexpected-pane-count refusal without a Python attribute error.

- item: Make a positively recognized generic empty prompt report the adapter's applicable visible-work surface as known zero while unknown layouts remain unknown
  status: done
  dispatched: inline by the controlling agent in the pure generic frame observer; the structural prompt grammar, not activity_hint, controls known-zero versus unknown evidence
  result: PASS — a recognized prompt yields known-zero values for the generic adapters' applicable visible-counter surface, while unrecognized layouts remain unknown; Grok tokenized send and busy-state integration pass without consulting activity_hint as a guard.

- item: Prioritize the one-pane identity invariant before pane-derived repository checks during mutation preparation
  status: done
  dispatched: inline by the controlling agent after multi-pane evidence showed repo_match is necessarily unavailable when no exact pane can be selected
  result: PASS — mutation preparation now returns unexpected-pane-count before any exact-pane repo or relay lookup, preserving the specific identity refusal.

- item: Repair the migrated multi-pane and decision fixtures to assert schema-v2 observation evidence and a complete structured decision marker without reintroducing activity authority
  status: done
  dispatched: tdd-guide (standard-reasoning tier) owns only test-kaola-tmux and its shared fake runtime: assert pane_count/guard_failures from observe before a typed mutation refusal, and make the intended HUMAN_DECISION_REQUIRED fixture use the exact full structured block so ordinary stop refusal is structural rather than activity-gated
  result: PASS — multi-pane checks use reporting observation plus typed mutation refusal, the decision fake emits the complete marker, and the focused Kaola tmux carrier passes with no remaining production finding.

- item: Make a real launch with no platform-specific environment variables reach the managed relay instead of failing under nounset
  status: done
  dispatched: inline by the controlling agent after the first Grok live launch exposed an empty launch-environment array expansion in the shared core; preserve all adapter arguments and Grok semantics while adding a focused regression
  result: PASS — zero platform-specific environment entries take the explicit empty-array launch branch, preserving all adapter argv; focused and full launch suites plus real Grok startup pass.

- item: Keep runtime descendant process facts snapshot-authoritative without treating persistent CLI infrastructure as semantic busy work
  status: done
  dispatched: inline by the controlling agent after the live Grok process tree proved the CLI's own native launcher and Node worker are stable descendants; retain exact facts and staleness while leaving their meaning to the controlling model and preserving visible-work hard guards
  result: PASS — descendant tables/counts remain canonical mutation facts and reporting evidence, while the shell no longer treats stable launcher/worker infrastructure as a semantic busy gate; visible editor/work/approval/decision guards remain fail closed.

- item: Make relay request failures, half-open control sockets, and pane shutdown restore or terminate only the exact runtime group with zero orphan or socket residue
  status: done
  dispatched: inline by the controlling agent after a real Grok prepare failure left the child group stopped and a pane shutdown left one exact native descendant plus its epoch socket; add bounded socket handling, exception restoration, signal cleanup, and live residue proof
  result: PASS — request/read timeouts, disconnect restoration, signal cleanup, exact process-group teardown, and secure epoch-socket unlinking pass deterministic PTY/half-open/SIGKILL tests and live terminal residue checks.

- item: Bound live startup by the configured wall-clock deadline instead of multiplying that timeout by full observation latency
  status: done
  dispatched: inline by the controlling agent after OpenCode reached its TUI but the start controller remained in a nominal 20-second loop for more than one minute; preserve readiness checks and return start-pending at the actual deadline
  result: PASS — a single wall-clock deadline bounds the entire readiness loop; the dedicated timing oracle and all runtime launch suites pass.

- item: Rebind each adapter's TUI proof to the attested relay child plus live-proven stable platform surfaces instead of the pane leader command
  status: done
  dispatched: inline by the controlling agent after the managed relay correctly made pane_current_command Python and OpenCode's former direct-runtime predicate became impossible; add only measured platform surfaces during five-runtime validation
  result: PASS — all five adapters bind TUI evidence to the attested nested child and measured live surfaces; OpenCode empty chrome, Kimi workspace trust, Cursor placeholder, and Claude placeholder fixtures are structural and fail closed outside the complete surface.

- item: Reconcile force-stop transport loss with proven terminal absence so an exact successful shutdown cannot be reported as uncertain
  status: done
  dispatched: inline by the controlling agent after the live Grok relay terminated its exact child/session but closed the control connection before the terminating reply arrived; preserve exact-session ownership and require post-action absence plus zero socket/process residue before returning stopped
  result: PASS — force stop reports success only after exact session, child, process group, socket, and pane-input terminal facts converge; deterministic tests and live Kimi, Cursor, and Claude shutdown receipts prove zero residue.

- item: Preserve atomic stale-snapshot safety while allowing a live TUI that redraws an equivalent frame after every quiesce-resume cycle to accept input
  status: done
  dispatched: code-architect (heavy-reasoning tier) revisits only the schema-v2 snapshot/transport boundary after Claude Code proved each restored idle frame emits new grid-neutral child bytes; specify the minimal evidence split or lease transaction that keeps editor, identity, visible-work, approval, and later-output guards atomic without making raw activity authoritative or weakening Grok semantics
  result: PASS — pane_revision remains the complete transport-byte report while snapshot_id excludes output-only redraw counters and binds the equal visible frame, editor, identity, input offset, process, approval, barrier, and Git facts; a deterministic SIGCONT full-redraw fixture and live Claude Code both prove guarded workflow-next delivery, with Claude stopping at the measured expired-login boundary and exact zero-residue force shutdown.

- item: Make every generated Skill route send and stop through the schema-v2 observe and guarded-action API without changing frozen Grok lifecycle semantics
  status: done
  dispatched: tdd-guide owns only generated-Skill contract tests that prove every routed mutation example supplies a fresh snapshot and required editor guard, including the frozen-Grok transport overlay boundary; no production, template, or generated Skill edits
  result: PASS — baseline RED caught unguarded routed commands; the exact renderer overlay now routes all five generated Skills through fresh snapshots and editor guards while templates/grok-golden remains byte-identical, and deterministic generation/contract checks pass.

- item: Prove ordinary send and stop cannot act after prepare-time surface drift and cannot replay unaccounted outer PTY input around the fence
  status: done
  dispatched: tdd-guide owns only relay/guarded-action acceptance that deterministically reproduces prepare-time approval or editor drift plus prefix/suffix outer-input replay; no production, documentation, or generated Skill edits
  result: PASS — baseline RED reproduced all three races; send/stop now rebuild and revalidate the prepared surface, and the exact nonce fence refuses and discards any unrelated outer-PTY prefix or suffix instead of replaying it. Focused guarded-action and six-case fence suites pass.

- item: Make Claude and Cursor placeholder recognition distinguish rendered placeholder chrome from an identical user-entered editor value
  status: done
  dispatched: tdd-guide owns only observation fixtures/tests that prove true placeholders remain empty while identical typed text is nonempty or unknown; no production, adapter, documentation, or generated Skill edits
  result: PASS — baseline RED proved painted text alone was ambiguous; Claude and Cursor placeholder recognition now requires the measured input-origin cursor, while identical typed text with an advanced cursor is nonempty/unknown. Nineteen observation contract tests and a real styled Claude probe pass.

- item: Contain or track runtime descendants that escape the original child process group so guarded quiescence and force-stop cannot report a false terminal state
  status: done
  dispatched: tdd-guide owns only relay/process acceptance with a start_new_session descendant, proving mutation refuses incomplete containment and force-stop cannot succeed until every tracked runtime descendant is absent; no production/docs/templates/generated edits
  result: PASS — baseline RED proved a start_new_session descendant remained running and survived a false successful stop. The relay now recursively fingerprint-tracks, quiesces, resumes, and terminates escaped descendants; force-stop verifies their exact absence before success. The two-case escaped-descendant suite and relay PTY cleanup suite pass.

- item: Keep prompt and answer payloads literal by rejecting terminal control injection and embedded bracketed-paste protocol delimiters before any PTY write
  status: done
  dispatched: tdd-guide owns only public guarded-action/protocol acceptance for CR, LF, ESC, C0/C1 controls, and embedded paste delimiters, proving no early submit or child input; no production/docs/templates/generated edits
  result: PASS — forty baseline failures proved control bytes could reach the child. Send and answer now refuse CR, ESC, DEL, other C0/C1 and raw invalid controls before PTY writes; LF/TAB require attested bracketed paste and submit exactly once. The complete terminal-control acceptance passes.

- item: Re-review the repaired frozen candidate for correctness, security, regression coverage, and Grok-boundary preservation
  status: done
  dispatched: code-reviewer (heavy-reasoning tier) and security-reviewer (heavy-reasoning tier) independently inspect the final Issue #6 worktree read-only after the six review-derived repairs and full validation, returning only evidence-backed blockers or a clean verdict
  result: FAIL — correctness re-review reproduced three remaining mutation blockers: send could submit a prepared editor with foreign suffix bytes, a separately queued outer-PTY byte could escape the fence and replay after resume, and OpenCode placeholder text ignored cursor evidence. Security re-review continues independently under its own final audit mission; the candidate is unfrozen for focused RED and repair.

- item: Bind prepared send state to the requested payload so child-side editor drift cannot reach Enter
  status: done
  dispatched: tdd-guide owns only a deterministic public send acceptance that reproduces child-side foreign editor bytes after prepare and proves zero submit; no production/docs/templates/generated edits
  result: PASS — independent RED reproduced submitted=drift-send-foreign-draft. Send now verifies the relay's exact prepared payload fingerprint and requires the visible single-line editor fingerprint to match before Enter; the truthful raw TUI carrier redraws prepared text, and guarded-action acceptance passes.

- item: Refuse or discard separately queued outer-PTY bytes across the fence-to-submit boundary without replay
  status: done
  dispatched: tdd-guide owns only relay acceptance that splits the exact nonce reply and unrelated outer input across reads and proves no later child replay; no production/docs/templates/generated edits
  result: PASS — independent RED proved an exact nonce first read could hide a queued second byte. The fence now checks the immediately queued next read, submit refuses queued outer input, and restore/final-submit discard any disabled-pane race bytes; all seven fence tests pass.

- item: Bind OpenCode painted placeholder recognition to measured cursor-origin evidence
  status: done
  dispatched: tdd-guide owns only observation/adapter acceptance proving a true OpenCode placeholder is empty at the input origin while identical typed text with an advanced cursor is nonempty or unknown; no production/docs/templates/generated edits
  result: PASS — live OpenCode 1.18.23 measured the true empty placeholder at cursor_x=0, cursor_y=18. The adapter now passes pane facts and only cursor_x=0 can classify the complete painted surface as empty; identical entered text with an advanced cursor is unknown. Twenty observation tests pass.

- item: Perform the terminal independent correctness and security review of the fully repaired candidate
  status: done
  dispatched: code-reviewer (heavy-reasoning tier) and security-reviewer (heavy-reasoning tier) re-review the complete final diff read-only after prepared-payload binding, split-read fence hardening, OpenCode cursor proof, regenerated five-Skill output, and a fully green ./scripts/validate.sh
  result: FAIL — R3 split-read replay and R5 OpenCode cursor proof passed, but correctness re-review reproduced one remaining HIGH gap: multiline send skipped exact prepared-editor binding and submitted drift plus a foreign suffix. Security's prior OpenCode blocker is closed; the candidate is unfrozen only for multiline prepared-editor integrity.

- item: Bind multiline prepared send state to the exact requested text before Enter
  status: done
  dispatched: tdd-guide owns only a deterministic multiline variant of the prepare-time editor-drift public send acceptance, proving no submit when foreign bytes alter any prepared multiline editor; no production/docs/templates/generated edits
  result: PASS — multiline prompt and Claude answer preparation now reconstruct the visible editor through the cursor row and require its exact payload fingerprint before Enter; the independent foreign-suffix RED, legal LF/TAB single-submit oracle, and complete guarded-action suite pass.

- item: Isolate relay socket namespaces in tests and prove exact cleanup after direct teardown
  status: done
  dispatched: inline by the controlling agent owns only per-test TMPDIR isolation and exact post-test socket absence assertions; it must not remove shared or ambiguously owned stale sockets
  result: PASS — every relay-launching shell and Python carrier uses a short private /tmp namespace, asserts the socket stays inside it, and removes only that exact directory; relay PTY, escaped-descendant, Grok, terminal-control, and guarded-action suites pass without touching shared stale sockets.

- item: Independently re-review the final multiline and socket-isolation candidate
  status: done
  dispatched: code-reviewer (heavy-reasoning tier) and security-reviewer (heavy-reasoning tier) independently inspect the frozen full Issue #6 diff after exact multiline binding, private socket namespaces, regenerated five-Skill output, zero Grok-golden drift, zero owned residue, and a fully green ./scripts/validate.sh; both are read-only and must return evidence-backed blockers or a clean verdict
  result: FAIL — correctness reproduced a medium protected-behavior regression: a long single-line prompt that naturally wraps is reconstructed as a hard newline and refused before submit, including the frozen Grok large-prompt surface. Multiline/TAB drift guards otherwise pass; security review continues independently.

- item: Distinguish natural terminal wrapping from literal payload newlines during prepared-editor binding
  status: done
  dispatched: tdd-guide owns only public Claude and Grok acceptance for a long single-line prompt that naturally wraps, proving exact one-time submission without weakening the foreign-suffix multiline refusal; no production/docs/templates/generated edits
  result: PASS — a 40-column, 203-character no-LF public Claude/Grok RED proved the regression; current-frame capture now joins only tmux soft-wrap rows, so both platforms submit the exact original line once while real multiline/TAB fingerprints and foreign-suffix refusal remain GREEN.

- item: Perform the terminal correctness and security re-review after soft-wrap convergence
  status: done
  dispatched: code-reviewer (heavy-reasoning tier) and security-reviewer (heavy-reasoning tier) independently inspect the final frozen Issue #6 diff read-only after the soft-wrap RED repair, exact multiline/TAB binding, private socket namespaces, regenerated five Skills, zero Grok-golden drift, zero owned residue, and the second fully green ./scripts/validate.sh
  result: FAIL — correctness proved the initial soft-wrap repair still mixed a logical joined frame with physical cursor_y: a wrapped first logical line followed by a real newline/TAB was refused for Claude/Grok send and Claude answer. The constituent tests passed but the composition was uncovered.

- item: Map the physical tmux cursor row to the joined logical frame for wrapped multiline payloads
  status: done
  dispatched: tdd-guide owns only a composed public acceptance with a naturally wrapped first line plus real newline and TAB for Claude/Grok send and Claude answer, proving exact one-time submission while retaining foreign-suffix refusal; no production/docs/templates/generated edits
  result: PASS — Claude/Grok send and Claude answer composed REDs proved joined logical frames could not use physical cursor_y. The controller now derives cursor_logical_y from an exact cursor-clipped joined capture, and all three submit the original long LF/TAB payload exactly once.

- item: Prove wrapped multiline prepared-editor drift cannot hide a foreign hard line before Enter
  status: done
  dispatched: tdd-guide owns only a public prepared-time drift acceptance combining a soft-wrapped first line, real newline, and child-added foreign logical line, asserting typed refusal, zero submit, and preserved exact session; no production/docs/templates/generated edits
  result: PASS — independent Claude and Grok public regressions append a foreign hard logical line after a wrapped multiline payload; both return typed refusal, write zero submissions, and preserve the exact session under the logical-cursor mapping.

- item: Complete the terminal clean-room correctness and security verdict
  status: done
  dispatched: code-reviewer (heavy-reasoning tier) and security-reviewer (heavy-reasoning tier) independently re-review the final frozen Issue #6 diff after physical-to-logical cursor mapping and the composed foreign-hard-line regression, with regenerated five Skills, zero Grok-golden drift, zero owned residue, two consecutive focused guarded-action passes, and a final fully green ./scripts/validate.sh
  result: PASS — both independent reviewers returned zero blockers. Correctness confirmed R6 resolved across Claude/Grok long-wrap, composed LF/TAB send, Claude answer, and generated parity; security reproduced physical cursor_y=7 mapped to logical y=4 and proved foreign-hard-line coverage, zero submit, exact-session preservation, private cleanup, and frozen Grok golden bytes.

- item: Independently security-audit the final transport repairs and terminal cleanup boundary
  status: done
  dispatched: security-reviewer (heavy-reasoning tier) continues its read-only final audit of the Issue #6 candidate and returns evidence-backed blockers or a clean verdict
  result: FAIL — the security audit independently confirmed the OpenCode identical-placeholder cursor bypass as the sole remaining blocker; socket attestation, lease recovery, exact targeting, terminal-control payloads, force-stop proof, generated Skills, and frozen Grok boundaries otherwise passed its review frontier.
