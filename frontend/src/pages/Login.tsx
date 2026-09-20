import {
  type FormEvent,
  useId,
  useRef,
  useState,
} from 'react'

import {
  Navigate,
  useLocation,
  useNavigate,
} from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'
import '../styles/login.css'

const EMAIL_MAX_LENGTH = 254
const PASSWORD_MAX_LENGTH = 128

const ALLOWED_REDIRECTS = new Set([
  '/home',
  '/documents',
  '/assistant',
  '/testing',
])

type FieldErrors = {
  email?: string
  password?: string
}

function isValidEmailFormat(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function safeRedirectTarget(from: unknown): string {
  if (
    from &&
    typeof from === 'object' &&
    'pathname' in from &&
    typeof (from as { pathname: unknown }).pathname === 'string'
  ) {
    const pathname = (from as { pathname: string }).pathname

    if (ALLOWED_REDIRECTS.has(pathname)) {
      return pathname
    }
  }

  return '/assistant'
}

export function Login() {
  const {
    login,
    isAuthenticated,
    loading,
  } = useAuth()

  const navigate = useNavigate()
  const location = useLocation()

  const emailId = useId()
  const passwordId = useId()
  const messageId = useId()

  const passwordRef = useRef<HTMLInputElement>(null)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const [fieldErrors, setFieldErrors] =
    useState<FieldErrors>({})

  const [formError, setFormError] =
    useState<string | null>(null)

  const [submitting, setSubmitting] =
    useState(false)

  if (loading) {
    return (
      <main className="login-page">
        <div className="login-frame">
          <div className="login-loading">
            <span
              className="login-spinner"
              aria-hidden="true"
            />
            Checking your session…
          </div>
        </div>
      </main>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/assistant" replace />
  }

  function validate(): FieldErrors {
    const errors: FieldErrors = {}

    const trimmedEmail = email.trim()

    if (!trimmedEmail) {
      errors.email = 'Email address is required.'
    } else if (!isValidEmailFormat(trimmedEmail)) {
      errors.email = 'Enter a valid email address.'
    }

    if (!password) {
      errors.password = 'Password is required.'
    }

    return errors
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setFormError(null)

    const errors = validate()

    setFieldErrors(errors)

    if (Object.keys(errors).length > 0) {
      return
    }

    setSubmitting(true)

    try {
      const result = await login(
        email.trim().toLowerCase(),
        password,
      )

      if (!result.ok) {
        setFormError(result.message)
        setPassword('')

        requestAnimationFrame(() => {
          passwordRef.current?.focus()
        })

        return
      }

      const from =
        (location.state as { from?: unknown } | null)?.from

      navigate(
        safeRedirectTarget(from),
        { replace: true },
      )
    } catch {
      setFormError(
        'Sign-in is temporarily unavailable. Please try again shortly.',
      )

      setPassword('')

      requestAnimationFrame(() => {
        passwordRef.current?.focus()
      })
    } finally {
      setSubmitting(false)
    }
  }

  const message =
    formError ??
    fieldErrors.email ??
    fieldErrors.password ??
    'Validation and authentication messages appear here.'

  const hasError =
    Boolean(
      formError ||
      fieldErrors.email ||
      fieldErrors.password,
    )

  return (
    <main className="login-page">
      <div className="login-frame">

        <header className="login-page-brand">
          <div className="login-page-brand__name">
            ALFA FOCUS
          </div>

          <div className="login-page-brand__product">
            SMSF ASSISTANT
          </div>
        </header>

        <section
          className="login-card"
          aria-labelledby="login-title"
        >
          <div
            className="login-monogram"
            aria-hidden="true"
          >
            AF
          </div>

          <div className="login-card-heading">
            <h1 id="login-title">
              Alfa Focus SMSF Assistant
            </h1>

            <p>
              Sign in to access the internal knowledge assistant
            </p>
          </div>

          <form
            className="login-form"
            onSubmit={handleSubmit}
            noValidate
          >
            <div className="login-field">
              <label htmlFor={emailId}>
                Email Address
              </label>

              <input
                id={emailId}
                type="email"
                inputMode="email"
                autoComplete="username"
                placeholder="name@alfafocus.com.au"
                value={email}
                maxLength={EMAIL_MAX_LENGTH}
                disabled={submitting}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={messageId}
                onChange={(event) => {
                  setEmail(event.target.value)

                  if (fieldErrors.email) {
                    setFieldErrors((previous) => ({
                      ...previous,
                      email: undefined,
                    }))
                  }

                  if (formError) {
                    setFormError(null)
                  }
                }}
              />
            </div>

            <div className="login-field">
              <label htmlFor={passwordId}>
                Password
              </label>

              <div className="login-password">
                <input
                  ref={passwordRef}
                  id={passwordId}
                  type={
                    showPassword
                      ? 'text'
                      : 'password'
                  }
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  maxLength={PASSWORD_MAX_LENGTH}
                  disabled={submitting}
                  aria-invalid={
                    Boolean(fieldErrors.password)
                  }
                  aria-describedby={messageId}
                  onChange={(event) => {
                    setPassword(event.target.value)

                    if (fieldErrors.password) {
                      setFieldErrors((previous) => ({
                        ...previous,
                        password: undefined,
                      }))
                    }

                    if (formError) {
                      setFormError(null)
                    }
                  }}
                />

                <button
                  type="button"
                  className="login-password-toggle"
                  disabled={submitting}
                  aria-label={
                    showPassword
                      ? 'Hide password'
                      : 'Show password'
                  }
                  aria-pressed={showPassword}
                  onClick={() => {
                    setShowPassword(
                      (current) => !current,
                    )
                  }}
                >
                  <i
                    className={
                      showPassword
                        ? 'far fa-eye-slash'
                        : 'far fa-eye'
                    }
                    aria-hidden="true"
                  />
                </button>
              </div>
            </div>

            <div
              id={messageId}
              className={
                hasError
                  ? 'login-message login-message--error'
                  : 'login-message'
              }
              role={hasError ? 'alert' : 'status'}
            >
              {message}
            </div>

            <button
              type="submit"
              className="login-submit"
              disabled={submitting}
            >
              {submitting && (
                <span
                  className="login-button-spinner"
                  aria-hidden="true"
                />
              )}

              {submitting
                ? 'Signing in…'
                : 'Log In'}
            </button>
          </form>

          <p className="login-authorised-note">
            Authorised Alfa Focus staff only. Access is monitored
            and restricted.
          </p>
        </section>
      </div>
    </main>
  )
}