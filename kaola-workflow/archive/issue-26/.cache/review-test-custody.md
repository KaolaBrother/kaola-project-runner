# Test-custody review — frozen `833fc86` / issue #26

Reviewer: code-reviewer (test custody only).
Candidate: `833fc86f249bb512bf98ff60c53a2bb313cfdb61` on `workflow/issue-26`.
Worktree used to run suites: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-26`.
No candidate files were modified.

## Verdict

**DEFECTS** — 3 findings.

The implementer did **not** delete, rewrite, or green-wash the existing L0 suite, and did **not** unregister the new watch suite. `tests/contract/test-acp-contract.py` is byte-identical to parent `a3406d1`. `scripts/validate.sh` only adds a call to `test-acp-watch-contract.py`. Mock `watch_projection` is confined to `tests/contract/mock-acp-agent.py` and is not a production backdoor.

The committed #26 suite still fails the pre-implementation surface (RED proof: 7 FAIL / 1 PASS) and goes green on this candidate. That is not the defect. The defect is that several frozen-schema behaviors in issue #26 / `docs/acp-watch/list-view.md` are asserted so loosely that an **incorrect** implementation still passes the happy-path tests.

## What was checked and is clean

| Check | Evidence |
|---|---|
| `test-acp-contract.py` not weakened | `git rev-parse a3406d1:tests/contract/test-acp-contract.py` == `833fc86:…` == `2a1a69e…`. Still 14 tests. Ran on candidate: `Ran 14 tests in 17.643s OK`. |
| `validate.sh` registration | Single additive line after `test-acp-contract.py`: `python3 "$repo_root/tests/contract/test-acp-watch-contract.py"`. No other suite dropped. |
| Fixture vs design sample | `tests/contract/fixtures/kaola-acp-view-1.sample.json` is JSON-equal to the `### 样例` block in `docs/acp-watch/list-view.md`. |
| Mock not a production backdoor | `watch_projection` exists only in `tests/contract/mock-acp-agent.py` (`run_prompt` branch + `--scenario` allowlist). `scripts/` and `templates/` have no `watch_projection` / `mock-acp-agent` references. Helper changes (`message_id=None`, string-or-dict `ask_permission`) keep existing L0 scenarios on the string path. |
| Tests not swapped after RED | TDD proof lists the same 8 names; worktree mtime of `test-acp-watch-contract.py` is 08:38 (RED) vs commit 08:54; file hash at HEAD matches `833fc86`. |
| Candidate suite green | `python3 tests/contract/test-acp-watch-contract.py -v` → `Ran 8 tests in 4.213s OK`. |

Wording pins (`I'll start by`, `cookie`, plan titles `Read middleware` / `Patch redirect guard`, `Stale merged entry` absent) are the scripted mock stream, not a rewrite of the schema. Those pins **do** distinguish join/full-replace from a silent merge. They are not counted as defects.

---

## Finding 1 — `assert_shape` does not enforce the frozen type contract

**File:** `tests/contract/test-acp-watch-contract.py:72-100` (invoked from `test_view_matches_sample_key_set_and_types` at line 325)

**Issue #26 meaning:** happy `view` “matches `tests/contract/fixtures/kaola-acp-view-1.sample.json` by key set and type”; `docs/acp-watch/list-view.md` says `null` is allowed only on `|null` positions, and `ContentItem` is a closed union (`text`/`diff`/`terminal` with required fields).

**What the test actually does:**

```72:100:tests/contract/test-acp-watch-contract.py
def assert_shape(test: unittest.TestCase, sample: Any, actual: Any, path: str) -> None:
    ...
    if sample is None:
        return
    ...
        if isinstance(sample[0], dict) and "type" in sample[0]:
            for index, item in enumerate(actual):
                test.assertIsInstance(item, dict, ...)
                test.assertIn("type", item, ...)
                test.assertIsInstance(item["type"], str, ...)
            return
        if isinstance(sample[0], dict):
            for index, item in enumerate(actual):
                assert_shape(test, sample[0], item, ...)
```

- Sample `null` → **any** actual type is accepted (`commands`, `turn.outcome`, `turn.stop_reason`).
- `messages[]` is typed from `sample[0]`, whose `messageId` is `null`, so **every** message’s `messageId` skips the type check.
- Any array whose first sample element has `"type"` (i.e. `tools[].content`) only requires `type: str`. `{type:"garbage"}` is enough. Required `text` / `path`+`oldText`+`newText` / `terminalId` are not required here.

Later lines 348-356 only inspect `call_7` for `oldText`/`newText` presence, not the union.

**Concrete incorrect payload that still passes `assert_shape`:** take the checked-in sample and set `commands="not-an-array"`, `turn.outcome=123`, `tools[0].content=[{type:"garbage"}]`, `messages[0].messageId={"x":1}`. Replaying the candidate’s `assert_shape` against that object **raises nothing** (`assert_shape PASSED on incorrect payload`). Established by executing the function from `833fc86` against that input.

