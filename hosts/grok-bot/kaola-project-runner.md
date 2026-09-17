---
name: kaola-project-runner
description: "Use when the controlling Agent should supervise explicitly authorized CLI workers through Project Runner on a bound execution target: locate that target's verified kaola-project-runner checkout, then load the main Skill and one selected platform worker from it."
---

# Project Runner bridge

Project Runner is the Git repository `KaolaBrother/kaola-project-runner`. This Skill holds no policy, transport,
path, or credential: everything is loaded from a verified checkout on the execution target you
bind.
Accepted revision: `bb6d74022bd187e86307a00b93ea8c869caf078f` (release v0.3.5).

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
4. Load `ROOT/skills/kaola-project-runner/SKILL.md` and follow it with ROOT, the target, and the consumer
   project root (a separate path on the same target) as inputs. When it selects worker
   `<platform>`, load only `ROOT/skills/<platform>-kaola-project-runner/SKILL.md` and run that
   directory's `scripts/runtime-tmux.sh` on the same target; never read script source.
