# v0.9.2 install-migration evidence (2026-10-08, for root)

## Release facts (each separately verified)
- Tag: v0.9.2 (tag object ea07dff8) at R3 57ab88df160256e25722eeef4d338da73ffe1624, pushed to origin.
- Main merge: e38f5591 (merge of release-v0.9.2-staging P4 b8531bca), pushed.
- GitHub Release object: https://github.com/KaolaBrother/kaola-project-runner/releases/tag/v0.9.2
  published 2026-10-07T19:51:27Z (verified via API releases/tags/v0.9.2 after the bridge's 404 finding).

## Protected originals restored (triple byte verification: working tree = backup = R1 a6af2d88)
Backups: /tmp/protected-original-pre-merge-{INSTALL.md,bridge.json,kaola-delegator.md,accepted-revision.json}
- hosts/grok-bot/INSTALL.md            sha256 218b2e0fe55b5df9e81c9277b3759348efcc101b3c7c4bef818c08e673d65ae2
- hosts/grok-bot/bridge.json           sha256 27866e527152cb8ba92e1c31013a34abbb9761bcd8813c56b4c6a4d51787f1e5
- hosts/grok-bot/kaola-delegator.md    sha256 54fbdf39843e13a0e15d46ede86bb01c47c0f38bdab8656db5b5df4200e008ef
- templates/grok-bot/accepted-revision.json sha256 b9509fd150ffa8dc5931fbb834357f51b274f8d72d7a18ab11acd6b91dae6fc9
Main checkout holds them dirty with original ownership after the release merge.

## Install: gate refusal (preserved separately) then success
- FIRST attempt from post-merge main: every runtime REFUSED by the pin gate — verbatim refusal:
  "pin: P may differ from 57ab88df1602 only by templates/grok-bot/accepted-revision.json and the
  three generated hosts/grok-bot/ products; found docs/release-candidate-2026-10-08/…
  run ./scripts/render-skills.py --write in this checkout first, then re-run this install" (exit 1).
  Underlying gate evidence: r92-postmerge-render.log (exit 1, 18 pin findings, all docs-only).
  The first-run stderr files were overwritten by the successful reruns at the same /tmp names;
  the refusal text above is the verbatim in-turn record.
- SECOND attempt from the verified P4 tree (/tmp/kpr-v092-staging @ b8531bca): all seven runtimes
  exit 0 — r92-install-*.log in this directory (success logs).

## verify-install receipts (read-only verifier, captured after install)
r92-verifyinstall-{zcode,agents,codex,claude,cursor,grok,devin}.json — exit 0, result "aligned"
each; kaola-compact-recovery.py present in every root's kaola-project-runner/scripts; installed
kaola-dispatch.py sha256 b35d9df8… (release payload; supersedes v0.9.1's 7cbde08d…).

## Locator / accepted-checkout switch (shared links, live consumers untouched)
- Accepted checkout /Users/ylmacstudio/Workspace/kaola-project-runner-advanced — correct path:
  kaola-project-runner-accepted — advanced 3de9f61a (v0.9.1) → detached at R3 57ab88df (clean,
  origin verified). Shared links ~/.local/bin/{kaola-acp,kaola-acp-holder,kaola-project-runner-locate}
  keep the same target path, so they now resolve to v0.9.2 scripts without link churn.
- Register receipt (verbatim, relayed from the executing turn): action register, result ok,
  registration replaced (.kaola-project-runner-locate.json, target local, accepted_revision
  57ab88df…, root clean + revision_match true).
- Post-switch check receipt: r92-locator-check.json — result ok, revision_match true, head 57ab88df.
- Link-target hash: kaola-project-runner-locate resolves to kaola-locate.py sha256 e3b248d3…
  (identical to the v0.9.2 staging tree's script).
- No consumer session was stopped or restarted; in-flight work preserved.

## Not claimed as adopted
Payload install + locator switch ≠ live Host load. Consumer actual loading and real-business
maintenance receipts are coordinated by dot/root through the original bridges and remain pending.
