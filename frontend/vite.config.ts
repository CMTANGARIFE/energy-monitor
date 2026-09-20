import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// En desarrollo (sin Docker) el proxy envía /api y /health al backend FastAPI.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    // Los chunks del build van a /static/ para que la carpeta /assets/
    // quede reservada a los archivos reemplazables por el usuario
    // (montada como volumen en Docker, ver docs/ASSETS.md).
    assetsDir: 'static',
    sourcemap: false,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/tests/setup.ts',
  },
})
