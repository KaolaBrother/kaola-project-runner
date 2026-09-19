# ZCode native Skill ACP live verification

Date: 2026-09-19 Asia/Shanghai

## Scope and safety

- Transport: ACP only through `runtime-tmux.sh`; no PTY.
- Fixture: `/tmp/kpr-zcode-native-live-cMR6oa`, an isolated empty Git repository plus two disposable project Skills under `.zcode/skills/`.
- ZCode entry: `/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`.
- Node: `/opt/homebrew/bin/node` (`v24.18.0`).
- No tracked project files changed; no credentials printed or written; no other session/Issue touched.
- Current generated adapter: `skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py`, SHA-256 `aafae87bfe2839e30d24e576cf9d03f360a829504b078988ffd18a729c8ddf36`, version `0.3.3`.
- User-installed adapter separately tested: `/Users/ylminiserver/.codex/skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py`, SHA-256 `a93139e94c195a689b67d5c5d54fa2de2cdc4f1fd7e36f156b2a72976c15515c`, version `0.3.0`.

## Exact command form

```bash
SKILL_DIR=/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/skills/zcode-kaola-project-runner
REPO=/tmp/kpr-zcode-native-live-cMR6oa
SESSION=zcode-kaola-kpr-native-skill-live-20260919e
KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs \
KAOLA_ZCODE_NODE=/opt/homebrew/bin/node \
"$SKILL_DIR/scripts/runtime-tmux.sh" start --transport acp --repo "$REPO" --session "$SESSION"
KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs \
KAOLA_ZCODE_NODE=/opt/homebrew/bin/node \
"$SKILL_DIR/scripts/runtime-tmux.sh" send --transport acp --repo "$REPO" --session "$SESSION" --text '/kpr-native-probe'
KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs \
KAOLA_ZCODE_NODE=/opt/homebrew/bin/node \
"$SKILL_DIR/scripts/runtime-tmux.sh" send --transport acp --repo "$REPO" --session "$SESSION" --text '/compact'
KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs \
KAOLA_ZCODE_NODE=/opt/homebrew/bin/node \
"$SKILL_DIR/scripts/runtime-tmux.sh" send --transport acp --repo "$REPO" --session "$SESSION" --text '/kpr-native-probe-after'
KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs \
KAOLA_ZCODE_NODE=/opt/homebrew/bin/node \
"$SKILL_DIR/scripts/runtime-tmux.sh" send --transport acp --repo "$REPO" --session "$SESSION" --text '/kaola-project-runner'
KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs \
KAOLA_ZCODE_NODE=/opt/homebrew/bin/node \
"$SKILL_DIR/scripts/runtime-tmux.sh" stop --transport acp --repo "$REPO" --session "$SESSION"
```

## Result matrix

| Check | Observation | Verdict |
|---|---|---|
| User-installed 0.3.0 start | `session/create` caused `zcode app-server exited`; first send was broken pipe | FAIL for current ZCode 3.12.3 |
| Current repo adapter start | ACP ready; mode `yolo` applied; native `sess_16034e51-79ac-4bf2-9346-55e3d6e0994f`; model account provider selected | PASS |
| Native disposable Skill | `/kpr-native-probe` returned unique body marker; capture cursors 11-13 show `tool_call` title `Skill` pending/in_progress/completed | PASS: native loading, not manual file read |
| Native Project Runner | `/kaola-project-runner` returned probe marker; capture cursors 23-25 show `Skill` tool call | PASS |
| Manual compact | `/compact` completed; ACP has no compact-specific event, so do not claim an ACP compact event | PASS for command path; event visibility is absent |
| New Skill after compact | `/kpr-native-probe-after` returned a marker that was never previously invoked; cursors 24-26 show a new `Skill` tool call | PASS |
| Project Runner after compact | `/kaola-project-runner` returned post-compact marker; cursors 34-36 show a new `Skill` tool call | PASS |
| Dollar-slash Project Runner form | `/$kaola-project-runner` produced a native `Skill` tool call (dollar-f form cursors 11-13), then correctly entered the Project Runner authorization flow; it was stopped without answering the permission prompt | PASS for native route; semantic work intentionally not run |
| Exact stop | `agent_exit_code=0`, top-level `residual_pids=[]`; post-stop `state=stopped`, `stopped=true`, `residual_pids=[]` | PASS |
| Real-model automatic compact | Not forced against GLM's 1M context in this run; prior runtime-only mock-provider evidence remains separate | NOT CLAIMED |

## Evidence receipts

All receipts are in this directory: `start-e.json`, `send-before-e.json`, `send-compact-e.json`, `send-after-e.json`, `send-project-after-compact-e.json`, `capture-after-e.json`, `capture-project-after-compact-e.json`, and `stop-e.json`. The capture receipts include the ACP `Skill` tool-call events and unique response markers.

## Inference boundary

The current generated adapter plus installed ZCode 3.12.3 runtime supports native Skill invocation through ACP, including a fresh native invocation after manual `/compact`. The older installed adapter is not a valid live carrier for this runtime until updated. This run does not prove a real GLM automatic-compaction case; that requires either a sufficiently large real context or a previously verified runtime-level automatic-compaction fixture.

## Addendum: Skill discovery roots (Issue #94 outer-review fix)

