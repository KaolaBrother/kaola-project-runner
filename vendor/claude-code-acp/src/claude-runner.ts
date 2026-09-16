import { spawn, type ChildProcess } from "node:child_process";
import {
  appendFileSync,
  writeFileSync,
  mkdtempSync,
  rmSync,
  statSync,
  accessSync,
  constants as fsConstants,
} from "node:fs";
import { tmpdir } from "node:os";
import { isAbsolute, join } from "node:path";
import { type AgentConfig, loadConfig } from "./config.js";
import { logger } from "./logger.js";

export interface McpServerConfig {
  name: string;
  transport: {
    type: "stdio";
    command: string;
    args?: string[];
    env?: Record<string, string>;
  };
}

export interface ClaudeResult {
  text: string;
  sessionId: string;
}

export interface StreamEvent {
  type: "text_delta" | "tool_use" | "result" | "permission_request" | "thinking";
  text?: string;
  toolName?: string;
  toolInput?: unknown;
  sessionId?: string;
  permissionId?: string;
  usage?: { input_tokens?: number; output_tokens?: number };
}

/**
 * Kaola fork: per-session launch options translated onto every `claude`
 * subprocess (first turn and every `--resume` turn alike).
 */
export interface LaunchOptions {
  /** `--model <id>`; omitted when unset (the process-global config model applies). */
  model?: string;
  /** `--effort <level>`; omitted when unset. */
  effort?: string;
  /** `--permission-mode <mode>`; omitted when unset. */
  permissionMode?: string;
  /**
   * Fast pin. Mirrors the PTY adapter: `--settings '{"fastMode": true}'`
   * only for "on"; every other value pins false so a saved preference never
   * leaks into the session. Always emitted.
   */
  fast?: "on" | "off";
}

/** Kaola fork: raised when the configured Claude binary cannot be used. */
export class ClaudeBinaryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ClaudeBinaryError";
  }
}

const SENSITIVE_FLAGS = new Set(["-p", "--print"]);
const REDACT_FLAGS = new Set(["--resume"]);
const KILL_GRACE_MS = 2000;

export function maskArgs(args: string[]): string {
  const masked: string[] = [];
  for (let i = 0; i < args.length; i++) {
    if (SENSITIVE_FLAGS.has(args[i]) && i + 1 < args.length) {
      masked.push(args[i], `<prompt: ${args[i + 1].length} chars>`);
      i++;
    } else if (REDACT_FLAGS.has(args[i]) && i + 1 < args.length) {
      masked.push(args[i], "<session-id>");
      i++;
    } else {
      masked.push(args[i]);
    }
  }
  return masked.join(" ");
}

/**
 * Kaola fork: resolve the exact binary. A configured path must be absolute,
 * exist, be a regular file, and be executable; otherwise the runner fails
 * closed instead of falling back to `PATH`.
 */
export function resolveClaudeBinary(config: AgentConfig): string {
  const configured = config.claudeBin;
  if (configured === undefined) {
    return "claude";
  }
  if (!isAbsolute(configured)) {
    throw new ClaudeBinaryError(
      `CLAUDE_BIN must be an absolute path to the claude binary (got: ${configured})`
    );
  }
  let stat;
  try {
    stat = statSync(configured);
  } catch {
    throw new ClaudeBinaryError(`CLAUDE_BIN does not exist: ${configured}`);
  }
  if (!stat.isFile()) {
    throw new ClaudeBinaryError(`CLAUDE_BIN is not a regular file: ${configured}`);
  }
  try {
    accessSync(configured, fsConstants.X_OK);
  } catch {
    throw new ClaudeBinaryError(`CLAUDE_BIN is not executable: ${configured}`);
  }
  return configured;
}

/**
 * Kaola fork: the child runs detached in its own process group, invisible to
 * a supervisor that only knows this bridge's group. When the supervisor
 * names a record file (`KAOLA_ACP_CHILD_RECORD`), append the child's identity
 * synchronously at spawn, before any of its output can be forwarded, so the
 * supervisor can still find and stop the child if this process dies first.
 * Never fails the turn.
 */
