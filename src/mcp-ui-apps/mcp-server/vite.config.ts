import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// Bundle the View into ONE self-contained HTML file: the host loads it into a
// sandboxed iframe via srcdoc, so it can't fetch sibling JS/CSS files.
export default defineConfig({
  plugins: [viteSingleFile()],
  build: { rollupOptions: { input: "wire-review.html" }, outDir: "dist", emptyOutDir: true },
});
