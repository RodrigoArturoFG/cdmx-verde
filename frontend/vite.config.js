import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/alcaldias': 'http://localhost:8000',
      '/cobertura': 'http://localhost:8000',
      '/job': 'http://localhost:8000',
      '/cache': 'http://localhost:8000',
    }
  }
})
