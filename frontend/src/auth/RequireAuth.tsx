import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { loading, isAuthenticated } = useAuth()
  const location = useLocation()

  if (loading) return null

  if (!isAuthenticated) {
    // AU-26/27: the real login page (built by the auth task) is responsible for
    // reading this "from" location and redirecting back after sign-in, against
    // a validated list of the app's own routes — not an open redirect.
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
