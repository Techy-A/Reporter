import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to this portal's own backend process only.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5171,
    strictPort: true,
    proxy: { "/api": { target: "http://127.0.0.1:8001", changeOrigin: false } },
  },
  preview: { port: 5171, strictPort: true },
  build: { sourcemap: false },
});
