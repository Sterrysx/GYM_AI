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
      '/complete-exercise': 'http://localhost:8000',
      '/has-completed-days': 'http://localhost:8000',
      '/progression': 'http://localhost:8000',
      '/dashboard': 'http://localhost:8000',
      '/targets': 'http://localhost:8000',
      '/muscle-levels': 'http://localhost:8000',
      '/webhook': 'http://127.0.0.1:8000',
      '/chat': 'http://localhost:8000',
      '/plan': 'http://localhost:8000',
    }
  }
})