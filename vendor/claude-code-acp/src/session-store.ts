import { readFileSync, writeFileSync, mkdirSync, existsSync, renameSync } from "node:fs";
import { join } from "node:path";
import type { McpServerConfig } from "./claude-runner.js";
import { loadConfig } from "./config.js";
import { logger } from "./logger.js";

const STORE_FILE_NAME = "sessions.json";

export interface SessionInfo {
  sessionId: string;
  cwd: string;
  title?: string;
  updatedAt?: string;
}

interface SessionData {
  cwd: string;
  claudeSessionId?: string;
  mcpServers: McpServerConfig[];
  createdAt: string;
  mode?: string;
  title?: string;
  updatedAt: string;
  configOverrides: Record<string, unknown>;
}

/** Kaola fork: one persisted Claude Code conversation (id is the map key). */
interface PersistedSession {
  cwd: string;
  updatedAt: string;
}

/**
 * Kaola fork: persisted record, version 2.
 * `names` maps an `ACPX_SESSION_NAME` to the Claude Code session it last
 * used; `sessions` records every Claude Code session id the bridge produced
 * or resumed, keyed by that id, so `session/list` can offer them per cwd.
 * A version-1 file (flat `persistKey -> claudeSessionId`) is read once and
 * converted in memory.
 */
interface PersistedRecord {
  version: 2;
  names: Record<string, string>;
  sessions: Record<string, PersistedSession>;
}

function emptyRecord(): PersistedRecord {
  return { version: 2, names: {}, sessions: {} };
}

/** Never log a raw Claude Code session id. */
function maskId(id: string | undefined): string {
  return id ? "<claude-session-id>" : "<none>";
}

export class SessionStore {
  private sessions = new Map<string, SessionData>();
  private readonly storeDir: string;
  private readonly storeFile: string;

  constructor(stateDir?: string) {
    this.storeDir = stateDir ?? loadConfig().stateDir;
    this.storeFile = join(this.storeDir, STORE_FILE_NAME);
  }

  /**
   * Create an ACP session. A fresh session starts a new Claude Code
   * conversation unless the process carries `ACPX_SESSION_NAME` and that
   * name already maps to a conversation (explicit named continuity), or a
   * `claudeSessionId` is passed (explicit resume). The upstream cwd-keyed
   * auto-restore is intentionally gone: two sessions in one repository stay
   * isolated unless the caller asks to continue.
   */
  create(
    sessionId: string,
    cwd: string,
    mcpServers: McpServerConfig[] = [],
    claudeSessionId?: string
  ): void {
    if (this.sessions.has(sessionId)) {
      throw new Error(`Session ${sessionId} already exists`);
    }

    let restored = claudeSessionId;
    const sessionName = process.env.ACPX_SESSION_NAME;
    if (!restored && sessionName) {
      restored = this.loadPersisted().names[sessionName];
    }

    const now = new Date().toISOString();
    this.sessions.set(sessionId, {
      cwd,
      mcpServers,
      claudeSessionId: restored,
      createdAt: now,
      updatedAt: now,
      configOverrides: {},
    });

    if (restored) {
      logger.info(
        `Bound Claude Code session ${maskId(restored)} to ACP session ${sessionId}` +
          (claudeSessionId ? " (explicit resume)" : ` (ACPX_SESSION_NAME)`)
      );
    }
  }

  getMcpServers(sessionId: string): McpServerConfig[] {
    return this.sessions.get(sessionId)?.mcpServers ?? [];
  }

  getCwd(sessionId: string): string | undefined {
    return this.sessions.get(sessionId)?.cwd;
  }

  setClaudeSessionId(sessionId: string, claudeId: string): void {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    session.claudeSessionId = claudeId;
    if (!claudeId) return;

    const record = this.loadPersisted();
    record.sessions[claudeId] = { cwd: session.cwd, updatedAt: new Date().toISOString() };
    const sessionName = process.env.ACPX_SESSION_NAME;
    if (sessionName) {
      record.names[sessionName] = claudeId;
    }
    this.writePersisted(record);
    logger.debug(`Persisted Claude Code session ${maskId(claudeId)} for ${session.cwd}`);
  }

  getClaudeSessionId(sessionId: string): string | undefined {
    return this.sessions.get(sessionId)?.claudeSessionId;
  }

  getMode(sessionId: string): string | undefined {
    return this.sessions.get(sessionId)?.mode;
  }

  setMode(sessionId: string, mode: string): void {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    session.mode = mode;
    session.updatedAt = new Date().toISOString();
  }

  getTitle(sessionId: string): string | undefined {
    return this.sessions.get(sessionId)?.title;
  }

