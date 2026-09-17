import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 开发时 `npm run dev` 把 /api 与 /ws 代理到本地后端(8000);
// 正式运行由 FastAPI 直接托管 frontend/dist(单端口,无需代理)。
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
