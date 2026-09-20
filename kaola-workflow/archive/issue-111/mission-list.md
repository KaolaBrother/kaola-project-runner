# Issue #111 — re-point Kimi/Droid/DSH/ZCode/Devin model presets at live-verified ids and add a third (alternative/fable) tier

Branch: `workflow/issue-111`
Worktree: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-111`
Main root: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner`

Host-confirmed decisions (do not re-ask): Droid alternative = `kimi-k2.7-code`;
Devin catalog read on live cli `3000.10.31`.

Boundaries: never write under `~/.dsh`, `~/.factory`, `~/.zcode`; never touch tmux session
`kaola-ae2f524c`; `templates/grok-golden/` frozen; `skills/` + `hosts/` regenerate only via
`./scripts/render-skills.py --write`. Do not finalize, merge, or close — the Host accepts first.

---

## 1. Third preset slot in the field registry and the shared template

- item: Add the optional third preset group (`alt_tier_label`, `alt_model_name`, `alt_model_id`,
  `alt_model_parameters`, `alt_model_effort`) to `REQUIRED` in `scripts/render-skills.py`, validate
  the all-or-nothing shape, and render it through a computed `TIER_BLOCK` (the `steering_block()`
  pattern) that is the empty string where no third tier is declared. Spend the prose in
  `templates/references/platform.md.tmpl`, not `templates/SKILL.md.tmpl` — cursor-cli has 152 B of
  `worker_skill_bytes` headroom. All ten manifests must carry the keys (empty where unused) because
  `parse_manifest` rejects both `missing` and `extra`.
- status: done
- dispatched: self
- result: `scripts/render-skills.py` carries `alt_tier_label`/`alt_model_*` in `REQUIRED` with an
  all-or-nothing shape check, plus `tier_block()` (SKILL.md, one sentence) and `alt_tier_line()`
  (references/platform.md bullet) injected through `variables()`. Ten manifests carry the keys;
  seven render them to nothing. `--check` PASS, every budget green.

## 2. Tier vocabulary across the CLI surface

- item: Teach `--tier` the third value in `scripts/kaola-acp.py` (choices + the `prefix` resolution
  at ~L1014) and `scripts/kaola-tmux.sh` (usage line ~L33, the `case` at ~L276, the preset branch at
  ~L329, and the `ADAPTER_ALT_MODEL_*` adapter variables). A third tier requested on a platform that
  declares none must be a typed refusal, never a silent fallback to `default`.
- status: done
- dispatched: self
- result: `--tier` is free-form in `kaola-acp.py` and validated after the manifest loads:
  `tier_declared()` + `tier_refusal()` answer `{"result":"refused","reason":"tier-not-declared"}`
  at exit 1 with nothing mutated. `kaola-tmux.sh` validates against `ADAPTER_ALT_TIER_LABEL` and
  dies by name on the PTY path. Two defects found and fixed while testing: the shell message
  doubled the label, and `kaola-model-policy.py --source` rejected `runner-<tier>` with an
  argparse usage error (closed four-value list -> validated `runner-<tier>` shape).

## 3. Five manifests + their adapters re-pointed at the live-verified ids

- item: `platforms/*.yaml` and the matching `scripts/adapters/*.sh` (the PTY path reads
  `ADAPTER_*_MODEL_*`, the ACP path reads the manifest — both are live and must agree):
  kimi-cli default `kimi-code/k3` "Kimi K3 Max" thinking=max + alternative `kimi-code/kimi-for-coding`
  "Kimi K2.8", no upgrade; droid default `kimi-k3` "Kimi K3 Max" reasoning_effort=max + alternative
  `kimi-k2.7-code`, no upgrade, `acp_model_map` still empty, `launch_summary`'s `model=auto` sentence
  rewritten; dsh default `opencode-go/deepseek-v4.1-flash` "DeepSeek V4.1 Flash (OpenCode Go)" with
  the Runner-side-display-name fact recorded and `acp_model_map` untouched; zcode `default_model_*`
  and the upgrade preset = GLM-5.3 at max; devin new `fable` tier `claude-fable-5-1-high`.
- status: done
- dispatched: self
- result: Ten `platforms/*.yaml` and five `scripts/adapters/*.sh` updated. Both transports now
  resolve identically, verified by direct probe: kimi-cli default kimi-code/k3 effort max /
  alternative kimi-code/kimi-for-coding effort max; droid default kimi-k3 effort max /
  alternative kimi-k2.7-code no effort; dsh default opencode-go/deepseek-v4.1-flash;
  zcode default GLM-5.3 effort max; devin fable claude-fable-5-1-high.

