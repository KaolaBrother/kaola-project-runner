# ZCode Skill discovery — wire extract (Issue #94)

Provenance: scratch-HOME probe rig `/tmp/kpr-i94-mock` (real installed ZCode 3.12.3
app-server + local mock OpenAI provider; the real user config was never touched).
Each row is one one-prompt session; the lines below are copied verbatim from the
`skills` block the app-server injected into that turn's request, with only the
skill DESCRIPTION elided — the name and the `file:` path are the evidence.

Unrelated bundled plugin skills (browser-use, document-skills, skill-creator,
zcode-guide) are present in every block and are omitted here.

Probe config in the scratch HOME (`~/.zcode/cli/config.json`) for req-13/15/17:

```json
{"plugins":{"dirs":["/tmp/kpr-i94-mock/extra-plugin"]},"skills":{"roots":["/tmp/kpr-i94-mock/extra-roots"]}}
```

## req-1 — ~/.zcode/skills (default user root)

```
- kaola-project-runner: <description elided> (file: /tmp/kpr-i94-mock/home/.zcode/skills/kaola-project-runner/SKILL.md)
```

## req-10 — <workspace>/.agents/skills (default workspace root)

```
- kaola-project-runner: <description elided> (file: /tmp/kpr-i94-mock/repo/.agents/skills/kaola-project-runner/SKILL.md)
```

## req-11 — ~/.agents/skills (default user root)

```
- kaola-project-runner: <description elided> (file: /tmp/kpr-i94-mock/home/.agents/skills/kaola-project-runner/SKILL.md)
```

## req-13 — plugins.dirs configured plugin root

```
- kpr-extra:kaola-project-runner: <description elided> (also loadable as kaola-project-runner) (file: /tmp/kpr-i94-mock/extra-plugin/skills/kaola-project-runner/SKILL.md)
```

## req-15 — skills.roots configured root (this block carries no `~/.zcode/skills` copy)

```
- kaola-project-runner: <description elided> (file: /tmp/kpr-i94-mock/extra-roots/kaola-project-runner/SKILL.md)
- kpr-extra:kaola-project-runner: <description elided> (also loadable as kaola-project-runner) (file: /tmp/kpr-i94-mock/extra-plugin/skills/kaola-project-runner/SKILL.md)
```

## req-17 — skills.roots + ~/.zcode/skills + plugins.dirs, all three at once

```
- kaola-project-runner: <description elided> (file: /tmp/kpr-i94-mock/extra-roots/kaola-project-runner/SKILL.md)
- kaola-project-runner: <description elided> (file: /tmp/kpr-i94-mock/home/.zcode/skills/kaola-project-runner/SKILL.md)
- kpr-extra:kaola-project-runner: <description elided> (also loadable as kaola-project-runner) (file: /tmp/kpr-i94-mock/extra-plugin/skills/kaola-project-runner/SKILL.md)
```

## Boundary

The mock provider proves DISCOVERY and the metadata that reached the wire.
It proves nothing about model behaviour; model-side native `Skill` tool_call
evidence is the real-GLM ACP run in `zcode-acp-live/` and the matrix.
