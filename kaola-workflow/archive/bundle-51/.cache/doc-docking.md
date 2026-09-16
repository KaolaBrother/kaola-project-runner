# Documentation docking — bundle-51

Status: DOCKED
Candidate: `58d72ac87370e238359ef3c640a17d92a13fccd7`

- `README.md`: eight-worker inventory, ZCode default ACP, installed App runtime paths, BigModel Coding Plan bridge, and PTY product limitation are documented.
- `docs/api.md`: ACP/schema-v3 surface and platform-specific ZCode behavior are documented; no new public network API.
- `docs/architecture.md` and `docs/conventions.md`: eighth worker versus Grok Bot host, generated-skill architecture and progressive disclosure updated.
- `CHANGELOG.md`: ZCode addition and compatibility boundary recorded.
- `third_party/zcode-acp/UPSTREAM.md`: active upstream pin/license and Gate-2 reference-only decision recorded; no upstream runtime bytes vendored.
- `platforms/zcode.yaml`, generated `skills/zcode-kaola-project-runner/`, shared `templates/SKILL.md.tmpl` and `templates/references/acp.md.tmpl`: default ACP, no PTY login promise, and known-unsupported PTY diagnostic entry agree. Other generated workers inherit only the platform-neutral wording.
- `AGENTS.md`: project inventory and validation policy updated. No separate installer guide or example app is needed; `scripts/install-local.sh` and the README describe installation.

The source templates, not generated `skills/`, own future edits. `render-skills.py --check` and `validate.sh` passed at this candidate. Historical Issue #51 body still mentions PTY fallback and no credential read; the owner's later correction comments supersede it and the delivery comment will restate the final boundary before closure.
