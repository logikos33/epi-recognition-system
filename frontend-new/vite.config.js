import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    watch: {
      usePolling: true,
      interval: 500,
    },
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/streams': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
  cacheDir: '/tmp/vite-cache-epi',
})