function recordChildSpawn(proc: ChildProcess, binary: string): void {
  const path = process.env.KAOLA_ACP_CHILD_RECORD;
  if (!path || !proc.pid) return;
  try {
    appendFileSync(
      path,
      JSON.stringify({ pid: proc.pid, pgid: proc.pid, spawned_at: Date.now(), binary }) + "\n"
    );
  } catch (err) {
    logger.warn(
      `Failed to record child spawn: ${err instanceof Error ? err.message : String(err)}`
    );
  }
}

function killGroup(proc: ChildProcess, signal: NodeJS.Signals): void {
  if (!proc.pid) return;
  try {
    // Children are spawned detached into their own process group, so the
    // negative pid reaches claude and everything it started.
    process.kill(-proc.pid, signal);
  } catch {
    try {
      proc.kill(signal);
    } catch {
      // already gone
    }
  }
}

function isRunning(proc: ChildProcess): boolean {
  return proc.exitCode === null && proc.signalCode === null;
}

export class ClaudeRunner {
  private runningProcesses = new Map<string, ChildProcess>();
  private tempDirs: string[] = [];
  private config: AgentConfig;

  constructor(config?: AgentConfig) {
    this.config = config ?? loadConfig();
  }

  /** Kaola fork: validate the exact binary without spawning anything. */
  checkBinary(): string {
    return resolveClaudeBinary(this.config);
  }

  private buildExtraArgs(options: LaunchOptions = {}): string[] {
    const extra: string[] = [];
    const model = options.model ?? this.config.model;
    if (model) {
      extra.push("--model", model);
    }
    if (options.effort) {
      extra.push("--effort", options.effort);
    }
    if (this.config.maxTurns) {
      extra.push("--max-turns", String(this.config.maxTurns));
    }
    if (options.permissionMode) {
      extra.push("--permission-mode", options.permissionMode);
    } else if (this.config.dangerouslySkipPermissions) {
      // Only when no explicit permission mode governs the session.
      extra.push("--dangerously-skip-permissions");
    }
    extra.push("--settings", JSON.stringify({ fastMode: options.fast === "on" }));
    for (const tool of this.config.allowedTools) {
      extra.push("--allowedTools", tool);
    }
    return extra;
  }

  async startSession(
    cwd: string,
    prompt: string,
    options?: LaunchOptions
  ): Promise<ClaudeResult> {
    const args = ["-p", prompt, "--output-format", "json", ...this.buildExtraArgs(options)];
    return this.runJson(args, cwd);
  }

  async continueSession(
    claudeSessionId: string,
    prompt: string,
    options?: LaunchOptions,
    cwd?: string
  ): Promise<ClaudeResult> {
    const args = [
      "-p",
      prompt,
      "--resume",
      claudeSessionId,
      "--output-format",
      "json",
      ...this.buildExtraArgs(options),
    ];
    return this.runJson(args, cwd);
  }

  async startSessionStreaming(
    cwd: string,
    prompt: string,
    onEvent: (event: StreamEvent) => void,
    trackingId?: string,
    options?: LaunchOptions
  ): Promise<ClaudeResult> {
    const args = [
      "-p",
      prompt,
      "--output-format",
      "stream-json",
      "--verbose",
      ...this.buildExtraArgs(options),
    ];
    return this.runStreaming(args, cwd, onEvent, trackingId);
  }

  async continueSessionStreaming(
    claudeSessionId: string,
    prompt: string,
    onEvent: (event: StreamEvent) => void,
    trackingId?: string,
    options?: LaunchOptions,
    cwd?: string
  ): Promise<ClaudeResult> {
    const args = [
      "-p",
      prompt,
      "--resume",
      claudeSessionId,
      "--output-format",
      "stream-json",
      "--verbose",
      ...this.buildExtraArgs(options),
    ];
    return this.runStreaming(args, cwd, onEvent, trackingId);
  }

  async startSessionWithMcp(
    cwd: string,
    prompt: string,
    mcpServers: McpServerConfig[],
    onEvent?: (event: StreamEvent) => void,
    trackingId?: string,
    options?: LaunchOptions
  ): Promise<ClaudeResult> {
    const { args: mcpArgs, dir } = this.buildMcpArgs(mcpServers);
    if (onEvent) {
      const args = [
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        ...this.buildExtraArgs(options),
        ...mcpArgs,
      ];
      return this.runStreaming(args, cwd, onEvent, trackingId, dir);
    } else {
      const args = [
        "-p",
        prompt,
        "--output-format",
        "json",
        ...this.buildExtraArgs(options),
        ...mcpArgs,
      ];
      return this.runJson(args, cwd, dir);
    }
  }

