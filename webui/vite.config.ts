import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../src/aero/server/static",
    emptyOutDir: true,
  },
  server: {
    port: 4174,
    proxy: {
      "/api": "http://127.0.0.1:8765",
    },
  },
});
