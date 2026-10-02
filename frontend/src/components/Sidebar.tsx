import { useEffect, useState, type MouseEvent } from 'react'
import { NavLink, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'

interface ThreadItem {
  id: string
  name: string
  createdAt: string | null
}

export function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const currentThreadId = searchParams.get('threadId')
  const [threads, setThreads] = useState<ThreadItem[]>([])

  useEffect(() => {
    fetch('/api/chat/threads', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : []))
      .then((data: ThreadItem[]) => setThreads(data))
      .catch((err) => console.error('Error fetching threads:', err))
  }, [currentThreadId])

  const handleDeleteThread = async (e: MouseEvent, threadId: string) => {
    e.stopPropagation() // Prevent triggering conversation navigation

    if (!window.confirm('Are you sure you want to delete this conversation?')) {
      return
    }

    try {
      const res = await fetch(`/api/chat/threads/${threadId}`, {
        method: 'DELETE',
        credentials: 'include',
      })

      if (res.ok) {
        setThreads((prev) => prev.filter((t) => t.id !== threadId))
        // If current open thread is deleted, redirect to empty assistant page
        if (currentThreadId === threadId) {
          window.location.href = '/assistant'
        }
      } else {
        alert('Failed to delete conversation.')
      }
    } catch (err) {
      console.error('Delete conversation error:', err)
      alert('Error occurred while deleting conversation.')
    }
  }

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
        <a
          href="/assistant"
          className="new-chat-btn"
          onClick={(e) => {
            e.preventDefault()
            window.location.href = '/assistant'
          }}
        >
          <i className="fas fa-plus" /> New Chat
        </a>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-title">Recent Conversations</div>
        {threads.length === 0 ? (
          <div className="sidebar-item" style={{ color: '#888', fontSize: '0.85rem' }}>
            No past sessions yet
          </div>
        ) : (
          threads.map((t) => {
            const isSelected = currentThreadId === t.id
            return (
              <div
                key={t.id}
                className={`sidebar-item${isSelected ? ' active' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  paddingRight: '8px',
                }}
                onClick={() => {
                  window.location.href = `/assistant?threadId=${t.id}`
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={t.name}
                >
                  <i className="far fa-file-alt" style={{ marginRight: '8px', flexShrink: 0 }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {t.name}
                  </span>
                </div>

                <button
                  type="button"
                  title="Delete conversation"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#999',
                    cursor: 'pointer',
                    padding: '2px 4px',
                    marginLeft: '6px',
                    flexShrink: 0,
                  }}
                  onClick={(e) => handleDeleteThread(e, t.id)}
                >
                  <i className="fas fa-trash-alt" />
                </button>
              </div>
            )
          })
        )}
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
            <span className="user-name">{user?.email ?? 'Not signed in'}</span>
            <span className="user-role">{user?.role ?? ''}</span>
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

        <div className="version-text">v0.2 · Week 2 wireframes</div>
      </div>
    </aside>
  )
}