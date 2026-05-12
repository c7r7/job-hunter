import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Change "job-hunter" to your actual GitHub repo name
export default defineConfig({
  plugins: [react()],
  base: "/job-hunter/",
  build: {
    outDir: "../docs",   // GitHub Pages can serve from /docs on main branch
    emptyOutDir: true,
  },
});
