import { type FormEvent, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import "../styles/legacy.css";

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const { refetch } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const fromLocation = (location.state as { from?: Location })?.from?.pathname || '/home'

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setErrorMessage(null)

   
    if (!email || !password) {
      setErrorMessage('Please fill in all fields.')
      return
    }

    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters.')
      return
    }

    setSubmitting(true)

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', 
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed. Please check your credentials.')
      }
      refetch()
      navigate(fromLocation, { replace: true })
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message)
      } else {
        setErrorMessage('An unexpected error occurred. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-form" onSubmit={handleSubmit}>
        <h1>Sign in</h1>

        {errorMessage && (
          <div
            style={{
              padding: '10px 14px',
              backgroundColor: '#fef2f2',
              color: '#991b1b',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              fontSize: '13px',
              marginBottom: '16px',
            }}
          >
            {errorMessage}
          </div>
        )}

        <label>
          Email address
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            disabled={submitting}
          />
        </label>
        <label>
          Password
          <input
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            disabled={submitting}
          />
        </label>
        <label className="login-form__toggle">
          <input
            type="checkbox"
            checked={showPassword}
            onChange={(event) => setShowPassword(event.target.checked)}
            disabled={submitting}
          />
          Show password
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="login-form__support">Trouble signing in? Contact your administrator.</p>
      </form>
    </div>
  )
}