verdict: DOCKED

Checked files:
- `platforms/cursor-cli.yaml` and `platforms/grok.yaml`: the Cursor `default_model_profile` contains the owner-approved Cursor-only sentence; Grok CLI retains the exact prior sentence. These are profile descriptions, with class and runtime configuration unchanged.
- `README.md`: renderer-generated profile table shows the distinct Cursor and Grok CLI rows.
- `skills/kaola-project-runner/references/profile-catalog.md`: authorized Host catalog rows agree with the README and source manifests.
- `skills/cursor-cli-kaola-project-runner/scripts/platform.yaml` and `skills/grok-kaola-project-runner/scripts/platform.yaml`: generated Agent-facing platform records match their respective source values.
- `CHANGELOG.md`: Issue #211 describes the Cursor-only profile wording and states `Seats: restart not required`.

No API, setup, architecture, environment, validation-instruction, or example documentation changes are needed: this issue changes only owner-authored profile wording. The existing renderer preserves single-source generation and the authorized-row disclosure. The frozen `templates/grok-golden/` surface was not changed.