  setTitle(sessionId: string, title: string): void {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    session.title = title;
    session.updatedAt = new Date().toISOString();
  }

  getUpdatedAt(sessionId: string): string | undefined {
    return this.sessions.get(sessionId)?.updatedAt;
  }

  touch(sessionId: string): void {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    session.updatedAt = new Date().toISOString();
    if (session.claudeSessionId) {
      const record = this.loadPersisted();
      const entry = record.sessions[session.claudeSessionId];
      if (entry) {
        entry.updatedAt = session.updatedAt;
        this.writePersisted(record);
      }
    }
  }

  getConfigOverrides(sessionId: string): Record<string, unknown> {
    return this.sessions.get(sessionId)?.configOverrides ?? {};
  }

  setConfigOverride(sessionId: string, key: string, value: unknown): void {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    session.configOverrides[key] = value;
    session.updatedAt = new Date().toISOString();
  }

  listAll(cwdFilter?: string): SessionInfo[] {
    const result: SessionInfo[] = [];
    for (const [sessionId, data] of this.sessions) {
      if (cwdFilter && data.cwd !== cwdFilter) continue;
      result.push({
        sessionId,
        cwd: data.cwd,
        title: data.title,
        updatedAt: data.updatedAt,
      });
    }
    return result;
  }

  /**
   * Kaola fork: persisted Claude Code sessions (newest first), listed under
   * their Claude Code session id so a later process can resume them.
   */
  listPersisted(cwdFilter?: string): SessionInfo[] {
    const record = this.loadPersisted();
    return Object.entries(record.sessions)
      .filter(([, data]) => !cwdFilter || data.cwd === cwdFilter)
      .map(([claudeSessionId, data]) => ({
        sessionId: claudeSessionId,
        cwd: data.cwd,
        updatedAt: data.updatedAt || undefined,
      }))
      .sort((a, b) => (b.updatedAt ?? "").localeCompare(a.updatedAt ?? ""));
  }

  /** Kaola fork: whether a Claude Code session id is on record. */
  hasPersisted(claudeSessionId: string): boolean {
    return Object.prototype.hasOwnProperty.call(
      this.loadPersisted().sessions,
      claudeSessionId
    );
  }

  delete(sessionId: string): void {
    this.sessions.delete(sessionId);
  }

  has(sessionId: string): boolean {
    return this.sessions.has(sessionId);
  }

  /** Forget a Claude Code session that can no longer be resumed. */
  clearPersistedSession(claudeSessionId: string): void {
    const record = this.loadPersisted();
    delete record.sessions[claudeSessionId];
    for (const [name, id] of Object.entries(record.names)) {
      if (id === claudeSessionId) delete record.names[name];
    }
    this.writePersisted(record);
    logger.info(`Cleared persisted Claude Code session ${maskId(claudeSessionId)}`);
  }

  private loadPersisted(): PersistedRecord {
    try {
      if (existsSync(this.storeFile)) {
        const data = readFileSync(this.storeFile, "utf-8");
        const parsed = JSON.parse(data);
        if (parsed && typeof parsed === "object") {
          if (parsed.version === 2) {
            return {
              version: 2,
              names: { ...(parsed.names ?? {}) },
              sessions: { ...(parsed.sessions ?? {}) },
            };
          }
          // Version 1 (upstream): persistKey -> claudeSessionId.
          const record = emptyRecord();
          for (const [key, id] of Object.entries(parsed)) {
            if (typeof id !== "string" || !id) continue;
            if (key.startsWith("session:")) {
              record.names[key.slice("session:".length)] = id;
            } else if (key.startsWith("cwd:")) {
              record.sessions[id] = { cwd: key.slice("cwd:".length), updatedAt: "" };
            }
          }
          return record;
        }
      }
    } catch {
      logger.warn(`Failed to load persisted sessions from ${this.storeFile}`);
    }
    return emptyRecord();
  }

  private writePersisted(data: PersistedRecord): void {
    try {
      if (!existsSync(this.storeDir)) {
        mkdirSync(this.storeDir, { recursive: true });
      }
      // Kaola fork: write to a sibling temp file and rename so a concurrent
      // bridge (one per Runner session) never reads a torn record.
      const temp = `${this.storeFile}.${process.pid}.${Date.now()}.tmp`;
      writeFileSync(temp, JSON.stringify(data, null, 2));
      renameSync(temp, this.storeFile);
    } catch (err) {
      logger.error(
        `Failed to write persisted sessions: ${err instanceof Error ? err.message : String(err)}`
      );
    }
  }
}
