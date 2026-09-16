import {
  PROTOCOL_VERSION,
  RequestError,
  type Agent,
  type AgentSideConnection,
  type InitializeRequest,
  type InitializeResponse,
  type NewSessionRequest,
  type NewSessionResponse,
  type AuthenticateRequest,
  type AuthenticateResponse,
  type PromptRequest,
  type PromptResponse,
  type CancelNotification,
  type LoadSessionRequest,
  type LoadSessionResponse,
  type ListSessionsRequest,
  type ListSessionsResponse,
  type ResumeSessionRequest,
  type ResumeSessionResponse,
  type SetSessionModeRequest,
  type SetSessionModeResponse,
  type SetSessionConfigOptionRequest,
  type SetSessionConfigOptionResponse,
} from "@agentclientprotocol/sdk";
import { SessionStore } from "./session-store.js";
import {
  ClaudeRunner,
  type ClaudeBinaryError,
  type LaunchOptions,
  type StreamEvent,
} from "./claude-runner.js";
import { logger } from "./logger.js";
import {
  validateCwd,
  validateMcpCommand,
  validateMcpArgs,
} from "./validation.js";

function generateSessionId(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// Kaola fork: ACP session modes are Claude Code permission modes and travel
// as `--permission-mode` on every subprocess. The default matches the PTY
// launch (`--permission-mode bypassPermissions`).
const AVAILABLE_MODES = [
  {
    id: "bypassPermissions",
    name: "Bypass permissions",
    description: "Skip every permission prompt (default; matches the PTY launch)",
  },
  { id: "acceptEdits", name: "Accept edits", description: "Auto-accept file edits" },
  { id: "auto", name: "Auto", description: "Claude Code auto permission mode" },
  { id: "manual", name: "Manual", description: "Ask before every permissioned action" },
  { id: "dontAsk", name: "Don't ask", description: "Deny anything that would prompt" },
  { id: "plan", name: "Plan", description: "Plan without making changes" },
];

const DEFAULT_MODE = "bypassPermissions";
const MODE_IDS = new Set(AVAILABLE_MODES.map((m) => m.id));

// "default" means: pass no flag and let the native CLI decide.
const NATIVE_DEFAULT = "default";
const MODEL_CHOICES = [
  { value: NATIVE_DEFAULT, name: "Native default" },
  { value: "fable", name: "Fable" },
  { value: "opus", name: "Opus" },
  { value: "sonnet", name: "Sonnet" },
  { value: "haiku", name: "Haiku" },
];
const EFFORT_CHOICES = [
  { value: NATIVE_DEFAULT, name: "Native default" },
  { value: "low", name: "Low" },
  { value: "medium", name: "Medium" },
  { value: "high", name: "High" },
  { value: "xhigh", name: "Extra high" },
  { value: "max", name: "Max" },
];
const FAST_CHOICES = [
  { value: "off", name: "Off" },
  { value: "on", name: "On" },
];
const MODEL_VALUE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:/-]*$/;
const CLAUDE_SESSION_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function buildModeState(currentModeId: string) {
  return {
    availableModes: AVAILABLE_MODES,
    currentModeId,
  };
}

function buildConfigOptions(store: SessionStore, sessionId: string) {
  const overrides = store.getConfigOverrides(sessionId);
  const model = (overrides.model as string) ?? NATIVE_DEFAULT;
  const modelChoices = MODEL_CHOICES.some((c) => c.value === model)
    ? MODEL_CHOICES
    : [...MODEL_CHOICES, { value: model, name: model }];
  return [
    {
      id: "mode",
      name: "Permission mode",
      type: "select" as const,
      category: "mode",
      description: "Claude Code --permission-mode for every turn",
      currentValue: store.getMode(sessionId) ?? DEFAULT_MODE,
      options: AVAILABLE_MODES.map((m) => ({ value: m.id, name: m.name })),
    },
    {
      id: "model",
      name: "Model",
      type: "select" as const,
      category: "model",
      description: "Claude Code --model for every turn (alias or full model name)",
      currentValue: model,
      options: modelChoices,
    },
    {
      id: "effort",
      name: "Effort",
      type: "select" as const,
      category: "thought_level",
      description: "Claude Code --effort for every turn",
      currentValue: (overrides.effort as string) ?? NATIVE_DEFAULT,
      options: EFFORT_CHOICES,
    },
    {
      id: "fast",
      name: "Fast",
      type: "select" as const,
      category: "fast",
      description: "Process-scoped fastMode settings pin (on => true, otherwise false)",
      currentValue: (overrides.fast as string) ?? "off",
      options: FAST_CHOICES,
    },
  ];
}

