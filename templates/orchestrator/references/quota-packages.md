# Quota packages

Read-only catalog for a consumer agent (Issue #148). These commands start no agent, session, holder or record and spend no quota; login environment is not required. Only `--installed-only` runs the Issue #147 survey login shell, keeping platforms whose survey status is `present`.

Package ids are `<platform>:<token>`. Manifest tokens and `model_package_rule` are validated at render. Rule kinds: `single`; `explicit` (exact model id); `provider_prefix` (segment before a slash or backslash, or the first element of a JSON-array id; a `gaps` entry forces unmapped); `native_field` (a row field such as `billingPool` or `limitIds`). A static query has no row: `native_field` uses a declared `absent` (codex `absent` is `primary`), otherwise unmapped; a present unknown value does not fall back to `absent`. Nothing guesses a package for an id the rule does not name.

## packages

`kaola-acp packages [--platform P] [--installed-only] [--login-shell SHELL]`

Exit 0. Stdout is one `kaola-acp-packages/1` object with sorted keys. `installed_only` is false unless set, and `login_env` is present only then (from `kaola-acp-survey/1`). Each row is `id`, `name`, `windows`, `binds_models`. `windows` lists confirmed reset windows (`5h`, `weekly`, `monthly`); it is null when no reset period is established and empty when the package is verified to have none. Omission from an array establishes no absence where provider docs leave a separate pool's windows unspecified; the field names windows only, not amounts or reset timestamps. For display, show the weekly or monthly window when the plan has one; show the 5h window only when it has neither. `binds_models` false is a balance listed for a later Usage reader, not a model target.

One platform:

```json
{"installed_only": false, "platforms": [{"packages": [{"binds_models": true, "id": "grok:account", "name": "Account", "windows": ["weekly"]}], "platform": "grok"}], "schema": "kaola-acp-packages/1"}
```

A platform with several packages:

```json
{"installed_only": false, "platforms": [{"packages": [{"binds_models": true, "id": "droid:standard", "name": "Standard", "windows": ["5h", "weekly", "monthly"]}, {"binds_models": true, "id": "droid:core", "name": "Core", "windows": ["weekly", "monthly"]}, {"binds_models": true, "id": "droid:extra_usage", "name": "Extra usage", "windows": []}], "platform": "droid"}], "schema": "kaola-acp-packages/1"}
```

Factory's Individual Plans docs give Standard Usage three rolling windows (5h, 7d, 30d); Droid Core has its own Rate Limits after Standard Usage runs out, with no documented Core-specific windows. The catalog therefore includes the verified 5h window for `droid:standard`, retains the owner-confirmed weekly and monthly windows for `droid:core`, and infers no Core 5h window ([Factory Individual Plans](https://docs.factory.ai/pricing/individuals)).

Omit `--platform` for every platform in Runner order. The object uses the same row shape.

## model-package

`kaola-acp model-package --platform P --model ID`

Exit 0 when the id is mapped or unmapped. A usage error exits 2. Stdout is one `kaola-acp-model-package/1` object: `schema`, `platform`, `model`, `packageId` (qualified id or null), `status` (`mapped` or `unmapped`).

Mapped:

```json
{"model": "grok-4.7", "packageId": "grok:account", "platform": "grok", "schema": "kaola-acp-model-package/1", "status": "mapped"}
```

Unmapped (no verified rule for this static query; droid `billingPool` is read from a live row, not from the model id):

```json
{"model": "claude-opus-5-5", "packageId": null, "platform": "droid", "schema": "kaola-acp-model-package/1", "status": "unmapped"}
```

## Emission stamps

`observe` and `status` stamp model leaves on the receipt copy: `configOptions` (including one nested group), `session_meta.models.availableModels`, `session_meta.availableModels`, and `initial_config_options`. `view` adds `models` (`availableModels` and `options`); `options` holds only the model config option. A mapped leaf sets `quotaPool` to the qualified id, omitting `quotaPoolStatus`; an unmapped leaf sets it null with status `unmapped`. Mode and effort options are left untouched. The holder's stored `session_meta` and `record.json` stay native ACP payload.

## Confirmed exhaustion

Recover only on a confirmed limit failure: an explicit runtime/provider error or usage fact in an existing receipt, capture or event that the quota is exhausted, a rate limit was reached, or a reset/window/account limit was stated. A bare 429, timeout, network error or reset-window metadata without an explicit limiting reason is not - nor is a session still connecting or awaiting a reply: keep the unknown, observe at the existing cadence, and escalate a persistent blocker with evidence. Label neither quota nor authentication; create no probe, retry loop, detector or new record - existing receipts and the heartbeat snapshot keep the evidence and any known pool/reset facts. A different preset or runtime is not fresh quota when evidence (the error, `quotaPool`, `model-package`) puts it in the exhausted pool; an unmapped pool proves neither.

Never log in: no attempt, retry or delegation of login, logout/login cycling, credential refresh or replacement, or account switching, and no change to credentials, billing routes or purchased quota.

By the limited seat's class ([worker-profiles.md](worker-profiles.md)):

| Class | Action |
|---|---|
| Expert | Preserve task, output and native resume id; ask the user. No substitute Expert, old grant reuse, or downgrade; unrelated work continues. |
| Elite | Preserve output and locator, exact-stop the seat, drop its availability from this run's heartbeat snapshot, and hand the task to another already-authorized Elite not sharing the limited pool, within existing counts/caps. Never restart it under the old grant or switch its model to bypass this; only the user reauthorizes it. |
| Worker | Preserve the task; another suitable Worker preset takes it under the pool permission (cap exemption kept, real limits applied). Never cycle a confirmed limited shared pool's seats. |

No suitable same-class replacement: report the blocked task with its evidence and ask the user; never cross classes, create grants or discard work. Under single-writer ownership the replacement continues the same run from its worktree, ledger and receipts: no duplicate claim, automatic redo or loss of valid output. Revocation touches only that seat in this run, never a preset, credential, global config or other-project grant. The Host's own limit failure is the Delegator's (`kaola-delegator` `references/host-brick.md`): report it, do not replace yourself.

## Account unavailable

An explicit `login expired`, `authentication required`, revoked or invalid credentials, `account disabled` or equivalent account-access refusal in an existing receipt, capture or event takes this branch; an explicit refusal with no supported class remedy does too, stating the reason. A timeout, 429, network error or uncertain message does not: keep the unknown and report a blocking access failure if the seat cannot continue. Not a limit failure: the class recovery above never applies.

Pause that seat: preserve its task, worktree/ledger locator, valid output and exact Runner identity; give it no new work; once the failed turn settles, exact-stop it under the existing safe lifecycle and mark it temporarily paused in this run's authorization/heartbeat snapshot: a pause, not a limit-failure grant revocation, deleting no model/profile, and unrelated authorized work continues.

Report to the user the affected runtime and seat, the exact runtime message, what was preserved, and that account repair outside KPR or another course is the user's call; ask for no secrets in chat and dispatch no other seat for that task before user direction. Resume only after the user confirms access restored and directs continuation, from existing receipts and records, with no duplicate claim or lost valid work; a user-directed replacement follows the existing seat/class boundaries. No automatic login probe or scheduled retry.