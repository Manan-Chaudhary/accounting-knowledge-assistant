import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'

export interface AppUser {
  email: string
  role: string
}

export interface LoginResult {
  ok: boolean
  message: string
}

interface AuthState {
  user: AppUser | null
  loading: boolean
  isAuthenticated: boolean

  login: (
    email: string,
    password: string,
  ) => Promise<LoginResult>

  logout: () => Promise<void>

  refetch: () => Promise<void>
}

const AuthContext =
  createContext<AuthState | undefined>(undefined)

async function getResponseMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const data = await response.json()

    if (
      data &&
      typeof data === 'object'
    ) {
      if (
        'message' in data &&
        typeof data.message === 'string'
      ) {
        return data.message
      }

      if (
        'detail' in data &&
        typeof data.detail === 'string'
      ) {
        return data.detail
      }
    }
  } catch {
    // Use safe fallback below.
  }

  return fallback
}

export function AuthProvider({
  children,
}: {
  children: ReactNode
}) {
  const [user, setUser] =
    useState<AppUser | null>(null)

  const [loading, setLoading] =
    useState(true)

  const loadCurrentUser =
    useCallback(async (): Promise<AppUser | null> => {
      try {
        const response = await fetch(
          '/api/auth/me',
          {
            method: 'GET',
            credentials: 'include',
            headers: {
              Accept: 'application/json',
            },
          },
        )

        if (!response.ok) {
          setUser(null)
          return null
        }

        const currentUser =
          (await response.json()) as AppUser

        setUser(currentUser)

        return currentUser
      } catch {
        setUser(null)
        return null
      }
    }, [])

  const refetch = useCallback(async () => {
    await loadCurrentUser()
  }, [loadCurrentUser])

  useEffect(() => {
    let active = true

    async function initialiseAuth() {
      setLoading(true)

      try {
        const currentUser =
          await loadCurrentUser()

        if (!active) {
          return
        }

        setUser(currentUser)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void initialiseAuth()

    return () => {
      active = false
    }
  }, [loadCurrentUser])

  const login = useCallback(
    async (
      email: string,
      password: string,
    ): Promise<LoginResult> => {
      try {
        const response = await fetch(
          '/api/auth/login',
          {
            method: 'POST',
            credentials: 'include',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'application/json',
            },
            body: JSON.stringify({
              email,
              password,
            }),
          },
        )

        if (!response.ok) {
          return {
            ok: false,
            message:
              await getResponseMessage(
                response,
                'Invalid email or password. Please check your credentials and try again.',
              ),
          }
        }

        // Identity and role must come from the server-owned session.
        const currentUser =
          await loadCurrentUser()

        if (!currentUser) {
          return {
            ok: false,
            message:
              'Your session could not be established. Please try again.',
          }
        }

        return {
          ok: true,
          message: '',
        }
      } catch {
        return {
          ok: false,
          message:
            'Sign-in is temporarily unavailable. Please try again shortly.',
        }
      }
    },
    [loadCurrentUser],
  )

  const logout =
    useCallback(async (): Promise<void> => {
      const response = await fetch(
        '/api/auth/logout',
        {
          method: 'POST',
          credentials: 'include',
          headers: {
            Accept: 'application/json',
          },
        },
      )

      if (!response.ok) {
        throw new Error(
          await getResponseMessage(
            response,
            'Unable to sign out. Please try again.',
          ),
        )
      }

      setUser(null)
    }, [])

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      isAuthenticated: user !== null,
      login,
      logout,
      refetch,
    }),
    [
      user,
      loading,
      login,
      logout,
      refetch,
    ],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error(
      'useAuth must be used within an AuthProvider',
    )
  }

  return context
}