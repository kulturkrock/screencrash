import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  clearScreen: false,
  server: {
    open: "/?core=localhost%3A8001",
    port: 3000
  },
  plugins: [react()],
})
