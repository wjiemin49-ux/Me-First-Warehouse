import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  // Tauri 要求的基本配置
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
})
