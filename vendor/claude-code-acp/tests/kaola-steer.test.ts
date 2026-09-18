/**
 * Kaola fork (Issue #65): behaviour of `ClaudeRunner.steer`.
 *
 * Claude Code's stream-json input channel acknowledges nothing when a message
 * joins a running turn (verified live on cli 2.1.272: no echo, no `user` event
 * beyond tool results). These tests pin the consequence — the runner reports
 * what it actually knows and never turns a bare `write()` into a consumption
 * claim — and cover the failure shapes a real pipe produces: an asynchronous
 * error, backpressure, the turn settling mid-write, and cancellation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ClaudeRunner } from "../src/claude-runner.js";
import { EventEmitter } from "node:events";
import type { ChildProcess } from "node:child_process";

vi.mock("node:child_process", () => ({ spawn: vi.fn() }));
import { spawn } from "node:child_process";
const mockSpawn = vi.mocked(spawn);

type WriteCb = (err?: Error | null) => void;

interface FakeStdin extends EventEmitter {
  writes: string[];
  destroyed: boolean;
  writableEnded: boolean;
  /** queued flush callbacks, so a test decides when the chunk reaches the pipe */
  pending: WriteCb[];
  write(chunk: string, cb?: WriteCb): boolean;
  end(): void;
  flushAll(err?: Error): void;
}

function makeStdin(opts: { manualFlush?: boolean; throwOnWrite?: Error } = {}): FakeStdin {
  const stdin = new EventEmitter() as FakeStdin;
  stdin.writes = [];
  stdin.destroyed = false;
  stdin.writableEnded = false;
  stdin.pending = [];
  stdin.write = (chunk: string, cb?: WriteCb) => {
    if (opts.throwOnWrite) throw opts.throwOnWrite;
    stdin.writes.push(chunk);
    if (cb) {
      if (opts.manualFlush) stdin.pending.push(cb);
      else setImmediate(() => cb(null));
    }
    return !opts.manualFlush; // manual flush models backpressure
  };
  stdin.end = () => {
    stdin.writableEnded = true;
  };
  stdin.flushAll = (err?: Error) => {
    const queued = stdin.pending.splice(0);
    for (const cb of queued) cb(err ?? null);
  };
  return stdin;
}

/** A child that streams nothing until the test tells it to. */
function makeProc(stdin: FakeStdin) {
  const proc = new EventEmitter() as ChildProcess & EventEmitter;
  const stdout = new EventEmitter();
  const stderr = new EventEmitter();
  (proc as any).stdout = stdout;
  (proc as any).stderr = stderr;
  (proc as any).stdin = stdin;
  (proc as any).pid = 4242;
  (proc as any).exitCode = null;
  (proc as any).signalCode = null;
  (proc as any).kill = vi.fn(() => true);
  return { proc, stdout, stderr };
}

const tick = () => new Promise((resolve) => setImmediate(resolve));

