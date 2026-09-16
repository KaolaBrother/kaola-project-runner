import { defineConfig } from "tsup";

// Kaola fork: emit one self-contained ESM file. The ACP SDK and its zod peer
// are bundled so runtime needs only the local `node` and the local `claude`;
// no registry install happens on the machine that runs the bridge. Source
// maps and declaration output are off so the committed dist is a single
// reproducible artifact.
export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"],
  target: "node20",
  platform: "node",
  outDir: "dist",
  clean: true,
  sourcemap: false,
  dts: false,
  noExternal: ["@agentclientprotocol/sdk", "zod"],
});
