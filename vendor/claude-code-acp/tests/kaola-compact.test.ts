import { describe, expect, it } from "vitest";
import { ClaudeRunner, type StreamEvent } from "../src/claude-runner.js";

// Test the wire parser directly. No Claude process or native hook is mocked.
function parse(frame: unknown): StreamEvent[] {
  const events: StreamEvent[] = [];
  (new ClaudeRunner() as any).processStreamLine(frame, (event: StreamEvent) => events.push(event));
  return events;
}

describe("Kaola compact completion (Issue #264)", () => {
  it.each(["auto", "manual"])("keeps native %s metadata", (trigger) => {
    expect(parse({ type: "system", subtype: "compact_boundary", uuid: "native-boundary",
      compact_metadata: { trigger, pre_tokens: 152000, post_tokens: 41000 } })).toEqual([{
      type: "compact_boundary", compactUuid: "native-boundary", compactTrigger: trigger,
      compactPreTokens: 152000, compactPostTokens: 41000,
    }]);
  });

  it.each([[], ["auto"], null, undefined, "completed"])("rejects non-object metadata %j", (meta) => {
    expect(parse({ type: "system", subtype: "compact_boundary", compact_metadata: meta })).toEqual([]);
  });

  it("does not convert an in-progress status into a completed event", () => {
    expect(parse({ type: "system", subtype: "status", status: "compacting",
      compact_metadata: { trigger: "auto", pre_tokens: 152000 } })).toEqual([]);
  });

  it("does not infer completion from assistant text", () => {
    expect(parse({ type: "assistant", message: { content: [{ type: "text", text: "compact_boundary completed" }] } }))
      .toEqual([{ type: "text_delta", text: "compact_boundary completed" }]);
  });

  it("omits malformed optional fields and keeps the actual event", () => {
    const event = parse({ type: "system", subtype: "compact_boundary", uuid: [],
      compact_metadata: { trigger: "other", pre_tokens: Infinity, post_tokens: "41000" } })[0];
    expect(event).toEqual({ type: "compact_boundary", compactUuid: undefined,
      compactTrigger: undefined, compactPreTokens: undefined, compactPostTokens: undefined });
  });
});
