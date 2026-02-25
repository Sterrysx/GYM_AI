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
      '/chat/stream': {
        target: 'http://localhost:8000',
        // Disable response buffering for SSE streaming
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['cache-control'] = 'no-cache';
            proxyRes.headers['x-accel-buffering'] = 'no';
          });
        },
      },
      '/chat': 'http://localhost:8000',
      '/plan': 'http://localhost:8000',
      '/abs': 'http://localhost:8000',
    }
  }
})