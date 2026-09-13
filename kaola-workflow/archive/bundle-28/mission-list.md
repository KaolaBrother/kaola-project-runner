# Goal: issue #28 — add Codex CLI as the seventh Kaola Project Runner platform (ACP default, explicit PTY)

Issue: https://github.com/KaolaBrother/kaola-project-runner/issues/28
Branch: workflow/bundle-28
Worktree: .kw/worktrees/bundle-28
Runtime: Devin CLI, model swe-2-max (owner-directed; do not change)
Spec: frozen issue body (2026-09-13 rewrite) + supervisor evidence at
/Users/ylpromax5/Documents/Codex/runner-issue28-design/ — Devin implements, Codex supervises.

## Missions

- item: Codex production surface — platforms/codex.yaml (ACP default, pinned
  npx @openai/codex@0.153.4 + @agentclientprotocol/codex-acp@1.11.0 command,
  model/reasoning_effort config IDs), scripts/adapters/codex.sh (PTY --no-alt-screen,
  resume/continue mapping, model/effort argv, read-only|agent|agent-full-access
  permission mapping), registration in kaola-tmux.sh, kaola-acp.py PLATFORMS +
  ACP_SKIP_MODE agent-full-access, kaola-model-policy.py probes + TUI evidence,
  install-local.sh selection.
  status: done
  dispatched: self — edits in .kw/worktrees/bundle-28 production files
  result: PASS — codex.yaml + codex.sh + all registrations landed; bash -n/py
  syntax clean; adapter acceptance PASS.
- item: Shared holder fixes — capability-object detection ({} means supported;
  absent/null/false unsupported) at resume/list/close/probe sites; continue
  follows nextCursor over cwd-filtered session/list pages and selects latest
  updatedAt, failing with factual identity evidence when indeterminate.
  status: done
  result: PASS — capability_object_supported() helper applied at all sites;
  continue paginates via nextCursor, filters cwd across pages, picks max
  updatedAt. 17-test holder contract suite green.
- item: Renderer inventory + generated codex-kaola-project-runner via
  render-skills.py --write; grok-golden frozen; no PTY-only capability logic.
  status: done
  result: PASS — 7 Skills rendered; render-skills --check CHECK-PASS; grok-golden
  byte-frozen (observation contract test_10 ok).
- item: Contract test coverage — fake-runtime lib + adapter/installer/model-policy/
  generated-skills/direct-transport/ACP suites extended for codex; holder unit
  fixtures for {} capabilities and list pagination; validate.sh green.
  status: done
  result: PASS — validate.sh fully green (8 suites + 7 skill validators);
  full issue-1 acceptance PASS incl. all ACP-default stale-suite repairs
  (--transport pty pins, schema v3, relay-attestation-failed, transport field).
- item: Docs + user-visible surface — README/docs platform counts and Codex
  ACP/PTY facts (CODEX_PATH vs CODEX_BIN distinction), CHANGELOG entry,
  AGENTS.md stale six-platform facts corrected surgically.
  status: done
  result: PASS — README codex row + transport note, docs/api+architecture+
  conventions seven-platform counts, AGENTS.md managed region corrected,
  CHANGELOG Unreleased entry added.
- item: Live smoke evidence — real Codex disposable ACP lifecycle
  (preflight/start/model+effort+mode/send two replies/capture/exact-stop+absence;
  exact resume on persisted completed history; continue on isolated cwd;
  cancellation/permission with harmless actions), PTY start/send/read/stop,
  honest per-platform smoke record.
  status: done
  result: PASS — Codex ACP full lifecycle on /tmp/kpr-i28-smoke/acp-repo:
  preflight adapter 1.11.0 all caps (incl {} objects); start configured
  model=gpt-5.6-luna/effort=low/mode=agent-full-access; two real replies
  (ALPHA + cross-turn recall); capture events; stop → holder+agent absent;
  --resume reattached same acp_session_id with history recalled post-stop;
  --continue cwd-filtered and picked latest updatedAt across repos;
  cancel → turn_canceled/stop_reason cancelled (receipt read raced
  holder-closed — cosmetic, cancel landed); read-only mode accepted.
  Codex PTY: start argv codex --cd --no-alt-screen --model gpt-5.6-luna
  -c model_reasoning_effort=\"low\" --sandbox danger-full-access
  --ask-for-approval never; trust via key enter; tui_detected+model_verified
  actual=gpt-5.6-luna; send → BRAVO; stop → absent.
  FINDING for supervisor: ACP mode read-only was configured:true but the
  codex-acp adapter still executed a file-write turn (HELLO.txt created);
  upstream adapter read-only does not sandbox tools like PTY
  --sandbox read-only. Transport semantics differ factually; Runner reported
  both faithfully.
  Existing platforms: grok/kimi-cli/cursor-cli/opencode full ACP cycles PASS
  (DELTA/ECHO/ECHO/FOXTROT); devin transport OK, upstream -32011
  resource_exhausted quota; claude-code PTY transport OK, upstream login
  expired. No i28- holders/tmux sessions remain.
