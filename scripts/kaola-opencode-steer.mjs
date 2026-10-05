// OpenCode V2 plugin API. Native ACP retains its stream and prompt lifecycle.
import net from "node:net";

export default {
  id: "kaola-steer",
  async setup(context) {
    const { socket, directory } = context.options;
    if (context.location.directory !== directory) return;
    const server = net.createServer((connection) => {
      let input = "";
      connection.setEncoding("utf8");
      connection.on("data", async (part) => {
        input += part;
        if (!input.includes("\n")) return;
        connection.removeAllListeners("data");
        try {
          const request = JSON.parse(input);
          // resume:false admits input without starting an idle session. The
          // existing execution can drain steer input at its next safe point.
          const admitted = await context.session.prompt({
            sessionID: request.sessionId, text: request.text,
            delivery: "steer", resume: false,
          });
          connection.end(JSON.stringify({ outcome: "written", confirmation: "native-admitted",
            reason: "native steer inbox admission; consumption is unconfirmed",
            admitted: { id: admitted.id, sessionID: admitted.sessionID, delivery: admitted.delivery,
              type: admitted.type, time: admitted.time } }) + "\n");
        } catch (error) {
          // A thrown native call can have unknown effects. Never replay here.
          connection.end(JSON.stringify({ outcome: "unknown", reason: String(error) }) + "\n");
        }
      });
    });
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(socket, resolve);
    });
    return () => new Promise((resolve) => server.close(resolve));
  },
};
