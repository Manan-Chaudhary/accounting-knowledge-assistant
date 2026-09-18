import { createContext, type ReactNode, useContext, useEffect, useState } from 'react'

// Thin seam only — NOT a second auth system. FastAPI owns the real session
// (see docs/LOGIN-PAGE-REQUIREMENTS.md AU-83) via a cookie this app can never
// read directly (HttpOnly, AU-42). The only thing this file may ever do is
// ask a server endpoint "who am I" and act on the answer.
export interface AppUser {
  email: string
  role: string
}

interface AuthState {
  user: AppUser | null
  loading: boolean
  isAuthenticated: boolean
  refetch: () => void
}

const AuthContext = createContext<AuthState | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetch('/api/auth/me', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled) setUser(data)
      })
      .catch(() => {
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [nonce])

  const refetch = () => setNonce((n) => n + 1)

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated: user !== null, refetch }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