  private buildMcpArgs(mcpServers: McpServerConfig[]): {
    args: string[];
    dir: string | undefined;
  } {
    if (mcpServers.length === 0) return { args: [], dir: undefined };

    // Write MCP config to a temp file under the runtime dir; removed when
    // the subprocess that consumed it exits, and again on shutdown.
    const tmpDir = mkdtempSync(join(this.config.runtimeDir ?? tmpdir(), "claude-acp-mcp-"));
    const configPath = join(tmpDir, "mcp.json");
    const mcpConfig: Record<string, any> = {
      mcpServers: Object.fromEntries(
        mcpServers.map((s) => [
          s.name,
          {
            command: s.transport.command,
            args: s.transport.args ?? [],
            env: s.transport.env ?? {},
          },
        ])
      ),
    };
    writeFileSync(configPath, JSON.stringify(mcpConfig, null, 2));
    this.tempDirs.push(tmpDir);
    logger.debug(`MCP config written to ${configPath}`);
    return { args: ["--mcp-config", configPath], dir: tmpDir };
  }

  private removeTempDir(dir: string): void {
    try {
      rmSync(dir, { recursive: true, force: true });
    } catch {
      // ignore cleanup errors
    }
    this.tempDirs = this.tempDirs.filter((entry) => entry !== dir);
  }

  cleanup(): void {
    for (const dir of [...this.tempDirs]) {
      this.removeTempDir(dir);
    }
    this.tempDirs = [];
  }

  private sanitizeEnv(): NodeJS.ProcessEnv {
    const env = { ...process.env };
    delete env.ANTHROPIC_API_KEY;
    delete env.ANTHROPIC_AUTH_TOKEN;
    return env;
  }

  cancel(trackingId: string): void {
    const proc = this.runningProcesses.get(trackingId);
    if (proc) {
      this.runningProcesses.delete(trackingId);
      this.terminate(proc);
    }
  }

  /** Kaola fork: SIGTERM the child's process group, SIGKILL after a grace period. */
  private terminate(proc: ChildProcess): void {
    killGroup(proc, "SIGTERM");
    if (!isRunning(proc)) return;
    const timer = setTimeout(() => {
      if (isRunning(proc)) killGroup(proc, "SIGKILL");
    }, KILL_GRACE_MS);
    timer.unref();
    proc.once("close", () => clearTimeout(timer));
  }

