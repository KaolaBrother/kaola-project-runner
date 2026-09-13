# Issue #30 — 统一全部 Runner 的任务收尾与恢复建议（提示词驱动，无 hard gate）

Unify all Runner Skills' task-completion, resource-release, and resume guidance:
the shared prompt tells the main agent what it can do and when it is suggested;
the Runner only executes chosen operations and reports true results. No new hard
gate, auto-shutdown, watchdog, classifier, checkpoint/token system, or
orchestration layer. Prompt-level guidance only; Codex owns design and acceptance.

Base: `workflow/bundle-30` from accepted PR-29 head `b5854f0` (dependent PR
targets `workflow/bundle-28` so the diff contains only #30 changes).

## Missions

- item: Shared SKILL template — add end-of-delegation/resume guidance distinguishing
  reply-end vs delegation-complete vs project-complete; default-recommend stopping
  owned resources after delegation; keep session IDs/records; stop != delete history;
  no gates.
  status: done
  dispatched: self — edits land in templates/SKILL.md.tmpl, rendered into all 7 skills/
  result: "Ending, releasing, and resuming" section added; all 7 generated SKILL.md carry it

- item: ACP reference template — completion/stop/resume guidance: session/close when
  advertised, owned holder/agent exit + residual reporting, end_turn not completion,
  in-flight work follows existing cancel/exit path.
  status: done
  dispatched: self — templates/references/acp.md.tmpl
  result: "Ending and resuming an ACP session" section added

- item: Platform + transport reference templates — factual per-platform
  continue/resume syntax (no universal history/resume promise), native session ID vs
  Runner session name, stop reports actual exit evidence.
  status: done
  dispatched: self — templates/references/platform.md.tmpl + transport.md.tmpl
  result: Launch-section resume paragraph; transport stop semantics paragraph

- item: Docs — README + docs/api.md (and CHANGELOG) carry the same principles.
  status: done
  dispatched: self — README.md, docs/api.md, docs/conventions.md, CHANGELOG.md
  result: lifecycle paragraph in README (Chinese), api.md stop/resume paragraph,
          conventions.md sentence, CHANGELOG Unreleased entry

- item: Regenerate all 7 Skills, render --check, validate.sh; confirm grok-golden
  frozen; inspect diff for scope.
  status: done
  dispatched: self
  result: render --write WROTE 7, --check PASS (7), validate.sh PASS,
          test-generated-skills.py PASS, grok-golden diff empty

- item: Commit, push workflow/bundle-30, open dependent PR with base
  workflow/bundle-28, post evidence on issue #30. No merge/close/release.
  status: done
  dispatched: self
  result: commit 415a1cd389ac49479dfe01f7d85b42f355ffa973 pushed; PR #31 OPEN
          (base workflow/bundle-28); evidence comment posted