## 4. Tests pinning the new ids and the ZCode config-id tolerance

- item: One suite pinning each new default/alternative id, manifest/adapter agreement, the
  no-third-tier typed refusal, the equality of `platforms/zcode.yaml` with `ZCODE_HOST_MODEL_ID` /
  `ZCODE_HOST_EFFORT` (the issue's "no second source of truth"), and the `thought` /`thoughtLevel` /
  `thought_level` tolerance on both the read path (`kaola-acp.py`) and the adapter write path
  (`kaola-zcode-acp.py`). Register it in `scripts/validate.sh` — the suite list is explicit.
- status: done
- dispatched: self
- result: `tests/contract/test-issue-111-model-tiers.py` (22 tests, ~2 s, registered in
  `scripts/validate.sh` in `python_suites_all` and lane b; lanes still partition the 49-suite list
  exactly). Mutation-checked: re-pointing the ZCode default, narrowing the `thought` tuple,
  drifting an adapter id, and dropping Devin's `fable` label each fail it (5/1/1/5 failures).
  The first draft drove resolution end-to-end through `preflight`; that probes the real CLI
  catalogs (a single Droid probe ran past 2 min), so resolution is now asserted deterministically
  and only the refusal path -- which returns before any probe -- stays end-to-end on both
  transports.

## 5. Regenerate, document, and run both gates

- item: `./scripts/render-skills.py --write` then `--check`; `docs/api.md` gains the new field
  names; tier-prose docs and `CHANGELOG.md` get an unreleased 0.5.5 heading; `templates/grok-golden/`
  proven byte-identical; `./scripts/validate.sh` run in the foreground under
  `env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE -u KAOLA_ACP_DISPATCHER`, exit line recorded;
  per-skill byte headroom recorded against the issue's acceptance table.
- status: done
- dispatched: self
- result: `--check` PASS and `validate.sh` EXIT=0 (`/tmp/validate-111c.log`). Three
  pre-existing contract suites pinned the replaced behaviour and were updated, not weakened:
  `test-droid-acp-contract.py` (+ its fake agent's catalog) now pins the kimi-k3 default and
  gains alternative-tier and typed-refusal cases (13 tests); `test-zcode-heartbeat-contract.py`
  keeps the real #108 boundary (no Host machinery on a worker) while accepting the new preset;
  `test-generated-skills.py` gains narrow named leakage exemptions for the exact declared model
  facts, in the style it already uses for cursor-cli and devin. Docs: `docs/api.md` (new fields,
  the typed refusal, the rewritten Droid paragraph, and two duplicated lines removed from the
  manifest-fields paragraph), `docs/architecture.md`, `README.md`, `CHANGELOG.md` 0.5.5.
  Committed d6bd56b.

## 6. Deliver for Host review

- item: Report branch/worktree locators, changed-file summary, trimmed `--check` and `validate.sh`
  outputs, budget status, and every residual left open. Stop there — acceptance is the Host's.
- status: done
- dispatched: self; report delivered to the Host in-session
- result: Host ACCEPTANCE PASS for workflow/issue-111@d6bd56b, verified independently
  (render --check + budgets, grok-golden zero-diff, manifest diffs vs the issue's live ids,
  third-tier renders, 0 FAILED in the validate log, and a live probe through this worktree's
  generated kimi-cli runner: --tier alternative -> model=kimi-code/kimi-for-coding, effort=max,
  source=runner-alternative, probe session stopped cleanly). The Host's own rerun hit
  test_resolve_runtime_fails_closed, root-caused to its environment leaking
  KAOLA_ZCODE_ENTRY/KAOLA_ZCODE_NODE; stripped, the zcode contract suite passes 71/71.
  Accepted residuals, not fixed in this run: the validate.sh env-hermeticity gap (KAOLA_ZCODE_*
  and KAOLA_ACP_HEARTBEAT_HOST leak class) is pre-existing and Host-held for the release phase;
  Droid's alternative tier carries no effort (documented); the ZCode thought/thoughtLevel
  tolerated spelling is pinned by tests. CHANGELOG stays "0.5.5 - unreleased": tagging and the
  Grok Bot saveable pin are the Host's release step, after both runs land.
