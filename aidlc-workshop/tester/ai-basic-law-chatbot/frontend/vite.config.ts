import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/admin/parse-law': 'http://localhost:8000',
      '/admin/embed-law': 'http://localhost:8000',
      '/admin/embed-guideline': 'http://localhost:8000',
      '/admin/embed-guideline-ocr': 'http://localhost:8000',
      '/admin/tag-guidelines': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true,
  },
})
