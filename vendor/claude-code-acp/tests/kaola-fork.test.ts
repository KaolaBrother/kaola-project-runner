import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mkdtempSync, writeFileSync, chmodSync, rmSync, mkdirSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { EventEmitter } from "node:events";
import type { ChildProcess } from "node:child_process";

// Kaola fork: unit coverage for the exact-binary rule, per-session launch
// flags, and the version-2 session record. The offline end-to-end proof is
// tests/contract/test-issue-50-claude-acp-bridge.py in the Runner repository.

vi.mock("node:child_process", () => ({
  spawn: vi.fn(),
}));

import { spawn } from "node:child_process";
import { ClaudeRunner, ClaudeBinaryError, resolveClaudeBinary } from "../src/claude-runner.js";
import { SessionStore } from "../src/session-store.js";
import type { AgentConfig } from "../src/config.js";

const mockSpawn = vi.mocked(spawn);

function config(overrides: Partial<AgentConfig> = {}): AgentConfig {
  return {
    allowedTools: [],
    model: undefined,
    maxTurns: undefined,
    timeout: 300000,
    dangerouslySkipPermissions: true,
    claudeBin: undefined,
    runtimeDir: tmpdir(),
    stateDir: join(tmpdir(), "unused"),
    ...overrides,
  };
}

function streamProcess(lines: string[]): ChildProcess {
  const proc = new EventEmitter() as ChildProcess & EventEmitter;
  const stdout = new EventEmitter();
  (proc as any).stdout = stdout;
  (proc as any).stderr = new EventEmitter();
  (proc as any).pid = 4242;
  (proc as any).exitCode = null;
  (proc as any).signalCode = null;
  (proc as any).kill = vi.fn();
  setTimeout(() => {
    for (const line of lines) stdout.emit("data", Buffer.from(line + "\n"));
    setTimeout(() => {
      (proc as any).exitCode = 0;
      proc.emit("close", 0);
    }, 5);
  }, 5);
  return proc;
}

describe("exact binary", () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "kaola-fork-"));
  });
  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  it("uses PATH lookup only when nothing is configured", () => {
    expect(resolveClaudeBinary(config())).toBe("claude");
  });

  it("returns the configured absolute executable", () => {
    const bin = join(dir, "claude");
    writeFileSync(bin, "#!/bin/sh\nexit 0\n");
    chmodSync(bin, 0o755);
    expect(resolveClaudeBinary(config({ claudeBin: bin }))).toBe(bin);
  });

  it("fails closed for relative, missing, directory, and non-executable values", () => {
    const plain = join(dir, "plain");
    writeFileSync(plain, "x");
    chmodSync(plain, 0o644);
    for (const value of ["claude", join(dir, "missing"), dir, plain]) {
      expect(() => resolveClaudeBinary(config({ claudeBin: value }))).toThrow(ClaudeBinaryError);
    }
  });

  it("never spawns when the binary is unusable", async () => {
    const runner = new ClaudeRunner(config({ claudeBin: join(dir, "missing") }));
    await expect(runner.startSessionStreaming("/tmp", "hi", () => {})).rejects.toBeInstanceOf(ClaudeBinaryError);
    expect(mockSpawn).not.toHaveBeenCalled();
  });
});

