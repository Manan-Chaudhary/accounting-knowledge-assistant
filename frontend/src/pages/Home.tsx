import { Link } from 'react-router-dom'
import { Layout } from '../components/Layout'

// Port of templates/index.html — static content, no fetches (the original
// passes no template context either).
export function Home() {
  return (
    <Layout badge="INTERNAL · SPRINT 1 W2">
      <div className="welcome-section">
        <h1 className="welcome-title">Accounting Knowledge Assistant</h1>
        <p className="welcome-subtitle">
          Access trusted accounting information, internal documents and AI-powered tools.
        </p>
        <h2 style={{ fontSize: 20, marginBottom: 8 }}>Welcome back</h2>
        <p style={{ color: '#6b7280', fontSize: 14, marginBottom: 24 }}>What would you like to do?</p>
      </div>

      <div className="cards-grid">
        <div className="card">
          <div className="card-icon"><i className="fas fa-robot" /></div>
          <div className="card-title">AI Assistant</div>
          <div className="card-desc">
            Ask accounting questions and receive answers grounded in the internal knowledge base.
          </div>
          <Link to="/assistant" className="card-btn">Open Chat</Link>
        </div>

        <div className="card">
          <div className="card-icon"><i className="far fa-file-alt" /></div>
          <div className="card-title">Documents</div>
          <div className="card-desc">Access and manage documents used by the accounting knowledge base.</div>
          <div style={{ marginBottom: 12 }}>
            <span className="status-badge uploaded" style={{ background: '#f3f4f6', color: '#374151' }}>
              Admin management
            </span>
          </div>
          <Link to="/docs" className="card-btn">View Documents</Link>
        </div>

        <div className="card">
          <div className="card-icon"><i className="fas fa-flask" /></div>
          <div className="card-title">LLM Testing & Evaluation</div>
          <div className="card-desc">Test, evaluate and compare candidate language models.</div>
          <div style={{ marginBottom: 12 }}>
            <span className="status-badge uploaded" style={{ background: '#f3f4f6', color: '#374151' }}>
              Project team
            </span>
          </div>
          <Link to="/testing" className="card-btn">Open Testing</Link>
        </div>
      </div>

      <div className="info-banner">
        <div className="banner-text">
          <h3>Trusted internal knowledge</h3>
          <p>All responses are grounded in approved documents and should display traceable source citations.</p>
        </div>
        <div className="banner-arrow"><i className="fas fa-arrow-right" /></div>
      </div>
    </Layout>
  )
}
