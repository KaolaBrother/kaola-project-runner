# Independent QA Reader — #271 evidence

Reader role: independent QA reader with NO prior context on this project's dispatch tooling.
Date: 2026-10-07. Working dir: /Users/ylmacstudio/Workspace/kaola-project-runner

## 0. Hop log (every file opened, every --help, every failed attempt)

| # | Hop | Result |
|---|---|---|
| 1 | Read `/Users/ylmacstudio/Workspace/kaola-project-runner/skills/kaola-project-runner/SKILL.md` (264 lines) | Body. Points to `dispatch-collect.md` at lines 83 and 180-183. |
| 2 | Read `skills/kaola-project-runner/references/dispatch-collect.md` (132 lines) | Only because the body pointed there for command details. |
| 3 | `kaola-dispatch.py --help` | exit 0; top-level subcommands: project, execute, collect, snapshot, state, delegator. |
| 4 | `kaola-dispatch.py project --help` | exit 0 |
| 5 | `kaola-dispatch.py execute --help` | exit 0 |
| 6 | `kaola-dispatch.py collect --help` | exit 0 |
| 7 | `collect --index /tmp/reader-index.json --skills-root .../skills --item i271-reader` | **FAILED exit 2**: `{"detail": "index repo is required", "reason": "invalid-input", "result": "error"}` |
| 8 | Edited `/tmp/reader-index.json` to add top-level `"repo"` | retry |
| 9 | Same `collect ... --item i271-reader` command | exit 0, full turn-view JSON (receipt below) |
| 10 | `cat` / `stat` /tmp/reader-index.json | file byte-identical, read-only confirmed |

I read ONLY the two named files; I opened no other project file, no script source, and no other reference.
Refusals/errors hit: **1** (hop 7, `index repo is required`). The four `--help` calls (hops 3-6) all succeeded.

## 1. DISCOVERY — from the Skill body alone

(a) **Observe current seat occupancy before dispatching** → `project --seats --repo "$PROJECT" --authorization "$AUTH"`.
Body sentence (SKILL.md line 177-184): "Before planning, assigning, accepting or judging QA ... Planned dispatch (research, QA, report or implementation) uses `execute` (with `project --seats` and `collect`; ([dispatch-collect.md](references/dispatch-collect.md)))".
The precise command form is in the reference the body points to (dispatch-collect.md lines 47-49): "`project --seats --repo "$PROJECT" --authorization "$AUTH" [--live "$LIVE"] [--index "$INDEX"] [--skills-root "$SKILLS"]`: observed seats against supplied grants, count/shared occupancy and unknown reasons."

(b) **Dispatch a planned item** → `execute --plan "$PLAN" --authorization "$AUTH" --skills-root "$SKILLS"`.
Body sentence (SKILL.md lines 179-183): "Planned dispatch (research, QA, report or implementation) uses `execute` (with `project --seats` and `collect`; ...): it starts absent seats at the preset `--tier` and records their facts. Direct Runner `start`/`send` is standalone, degraded or same-assignment recovery".
Reference command form (dispatch-collect.md lines 50-51): "`execute --plan "$PLAN" --authorization "$AUTH" --skills-root "$SKILLS" [--availability "$AVAIL"] [--prior-index "$PRIOR"] [--index "$INDEX"] [--live "$LIVE"]`."

(c) **Collect results** → `collect --index "$INDEX" --skills-root "$SKILLS"`.
Body sentence (SKILL.md line 181-182): "Planned dispatch ... uses `execute` (with `project --seats` and `collect`; ([dispatch-collect.md](references/dispatch-collect.md)))".
Reference command form (dispatch-collect.md line 52): "`collect --index "$INDEX" --skills-root "$SKILLS"`: update correlation." and line 53: "Add `--item <exact item_id>` to `collect` for a read-only turn view."

## 2. PARAMS — minimal one-item plan + authorization

Files written (no `execute` run):

`/tmp/reader-plan.json`:
```json
{
  "scope": "qa",
  "repo": "/Users/ylmacstudio/Workspace/kaola-project-runner",
  "items": [
    {
      "item_id": "i271-reader",
      "preset": "zcode/default",
      "session": "zcode-KPR-i271-reader",
      "prompt": "Reply with exactly READER-DONE"
    }
  ]
}
```

`/tmp/reader-auth.json`:
```json
{
  "grants": [
    {
      "id": "zcode/default",
      "state": "granted",
      "count": 1
    }
  ],
  "exclusions": []
}
```

Format basis: dispatch-collect.md line 66 "`scope` is `research`, `qa`, `report` or `implementation`"; line 67 "`repo` is absolute, realpathed"; lines 67-70 "Each item has `item_id`, `preset`, `session` and `prompt`, plus optional ..."; lines 24-28 "Input: `grants[]` (`id` or grouped `preset_ids`, `state`, exact `count`, ...)" and "`state`: `granted`, `paused`, `revoked` or `excluded`".

Refusals/errors while learning the format: **1** total (the hop-7 `index repo is required`). The plan/auth formats produced no errors, because they were never executed (per instruction).

