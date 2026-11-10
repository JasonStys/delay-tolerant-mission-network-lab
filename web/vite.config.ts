/** Canonical local asset/release build by Jason Stys; symbols: docs/CODE_INDEX.md. */
import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
const product = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8")) as {
  version: string;
};
export default defineConfig({
  root: "web",
  define: { __APP_VERSION__: JSON.stringify(product.version) },
  build: { outDir: "dist", emptyOutDir: true },
});
