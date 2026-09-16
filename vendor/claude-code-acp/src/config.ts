import { homedir, tmpdir } from "node:os";
import { join } from "node:path";

export interface AgentConfig {
  allowedTools: string[];
  model: string | undefined;
  maxTurns: number | undefined;
  timeout: number;
  dangerouslySkipPermissions: boolean;
  /**
   * Kaola fork: exact Claude binary. `CLAUDE_ACP_CLAUDE_BIN` wins over
   * `CLAUDE_BIN`; an empty value counts as unset. When set it must be an
   * absolute path to an executable file and the runner never falls back to
   * `PATH`; when unset the upstream `claude` PATH lookup applies.
   */
  claudeBin: string | undefined;
  /** Kaola fork: directory for per-turn temp files (MCP config). */
  runtimeDir: string;
  /** Kaola fork: directory for the bridge's own session-id record. */
  stateDir: string;
}

function nonEmpty(value: string | undefined): string | undefined {
  return value && value.trim() ? value : undefined;
}

export function loadConfig(): AgentConfig {
  return {
    allowedTools: process.env.CLAUDE_ACP_ALLOWED_TOOLS
      ? process.env.CLAUDE_ACP_ALLOWED_TOOLS.split(",").map((t) =>
          t.trim()
        )
      : [],
    model: process.env.CLAUDE_ACP_MODEL || undefined,
    maxTurns: process.env.CLAUDE_ACP_MAX_TURNS
      ? parseInt(process.env.CLAUDE_ACP_MAX_TURNS, 10)
      : undefined,
    timeout: process.env.CLAUDE_ACP_TIMEOUT
      ? parseInt(process.env.CLAUDE_ACP_TIMEOUT, 10)
      : 300000, // 5 minutes default
    dangerouslySkipPermissions:
      process.env.CLAUDE_ACP_SKIP_PERMISSIONS === "true",
    claudeBin:
      nonEmpty(process.env.CLAUDE_ACP_CLAUDE_BIN) ??
      nonEmpty(process.env.CLAUDE_BIN),
    runtimeDir: nonEmpty(process.env.CLAUDE_ACP_RUNTIME_DIR) ?? tmpdir(),
    stateDir:
      nonEmpty(process.env.CLAUDE_ACP_STATE_DIR) ??
      join(homedir(), ".claude-code-acp"),
  };
}
