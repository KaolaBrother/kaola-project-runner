# KPR issue #270 — OpenHands `software-agent-sdk` interface review

Read-only. Source: github.com/OpenHands/software-agent-sdk @ commit `608a102c637d8d8a999f49d7b04846524bd8bd1c` (tree `5ecbb5c214b2b39976ef7adab41ac93492b6862f`), blobless clone fetched 2026-10-07. Representative files: `README.md`, `LICENSE`, root+sdk+`clients/typescript` `AGENTS.md`, `openhands-sdk/openhands/sdk/{__init__,agent/{base,agent,acp_agent},conversation/{base,event_store,impl/remote_conversation},event/{base,types},tool/{spec,tool,registry},mcp/{client,config,utils},secret/secrets,plugin/*,workspace/base,settings/model}.py`, `openhands-agent-server/openhands/agent_server/` listing. No install/deploy.

**License** (SOURCE_VERIFIED): MIT — root `LICENSE` ("Copyright (c) 2026 OpenHands contributors"); `clients/typescript/LICENSE` also MIT; no license partition found. README_MENTIONED: MIT badge.

**Identity** (README_MENTIONED): "Python, TypeScript, and REST APIs for building agents that work with code"; local machine or ephemeral Docker/K8s workspaces via Agent Server; engine behind OpenHands CLI and Cloud.

## Composable surface (SOURCE_VERIFIED — `sdk/__init__.py` `__all__` + files)

- **Agent loop**: `AgentBase` = frozen Pydantic model (stateless, config-defined); abstract `step()/astep(conversation, on_event, on_token)`; concrete `Agent`. Fields: `llm`, `tools: list[Tool]`, `mcp_config: dict[str, MCPServer]`.
- **Conversation/events**: `BaseConversation` ABC → `LocalConversation` (in-process) / `RemoteConversation` (httpx.Client + websockets, `session_api_key` auth). `Event` = frozen discriminated union: `id`/`timestamp`/`source` (`agent|user|environment|hook`)/`parent_id` tree with `ROOT_PARENT_ID` sentinel; `LLMConvertibleEvent.to_llm_message()`; `EventLog` persists via `FileStore` (thread/process-safe claim, flock caveat on local FS).
- **Tools**: declarative spec `Tool{name, params}` resolved to `ToolDefinition.create()` → `ToolExecutor` protocol (`close()`, `interrupt()` called cross-thread); name→resolver registry (`register_tool`/`resolve_tool`/`list_registered_tools`); `to_mcp_tool()`/`to_openai_tool()` export adapters.
- **MCP/skills**: `MCPClient` extends `fastmcp.Client` with sync bridges; `create_mcp_tools()`; `MCPServer` config + auth union (none/api-key/bearer/basic/header/OAuth), converted at the FastMCP boundary. Skills: `load_skills_from_dir`/`load_project_skills`/`load_user_skills` (progressive disclosure into `<available_skills>` per AGENTS.md). Subagents: `register_agent`/`discover_agents`/`agent_definition_to_factory`. Plugins: `Plugin.load/load_all` + user/project discovery dirs.
- **Secrets**: single module `utils/pydantic_secrets` (`SecretStr`, serialize/validate/is_redacted); `LookupSecret` URLs resolve over HTTP or `register_local_secret_resolver`; AGENTS.md forbids parallel redaction.

**Role/module lifecycle**: frozen configs + registries; server-side `conversation_registry.py`/`conversation_lease.py` own live sessions.

**Multi-process boundary**: Agent Server = separate FastAPI process (conversation/event/bash/file/git/hooks/auth routers + `docker_runtime`); `RemoteConversation` mirrors `LocalConversation` over REST+WS; `clients/typescript` is generated from a pinned `openapi.json` (`package.json config.agentServerImage`), browser-compatible `IWorkspace`/`IConversation`/`ILLM`. SDK also ships `acp_agent.py` — an ACP *client-side* agent adapter (`acp.client.connection`).

**Cross-version** (SOURCE_VERIFIED via AGENTS.md + code): persisted settings `schema_version` + `_migrate_vN→vN+1` chain (`AGENT_SETTINGS_SCHEMA_VERSION` = 8) + golden fixtures `tests/sdk/persisted_settings_baselines/vN/` + CI gate; events use permanent `_DEPRECATED_FIELDS` + `handle_deprecated_model_fields`; public-API removal requires deprecation ≥5 minor releases (`check_sdk_api_breakage.py`).

## Fits / misfits vs KPR

**Fit**: one ABC behind local vs remote transport = KPR's transport-swap pattern; OpenAPI→generated client is a versioned multi-process contract (O1); `Tool{name,params}` + resolver registry ≈ manifest→adapter resolution (O3 shape); schema-version+migrations+golden fixtures = concrete conformance reference (O1/O4); single secrets module = #51 redaction analog.

**Misfit**: Python/Pydantic/LiteLLM/fastmcp stack — not adoptable by stdlib Bash+Python KPR; the SDK *is* the LLM agent loop while KPR drives external CLI runtimes — only the contract shape transfers; boundary is bespoke REST+WS (its ACP adapter is client-side, not an ACP-host surface); `EventLog` process-safety is single-host flock — no multi-agent shared-Git semantics.
