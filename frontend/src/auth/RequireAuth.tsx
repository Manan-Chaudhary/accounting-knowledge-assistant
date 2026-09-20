import type { ReactNode } from 'react'

import {
  Navigate,
  useLocation,
} from 'react-router-dom'

import { useAuth } from './AuthProvider'

export function RequireAuth({
  children,
}: {
  children: ReactNode
}) {
  const {
    loading,
    isAuthenticated,
  } = useAuth()

  const location = useLocation()

  if (loading) {
    return (
      <main className="auth-route-loading">
        <span
          className="login-spinner"
          aria-hidden="true"
        />

        <span>Loading…</span>
      </main>
    )
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location }}
        replace
      />
    )
  }

  return <>{children}</>
}