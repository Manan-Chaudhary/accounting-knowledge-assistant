import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'

// One shared sidebar for Home/Documents/Testing, replacing the copy-pasted
// markup in each Jinja template (templates/index.html, upload.html,
// testing.html all duplicated this by hand).
export function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    if (!window.confirm('Are you sure you want to log out?')) return

    try {
      await logout()
      navigate('/login')
    } catch (error) {
      console.error('Logout failed', error)
    }
  }

  const navItemClass = ({ isActive }: { isActive: boolean }) =>
    `sidebar-item${isActive ? ' active' : ''}`

  return (
    <aside className="sidebar">
      <div className="logo">Accounting Digital Assistant</div>

      <div className="sidebar-section">
        <div className="sidebar-title">TEAM 83 · RMIT CAPSTONE</div>
        <Link to="/assistant" className="new-chat-btn">
          <i className="fas fa-plus" /> New Chat
        </Link>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-title">Recent Conversations</div>
        <div className="sidebar-item">
          <i className="far fa-file-alt" /> Prepaid expenses
        </div>
        <div className="sidebar-item">
          <i className="far fa-file-alt" /> Revenue recognition
        </div>
        <div className="sidebar-item">
          <i className="far fa-file-alt" /> Monthly close checklist
        </div>
      </div>

      <div className="sidebar-section">
        <NavLink to="/home" className={navItemClass}>
          <i className="fas fa-home" /> Home
        </NavLink>

        <NavLink to="/documents" className={navItemClass}>
          <i className="far fa-file-pdf" /> Documents
        </NavLink>

        {user?.role === 'team' && (
          <NavLink to="/testing" className={navItemClass}>
            <i className="fas fa-flask" /> LLM Testing
          </NavLink>
        )}
      </div>

      <div className="sidebar-footer">
        <div className="settings-btn">
          <i className="fas fa-cog" /> Settings
        </div>

        <div className="user-profile">
          <div className="user-info">
            <span className="user-name">
              {user?.email ?? 'Not signed in'}
            </span>

            <span className="user-role">
              {user?.role ?? ''}
            </span>
          </div>

          <a
            href="#"
            className="logout-btn"
            onClick={(e) => {
              e.preventDefault()
              void handleSignOut()
            }}
          >
            Sign out
          </a>
        </div>

        <div className="version-text">
          v0.2 · Week 2 wireframes
        </div>
      </div>
    </aside>
  )
}