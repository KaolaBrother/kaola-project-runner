# Documentation docking

The changed public surface is the shared Project Runner transport contract. The current README,
architecture, API, conventions, changelog, shared template, and generated platform references now
agree on these facts:

- routine transport does not quiesce the child, acquire a lease, run a fence, or create recovery
  barriers;
- snapshots and runtime observations are evidence for the controlling Agent, not mutation gates;
- direct-transfer uncertainty is reported as `mutation_performed:null`;
- old live relays remain readable and require an Agent-selected exact-session restart before mutation;
- scheduler and recurring-loop choices remain outside the Runner Skill contract.

No new platform-specific semantic policy or external API was introduced. Kimi and OpenCode retain an
unknown live verdict; Grok's frozen golden evidence was not rewritten.

Verdict: DOCKED
