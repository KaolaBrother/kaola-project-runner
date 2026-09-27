# Quota packages

Read-only catalog for a consumer agent (Issue #148). These commands start no agent, open no session, create no holder or record, and spend no quota. Login environment is not required. `--installed-only` is the one path that runs the Issue #147 survey login shell; it keeps platforms whose survey status is `present`.

Package ids are `<platform>:<token>`. Manifest tokens and `model_package_rule` are validated at render. Rule kinds are `single`, `explicit` (exact model id), `provider_prefix` (the segment before a slash or backslash, or the first element of a JSON-array id; a `gaps` entry forces unmapped), and `native_field` (a row field such as `billingPool` or `limitIds`). A static query has no row: `native_field` uses `absent` when the rule declares one (codex `absent` is `primary`) and is otherwise unmapped. A present unknown value does not fall back to `absent`. Nothing guesses a package for an id the rule does not name.

## packages

`kaola-acp packages [--platform P] [--installed-only] [--login-shell SHELL]`

Exit 0. Stdout is one `kaola-acp-packages/1` object. Keys are sorted. `installed_only` is false unless the flag is set, and `login_env` is present only then (copied from `kaola-acp-survey/1`). Each package row is `id`, `name`, `windows`, `binds_models`. `windows` is null when no package reset period is established; otherwise the array lists confirmed reset windows (`5h`, `weekly`, `monthly`). An empty array means the package is verified to have no time-based reset. Omission from an array does not establish absence when provider documentation leaves a separate pool's windows unspecified. The field names windows only, not quota amounts or reset timestamps. For display, show the weekly or monthly window when the plan has one; show the 5h window only when it has neither. `binds_models` false is a balance listed for a later Usage reader, not a model target.

One platform:

```json
{"installed_only": false, "platforms": [{"packages": [{"binds_models": true, "id": "grok:account", "name": "Account", "windows": ["weekly"]}], "platform": "grok"}], "schema": "kaola-acp-packages/1"}
```

A platform with several packages:

```json
{"installed_only": false, "platforms": [{"packages": [{"binds_models": true, "id": "droid:standard", "name": "Standard", "windows": ["5h", "weekly", "monthly"]}, {"binds_models": true, "id": "droid:core", "name": "Core", "windows": ["weekly", "monthly"]}, {"binds_models": true, "id": "droid:extra_usage", "name": "Extra usage", "windows": []}], "platform": "droid"}], "schema": "kaola-acp-packages/1"}
```

Factory's Individual Plans docs give Standard Usage three independent rolling windows (5-hour, 7-day, and 30-day). Droid Core has its own Rate Limits after Standard Usage runs out; the docs do not state Core-specific windows. The catalog therefore includes the verified 5h window for `droid:standard`, retains the owner-confirmed weekly and monthly windows for `droid:core`, and does not infer a Core 5h window ([Factory Individual Plans](https://docs.factory.ai/pricing/individuals)).

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

`observe` and `status` stamp model leaves on the receipt copy: the model `configOptions` entry (including one nested group), `session_meta.models.availableModels`, `session_meta.availableModels`, and `initial_config_options`. `view` adds `models` with `availableModels` and `options`; `options` contains only the model config option. A mapped leaf sets `quotaPool` to the qualified id and omits `quotaPoolStatus`. An unmapped leaf sets `quotaPool` to null and `quotaPoolStatus` to `unmapped`. Mode and effort options are left untouched. The holder's stored `session_meta` and `record.json` stay the native ACP payload.
