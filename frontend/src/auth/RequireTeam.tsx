import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthProvider'

export function RequireTeam({
  children,
}: {
  children: ReactNode
}) {
  const { user } = useAuth()

  if (user?.role !== 'team') {
    return <Navigate to="/home" replace />
  }

  return <>{children}</>
}
