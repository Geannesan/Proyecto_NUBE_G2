import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        // IPv4 explícito evita que Node resuelva localhost como ::1 mientras
        // Uvicorn está publicado únicamente en la interfaz IPv4 del host.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        timeout: 120000,
        proxyTimeout: 120000,
      },
    },
  },
})
