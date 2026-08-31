Implementation is ready for finalization on `workflow/issue-10`.

Delivered:
- replaced normal relay quiesce/prepare/fence/submit with live observation plus one direct authenticated transfer;
- kept exact-session/relay/child identity, terminal-control, payload fingerprint, and exact-stop protections;
- report uncertain partial writes as `mutation_performed:null`;
- old relays remain readable and require an Agent-selected exact-session restart before mutation;
- rendered the shared contract into Claude, Cursor, Grok, Kimi, and OpenCode active Skills while preserving `templates/grok-golden/` byte-for-byte.

Evidence:
- Claude: failure reproduced twice before the change;
- Cursor: failure reproduced twice before the change;
- Grok: structurally shared path, previous live success preserved; no failure claim;
- Kimi/OpenCode: structurally shared path, live verdict remains unknown.

Validation:
- `./scripts/validate.sh` PASS at `f6d2839`;
- direct transport 5/5 and observation 16/16 PASS;
- focused transport, terminal-control, long-prompt, exact-stop, adapter, Cursor, Claude, Grok compatibility/isolation, and installer migration suites PASS;
- final candidate hash `b4adafd02b80bf82813b9533db78ae1884e020c52fe27dda9a745c9b3dabd84d`;
- gap sweep found no new independent causal class.

The remaining three full-acceptance failure classes were independently reproduced on clean `origin/main`, so this issue did not broaden into unmeasured platform or legacy policy changes.
