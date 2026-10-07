# F3 — issue #270: microsoft/agent-framework verified successor

## OFFICIAL-DOC CLAIMS (pages fetched)
- AutoGen repo (github.com/microsoft/autogen, README): banner **"Maintenance Mode"** — "AutoGen is now in maintenance mode. It will not receive new features or enhancements and is community managed going forward." New users directed to Microsoft Agent Framework; existing users to the from-autogen migration guide.
- Learn overview (learn.microsoft.com/en-us/agent-framework/overview/): Agent Framework is "the **direct successor**, created by the same teams"; combines AutoGen's agent abstractions with Semantic Kernel enterprise features (session-based state, type safety, middleware, telemetry), and adds graph-based workflows + robust state management for long-running/human-in-the-loop scenarios.
- Verdict: **microsoft/agent-framework is the maintained successor surface** to AutoGen.

## PIN (source read via GitHub API/raw)
- Repo `microsoft/agent-framework`, not archived/fork; **default branch `main`**.
- **HEAD commit** `279d97f75cb2e7eee885dcdc2c741ef7361ee903` (2026-10-06T18:32:33Z).
- **HEAD tree SHA** `fcc198e6ba2d0011a123145f2836a86f69cacf88`.
- **LICENSE**: root `LICENSE` MIT; `python/LICENSE` also MIT (checked at pin). The tree additionally carries per-package LICENSE files under `python/packages/*` (44 LICENSE/NOTICE-named paths in the recursive tree) — their individual terms were NOT all read; license partition beyond root+python is **marked uncovered**, not asserted absent.

## SOURCE_VERIFIED interfaces (paths at pinned commit)
1. **Orchestration graph API** — `python/packages/core/agent_framework/_workflows/_workflow_builder.py`: `class WorkflowBuilder` exposes `add_edge`, `add_fan_out_edges`, `add_switch_case_edge_group`, `add_multi_selection_edge_group`, `add_fan_in_edges`, `add_chain`; ctor accepts `checkpoint_storage`.
2. **Workflow run entry** — `_workflows/_workflow.py`: `class Workflow.run(message, *, stream, responses, checkpoint_id, checkpoint_storage, ...)` — one interface for initial run, checkpoint restore, and replying to pending request-info events; `message`/`responses` mutually exclusive.
3. **State** — `_workflows/_state.py`: `class State` with `set/get/has/delete/clear/commit/discard/export_state/import_state`; keys starting `_` reserved.
4. **Checkpoint model + storage protocol** — `_workflows/_checkpoint.py`: `@dataclass WorkflowCheckpoint` (`checkpoint_id`, `previous_checkpoint_id` lineage chain, `iteration_count`, `version`); `class CheckpointStorage(Protocol)` = `save/load/list_checkpoints/delete/get_latest`.
5. **Persistence backends** — same file: `InMemoryCheckpointStorage` and `FileCheckpointStorage` (line 505; path-escape guard); plus Cosmos backend `python/packages/azure-cosmos/agent_framework_azure_cosmos/_checkpoint_storage.py`.
6. **Recovery/replay semantics** — `_workflow.py`: checkpoints written at end of each superstep; a canonical **graph fingerprint is captured so checkpoints assert they are resumed with the same graph**; "Workflows can be paused and resumed across process restarts using checkpoint storage"; `responses=` supports restore-then-send replay. (SOURCE-READ only — not runtime-verified; and source reading does NOT imply any external-effects atomicity.)
7. **Runner context** — `_workflows/_runner_context.py`: `RunnerContext(Protocol)` + `InProcRunnerContext` with `build_checkpoint`/`create_checkpoint`/`set_runtime_checkpoint_storage`.
8. **Module composition** — `python/packages/orchestrations/agent_framework_orchestrations/__init__.py` exports `SequentialBuilder`, `ConcurrentBuilder`, group-chat, handoff, magentic builders + `OrchestrationState`; `core/agent_framework/__init__.py` lazy-exports `Workflow`, `WorkflowBuilder`, `CheckpointStorage`, `FileCheckpointStorage`, `InMemoryCheckpointStorage`, `WorkflowExecutor`, `WorkflowCheckpoint`.

Both official links resolved (no 404). No installs; read-only.
