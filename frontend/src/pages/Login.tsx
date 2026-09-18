import { type FormEvent, useState } from 'react'

// PLACEHOLDER — form shape only, per docs/LOGIN-PAGE-REQUIREMENTS.md §5.
// There is no FastAPI /login route yet (that's the separate auth-flow task,
// AU-83..87). This page exists so RequireAuth has somewhere to redirect to
// and so the auth task can wire real submit logic into this slot without a
// second frontend PR. Do not add credential-checking logic here.
export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false) // AU-13
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true) // AU-15: disable submit while a request is in flight
    // TODO(auth task): POST to the real login endpoint once it exists, then
    // honour the "from" redirect target per AU-26/27 and clear this stub.
    window.setTimeout(() => setSubmitting(false), 500)
  }

  return (
    <div className="login-page">
      <form className="login-form" onSubmit={handleSubmit}>
        <h1>Sign in</h1>
        <label>
          Email address
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
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
          />
        </label>
        <label className="login-form__toggle">
          <input
            type="checkbox"
            checked={showPassword}
            onChange={(event) => setShowPassword(event.target.checked)}
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
