# Finalization summary — issue-41 (issue #41)

Issue: https://github.com/KaolaBrother/kaola-project-runner/issues/41
Candidate: `workflow/issue-41` @ `a19f528c33d19e024529474c3178ad9f47464c36`
Status: missions complete; offline validation PASS; live per-platform tmux smoke unexecuted.

## Delivered

Generated main orchestrator Skill `kaola-project-runner` (display name Project Runner)
from `templates/orchestrator/` through the existing `--write`/`--check` byte inventory.
It is a control-plane Skill, not an eighth platform: no `platforms/*.yaml`, no adapter,
not a `--platform` id. Installer puts it on every `--runtime` / `--skills-dir`
destination; `--platform` still filters workers only; `--no-orchestrator` skips it.
Worker Skills stay transport-only, with an optional pointer to the main Skill name.
`templates/grok-golden/` is unchanged.

## Files Changed

See `## Changed Paths`. New: `templates/orchestrator/`, `skills/kaola-project-runner/`,
`tests/contract/test-issue-41-orchestrator.py`. Tests were not weakened after TDD
(`git diff --exit-code fda090e a19f528 -- tests/ scripts/validate.sh`).

## Test Coverage

- `tests/contract/test-issue-41-orchestrator.py` (new, 9 tests): renderer inventory,
  not-an-eighth-platform, supported-worker summary from manifests, golden freeze,
  worker transport preservation, four scenario meaning checks.
- `tests/contract/test-generated-skills.py`: generated inventory includes the
  orchestrator without treating it as a platform.
- `tests/contract/test-installer-runtimes.sh` and `test-installer-migration.sh`:
  destination install, `--platform` worker filter, `--no-orchestrator`.
- `tests/contract/test-lifecycle-contract.py`: extra orchestrator templates allowed.
- `scripts/validate.sh` invokes the new suite and validates `*kaola-project-runner`
  including the main Skill directory.

## Validation

Finalize transaction: `classification: chains_green`, `mode: final-validation`,
`validated_candidate_hash: b3024e533ff6eb1074e43af3fe1dbef515bb53dfc2d0a7b332da0fd9081045cd`.
Agent record: `verdict: pass` for `./scripts/render-skills.py --check && ./scripts/validate.sh`
at `a19f528`. Independent review admitted no findings; orchestrator verdict PASS.

Unexecuted: live per-platform tmux smoke (start/observe/send/capture/stop). Out of
this issue's generation/install scope; adapters were not changed.

## Measured

- `./scripts/validate.sh` exit 0 at `a19f528` (this finalize run). A prior attempt
  in the same session failed once in `tests/contract/test-acp-follow-contract.py`
  (`pending_permissions` empty; later `test_holder_lost_emits_follow_error_line`);
  a serial retry on the same SHA passed 12/12, and `origin/main` also passed 12/12.
  Not treated as a candidate defect.
- `git diff origin/main...HEAD -- templates/grok-golden` empty at `a19f528`.

## Hypothesis

The follow-contract intermittency is timing around holder lifecycle, not this
diff (no ACP holder/follow files in `origin/main...HEAD`).

## Changed Paths

Finalize transaction listed AGENTS.md, scripts/, skills/, templates/, and tests/. Git
`origin/main...HEAD` also includes README.md, CHANGELOG.md, and docs/.

AGENTS.md
CHANGELOG.md
README.md
docs/README.md
docs/api.md
docs/architecture.md
docs/conventions.md
scripts/install-local.sh
scripts/render-skills.py
scripts/validate.sh
skills/claude-code-kaola-project-runner/SKILL.md
skills/codex-kaola-project-runner/SKILL.md
skills/cursor-cli-kaola-project-runner/SKILL.md
skills/devin-kaola-project-runner/SKILL.md
skills/grok-kaola-project-runner/SKILL.md
skills/kaola-project-runner/.generated-by-kaola-project-runner
skills/kaola-project-runner/SKILL.md
skills/kaola-project-runner/agents/openai.yaml
skills/kaola-project-runner/references/heartbeat-skeleton.md
skills/kimi-cli-kaola-project-runner/SKILL.md
skills/opencode-kaola-project-runner/SKILL.md
templates/SKILL.md.tmpl
templates/orchestrator/SKILL.md.tmpl
templates/orchestrator/agents/openai.yaml.tmpl
templates/orchestrator/references/heartbeat-skeleton.txt
tests/contract/test-generated-skills.py
tests/contract/test-installer-migration.sh
tests/contract/test-installer-runtimes.sh
tests/contract/test-issue-41-orchestrator.py
tests/contract/test-lifecycle-contract.py

## Documentation Docking

`.cache/doc-docking.md` → DOCKED.

## Issue statement coverage

| Issue #41 part | Satisfied by |
|---|---|
| Generate `skills/kaola-project-runner/` YAML name + marker, not an eighth platform | `test-issue-41-orchestrator.py`, `test-generated-skills.py`, `render-skills.py --check` |
| Render through existing inventory; worker summary from seven manifests | `render-skills.py` + TDD summary mutation test |
| Installer all destinations; `--platform` workers only; `--no-orchestrator` | installer tests + `--help` |
| README / architecture / AGENTS distinguish orchestration vs transport | docked docs |
| grok-golden frozen; workers stay transport-only | golden SHA tests + empty golden diff; worker template tests |
| Scenario meaning (recover, idle-before-stop, evidence-before-finalize, stop≠close-out) | `test-issue-41-orchestrator.py` + independent review |
| `render --write` / `--check` / `validate.sh` | recorded PASS |
| No extra engine / adapter / smoke heartbeat | review + empty `platforms/` and `scripts/adapters/` diff |

## Follow-Up Items

None filed. Review suspicions (implicit self-execute “on” behavior; resume triad
includes a fresh `start`) match Issue #41’s own wording and are not defects.

## Final readiness

Archived to `kaola-workflow/archive/issue-41`. User directed a pull request instead
of merge sink (main checkout has untracked `.cursor/` dirt). GitHub issue
metadata writes failed with this token (labels/comments); `Closes #41` is on
the PR.
