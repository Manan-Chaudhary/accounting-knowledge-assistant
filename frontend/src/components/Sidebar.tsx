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

  // --- 重命名功能逻辑 ---
  const handleRenameThread = async (e: MouseEvent, threadId: string, currentName: string) => {
    e.stopPropagation() // 阻止点击触发会话跳转

    const newName = window.prompt('Enter new conversation title (max 50 chars):', currentName)
    if (newName === null) {
      return // 用户点击了取消
    }

    const trimmed = newName.trim()
    // 校验 1：不能为空
    if (!trimmed) {
      alert('Conversation title cannot be empty.')
      return
    }

    // 校验 2：不能超过 50 个字符
    if (trimmed.length > 50) {
      alert(`Conversation title cannot exceed 50 characters. (Current: ${trimmed.length})`)
      return
    }

    try {
      const res = await fetch(`/api/chat/threads/${threadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: trimmed }),
      })

      if (res.ok) {
        // 即时更新本地列表显示，无需重新拉取
        setThreads((prev) =>
          prev.map((t) => (t.id === threadId ? { ...t, name: trimmed } : t))
        )
      } else {
        const errorData = await res.json().catch(() => ({}))
        alert(errorData.detail || 'Failed to rename conversation.')
      }
    } catch (err) {
      console.error('Rename error:', err)
      alert('Network error occurred while renaming conversation.')
    }
  }

  // --- 删除功能逻辑 ---
  const handleDeleteThread = async (e: MouseEvent, threadId: string) => {
    e.stopPropagation()

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
                    flex: 1,
                    minWidth: 0,
                    marginRight: '6px',
                  }}
                  title={t.name}
                >
                  <i className="far fa-file-alt" style={{ marginRight: '8px', flexShrink: 0 }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {t.name}
                  </span>
                </div>

                {/* 操作按钮区：编辑 + 删除 */}
                <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0, gap: '4px' }}>
                  <button
                    type="button"
                    title="Rename conversation"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#999',
                      cursor: 'pointer',
                      padding: '2px 4px',
                    }}
                    onClick={(e) => handleRenameThread(e, t.id, t.name)}
                  >
                    <i className="fas fa-edit" />
                  </button>

                  <button
                    type="button"
                    title="Delete conversation"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#999',
                      cursor: 'pointer',
                      padding: '2px 4px',
                    }}
                    onClick={(e) => handleDeleteThread(e, t.id)}
                  >
                    <i className="fas fa-trash-alt" />
                  </button>
                </div>
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