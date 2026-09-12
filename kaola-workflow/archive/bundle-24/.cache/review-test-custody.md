# Test custody review — issue #24 candidate `e8b91c6`

Focus: did the candidate alter acceptance meaning, weaken RED tests, or leave a suite that a wrong implementation still passes?

Candidate: `e8b91c6d0750d4ae423ab345c9e320d2aee41b7f` vs parent `2ede8a8`.
RED baseline: `/Users/ylpromax5/Workspace/kaola-project-runner/kaola-workflow/bundle-24/.cache/tdd-red-proof.md`.
Test path: `tests/contract/test-issue-24-opencode-pty-bypass.py` (registered `scripts/validate.sh:25`).

## Findings

None that show the RED contract was rewritten, skipped, or pointed at README instead of the generated Skill ACP surface.

## Evidence

### 1. RED tests were not weakened, deleted, or reinterpreted

- SHA of `tests/contract/test-issue-24-opencode-pty-bypass.py` on `e8b91c6` equals the RED worktree file: `dab0b5fc94bea81d961629853d44d31d1f4a051f`.
- `diff` of that file vs `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24/tests/contract/test-issue-24-opencode-pty-bypass.py` is empty.
- `scripts/validate.sh` is identical to the RED registration (`python3 .../test-issue-24-opencode-pty-bypass.py`).
- No `unittest.skip` / `expectedFailure`. Production green is filling `acp_quirks`, not changing asserts.

The four originally-RED methods are still present and still call `assert_documents_pty_auto_bypass`:

- `test_manifest_acp_quirks_documents_pty_bypass` (manifest `acp_quirks`)
- `test_generated_skill_quirks_document_pty_bypass` (checked-in `SKILL.md` via `its known quirks are \`...\``)
- `test_generated_acp_reference_quirks_document_pty_bypass` (checked-in `references/acp.md` via `Platform quirks:`)
- `test_renderer_copies_manifest_quirks_into_skill_templates` (in-memory render of `SKILL.md.tmpl` + `acp.md.tmpl`)

RED proof failed all four on empty string (`AssertionError: '' is not true`). Same helper, same line of attack.

### 2. Acceptance meaning is still the quirks surface, not README

Docstring L9–L11: README/CHANGELOG/`launch_summary` are explicitly *not* this contract. Those files changed on `e8b91c6` but no test reads them.

The helper (L167–L196) still requires, on the extracted quirks text only:

- non-empty
- `--auto\b`
- `--transport\s+pty`
- `\b(skip(?:-all)?|auto-approve|permission)\b`
- not `opencode acp --auto|yolo|dangerously-skip-permissions|always-approve`

Extractors bind the generated interpolation, not the later template sentence `Select either channel explicitly with --transport acp|pty` (`templates/SKILL.md.tmpl:14`). Empty backticks would still fail; a whole-file `--transport` grep would have false-passed that sentence (`acp|pty` does not match `--transport\s+pty`).

Wrong implementations that still fail (probed with the live helper, files unmodified):

| input | result |
|---|---|
| `''` | FAIL empty |
| `'see README'` | FAIL missing `--auto` |
| `'no ACP skip-all; PTY --auto is the bypass'` | FAIL missing `--transport pty` |
| `'no ACP skip-all; via --transport pty is the bypass'` | FAIL missing `--auto` |
| `'PTY --auto via --transport pty is the bypass'` | FAIL no skip/permission word |
| `'no skip-all; opencode acp --auto via --transport pty'` | FAIL advertised ACP skip argv |

Keep tests (already green on RED) still pin start behavior: `acp_command == "opencode acp"` with no skip argv; `default_transport == "acp"`; `ACP_SKIP_MODE` omits opencode; tmux start case has no `opencode)`; PTY `ADAPTER_LAUNCH_ARGS=(... --mini --auto`; holder does not auto-answer `request_permission`; no `OPENCODE_PERMISSION`.

On `e8b91c6`, `python3 tests/contract/test-issue-24-opencode-pty-bypass.py` → 13 OK.

### 3. Production text is the issue-24 contract, not a near-miss wording lock

Filled value (`platforms/opencode.yaml:24` and generated Skill/acp.md):

`no ACP skip-all; PTY --auto via --transport pty is the bypass`

That is the documented fact (ACP has no skip-all; PTY `--auto` is selected with `--transport pty`). The required tokens are those facts, not an unrelated unique phrase the production text happens to contain.

### Suspicion (not a RED rewrite)

`assert_documents_pty_auto_bypass` is token-presence, not polarity. These still **pass** the helper:

- `'ACP skip-all; PTY --auto via --transport pty is the bypass'` (inverted)
- `'skip --auto --transport pty'` (token salad)

That would not catch a *lie in the quirks string* if the keep-without-skip tests still held. It would still catch empty quirks, missing `--auto`, missing `--transport pty`, and `opencode acp --auto` advertising. Not used to go green: production text is the true polarity, and the helper is byte-identical to RED.

## Conclusion

**PASS.** Candidate did not alter acceptance meaning. The four RED documentation assertions are unchanged and still the ones that fail empty `acp_quirks`, missing `--auto` / `--transport pty`, and advertised ACP skip argv on the generated Skill/manifest/render path. README-only or launch_summary-only would not go green. Keep tests still guard a fake ACP skip implementation. Residual gap is helper polarity, not a weakened suite.
