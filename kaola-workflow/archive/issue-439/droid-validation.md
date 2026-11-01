# Issue 439 — Droid candidate evidence

Verdict: NOT GREEN for convergence. No pin or generated output changed; Host acceptance pending.

2026-11-01. npm @factory/cli latest 1.1.0; official native darwin-arm64 package 1.1.0 tarball SHA-1 67ee7276651810ba2ffe004869e09b1e8ee8e399, binary SHA-256 612bbc656fecf3330bbc2488822db862d70945a3b473a43d024e65199265b0d2. Bundled native ACP, no independently pinned adapter or declared external CLI range identified. Protocol 1; initialize agent @factory/cli 1.1.0. An isolated copy of the installed Runner skill changed only platform.yaml acp_command to the absolute candidate binary; no PATH shadow or fleet installation. DROID_BIN alone did not change the actual ACP command: identity was 0.241.1.

- Installed 0.241.1 control: ACP session 33767b2b-9223-4601-b227-c79c43f41521; auto and auto-high applied; send returned `KPR439 control OK.`, end_turn; capture read; exact stop exit 0, no residual PIDs.
- 1.1.0 default: session eb612a34-fb92-47ed-b322-d7ccc2aa5a85; auto, none and auto-high echoed; send returned `KPR439 latest OK.`, end_turn; capture read; stop exit 0, no residual PIDs. Resume with that native ID returned same ID and recalled the prior response; exact stop exit 0, no residual PIDs.
- 1.1.0 core: session 46404b76-b701-4460-a9dc-046f65cc9e55; model deepseek-v4.1-flash-1017 and reasoning_effort=max applied and echoed, auto-high; actual response `KPR439 core OK.`, end_turn; capture read; exact stop exit 0, no residual PIDs. This is account-specific evidence, not a grant change or proof for other accounts.
- 1.1.0 busy steer: session ecfdc8a0-1fee-4dec-aab2-247b34532242; native session/prompt while a turn was active returned JSON-RPC -32600, `Invalid request: A prompt is already running for this session`, steer_rejected, consumed false. Original shell tool returned KPR439_TOOL_OK, exit 0; turn completed end_turn. Exact stop exit 0, no residual PIDs. This contradicts R's native noninterrupting steering description for this candidate. No assertion about after-turn queue or other versions.

Raw local receipts: /tmp/kpr-439-droid/{v110-start,v110-observe,v110-send,v110-capture,v110-stop,resume,resume-send,resume-stop,core,core-send,core-capture,core-stop,tools-start,tools-send,steer,tools-observe,tools-capture,tools-stop}.json. Temporary data may expire. R records 0.225.1 ACP verification, separate 0.233.0 steer evidence and the 0.249.0 feature-flagged core entry rejected on 0.241.1. Studio 0.249.0, 0.251.0, explicit permission prompts, busy-turn after-turn delivery and fleet migration remain untested. Do not pin 1.1.0 as fully compatible until the steering regression is assessed and corrected or explicitly accepted with evidence; do not infer 0.251.0 compatibility.

## Continuation: real binary selection

The prior temporary manifest override is superseded for the primary candidate path. The source Runner now applies `DROID_BIN` to the manifest's first ACP command word, preserving explicit `--command` / `KAOLA_ACP_COMMAND` precedence and PATH fallback. The generated Skill was rendered from source. Direct worktree `scripts/kaola-acp.py` was used for live tests: invoking the generated Skill directly was refused before spawn by the installed worker-build-skew check; installed files were not changed.

- `DROID_BIN=/tmp/kpr-439-droid/artifact/package/bin/droid`, session `c8c59f2e-ebb0-4c70-b61b-31441e935193`: start reports native `@factory/cli` 1.1.0 / protocol 1, effective auto / none / auto-high; observe, send, capture and exact stop succeeded. Reply `KPR439 fixed candidate OK.`; no residual PIDs.
- Resume with the same native ID reported 1.1.0 and recalled `KPR439 fixed candidate OK.`; capture and exact stop succeeded, no residual PIDs.
- Core session `76cf1797-8a3f-4fd7-9e97-2bad0a192705`: reported 1.1.0, echoed exact `deepseek-v4.1-flash-1017`, max, auto-high; observe, send and capture succeeded; response `KPR439 fixed core OK.`; exact stop with no residual PIDs.
- Prior busy-steer rejection remains applicable to the same candidate binary and Runner transport. The 0.241.1 control remains a separate comparison above. Verdict remains NOT GREEN; no pin update recommended until the steering gap is resolved or accepted by the owner.

New receipts are `/tmp/kpr-439-droid/fixed-*.json`; they are transient. Focused contract suite and render check exercise the updated selection path. No fleet or PATH change.
