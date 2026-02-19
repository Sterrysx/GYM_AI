import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/workout': 'http://localhost:8000',
      '/log': 'http://localhost:8000',
      '/generate-next-week': 'http://localhost:8000',
      '/stats': 'http://localhost:8000',
      '/complete-day': 'http://localhost:8000',
      '/dashboard': 'http://localhost:8000',
    }
  }
})