Binary evidence from installed ZCode 3.12.3
(`/Applications/ZCode.app/Contents/Resources/app.asar`, `createSkillsService` module):

- `getWorkspaceZcodeSkillRoot`   -> `<workspace>/.zcode/skills`
- `getWorkspaceAgentsSkillRoot`  -> `<workspace>/.agents/skills`
- `getUserZcodeSkillRoot`        -> `~/.zcode/skills`
- `getUserAgentsSkillRoot`       -> `~/.agents/skills`
- `resolveAncestorWorkspaceRoots` additionally scans BOTH `.zcode/skills` and
  `.agents/skills` on every ancestor directory up to the workspace boundary.

Live corroboration (scratch-HOME probe, real ZCode 3.12.3 app-server + mock
provider, `/tmp/kpr-i94-mock/probe.py`, one prompt each):

| Install root (only location) | Session | Request | Skills metadata `file:` |
|---|---|---|---|
| `<ws>/.agents/skills` | `sess_f4296520-6e74-4303-92fc-d1da2f61f6a5` | req-10 | `/tmp/kpr-i94-mock/repo/.agents/skills/kaola-project-runner/SKILL.md` |
| `~/.agents/skills` | `sess_e75048c5-5656-419a-9c64-971c481bd89a` | req-11 | `/tmp/kpr-i94-mock/home/.agents/skills/kaola-project-runner/SKILL.md` |
| `~/.zcode/skills` | earlier runs (sess_689f01f7 / sess_f5e7468c) | req-1 | `/tmp/kpr-i94-mock/home/.zcode/skills/kaola-project-runner/SKILL.md` |

So a consuming project may install the generated Skill under either
`<repo>/.zcode/skills/` or `<repo>/.agents/skills/` (project scope), or the
operator may install it under `~/.zcode/skills/` or `~/.agents/skills/` (user
scope). Ancestor-directory skill roots are also scanned; the list above is the
root set relevant to installer guidance, not a claim that no other discovery
mechanism exists (plugins/cache roots are separate).

Wire-evidence boundary unchanged: mock provider proves discovery/metadata on
the wire, not model behavior.

## Addendum 2: configured plugin roots (Issue #94 P2 outer-review fix)

Binary evidence (same `createSkillsService` module): `discoverSkills` also
appends `resolvePluginSkillRoots`, which reads `plugins.dirs` from
`~/.zcode/cli/config.json` via `readPluginConfigFromConfig`. Each configured
dir is treated as a plugin root: a plugin manifest
(`.zcode-plugin/plugin.json`, `.claude-plugin/plugin.json`, or
`.codex-plugin/plugin.json`) with a `skills/` directory is scanned.

Live corroboration (same scratch-HOME probe rig): `plugins.dirs` set to
`/tmp/kpr-i94-mock/extra-plugin` whose `.zcode-plugin/plugin.json` declares a
plugin and whose `skills/kaola-project-runner/SKILL.md` carries the generated
Skill. One-prompt session `sess_…` req-13: `skill_meta: True`, injected
metadata line
`kpr-extra:kaola-project-runner: Use when the controlling Agent should
supervise explicitly authorized CLI workers … (also loadable as
kaola-project-runner) (file:
/tmp/kpr-i94-mock/extra-plugin/skills/kaola-project-runner/SKILL.md)`.

So the four `.zcode`/`.agents` workspace+user roots are the **defaults** —
not the whole surface: `plugins.dirs` configured roots are scanned too
(plugin skills surface namespaced `<plugin>:<skill>` and stay loadable by
their plain name). A `--skills-dir` outside every discovered root still
arrives as plain text.

## Addendum 3 — `skills.roots` configured roots (Issue #94 P2 re-review)

App-server source (installed 3.12.3 `glm/zcode.cjs`): config key
`SkillsRoots:"skills.roots"`; session construction passes
`extraRoots:e.configResult.config.skills.roots` into the skills service
(`cM({extraRoots:…})`), alongside `extraResolvedRoots`; skill service gated
by `features.skill` + `skills.enabled`. `skills.roots` entries are scanned
as additional project-scope roots (`dbi(u,r)` per entry).

Live corroboration (same scratch-HOME probe rig, real app-server + mock
provider; real user config untouched): `~/.zcode/cli/config.json` set to
`{"plugins":{"dirs":["/tmp/kpr-i94-mock/extra-plugin"]},"skills":{"roots":["/tmp/kpr-i94-mock/extra-roots"]}}`
with `extra-roots/kaola-project-runner/SKILL.md` = the generated Skill.
One-prompt session `sess_c6d4605f…`: turn request req-17 system prompt
injected all three simultaneously —
`kaola-project-runner … (file: /tmp/kpr-i94-mock/extra-roots/kaola-project-runner/SKILL.md)`
plus the `~/.zcode/skills` copy and `kpr-extra:kaola-project-runner` from
`plugins.dirs`. (req-16/18 are title-generation requests and carry no
skills block — expected, not a discovery gap.)

So configured discovery = `skills.roots` (plain skill roots) AND
`plugins.dirs` (plugin roots, namespaced `<plugin>:<skill>`), on top of the
four default `.zcode`/`.agents` workspace+user roots and ancestor scanning.