That is weaker than the issue’s “key set and type” acceptance, and would pass an implementation that violates the frozen `|null` and `ContentItem` rules.

---

## Finding 2 — `--since` only checks that flags are booleans

**File:** `tests/contract/test-acp-watch-contract.py:370-372`

**Issue #26 / `docs/acp-watch/list-view.md` meaning:** `view --since C` is still the current snapshot; when `C` is below the oldest retained cursor, the object must have `cursor_gap=true` **and** `truncated=true`.

**What the test actually does:** after a live `watch_projection` stream it calls `run_view(..., "--since", "0")` and only:

```370:372:tests/contract/test-acp-watch-contract.py
        gapped = self.run_view("grok", session, repo, "--since", "0")
        self.assertIsInstance(gapped["cursor_gap"], bool)
        self.assertIsInstance(gapped["truncated"], bool)
```

**Concrete incorrect behavior that still passes:** always emit `"cursor_gap": false, "truncated": false` (or always `true`). After any real EventLog, oldest cursor is ≥ 1, so `--since 0` must be a gap. The test does not require that. Established by reading the assertions; the candidate holder *does* compute `cursor_gap = isinstance(since, int) and … since < oldest` (`kaola-acp-holder.py:1184`), but the suite would stay green if that line were deleted or if `since` were left as a non-int.

---

## Finding 3 — rotation reload is not independently distinguished

**File:** `tests/contract/test-acp-watch-contract.py:374-396`

**Issue #26 meaning (test plan + design):** EventLog cursor reload from live **plus** rotated `.jsonl.1–.3` in order; “rotation still monotonic”; restart must not reuse cursor 1 on leftover high-cursor lines.

**What the test actually does:** writes `{"cursor": 800}` into `events.jsonl.1` **and** `{"cursor": 900}` into live `events.jsonl`, restarts, then `assertGreater(view["event_cursor"], 900)`.

**Concrete incorrect behavior that still passes:** restore max cursor from live `events.jsonl` only and ignore rotated files. Live already contains 900, so the next append is 901+ and the assertion holds. The rotated 800 never becomes the unique high-water mark. Established by reading the seed writes (lines 381-386) against `_restore_cursor`’s claimed contract (`kaola-acp-holder.py:98-128` iterates rotated+live). A distinguishing input would be: high cursor **only** on `.jsonl.1` (or `.jsonl.1` higher than live) and assert the new process continues above that rotated max.

The live-file leftover-high-cursor case **is** covered; the rotation half of the same requirement is not.

---

## Suspicions (not counted)

- `test_view_matches_sample_key_set_and_types` never binds `platform` / `session` / `repo` / `holder_pid` to the live `start` receipt. Combined with Finding 1 and wording that copies the fixture, a stub that returned the sample JSON for every `view` would pass **that one test**. The cursor-reload test would still fail a pure fixture dump (`event_cursor` 418 ≯ 900), so this is not suite-wide greenwashing.
- `test_list_is_host_wide_and_omits_dead_holders` omits a holder via `stop --force` (record remains, pid dead — so `pid_alive` **is** exercised). It does not cover a crashed holder whose `state` is still `ready`.
- Skill check is a backtick regex for `` `list` `` / `` `view` `` (`test-acp-watch-contract.py:454-464`), not that humans are told to subscribe with those commands.
- `holder-unreachable` and `unparsed_update_count` increment on unknown `session/update` variants are in the frozen schema and untested. Out of the numbered AC, so not findings.

---

## Mock `watch_projection` (not a finding)

`tests/contract/mock-acp-agent.py:333-413` is a scripted ACP agent scenario: thought + user chunk + two `m1` assistant chunks + `call_7` diff + two plan tables (stale then replace) + usage + mode + permission `{optionId,name,kind}`. It never `finish_turn`, which is why the tests use `--no-wait`. Production CLI/holder only talk to whatever `--command` the test injects. Existing L0 scenarios still pass string options through `ask_permission`.

---

## Conclusion

Test custody is **not** a greenwash of issue #26: L0 receipts stayed 14 OK and byte-stable, `validate.sh` gained the new suite, the sample fixture matches the design doc, and the mock scenario is test-only. The suite still distinguishes “no `list`/`view`/bin install” from the candidate.

It does **not** fully distinguish correct from incorrect **typed** `kaola-acp-view/1` behavior: the shape helper accepts illegal types and illegal `ContentItem`s, `--since` gap flags are type-only, and rotated jsonl reload can be skipped without failing. Those holes are in the frozen candidate’s tests as committed.

**conclusion: DEFECTS**
**finding count: 3**
**path:** `/Users/ylpromax5/Workspace/kaola-project-runner/kaola-workflow/issue-26/.cache/review-test-custody.md`
