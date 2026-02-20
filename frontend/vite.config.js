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
      '/targets': 'http://localhost:8000',
      '/webhook': 'http://127.0.0.1:8000', // Added this for your Apple Health testing
      '/chat': 'http://localhost:8000',
      '/plan': 'http://localhost:8000',
    }
  }
})