// vite.config.js
/// <reference types="vitest" />
/// <reference types="vite/client" />

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// CSP plugin for development server
function cspPlugin() {
  return {
    name: 'csp-headers',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        // CSP policy for development - allows Vite HMR to work
        const csp = [
          "default-src 'self'",
          "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  // unsafe-eval needed for Vite HMR
          "style-src 'self' 'unsafe-inline'",
          "img-src 'self' data: https:",
          "font-src 'self' data:",
          "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000 ws://localhost:5173 ws://127.0.0.1:5173",
          "frame-ancestors 'none'",
          "base-uri 'self'",
          "form-action 'self'"
        ].join('; ');

        res.setHeader('Content-Security-Policy', csp);
        res.setHeader('X-Frame-Options', 'DENY');
        next();
      });
    }
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), cspPlugin()],
  server: {
    allowedHosts: process.env.VITE_ALLOWED_HOSTS ? process.env.VITE_ALLOWED_HOSTS.split(',') : [],
  },
  test: {
    globals: true, // Enables global test APIs without imports
    environment: 'jsdom',
    setupFiles: './src/setupTests.js', // Path to your test setup file
    css: true,
  },
})
