import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import { RequireAuth } from './auth/RequireAuth'
import { ChainlitProvider } from './chainlit/ChainlitProvider'
import { Chat } from './pages/Chat'
import { Documents } from './pages/Documents'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Testing } from './pages/Testing'

function App() {
  return (
    <AuthProvider>
      <ChainlitProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route
            path="/home"
            element={
              <RequireAuth>
                <Home />
              </RequireAuth>
            }
          />
          <Route
            path="/docs"
            element={
              <RequireAuth>
                <Documents />
              </RequireAuth>
            }
          />
          <Route
            path="/testing"
            element={
              <RequireAuth>
                <Testing />
              </RequireAuth>
            }
          />
          <Route
            path="/assistant"
            element={
              <RequireAuth>
                <Chat />
              </RequireAuth>
            }
          />
        </Routes>
      </ChainlitProvider>
    </AuthProvider>
  )
}

export default App
