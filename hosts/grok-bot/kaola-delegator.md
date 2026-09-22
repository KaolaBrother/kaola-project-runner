---
name: kaola-delegator
description: "Use when Grok Bot should delegate a project run through Kaola-Delegator on a bound execution target: locate that target's verified kaola-project-runner checkout, then load the Kaola-Delegator Skill from it."
---

# Kaola-Delegator bridge

Kaola-Delegator is delivered from the Git repository `KaolaBrother/kaola-project-runner`. This Skill holds no policy, transport,
path, or credential: everything is loaded from a verified checkout on the execution target you
bind.
Accepted revision: `d2d29538f662415cefe96e429cf36236c9d71a13` (release v0.5.7).

1. **Bind the execution target first**: Local Computer when the project, CLI, and tmux sessions
   live on that machine, otherwise the cloud Agent Computer. Nothing on one target is reachable
   from the other. Never clone, install, update, or change anything on Local Computer; the cloud
   target manages only its own checkout.
2. On the bound target run `kaola-project-runner-locate` with `--target local|cloud --expect-revision
   <accepted>`: the device-local locator registered there at first configuration. Its receipt
   names ROOT (that target's checkout), the normalised origin, HEAD, whether the tree is clean,
   and the host fingerprint; `--target` only echoes your declaration, so the locator itself
   compares the running host fingerprint and that declaration with the registration receipt
   kept beside its link and refuses on mismatch (a fresh conversation needs no memory of it).
   If the command is missing, ask for that target's workspace; never search the filesystem,
   and never enter, print, or pass a token (the target's own Git or GitHub CLI authentication
   is the only credential).
3. Refuse any `refused` receipt: origin must be `github.com/KaolaBrother/kaola-project-runner`, HEAD must equal the
   accepted revision, the tree must be clean, and the registration must match. Only on the
   cloud target may you fetch and `checkout --detach` the accepted revision in ROOT,
   re-register, and repeat step 2.
4. Load `ROOT/skills/kaola-delegator/SKILL.md` and follow it with ROOT, the target, and the consumer
   project root (a separate path on the same target) as inputs. Host status/start/resume/send/stop
   on this bound target use that Skill's Grok Bot co-location attestation; refuse `refused`.
   Do not load Project Runner or
   `ROOT/skills/<platform>-kaola-project-runner/SKILL.md` from this bridge; never read script source.
