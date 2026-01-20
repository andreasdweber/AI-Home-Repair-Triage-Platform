import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Build as a library for widget embedding
    lib: {
      entry: resolve(__dirname, 'src/main.jsx'),
      name: 'FixItAI',
      fileName: (format) => `fixit-widget.${format}.js`,
      formats: ['es', 'umd']
    },
    rollupOptions: {
      // Don't externalize React - bundle it for standalone widget
      output: {
        // Ensure CSS is inlined
        assetFileNames: 'fixit-widget.[ext]'
      }
    },
    // Copy public folder contents to dist
    copyPublicDir: true
  },
  // CSS will be processed by Tailwind and can be imported as string
  css: {
    postcss: './postcss.config.js'
  }
})
