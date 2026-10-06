// kpr-dsh-steer-bridge — in-process steer bridge for `dsh --profile acp`.
//
// Loaded as an ordinary Cordis plugin through the launcher's documented
// `--patch` overlay mechanism (dsh-app-boot: anchorInsertedPluginNames anchors
// the `./`-relative `name` beside the patch file). The ACP wire keeps its
// shipped method set untouched; this plugin exposes the same call the shipped
// HTTP session controller already makes — `agent.steer(message)` from
// `ctx.agents.get(sessionId)` (dsh-api-session-controller prompt() mode:"steer")
// — on a per-process unix socket chosen by the supervising holder via
// KPR_DSH_STEER_SOCK. Newline-delimited JSON request/reply, one object per line:
//   {"id":1,"op":"ping"}                          -> {"id":1,"ok":true,"pong":true}
//   {"id":2,"op":"status","sessionId":"..."}      -> {"id":2,"ok":true,"agentStatus":"idle"|"running","pending":{"nextTurn":n,"nextStep":n}}
//   {"id":3,"op":"steer","sessionId":"...","text":"..."}
//     -> {"id":3,"ok":true,"admitted":"next-step","agentStatus":"running","statusAfter":"running"}
//     -> {"id":3,"ok":false,"error":{"code":"...","message":"..."}}
// The user message object replicates createUserMessage({content,source})
// (@deepseek-ai/dsh-llm): {id: randomUUID, role:"user", content, source:{kind:"user"}},
// deep-frozen — byte-identical shape to what dsh-acp's prompt path produces.

import { createServer } from "node:net";
import { randomUUID } from "node:crypto";
import { chmodSync, unlinkSync } from "node:fs";

export const name = "kpr-dsh-steer-bridge";

const MAX_LINE_BYTES = 1 << 20;

const deepFreeze = (value) => {
	if (value !== null && typeof value === "object") {
		for (const key of Object.keys(value)) deepFreeze(value[key]);
		Object.freeze(value);
	}
	return value;
};

function steerUserMessage(text) {
	return deepFreeze({
		id: randomUUID(),
		role: "user",
		content: [{ type: "text", text }],
		source: { kind: "user" },
	});
}

