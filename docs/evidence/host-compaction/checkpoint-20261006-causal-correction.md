# Checkpoint causal correction, Host1059

Independent parsing of ORIGINAL node tool commands --entries (shlex+JSON), not normalized checkpoint projection:
- core Codex945, Grok872, OpenCode1213: recovery#1 inputs have extra retained. This directly causes recovery-entry-unknown.
- edge Kimi1182, Devin1452: same extra retained; unavailable.links also overlaps checked.links, so after removing retained the scope-conflict check must be reconciled truthfully. Missing-originals path was NOT reached on original partial entry.
- edge ZCode1401 input has only input+checked, no unknown key; it settles recovery#1 verified. Its normalized result nevertheless has seq, proving seq is tool-added result provenance, not invalid input.
Source kaola-dispatch.py checkpoint_entry lines4794–4814 rejects extra input keys before checking scopes; lines4934–4937 adds seq to result projection. Host1056 inference from result projection was incorrect and is corrected here, without altering original raw outcomes/history or asserting a product defect.

Same-assignment repair: inspect exact input shape/prompt/node source; valid recovery entries use input/checked/unavailable/optional-applied only, with exactly one of checked/unavailable per scope. Do not weaken schema; no manual checkpoint/node/fake business edit. Preserve original negative proof as invalid-entry result. Positive finite actual automatic counterparts remain required; no broad native reread or full suite. Core and edge source custody and scope unchanged.
