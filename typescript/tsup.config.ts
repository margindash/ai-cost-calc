import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts", "src/tokenizer.ts"],
  format: ["cjs", "esm"],
  dts: true,
  clean: true,
  splitting: true,
  external: ["js-tiktoken"],
});