describe("Kaola steer (Issue #65)", () => {
  let runner: ClaudeRunner;

  beforeEach(() => {
    vi.clearAllMocks();
    runner = new ClaudeRunner();
  });

  async function startTurn(stdin: FakeStdin) {
    const { proc, stdout } = makeProc(stdin);
    mockSpawn.mockReturnValue(proc as any);
    const turn = runner.startSessionStreaming("/tmp", "do the long thing", () => {}, "s1");
    await tick();
    return { proc, stdout, turn };
  }

  it("writes the prompt to stdin instead of argv, keeping the channel open", async () => {
    const stdin = makeStdin();
    await startTurn(stdin);
    expect(stdin.writes).toHaveLength(1);
    expect(JSON.parse(stdin.writes[0])).toMatchObject({
      type: "user",
      message: { role: "user", content: [{ type: "text", text: "do the long thing" }] },
    });
    expect(stdin.writableEnded).toBe(false);
    const argv = mockSpawn.mock.calls[0][1] as string[];
    expect(argv).toContain("--input-format");
    expect(argv).not.toContain("do the long thing");
  });

  it("reports `written` with a write-only basis, never `injected`", async () => {
    const stdin = makeStdin();
    await startTurn(stdin);
    const result = await runner.steer("s1", "change course");
    expect(result.outcome).toBe("written");
    expect(result.confirmation).toBe("write-only");
    // The platform confirms nothing, so nothing may claim it did.
    expect(result.outcome).not.toBe("injected");
    expect(JSON.parse(stdin.writes[1]).message.content[0].text).toBe("change course");
  });

  it("waits for the flush under backpressure before answering", async () => {
    const stdin = makeStdin({ manualFlush: true });
    await startTurn(stdin);
    stdin.flushAll(); // the initial prompt
    let settled = false;
    const pending = runner.steer("s1", "change course").then((r) => {
      settled = true;
      return r;
    });
    await tick();
    expect(settled).toBe(false); // enqueued is not delivered
    stdin.flushAll();
    expect((await pending).outcome).toBe("written");
  });

  it("does not answer `written` when the flush fails asynchronously", async () => {
    const stdin = makeStdin({ manualFlush: true });
    await startTurn(stdin);
    stdin.flushAll();
    const pending = runner.steer("s1", "change course");
    await tick();
    stdin.flushAll(new Error("EPIPE: broken pipe"));
    const result = await pending;
    expect(result.outcome).toBe("unknown");
    expect(result.confirmation).toBe("none");
    expect(result.reason).toContain("EPIPE");
  });

  it("surfaces an asynchronous stream error to the NEXT steer instead of swallowing it", async () => {
    const stdin = makeStdin();
    await startTurn(stdin);
    expect((await runner.steer("s1", "first")).outcome).toBe("written");
    stdin.emit("error", new Error("EPIPE: broken pipe"));
    await tick();
    const result = await runner.steer("s1", "second");
    expect(result.outcome).toBe("notConsumed");
    expect(result.reason).toContain("EPIPE");
  });

  it("reports `unknown` when the turn settles while the write is in flight", async () => {
    const stdin = makeStdin({ manualFlush: true });
    const { stdout } = await startTurn(stdin);
    stdin.flushAll();
    const pending = runner.steer("s1", "change course");
    await tick();
    stdout.emit(
      "data",
      Buffer.from(JSON.stringify({ type: "result", result: "done", session_id: "s1" }) + "\n")
    );
    await tick();
    stdin.flushAll();
    const result = await pending;
    expect(result.outcome).toBe("unknown");
    expect(result.reason).toBe("turnSettledDuringWrite");
  });

  it("refuses to write once the turn reported its result", async () => {
    const stdin = makeStdin();
    const { stdout } = await startTurn(stdin);
    stdout.emit(
      "data",
      Buffer.from(JSON.stringify({ type: "result", result: "done", session_id: "s1" }) + "\n")
    );
    await tick();
    const before = stdin.writes.length;
    const result = await runner.steer("s1", "too late");
    expect(result.outcome).toBe("notConsumed");
    expect(result.reason).toBe("turnAlreadySettled");
    expect(stdin.writes).toHaveLength(before); // nothing was written
  });

  it("refuses to write after cancel, and writes nothing to an unknown session", async () => {
    const stdin = makeStdin();
    await startTurn(stdin);
    runner.cancel("s1");
    const cancelled = await runner.steer("s1", "after cancel");
    expect(cancelled.outcome).toBe("notConsumed");
    expect(stdin.writes).toHaveLength(1);
    const unknown = await runner.steer("no-such-session", "nowhere");
    expect(unknown.outcome).toBe("notConsumed");
    expect(unknown.reason).toBe("noRunningTurn");
  });

  it("reports `unknown` rather than success when the flush never completes", async () => {
    vi.useFakeTimers();
    try {
      const stdin = makeStdin({ manualFlush: true });
      const { proc, stdout } = makeProc(stdin);
      mockSpawn.mockReturnValue(proc as any);
      runner.startSessionStreaming("/tmp", "long", () => {}, "s1");
      await vi.advanceTimersByTimeAsync(0);
      stdin.flushAll();
      const pending = runner.steer("s1", "never flushes");
      await vi.advanceTimersByTimeAsync(2100);
      const result = await pending;
      expect(result.outcome).toBe("unknown");
      expect(result.reason).toBe("flushTimeout");
      expect(stdout).toBeDefined();
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not close stdin under an in-flight write", async () => {
    const stdin = makeStdin({ manualFlush: true });
    const { stdout } = await startTurn(stdin);
    stdin.flushAll();
    const pending = runner.steer("s1", "in flight");
    await tick();
    stdout.emit(
      "data",
      Buffer.from(JSON.stringify({ type: "result", result: "done", session_id: "s1" }) + "\n")
    );
    await tick();
    expect(stdin.writableEnded).toBe(false); // the close waits for the drain
    stdin.flushAll();
    await pending;
    await new Promise((resolve) => setTimeout(resolve, 60));
    expect(stdin.writableEnded).toBe(true);
  });
});
