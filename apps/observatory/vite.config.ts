import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const securityHeaders = {
  'Content-Security-Policy': "default-src 'self'; img-src 'self' data:; media-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; script-src 'self'; connect-src 'self' http://127.0.0.1:8000 http://localhost:8000 ws://127.0.0.1:5173 ws://localhost:5173; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'",
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
  'Referrer-Policy': 'no-referrer',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
}

const developmentHeaders = {
  ...securityHeaders,
  'Content-Security-Policy': securityHeaders['Content-Security-Policy']
    .replace("script-src 'self'", "script-src 'self' 'unsafe-inline'")
    // Vite HMR injects <style> elements; production style-src stays 'self'.
    .replace("style-src 'self'", "style-src 'self' 'unsafe-inline'"),
}

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'dev-inline-css-csp',
      transformIndexHtml(html) {
        return html
          .replace("style-src 'self'", "style-src 'self' 'unsafe-inline'")
          .replace("script-src 'self'", "script-src 'self' 'unsafe-inline'")
      },
    },
  ],
  server: { host: '127.0.0.1', strictPort: true, headers: developmentHeaders },
  preview: { host: '127.0.0.1', strictPort: true, headers: securityHeaders },
})
