import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 自定义插件：在启动时打印后台地址
const printBackendInfo = () => {
  return {
    name: 'print-backend-info',
    configureServer(server) {
      server.httpServer?.once('listening', () => {
        const backendHost = process.env.VITE_BACKEND_HOST || 'localhost'
        const backendPort = process.env.VITE_BACKEND_PORT || '8000'
        const backendUrl = `http://${backendHost}:${backendPort}`
        const adminUrl = `http://localhost:5173/admin`
        
        console.log('\n')
        console.log('  \x1b[36m%s\x1b[0m', '🔐 Admin Panel')
        console.log('  \x1b[90m%s\x1b[0m', `  Access the admin panel at: ${adminUrl}`)
        console.log('  \x1b[90m%s\x1b[0m', `  Backend API at: ${backendUrl}`)
        console.log('  \x1b[31m%s\x1b[0m', '  Note: Admin access is restricted to authorized personnel only.')
        console.log('\n')
      })
    }
  }
}

export default defineConfig({
  plugins: [vue(), printBackendInfo()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    cors: true,
    historyApiFallback: true,
    proxy: {
      '/api': {
        target: `http://${process.env.VITE_BACKEND_HOST || 'localhost'}:${process.env.VITE_BACKEND_PORT || '8000'}`,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path
      }
    }
  },
  preview: {
    port: 5174,
    host: '0.0.0.0'
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
  }
})