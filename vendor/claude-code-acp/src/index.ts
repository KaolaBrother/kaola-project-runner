import { Readable, Writable } from "node:stream";
import {
  AgentSideConnection,
  ndJsonStream,
} from "@agentclientprotocol/sdk";
import { createClaudeCodeAgent } from "./agent.js";
import { ClaudeRunner } from "./claude-runner.js";
import { logger } from "./logger.js";

export { createClaudeCodeAgent } from "./agent.js";
export { ClaudeRunner } from "./claude-runner.js";
export { SessionStore } from "./session-store.js";
export type { SessionInfo } from "./session-store.js";
export { loadConfig } from "./config.js";
export type { AgentConfig } from "./config.js";
export type { ClaudeResult, StreamEvent, McpServerConfig, LaunchOptions } from "./claude-runner.js";

export function startAgent(): AgentSideConnection {
  const input = Writable.toWeb(process.stdout);
  const output = Readable.toWeb(
    process.stdin
  ) as ReadableStream<Uint8Array>;
  const stream = ndJsonStream(input, output);

  // Kaola fork: one runner shared with the shutdown path so every running
  // claude process group is stopped and temp files are removed on exit.
  const runner = new ClaudeRunner();
  const connection = new AgentSideConnection(
    (conn) => createClaudeCodeAgent(conn, runner),
    stream
  );

  logger.info("Agent started, waiting for connections on stdio...");

  let shuttingDown = false;
  const shutdown = (reason: string) => {
    if (shuttingDown) return;
    shuttingDown = true;
    logger.info(`${reason}, shutting down...`);
    runner.shutdown().finally(() => process.exit(0));
  };

  connection.closed.then(() => shutdown("Connection closed"));
  process.stdin.on("end", () => shutdown("Client stream ended"));
  process.on("SIGINT", () => shutdown("Received SIGINT"));
  process.on("SIGTERM", () => shutdown("Received SIGTERM"));

  return connection;
}

// Auto-start when run directly
startAgent();