export function apply(ctx, config) {
	const socketPath = typeof config?.socketPath === "string" && config.socketPath
		? config.socketPath
		: process.env.KPR_DSH_STEER_SOCK;
	if (typeof socketPath !== "string" || socketPath.length === 0) {
		ctx.logger?.warn?.("kpr-dsh-steer-bridge: inactive (no socketPath config and KPR_DSH_STEER_SOCK unset)");
		return;
	}

	const reply = (conn, id, obj) => {
		try { conn.write(JSON.stringify({ id, ...obj }) + "\n"); } catch {}
	};

	const handle = async (conn, raw) => {
		let req;
		try { req = JSON.parse(raw); } catch {
			reply(conn, null, { ok: false, error: { code: "bad-json", message: "request line is not JSON" } });
			return;
		}
		const id = req && typeof req === "object" ? req.id ?? null : null;
		try {
			const op = req?.op;
			if (op === "ping") { reply(conn, id, { ok: true, pong: true }); return; }
			if (op === "status" || op === "steer" || op === "compact") {
				const agents = ctx.get("agents");
				if (agents === void 0) {
					reply(conn, id, { ...(op === "compact" ? { sessionId: req.sessionId } : {}), ok: false, error: { code: "service-unavailable", message: "agents service is not mounted" } });
					return;
				}
				const agent = agents.get(String(req?.sessionId ?? ""));
				if (agent === void 0) {
					reply(conn, id, { ...(op === "compact" ? { sessionId: req.sessionId } : {}), ok: false, error: { code: "session/not-found", message: `no live agent for session ${JSON.stringify(req?.sessionId)}` } });
					return;
				}
				if (op === "compact") {
					const compaction = ctx.get("compaction");
					if (typeof compaction?.compactNow !== "function") {
						reply(conn, id, { sessionId: req.sessionId, ok: false, error: { code: "service-unavailable", message: "compactNow is not mounted" } });
						return;
					}
					// The shipped command calls this seam. Do not compact through
					// a model prompt or bypass its idle/range/model/flush checks.
					const commandId = randomUUID();
					const controller = new AbortController();
					const cancel = () => controller.abort();
					conn.once("close", cancel);
					let summary, end;
					const dispose = ctx.on("session/event", (session, event) => {
						if (session !== agent.session || event.data?.sourceCommandId !== commandId) return;
						if (event.type === "compaction/summary") summary = { seq: event.seq, data: {
							compactionId: event.data.compactionId, sourceCommandId: commandId,
							shadowedRange: event.data.shadowedRange, shadowedTokenCount: event.data.shadowedTokenCount } };
						if (event.type === "compaction/end") end = { seq: event.seq, data: event.data };
					});
					try {
						const result = await compaction.compactNow(agent, controller.signal, commandId);
						if (result === null) reply(conn, id, { ok: true, sessionId: req.sessionId, compacted: false });
						else reply(conn, id, { ok: true, sessionId: req.sessionId, compacted: true,
							compactionId: result.compactionId, sourceCommandId: commandId,
							summarySeq: result.summarySeq, endSeq: result.endSeq, summary, end });
					} catch (error) {
						reply(conn, id, { ok: false, sessionId: req.sessionId, summary, end,
							error: { code: error?.code ?? "internal", message: String(error?.message ?? error) } });
					} finally {
						dispose();
						conn.removeListener("close", cancel);
					}
					return;
				}
				if (op === "status") {
					reply(conn, id, {
						ok: true,
						agentStatus: agent.status,
						pending: {
							nextTurn: agent.inbox?.nextTurn?.length ?? null,
							nextStep: agent.inbox?.nextStep?.length ?? null,
						},
					});
					return;
				}
				const text = typeof req?.text === "string" ? req.text : "";
				if (!text.trim()) {
					reply(conn, id, { ok: false, error: { code: "empty-text", message: "steer requires non-empty text" } });
					return;
				}
				const statusBefore = agent.status;
				// The same call the shipped session controller makes for
				// request.mode === "steer" (dsh-api-session-controller):
				// durable splice into the next-step inbox; a running driver
				// consumes it at its next step boundary and the turn cannot
				// close while next-step input is pending.
				agent.steer(steerUserMessage(text));
				reply(conn, id, { ok: true, admitted: "native-steer", agentStatus: statusBefore, statusAfter: agent.status });
				return;
			}
			reply(conn, id, { ok: false, error: { code: "unknown-op", message: `unknown op ${JSON.stringify(op)}` } });
		} catch (error) {
			reply(conn, id, { ok: false, error: { code: "internal", message: String(error?.message ?? error) } });
		}
	};

	const server = createServer((conn) => {
		let buf = "";
		conn.setEncoding("utf8");
		conn.on("data", (chunk) => {
			buf += chunk;
			if (buf.length > MAX_LINE_BYTES) { conn.destroy(); return; }
			let idx;
			while ((idx = buf.indexOf("\n")) >= 0) {
				const line = buf.slice(0, idx);
				buf = buf.slice(idx + 1);
				if (line.trim()) handle(conn, line);
			}
		});
		conn.on("error", () => {});
	});
	server.on("error", (error) => {
		ctx.logger?.warn?.(`kpr-dsh-steer-bridge: server error: ${String(error?.message ?? error)}`);
	});
	try { unlinkSync(socketPath); } catch {}
	server.listen(socketPath, () => {
		try { chmodSync(socketPath, 0o600); } catch {}
		process.stderr.write(`kpr-dsh-steer-bridge: listening on ${socketPath}\n`);
	});
	ctx.effect(() => () => {
		try { server.close(); } catch {}
		try { unlinkSync(socketPath); } catch {}
	}, "kpr-dsh-steer-bridge teardown");
}
