# Issue #24 TDD RED proof

Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24`

Production baseline unmodified except:

- `tests/contract/test-issue-24-opencode-pty-bypass.py` (new)
- `scripts/validate.sh` (registers that suite)

Suite registered as:

```bash
python3 "$repo_root/tests/contract/test-issue-24-opencode-pty-bypass.py"
```

## Command

cwd: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24`

```bash
python3 tests/contract/test-issue-24-opencode-pty-bypass.py
```

exit: 1

## Output

```
FFFF.........
======================================================================
FAIL: test_generated_acp_reference_quirks_document_pty_bypass (__main__.Issue24DocumentGeneratedAcpSurface.test_generated_acp_reference_quirks_document_pty_bypass)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24/tests/contract/test-issue-24-opencode-pty-bypass.py", line 221, in test_generated_acp_reference_quirks_document_pty_bypass
    self.assert_documents_pty_auto_bypass(quirks or "", "generated references/acp.md quirks")
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24/tests/contract/test-issue-24-opencode-pty-bypass.py", line 169, in assert_documents_pty_auto_bypass
    self.assertTrue(
    ~~~~~~~~~~~~~~~^
        text,
        ^^^^^
    ...<2 lines>...
        "--transport pty is the bypass",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
AssertionError: '' is not true : generated references/acp.md quirks is empty; Agent-facing ACP quirks must document that OpenCode ACP has no skip-all and that PTY --auto via --transport pty is the bypass

======================================================================
FAIL: test_generated_skill_quirks_document_pty_bypass (__main__.Issue24DocumentGeneratedAcpSurface.test_generated_skill_quirks_document_pty_bypass)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24/tests/contract/test-issue-24-opencode-pty-bypass.py", line 210, in test_generated_skill_quirks_document_pty_bypass
    self.assert_documents_pty_auto_bypass(quirks or "", "generated SKILL.md known quirks")
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24/tests/contract/test-issue-24-opencode-pty-bypass.py", line 169, in assert_documents_pty_auto_bypass
    self.assertTrue(
    ~~~~~~~~~~~~~~~^
        text,
        ^^^^^
    ...<2 lines>...
        "--transport pty is the bypass",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
AssertionError: '' is not true : generated SKILL.md known quirks is empty; Agent-facing ACP quirks must document that OpenCode ACP has no skip-all and that PTY --auto via --transport pty is the bypass

======================================================================
FAIL: test_manifest_acp_quirks_documents_pty_bypass (__main__.Issue24DocumentGeneratedAcpSurface.test_manifest_acp_quirks_documents_pty_bypass)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24/tests/contract/test-issue-24-opencode-pty-bypass.py", line 204, in test_manifest_acp_quirks_documents_pty_bypass
    self.assert_documents_pty_auto_bypass(quirks, "platforms/opencode.yaml acp_quirks")
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24/tests/contract/test-issue-24-opencode-pty-bypass.py", line 169, in assert_documents_pty_auto_bypass
    self.assertTrue(
    ~~~~~~~~~~~~~~~^
        text,
        ^^^^^
    ...<2 lines>...
        "--transport pty is the bypass",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
AssertionError: '' is not true : platforms/opencode.yaml acp_quirks is empty; Agent-facing ACP quirks must document that OpenCode ACP has no skip-all and that PTY --auto via --transport pty is the bypass

======================================================================
FAIL: test_renderer_copies_manifest_quirks_into_skill_templates (__main__.Issue24DocumentGeneratedAcpSurface.test_renderer_copies_manifest_quirks_into_skill_templates)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24/tests/contract/test-issue-24-opencode-pty-bypass.py", line 230, in test_renderer_copies_manifest_quirks_into_skill_templates
    self.assert_documents_pty_auto_bypass(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        skill_quirks(skill) or "",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
        "rendered SKILL.md.tmpl quirks",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-24/tests/contract/test-issue-24-opencode-pty-bypass.py", line 169, in assert_documents_pty_auto_bypass
    self.assertTrue(
    ~~~~~~~~~~~~~~~^
        text,
        ^^^^^
    ...<2 lines>...
        "--transport pty is the bypass",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
AssertionError: '' is not true : rendered SKILL.md.tmpl quirks is empty; Agent-facing ACP quirks must document that OpenCode ACP has no skip-all and that PTY --auto via --transport pty is the bypass

----------------------------------------------------------------------
Ran 13 tests in 0.023s

FAILED (failures=4)
```

## What failed vs what already holds

RED (4): empty `acp_quirks` on the generated Skill ACP surface (manifest, checked-in `SKILL.md`, `references/acp.md`, and in-memory render).

Already green on this baseline (9): `opencode acp` with no skip argv; `ACP_SKIP_MODE` omits opencode; tmux ACP start has no opencode `--mode`; PTY still `--mini --auto`; no auto-answer of `session/request_permission`; no `OPENCODE_PERMISSION` / permission-config skip substitute; templates still interpolate `{{ACP_QUIRKS}}`.

Full `./scripts/validate.sh` was not run (would fail at this new suite after earlier python tests).
