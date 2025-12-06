// vite.config.js
/// <reference types="vitest" />
/// <reference types="vite/client" />

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: process.env.VITE_ALLOWED_HOSTS ? process.env.VITE_ALLOWED_HOSTS.split(',') : [],
    middlewares: [
      {
        name: 'csp-headers',
        apply: 'serve',
        handler: (req, res, next) => {
          // Set CSP headers for Vite dev server
          res.setHeader(
            'Content-Security-Policy',
            [
              "'self'",
              "'unsafe-inline'",
              "'unsafe-eval'",  // Needed for Vite HMR
              'http://localhost:5173',
              'ws://localhost:5173',  // WebSocket for HMR
              'ws://127.0.0.1:5173',
              'http://localhost:8000',
              'http://127.0.0.1:8000'
            ].map(src => `default-src ${src}; script-src ${src}; style-src ${src}; connect-src ${src}; img-src 'self' data: https:; font-src 'self' data:; frame-ancestors 'none'`).join('; ')
          );
          next();
        }
      }
    ]
  },
  test: {
    globals: true, // Enables global test APIs without imports
    environment: 'jsdom',
    setupFiles: './src/setupTests.js', // Path to your test setup file
    css: true,
  },
})
