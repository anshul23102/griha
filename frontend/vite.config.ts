import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Production-grade headers for `vite preview` (the built app). The dev server needs inline scripts for hot reload, so it only gets the basics.
  preview: { headers: {
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'sha256-xU6i8AEYHDOfhdJR4oHFaQ3fnVINtaLzSzJeGLWBWk0='; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Permissions-Policy': 'camera=(), microphone=(), geolocation=()' } },
  server: { headers: { 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' }, port: 5173, proxy: { '/api': 'http://127.0.0.1:8000' } },
})