function validateConfigValue(configId: string, value: unknown): string {
  if (typeof value !== "string" || !value) {
    throw RequestError.invalidParams(`Config option ${configId} needs a string value`);
  }
  const allowed = (choices: { value: string }[]) => {
    if (!choices.some((c) => c.value === value)) {
      throw RequestError.invalidParams(
        `Unsupported ${configId} value: ${value} (allowed: ${choices.map((c) => c.value).join(", ")})`
      );
    }
  };
  switch (configId) {
    case "mode":
      if (!MODE_IDS.has(value)) {
        throw RequestError.invalidParams(
          `Unsupported mode value: ${value} (allowed: ${[...MODE_IDS].join(", ")})`
        );
      }
      return value;
    case "model":
      if (!MODEL_VALUE_PATTERN.test(value)) {
        throw RequestError.invalidParams(`Unsupported model value: ${value}`);
      }
      return value;
    case "effort":
      allowed(EFFORT_CHOICES);
      return value;
    case "fast":
      allowed(FAST_CHOICES);
      return value;
    default:
      throw RequestError.invalidParams(`Unknown config option: ${configId}`);
  }
}

function launchOptionsFor(store: SessionStore, sessionId: string): LaunchOptions {
  const overrides = store.getConfigOverrides(sessionId);
  const pick = (key: string): string | undefined => {
    const value = overrides[key];
    return typeof value === "string" && value !== NATIVE_DEFAULT ? value : undefined;
  };
  return {
    model: pick("model"),
    effort: pick("effort"),
    permissionMode: store.getMode(sessionId) ?? DEFAULT_MODE,
    fast: overrides.fast === "on" ? "on" : "off",
  };
}

