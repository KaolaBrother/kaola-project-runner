# KPR #270 — Family-3: three orchestration repos (read-only)

Reviewed 2026-10-07 via GitHub API, raw reads, and blob-filter clones pinned at exact SHAs; no installs, writes only under /tmp. Labels: **SV** = source-verified at pin; **RM** = README/docs-mentioned only.

## Pins
- langchain-ai/langgraph `main` @ `39c523eb0af1d192f739fd2b7ddfea38f3002a2a`; MIT, root `LICENSE` "Copyright (c) 2024 LangChain, Inc." (SV). Pushed 2026-10-07; `langgraph` 1.2.14 (SV pyproject).
- microsoft/agent-framework `main` @ `279d97f75cb2e7eee885dcdc2c741ef7361ee903`; MIT (SV). Pushed 2026-10-06; `agent-framework-core` 1.20.0 (SV).
- mastra-ai/mastra `main` @ `fb0376186c5fc8fc633c38d13a8dcc7c976318d8`. **Correction: org is `mastra-ai`, not `mastra-inc`** — `mastra-inc/mastra` is Repository-not-found. License: root `LICENSE.md` = Apache-2.0, "Copyright (c) 2025 Kepler Software, Inc.", with `ee/` directories excluded to a separate `ee/LICENSE` (SV). Pushed 2026-10-07; `@mastra/core` 1.75.0-alpha.7 (SV).

## AutoGen successor (recorded)
`openai/autogen`: Repository not found (SV ls-remote). `microsoft/autoflow`: Repository not found; web search finds no public Microsoft "Autoflow" GitHub repo. Both task-named candidates do not exist publicly. `microsoft/autogen` `main` @ `027ecf0a379bcc1d09956d46d12d44a3ad9cee14` (unarchived, last push 2026-04-15): README states "AutoGen is now in maintenance mode... community managed", "New users should start with Microsoft Agent Framework", calling it "1.0" enterprise-grade (SV). Repo license partition: docs CC-BY-4.0 + code MIT via LICENSE-CODE (SV). Current maintained successor: **microsoft/agent-framework**.

## 1) langgraph — graph-state orchestration
Mechanism: low-level framework for stateful, long-running agents (RM). `StateGraph` — "nodes communicate by reading and writing to a shared state", node signature `State -> Partial<State>` with per-key reducers; `add_node/add_edge/add_conditional_edges/add_sequence`; `compile(checkpointer=, interrupt_before/after=, store=)` → `CompiledStateGraph` (SV graph/state.py).
Durable state: `BaseCheckpointSaver.get_tuple/list/put/put_writes/delete_thread` + async variants (SV libs/checkpoint/.../base/__init__.py); backend libs `checkpoint-sqlite`, `checkpoint-postgres` (SV tree); durable execution "resuming from exactly where they left off" (RM).
Identity: `CheckpointTuple(config, checkpoint, metadata, parent_config, pending_writes)` (SV); thread_id with `delete_thread` lifecycle (SV).

## 2) microsoft/agent-framework — successor, graph workflows
Mechanism: multi-language (.NET/Python, Go elsewhere) production multi-agent framework (RM). Workflows = executors + event-driven graph: `_workflows/` holds `_workflow_builder.py`, `_edge_runner.py`, `_executor.py`, `_function_executor.py`, `_state.py` (SV tree); sequential/concurrent/handoff/group-chat patterns (RM).
Durable state: `WorkflowCheckpoint` + `CheckpointStorage` Protocol (`save/load/list_checkpoints/delete/get_latest` keyed by `workflow_name`) + `InMemoryCheckpointStorage` (SV _checkpoint.py). `WorkflowBuilder(checkpoint_storage=...)`; checkpoints "at the end of each superstep"; pause/resume across process restarts via `checkpoint_id`, graph fingerprint asserted on resume (SV _workflow.py). Deeper durability deferred to external "Durable Agent Framework extension" (RM).
Identity: workflow_name/checkpoint_id (SV); agent serialization via `SerializationMixin`/`SerializationProtocol` with `type` field (SV _serialization.py); `SessionContext` exists (SV); no named agent `save_state` at this HEAD.

## 3) mastra — TS workflows + storage
Mechanism: TS monorepo; `createWorkflow`/`cloneWorkflow` (SV workflows/create.ts:51,105) plus builder/execution-engine/scheduler/dynamic subdirs (SV tree).
Durable state: `MastraStorage extends MastraCompositeStore` (SV storage/base.ts:735); domain-partitioned abstract storage — `domains/workflows/base.ts` `persistWorkflowSnapshot`/`loadWorkflowSnapshot` (SV); run-keyed guard `getLastPersistedStatus(runId)` protects suspended/paused snapshots (SV default.ts:98); ~35 store backends under `stores/` (SV tree). Suspend/resume API: docs-level only here (RM). `workflows/temporal`, `workflows/inngest` integration dirs (SV tree).
Identity: snapshot persistence keyed by runId (SV); agent thread ids appear in tests (agent-thread-lease, agent-id-context) but the public memory threadId API was not verified here.

## Fits/misfits vs KPR (Agent-judgment-preserving)
Common misfit: all three move control flow into declared graphs executed by a runtime — routing/adoption become machine-decided; KPR deliberately keeps those judgments with the controlling Agent over transport-only Skills. None is a drop-in KPR layer.
Fits as patterns, not adoption: (a) LangGraph per-key reducers + checkpointer thread ≈ KPR typed JSONL fields + ledger resume; `interrupt` ≈ acceptance-before-finalize. (b) MAF's workflow-scoped checkpoint identity shows single-run resume without agent-seat identity — KPR's three-fact identity (session name, acp_session_id, native resume id) remains necessary. (c) Mastra's domain-partitioned storage contract ≈ KPR tool-enforced typed writes; runId-keyed snapshots ≈ one-issue-one-run.
