import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  // DEV PROXY: browser calls /api/... on :5173, Vite forwards to FastAPI. Change the port if the backend moves.
  // Effect of removing it: you must set VITE_API_BASE_URL and the backend must allow your origin (ALLOWED_ORIGINS).
  server: { proxy: { '/api': 'http://localhost:8000' } }
})
