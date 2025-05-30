import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,  // 指定したポートが使用中の場合はエラーを出す
    hmr: {
      port: 5173,
      protocol: 'ws',
      host: 'localhost'
    },
    watch: {
      usePolling: true
    }
  }
})