## 3. COLLECT-ENTRY — exact command + original receipt

Command determined (read-only turn view via `--item`):
```
python3 /Users/ylmacstudio/Workspace/kaola-project-runner/skills/kaola-project-runner/scripts/kaola-dispatch.py collect \
  --index /tmp/reader-index.json \
  --skills-root /Users/ylmacstudio/Workspace/kaola-project-runner/skills \
  --item i271-reader
```

Fixture `/tmp/reader-index.json` (schema kaola-dispatch-index/1, one item):
```json
{
  "schema": "kaola-dispatch-index/1",
  "repo": "/Users/ylmacstudio/Workspace/kaola-project-runner",
  "items": [
    {
      "item_id": "i271-reader",
      "session": "zcode-KPR-i271-reader",
      "status": "returned",
      "holder": "any"
    }
  ]
}
```

First attempt (before adding `repo`) returned exit 2:
```json
{"detail": "index repo is required", "reason": "invalid-input", "result": "error"}
```

Actual run after fix, exit 0, FULL JSON output (original receipt):
```json
{"count_scope":"complete-range totals or null; retained counts are inspected lower bounds; failure entries are observations, recovered ones included; outcome is the turn verdict","evidence_summary":{"failure_evidence":{"body_truncated_entries":0,"count":0,"first_cursor":null,"last_cursor":null,"omitted_entries":0,"omitted_first_cursor":null,"omitted_last_cursor":null,"raw":{"events":{"argv_key":"capture_argv","since":null,"source":"source","through":null},"status":{"argv_key":"status_argv","source":"source"}},"shown_entries":0},"permission_evidence":{"body_truncated_entries":0,"count":0,"first_cursor":null,"last_cursor":null,"omitted_entries":0,"omitted_first_cursor":null,"omitted_last_cursor":null,"raw":{"events":{"argv_key":"capture_argv","since":null,"source":"source","through":null},"status":{"argv_key":"status_argv","source":"source"}},"shown_entries":0}},"excerpt":null,"failure_count":null,"failure_evidence":[],"failure_present":null,"holder_instance_id":null,"item_id":"i271-reader","outcome":null,"pending_permission_count":null,"permission_count":null,"permission_evidence":[],"permission_present":null,"range_complete":null,"repo":"/Users/ylmacstudio/Workspace/kaola-project-runner","retained_failure_count":0,"retained_permission_count":0,"schema":"kaola-dispatch-turn/1","session":"zcode-KPR-i271-reader","source":{"as_of":"2026-10-07T06:50:20.719452+00:00","index":"/tmp/reader-index.json","runner":"/Users/ylmacstudio/Workspace/kaola-project-runner/skills/-kaola-project-runner/scripts/runtime-tmux.sh","since":null},"stop_reason":null,"truncation":{"evidence":false,"reply":false},"unknown_reasons":["dispatch-binding-missing"],"view_limit_bytes":8192}
```

Read-only proof: `cat`/`stat` after the run showed the fixture byte-identical (mtime 1791355817), so `--item` wrote nothing.

Observations: output `schema` is `kaola-dispatch-turn/1`; `unknown_reasons` is `["dispatch-binding-missing"]` (my fixture has no identity binding, expected); `source.runner` resolved to `skills/-kaola-project-runner/scripts/runtime-tmux.sh` (the platform segment resolved empty from the fixture `preset`/`session`, yet the call still returned a bounded turn view rather than erroring).

## 4. DEPENDENCY-SEMANTICS CASE (no-field baseline)

Case: item R10 is ready to start now; a stored `depends` lists item R08 needed only before ACCEPTING work W.

**Answer: Yes — R10 may start.** A dependency tied only to a later acceptance step is not a start blocker for unaffected work, and the guidance text has no per-item `depends` field that would hold an unrelated start.

Deciding sentences (SKILL.md lines 86-89):
> "Obey owner/project and single-writer rules. Holds stop only source-named actions. Distinguish implementation prerequisites, merge order and resource occupancy; a copied Host summary alone establishes no dependency. **Unaffected authorized work proceeds.**"

The clause "Holds stop only source-named actions" means the R08 dependency holds only the name it is attached to (accepting W), not R10; and "Unaffected authorized work proceeds" directly permits R10 to start.

Supporting text: SKILL.md line 176 "The count is a ceiling, not a target to fill; never invent work or expand authorization." and lines 177-184 (unaffected authorized work is dispatched). The only documented item-level prerequisite field is `requires` ("stated `class`/`presets`; unmet: `not-run` / `requirement-unmet`", dispatch-collect.md lines 69-70); there is no documented item `depends` field, which is the "no-field baseline".

## Summary

- Discovery commands named from the body: `project --seats` (observe occupancy), `execute` (dispatch), `collect` (collect). ✓
- Params files written to `/tmp/reader-plan.json` and `/tmp/reader-auth.json`. ✓
- Collect command run read-only against `/tmp/reader-index.json`; receipt captured; fixture unchanged. ✓
- Dependency case: R10 may start; deciding sentence quoted. ✓
- Refusals/errors: 1 (`index repo is required`).
