# Isolated candidate bytes (issue 244 release check)

This note is for a checkout that still carries candidate scripts. A copy
install of a released Skill does not have those checkout paths. Do not install
this checkout into a shared user Skill root.

Point the dispatch `--skills-root` at this checkout's rendered `skills/`
directory only when that tree is a runner-scripts harness without `SKILL.md`.
A full Skill tree (one that contains `SKILL.md`) refuses with
`worker-skill-build-skew`. The isolated route the Host used is
`/tmp/i244-qa-skills`: byte-compared candidate scripts, no `SKILL.md`, so the
invocation stays checkout-class. `runtime-tmux.sh` uses the `kaola-acp.py`
beside it, so the holder process is the candidate byte.

```bash
export KAOLA_ACP_RECORD_ROOT="<empty directory outside every shared skill root>"
mkdir -p "$KAOLA_ACP_RECORD_ROOT"
ACP="<checkout>/scripts/kaola-acp.py"
```

Keep that variable set for `list`, `execute`, `collect`, and `stop`. After an
admission, a send with a different `--expected-holder-instance-id` must return
`holder-instance-mismatch` and `mutation_status` `not_started`:

```bash
python3 "$ACP" <platform> send \
  --repo "$REPO" --session "<admitted session>" --no-wait \
  --text "binding probe; do not edit files" \
  --expected-holder-instance-id "not-the-live-holder"
```