export function createClaudeCodeAgent(
  connection: AgentSideConnection,
  runner: ClaudeRunner = new ClaudeRunner()
): Agent {
  const store = new SessionStore();
  const cancelledSessions = new Set<string>();

  function sessionState(sessionId: string) {
    return {
      modes: buildModeState(store.getMode(sessionId) ?? DEFAULT_MODE),
      configOptions: buildConfigOptions(store, sessionId),
    };
  }

  function resolveCwd(cwd: string): string {
    try {
      return validateCwd(cwd);
    } catch (err) {
      throw RequestError.invalidParams(
        `Invalid cwd: ${err instanceof Error ? err.message : String(err)}`
      );
    }
  }

  // Kaola fork: a misconfigured exact binary fails closed before any turn.
  function isBinaryError(err: unknown): err is ClaudeBinaryError {
    return err instanceof Error && err.name === "ClaudeBinaryError";
  }
  function ensureBinary(): void {
    try {
      runner.checkBinary?.();
    } catch (err) {
      if (isBinaryError(err)) {
        throw RequestError.internalError({ reason: "claude-binary" }, err.message);
      }
      throw err;
    }
  }

  return {
    async initialize(
      _params: InitializeRequest
    ): Promise<InitializeResponse> {
      logger.info("Initialize request received");
      return {
        protocolVersion: PROTOCOL_VERSION,
        agentInfo: {
          name: "claude-code-acp",
          title: "Claude Code ACP Bridge",
          version: "0.1.0",
        },
        agentCapabilities: {
          loadSession: false,
          promptCapabilities: {
            image: false,
            audio: false,
            embeddedContext: false,
          },
          mcpCapabilities: {
            http: false,
            sse: false,
          },
          sessionCapabilities: {
            list: {},
            resume: {},
          },
        },
        authMethods: [],
      };
    },

    async newSession(
      params: NewSessionRequest
    ): Promise<NewSessionResponse> {
      logger.debug(
        `newSession: cwd=${params.cwd} mcpServers=${(params.mcpServers ?? []).length}`
      );
      ensureBinary();
      const resolvedCwd = resolveCwd(params.cwd);

      const sessionId = generateSessionId();
      // Convert and validate ACP MCP server format
      // Kaola fork: accept the ACP stdio shape ({name, command, args, env:[{name,value}]})
      // that clients actually send, alongside upstream's {transport:{type:"stdio",...}}.
      const mcpServers = (params.mcpServers ?? [])
        .map((s: any) => {
          if (s.transport?.type === "stdio") return { source: s, stdio: s.transport };
          if (!s.type && typeof s.command === "string") return { source: s, stdio: s };
          return null;
        })
        .filter((entry): entry is { source: any; stdio: any } => entry !== null)
        .map(({ source, stdio }) => {
          const command = stdio.command;
          const args = stdio.args ?? [];
          try {
            validateMcpCommand(command);
            validateMcpArgs(args);
          } catch (err) {
            throw RequestError.invalidParams(
              `Invalid MCP server config: ${err instanceof Error ? err.message : String(err)}`
            );
          }
          const env: Record<string, string> | undefined = Array.isArray(stdio.env)
            ? Object.fromEntries(
                stdio.env
                  .filter((e: any) => e && typeof e.name === "string")
                  .map((e: any) => [e.name, String(e.value ?? "")])
              )
            : stdio.env;
          return {
            name: source.name ?? source.id ?? "unknown",
            transport: {
              type: "stdio" as const,
              command,
              args,
              env,
            },
          };
        });
      store.create(sessionId, resolvedCwd, mcpServers);
      logger.info(
        `Session created: ${sessionId} (cwd: ${resolvedCwd}, mcpServers: ${mcpServers.length})`
      );
      return {
        sessionId,
        ...sessionState(sessionId),
      } as NewSessionResponse;
    },

    async loadSession(
      params: LoadSessionRequest
    ): Promise<LoadSessionResponse> {
      const { sessionId } = params;

      if (!store.has(sessionId)) {
        throw RequestError.resourceNotFound(
          `Session ${sessionId} not found`
        );
      }

      logger.info(`Load session: ${sessionId}`);

      return sessionState(sessionId) as LoadSessionResponse;
    },

    /**
     * Kaola fork: `session/resume`. Accepts an ACP session id of this
     * process, or a Claude Code session id (UUID or on record); the latter
     * binds a new ACP session whose next turn runs `--resume <id>`.
     */
    async unstable_resumeSession(
      params: ResumeSessionRequest
    ): Promise<ResumeSessionResponse> {
      const { sessionId } = params;
      if (store.has(sessionId)) {
        logger.info(`Resume session: ${sessionId}`);
        return { sessionId, ...sessionState(sessionId) } as ResumeSessionResponse;
      }
      if (!CLAUDE_SESSION_ID_PATTERN.test(sessionId) && !store.hasPersisted(sessionId)) {
        throw RequestError.resourceNotFound(`Session ${sessionId} not found`);
      }
      ensureBinary();
      const resolvedCwd = resolveCwd(params.cwd);
      store.create(sessionId, resolvedCwd, [], sessionId);
      logger.info(`Resume bound: ACP session ${sessionId} (cwd: ${resolvedCwd})`);
      return { sessionId, ...sessionState(sessionId) } as ResumeSessionResponse;
    },

    async listSessions(
      params: ListSessionsRequest
    ): Promise<ListSessionsResponse> {
      const cwd = params.cwd ?? undefined;
      const sessions = store.listAll(cwd);
      const bound = new Set(
        sessions.map((s) => store.getClaudeSessionId(s.sessionId)).filter(Boolean)
      );
      for (const entry of store.listPersisted(cwd)) {
        if (!bound.has(entry.sessionId) && !store.has(entry.sessionId)) {
          sessions.push(entry);
        }
      }
      return { sessions };
    },

    async setSessionMode(
      params: SetSessionModeRequest
    ): Promise<SetSessionModeResponse> {
      const { sessionId, modeId } = params;

      if (!store.has(sessionId)) {
        throw RequestError.resourceNotFound(
          `Session ${sessionId} not found`
        );
      }
      validateConfigValue("mode", modeId);

      store.setMode(sessionId, modeId);
      logger.info(`Session ${sessionId} mode set to ${modeId}`);

      // Send current_mode_update notification
      await connection.sessionUpdate({
        sessionId,
        update: {
          sessionUpdate: "current_mode_update",
          currentModeId: modeId,
        } as any,
      });

      return {};
    },

    async setSessionConfigOption(
      params: SetSessionConfigOptionRequest
    ): Promise<SetSessionConfigOptionResponse> {
      const { sessionId, configId } = params as any;

      if (!store.has(sessionId)) {
        throw RequestError.resourceNotFound(
          `Session ${sessionId} not found`
        );
      }

      const value = validateConfigValue(configId, (params as any).value);
      if (configId === "mode") {
        store.setMode(sessionId, value);
        await connection.sessionUpdate({
          sessionId,
          update: {
            sessionUpdate: "current_mode_update",
            currentModeId: value,
          } as any,
        });
      } else {
        store.setConfigOverride(sessionId, configId, value);
      }
      logger.info(`Session ${sessionId} config ${configId} set to ${value}`);

      // Send config_option_update notification
      const configOptions = buildConfigOptions(store, sessionId);
      await connection.sessionUpdate({
        sessionId,
        update: {
          sessionUpdate: "config_option_update",
          configOptions,
        } as any,
      });

      return { configOptions } as SetSessionConfigOptionResponse;
    },

    async authenticate(
      _params: AuthenticateRequest
    ): Promise<AuthenticateResponse> {
      return {};
    },

    async prompt(params: PromptRequest): Promise<PromptResponse> {
      logger.debug(`prompt params keys: ${JSON.stringify(Object.keys(params))}`);
      const { sessionId, prompt } = params;

      if (!store.has(sessionId)) {
        throw RequestError.resourceNotFound(
          `Session ${sessionId} not found`
        );
      }

      // Extract text from content blocks
      const text = prompt
        .filter((block): block is { type: "text"; text: string } =>
          block.type === "text"
        )
        .map((block) => block.text)
        .join("\n");

      if (!text.trim()) {
        throw RequestError.invalidParams("Empty prompt text");
      }

      const claudeSessionId = store.getClaudeSessionId(sessionId);
      const cwd = store.getCwd(sessionId)!;
      const launch = launchOptionsFor(store, sessionId);
      let toolCallCounter = 0;

      logger.info(`Prompt for session ${sessionId}: ${text.length} chars`);
      logger.debug(
        `Prompt content: ${text.slice(0, 100)}${text.length > 100 ? "..." : ""}`
      );

      const permissionPromises: Promise<void>[] = [];

      const onEvent = (event: StreamEvent) => {
        if ((event as any).type === "thinking" && (event as any).text) {
          connection.sessionUpdate({
            sessionId,
            update: {
              sessionUpdate: "agent_thought_chunk",
              content: { type: "text", text: (event as any).text },
            } as any,
          });
        } else if (event.type === "text_delta" && event.text) {
          connection.sessionUpdate({
            sessionId,
            update: {
              sessionUpdate: "agent_message_chunk",
              content: { type: "text", text: event.text },
            },
          });
        } else if (event.type === "tool_use" && event.toolName) {
          const toolCallId = `call_${++toolCallCounter}`;
          logger.debug(`Tool call: ${event.toolName}`);
          connection.sessionUpdate({
            sessionId,
            update: {
              sessionUpdate: "tool_call",
              toolCallId,
              title: event.toolName,
              kind: "execute",
              status: "completed",
              rawInput: event.toolInput ?? {},
            },
          });
        } else if (event.type === "permission_request" && event.toolName) {
          const toolCallId = `call_${++toolCallCounter}`;
          const toolName = event.toolName;
          const toolInput = event.toolInput ?? {};
          logger.info(`Permission request: ${toolName}`);

          // Send pending tool_call status
          connection.sessionUpdate({
            sessionId,
            update: {
              sessionUpdate: "tool_call",
              toolCallId,
              title: toolName,
              kind: "execute",
              status: "pending",
              rawInput: toolInput,
            },
          });

          // Request permission from client (track promise for awaiting)
          const permPromise = connection
            .requestPermission({
              sessionId,
              toolCall: {
                toolCallId,
                title: toolName,
                kind: "execute",
                status: "pending",
                rawInput: toolInput,
              },
              options: [
                { optionId: "allow_once", kind: "allow_once", name: "Allow once" },
                { optionId: "allow_always", kind: "allow_always", name: "Allow always" },
                { optionId: "reject_once", kind: "reject_once", name: "Reject once" },
                { optionId: "reject_always", kind: "reject_always", name: "Reject always" },
              ],
            })
            .then((response) => {
              const outcome = response.outcome as any;
              const isSelected =
                outcome.outcome === "selected" || outcome.type === "selected";
              const optionId = outcome.optionId;
              const isApproved =
                isSelected &&
                (optionId === "allow_once" ||
                  optionId === "allow_always");

              connection.sessionUpdate({
                sessionId,
                update: {
                  sessionUpdate: "tool_call",
                  toolCallId,
                  title: toolName,
                  kind: "execute",
                  status: isApproved ? "completed" : "failed",
                  rawInput: toolInput,
                },
              });
            })
            .catch((err) => {
              logger.error(
                `Permission request failed: ${err instanceof Error ? err.message : String(err)}`
              );
              connection.sessionUpdate({
                sessionId,
                update: {
                  sessionUpdate: "tool_call",
                  toolCallId,
                  title: toolName,
                  kind: "execute",
                  status: "failed",
                  rawInput: toolInput,
                },
              });
            });

          permissionPromises.push(permPromise);
        }
      };

      try {
        let result;
        if (claudeSessionId) {
          try {
            result = await runner.continueSessionStreaming(
              claudeSessionId,
              text,
              onEvent,
              sessionId,
              launch,
              cwd
            );
          } catch (resumeErr) {
            if (isBinaryError(resumeErr)) throw resumeErr;
            // Resume failed (expired session, etc.) — fall back to new session
            logger.warn(
              `Resume failed for <claude-session-id>, starting fresh: ${resumeErr instanceof Error ? resumeErr.message : String(resumeErr)}`
            );
            store.clearPersistedSession(claudeSessionId);
            result = await runner.startSessionStreaming(
              cwd,
              text,
              onEvent,
              sessionId,
              launch
            );
            store.setClaudeSessionId(sessionId, result.sessionId);
          }
        } else {
          const mcpServers = store.getMcpServers(sessionId);
          if (mcpServers.length > 0) {
            result = await runner.startSessionWithMcp(
              cwd,
              text,
              mcpServers,
              onEvent,
              sessionId,
              launch
            );
          } else {
            result = await runner.startSessionStreaming(
              cwd,
              text,
              onEvent,
              sessionId,
              launch
            );
          }
          store.setClaudeSessionId(sessionId, result.sessionId);
        }

        // Wait for all pending permission requests to resolve
        await Promise.all(permissionPromises);

        // Check if this session was cancelled while running
        if (cancelledSessions.has(sessionId)) {
          cancelledSessions.delete(sessionId);
          logger.info(`Prompt cancelled for session ${sessionId}`);
          return { stopReason: "cancelled" };
        }

        // Send session_info_update with updatedAt
        store.touch(sessionId);
        await connection.sessionUpdate({
          sessionId,
          update: {
            sessionUpdate: "session_info_update",
            updatedAt: store.getUpdatedAt(sessionId),
          } as any,
        });

        logger.info(`Prompt completed for session ${sessionId}`);
        return { stopReason: "end_turn" };
      } catch (err) {
        // Check if cancelled
        if (cancelledSessions.has(sessionId)) {
          cancelledSessions.delete(sessionId);
          logger.info(`Prompt cancelled for session ${sessionId}`);
          return { stopReason: "cancelled" };
        }

        if (isBinaryError(err)) {
          // Kaola fork: an unusable exact binary is a hard error, never a chat message.
          logger.error(`Prompt failed for session ${sessionId}: ${err.message}`);
          throw RequestError.internalError({ reason: "claude-binary" }, err.message);
        }

        const message =
          err instanceof Error ? err.message : String(err);
        logger.error(`Prompt failed for session ${sessionId}: ${message}`);

        // Send error as agent message so client sees it
        await connection.sessionUpdate({
          sessionId,
          update: {
            sessionUpdate: "agent_message_chunk",
            content: {
              type: "text",
              text: `Error: ${message}`,
            },
          },
        });

        return { stopReason: "end_turn" };
      }
    },

    async cancel(params: CancelNotification): Promise<void> {
      logger.info(`Cancel request for session ${params.sessionId}`);
      cancelledSessions.add(params.sessionId);
      runner.cancel(params.sessionId);
    },
  };
}
