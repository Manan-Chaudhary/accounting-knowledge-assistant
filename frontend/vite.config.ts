import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// Proxies backend paths to the FastAPI dev server so the browser sees one
// origin locally too — the deploy topology this migration is built around
// (see docs/LOGIN-PAGE-REQUIREMENTS.md AU-42/AU-46 on the shared session cookie).
const FASTAPI_DEV_TARGET = 'http://localhost:8000'

// Dev-only stub for the not-yet-built /api/auth/me (see
// frontend/src/auth/AuthProvider.tsx — the real auth-flow task owns this
// endpoint). Off by default: the honest default dev state is "not
// authenticated" (a 404 from the real backend), which exercises
// RequireAuth's redirect-to-login path. Run with VITE_DEV_MOCK_AUTH=1 to
// simulate a signed-in user instead, to exercise the authenticated-render
// path. Delete this whole plugin once the real endpoint ships.
function mockAuthMeInDev(): Plugin {
  return {
    name: 'dev-mock-auth-me',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (process.env.VITE_DEV_MOCK_AUTH === '1' && req.url?.startsWith('/api/auth/me')) {
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ email: 'dev.user@alfafocus.com.au', role: 'staff' }))
          return
        }
        next()
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), mockAuthMeInDev()],
  server: {
    proxy: {
      '/chat': { target: FASTAPI_DEV_TARGET, ws: true, changeOrigin: true },
      '/upload': { target: FASTAPI_DEV_TARGET, changeOrigin: true },
      '/documents': { target: FASTAPI_DEV_TARGET, changeOrigin: true },
      '/api': { target: FASTAPI_DEV_TARGET, changeOrigin: true },
    },
  },
})
