# Issue 252 Sideagent terminology and consumer evidence

Scope is the current issue title/body and Latest owner correction, captured in
owner-correction-issue.json. This is the original issue-252 claim, not a new run.
The unchanged parent is df69f546f0a99c847a9bbd8fc38ac54d0714670e.

Before editing machine values, inspected scripts/kaola-acp.py session role
derivation, SESSION_ROLES readers, same-native inheritance and final start
recording; scripts/kaola-acp-holder.py spawn normalization, record/start_selection,
state/view/follow projections; scripts/kaola-dispatch.py launch_argv and recovery
role notes; shell forwarding; existing #244/#245 contract checks; public API and
ACP-watch consumer tables. These expose a public session_role string, not a
product role display-only name. Schema versions and field names stay unchanged.

Current source prompts, README/docs and generated Skills say Sideagent.
New explicit starts and dispatch plans use sideagent. The accepted legacy
sidekick flag/plan value and persisted session_role remain readable verbatim.
No live identity is migrated, no session is renamed and no admitted prompt is
replayed. Same-native resume with the current flag preserves a stored legacy
value; unrelated native resumes still derive the explicitly requested value.
Dispatch recovery recognizes the two values as the same role and only notes a
real persisted-role mismatch. Other role metadata remains non-authoritative.
The narrow public compatibility note is in docs/api.md, Session role; the
existing dispatch and watch consumer guidance references/maps the same values.

Native Devin Fusion IDs and model_display.components[].role main/sidekick
are provider model-composition facts, not this project role. Their manifests,
adapters, renderer and existing model-display checks remain unchanged. Existing
native strings and source locators remain valid. Historical receipts, the
interrupted archive, native session names and supporting /tmp notes were not
rewritten.

Affected existing #244/#245 checks now cover terminology across generated
references/README/docs, canonical start/dispatch/adapter values, legacy start
and persisted list/state/view/follow values, same-native resume identity, no
recovery dispatch or hot role change, and unchanged grant/class/capacity behavior.
The existing Fusion checks cover the distinct provider values. These are mock
and fixture checks; no additional live trial is claimed.

render-write-initial records the 8193-byte reference finding. Removing one
redundant article leaves that reference below the unchanged 8192-byte ceiling.
validate-interrupted records the intentionally stopped validation wrapper
(exit 130) before the same-native alias repair, not a completed validation.
Final render/validation logs and exit receipts record the corrected candidate.
bytes.md and bytes.json list every touched surface against the accepted parent.

Doc impact is the guidance, docs and role metadata this rename touches.
Host review remains the stop boundary; finalization and all sinks are stopped.

The first focused #245 run returned exit 1 because the new Grok mock fixture
did not advertise resume/loadSession. Its source assertions passed, but the
wire resume case correctly returned resume-unsupported. The fixture now
explicitly advertises resume (as the existing Codex resume fixture does).
The unchanged assertions passed in same-native-resume-focused.log (exit 0).
The original focused failure log/receipt are retained. This is mock capability
setup, not a new real grant or a manufactured credential failure. The final
full validation must establish the final candidate verdict.

Final verdict: render-write 0, render-check 0, full validation 0. All 64 touched
file hashes stayed unchanged. The full run passed the 46 #244 checks and 13 #245
checks, with the narrow watchdog prerequisite skips listed in skips.txt. Two
watchdog monitor/kill test cases were actually skipped on bash 3.2.57; affected
suites ran unwatched. No whole suite or missing-log skip occurred.