describe("per-session launch options", () => {
  beforeEach(() => vi.clearAllMocks());

  it("translates model, effort, permission mode, and fast on first and resume turns", async () => {
    const runner = new ClaudeRunner(config());
    mockSpawn.mockReturnValue(streamProcess([JSON.stringify({ type: "result", result: "ok", session_id: "s1" })]));
    const options = { model: "fable", effort: "high", permissionMode: "bypassPermissions", fast: "on" as const };
    await runner.startSessionStreaming("/tmp", "one", () => {}, "t1", options);
    mockSpawn.mockReturnValue(streamProcess([JSON.stringify({ type: "result", result: "ok", session_id: "s1" })]));
    await runner.continueSessionStreaming("s1", "two", () => {}, "t1", { ...options, fast: "off" }, "/tmp");
    const [firstArgs, secondArgs] = mockSpawn.mock.calls.map((call) => call[1] as string[]);
    for (const args of [firstArgs, secondArgs]) {
      expect(args).toEqual(expect.arrayContaining(["--model", "fable", "--effort", "high", "--permission-mode", "bypassPermissions"]));
      expect(args).not.toContain("--dangerously-skip-permissions");
    }
    expect(firstArgs[firstArgs.indexOf("--settings") + 1]).toBe(JSON.stringify({ fastMode: true }));
    expect(secondArgs[secondArgs.indexOf("--settings") + 1]).toBe(JSON.stringify({ fastMode: false }));
    expect(secondArgs).toEqual(expect.arrayContaining(["--resume", "s1"]));
    expect((mockSpawn.mock.calls[1][2] as any).cwd).toBe("/tmp");
    expect((mockSpawn.mock.calls[0][2] as any).detached).toBe(true);
  });

  it("keeps --dangerously-skip-permissions only without a permission mode", async () => {
    const runner = new ClaudeRunner(config());
    mockSpawn.mockReturnValue(streamProcess([]));
    await runner.startSessionStreaming("/tmp", "x", () => {});
    const args = mockSpawn.mock.calls[0][1] as string[];
    expect(args).toContain("--dangerously-skip-permissions");
    expect(args).not.toContain("--permission-mode");
    expect(args[args.indexOf("--settings") + 1]).toBe(JSON.stringify({ fastMode: false }));
  });
});

describe("session record v2", () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "kaola-store-"));
    delete process.env.ACPX_SESSION_NAME;
  });
  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
    delete process.env.ACPX_SESSION_NAME;
  });

  it("does not auto-continue by cwd, lists persisted sessions, and follows ACPX_SESSION_NAME", () => {
    const first = new SessionStore(dir);
    first.create("acp-1", "/repo");
    first.setClaudeSessionId("acp-1", "claude-1");
    const second = new SessionStore(dir);
    second.create("acp-2", "/repo");
    expect(second.getClaudeSessionId("acp-2")).toBeUndefined();
    expect(second.listPersisted("/repo").map((s) => s.sessionId)).toEqual(["claude-1"]);
    expect(second.listPersisted("/elsewhere")).toEqual([]);
    expect(second.hasPersisted("claude-1")).toBe(true);

    process.env.ACPX_SESSION_NAME = "alpha";
    const named = new SessionStore(dir);
    named.create("acp-3", "/repo");
    named.setClaudeSessionId("acp-3", "claude-3");
    const namedAgain = new SessionStore(dir);
    namedAgain.create("acp-4", "/repo");
    expect(namedAgain.getClaudeSessionId("acp-4")).toBe("claude-3");

    namedAgain.clearPersistedSession("claude-3");
    const after = new SessionStore(dir);
    after.create("acp-5", "/repo");
    expect(after.getClaudeSessionId("acp-5")).toBeUndefined();
    expect(after.hasPersisted("claude-3")).toBe(false);
  });

  it("leaves no temp sibling when the record cannot be renamed into place", () => {
    // A directory at the record path makes renameSync fail after the temp
    // sibling was written; the failure is logged and the sibling removed.
    mkdirSync(join(dir, "sessions.json"), { recursive: true });
    writeFileSync(join(dir, "sessions.json", "occupied"), "x");
    const store = new SessionStore(dir);
    store.create("acp-t", "/repo");
    store.setClaudeSessionId("acp-t", "claude-t");
    expect(readdirSync(dir).filter((name) => name.endsWith(".tmp"))).toEqual([]);
    expect(readdirSync(dir)).toEqual(["sessions.json"]);
  });

  it("binds an explicit resume id and converts a version-1 file", () => {
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "sessions.json"), JSON.stringify({ "session:beta": "claude-9", "cwd:/old": "claude-8" }));
    const store = new SessionStore(dir);
    expect(store.hasPersisted("claude-8")).toBe(true);
    process.env.ACPX_SESSION_NAME = "beta";
    store.create("acp-b", "/repo");
    expect(store.getClaudeSessionId("acp-b")).toBe("claude-9");
    store.create("claude-7", "/repo", [], "claude-7");
    expect(store.getClaudeSessionId("claude-7")).toBe("claude-7");
  });
});
