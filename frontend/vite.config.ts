import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Encaminha todas as chamadas REST ao backend FastAPI
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // Preserva o IP de quem chamou em X-Forwarded-For: sem isso, todo
        // acesso vindo da rede local chegaria ao backend como 127.0.0.1 e
        // passaria pela regra de loopback (ver core/auth.py).
        xfwd: true,
      },
      // Encaminha WebSocket ao backend FastAPI
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
        xfwd: true,
      },
    },
  },
})

