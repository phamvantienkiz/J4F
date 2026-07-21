import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Cho phép tất cả các host (bao gồm cả ngrok) truy cập vào dev server
    allowedHosts: true 
  }
});