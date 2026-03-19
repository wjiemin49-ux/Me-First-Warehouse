import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/main/main.ts", "src/main/preload.ts"],
  outDir: "dist-electron",
  clean: true,
  format: ["cjs"],
  target: "node24",
  sourcemap: true,
  splitting: false,
  bundle: true,
  platform: "node",
  external: ["electron", "node:sqlite"],
  minify: false,
});