  /**
   * Kaola fork: stop every running child (whole process groups) and remove
   * temp files. Resolves once the children have exited or been killed.
   */
  async shutdown(): Promise<void> {
    const procs = [...this.runningProcesses.values()];
    this.runningProcesses.clear();
    for (const proc of procs) killGroup(proc, "SIGTERM");
    const deadline = Date.now() + KILL_GRACE_MS;
    while (procs.some(isRunning) && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    for (const proc of procs) {
      if (isRunning(proc)) killGroup(proc, "SIGKILL");
    }
    this.cleanup();
  }

  private spawnClaude(args: string[], cwd: string | undefined): ChildProcess {
    const binary = resolveClaudeBinary(this.config);
    const proc = spawn(binary, args, {
      cwd,
      env: this.sanitizeEnv(),
      stdio: ["ignore", "pipe", "pipe"],
      detached: true,
    });
    recordChildSpawn(proc, binary);
    return proc;
  }

  private runJson(
    args: string[],
    cwd?: string,
    tempDir?: string
  ): Promise<ClaudeResult> {
    return new Promise((resolve, reject) => {
      logger.debug(`spawn: claude ${maskArgs(args)}`);
      let proc: ChildProcess;
      try {
        proc = this.spawnClaude(args, cwd);
      } catch (err) {
        if (tempDir) this.removeTempDir(tempDir);
        reject(err);
        return;
      }

      let stdout = "";
      let stderr = "";

      proc.stdout!.on("data", (data: Buffer) => {
        stdout += data.toString();
      });
      proc.stderr!.on("data", (data: Buffer) => {
        stderr += data.toString();
      });

      proc.on("close", (code) => {
        if (tempDir) this.removeTempDir(tempDir);
        if (code !== 0) {
          reject(
            new Error(
              `claude exited with code ${code}: ${stderr || stdout}`
            )
          );
          return;
        }
        try {
          const parsed = JSON.parse(stdout.trim());
          resolve({
            text: parsed.result ?? "",
            sessionId: parsed.session_id ?? "",
          });
        } catch {
          reject(new Error(`Failed to parse claude output: ${stdout}`));
        }
      });

      proc.on("error", reject);
    });
  }

  private runStreaming(
    args: string[],
    cwd: string | undefined,
    onEvent: (event: StreamEvent) => void,
    trackingId?: string,
    tempDir?: string
  ): Promise<ClaudeResult> {
    return new Promise((resolve, reject) => {
      logger.debug(`spawn streaming: claude ${maskArgs(args)}`);
      let proc: ChildProcess;
      try {
        proc = this.spawnClaude(args, cwd);
      } catch (err) {
        if (tempDir) this.removeTempDir(tempDir);
        reject(err);
        return;
      }

      if (trackingId) {
        this.runningProcesses.set(trackingId, proc);
      }

      let buffer = "";
      let resultText = "";
      let sessionId = "";

      proc.stdout!.on("data", (data: Buffer) => {
        buffer += data.toString();
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const parsed = JSON.parse(line);
            this.processStreamLine(parsed, onEvent);

            // Extract session_id and result from various event types
            if (parsed.session_id) {
              sessionId = parsed.session_id;
            }
            if (parsed.result !== undefined) {
              resultText = parsed.result;
            }
            if (parsed.type === "result") {
              sessionId = parsed.session_id ?? sessionId;
              resultText = parsed.result ?? resultText;
            }
          } catch {
            // Skip unparseable lines
          }
        }
      });

      proc.on("close", (code) => {
        if (trackingId) {
          this.runningProcesses.delete(trackingId);
        }
        if (tempDir) this.removeTempDir(tempDir);

        // Process remaining buffer
        if (buffer.trim()) {
          try {
            const parsed = JSON.parse(buffer);
            this.processStreamLine(parsed, onEvent);
            if (parsed.session_id) sessionId = parsed.session_id;
            if (parsed.result !== undefined) resultText = parsed.result;
          } catch {
            // ignore
          }
        }

        if (code !== 0 && code !== null) {
          // Kaola fork: carry the session id the CLI already announced so a
          // cancelled turn (exit 143 on SIGTERM) keeps its conversation.
          const err = new Error(`claude exited with code ${code}`) as Error & { claudeSessionId?: string };
          if (sessionId) err.claudeSessionId = sessionId;
          reject(err);
          return;
        }

        resolve({ text: resultText, sessionId });
      });

      proc.on("error", reject);
    });
  }

  private processStreamLine(
    parsed: any,
    onEvent: (event: StreamEvent) => void
  ): void {
    // Handle content_block_delta (streaming text)
    if (
      parsed.type === "content_block_delta" &&
      parsed.delta?.type === "text_delta"
    ) {
      onEvent({ type: "text_delta", text: parsed.delta.text });
      return;
    }

    // Handle assistant message with content array
    if (parsed.type === "assistant" && parsed.message?.content) {
      for (const block of parsed.message.content) {
        if (block.type === "text") {
          onEvent({ type: "text_delta", text: block.text });
        } else if (block.type === "tool_use") {
          onEvent({
            type: "tool_use",
            toolName: block.name,
            toolInput: block.input,
          });
        } else if (block.type === "thinking") {
          onEvent({ type: "thinking", text: block.thinking });
        }
      }
      return;
    }

    // Handle permission request from Claude CLI
    if (parsed.type === "permission_request") {
      onEvent({
        type: "permission_request",
        toolName: parsed.tool_name ?? parsed.toolName,
        toolInput: parsed.tool_input ?? parsed.toolInput,
        permissionId: parsed.permission_id ?? parsed.permissionId,
      });
      return;
    }

    // Handle thinking/extended thinking blocks
    if (
      parsed.type === "content_block_delta" &&
      parsed.delta?.type === "thinking_delta"
    ) {
      onEvent({ type: "thinking", text: parsed.delta.thinking });
      return;
    }

    // Handle result event
    if (parsed.type === "result") {
      onEvent({
        type: "result",
        text: parsed.result,
        sessionId: parsed.session_id,
        usage: parsed.usage,
      });
    }
  }
}
