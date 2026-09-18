import { Layout } from '../components/Layout'

// Port of templates/testing.html — static mockup only, per the locked-in
// decision for this ticket. No backend logic exists for this page today
// (no <script>, unpopulated selects, dead buttons) and this reproduces that
// exact state. Real test-run/evaluation logic is a separate, unscoped task
// (docs/TESTING-PAGE-REQUIREMENTS.md).
export function Testing() {
  return (
    <Layout badge="INTERNAL">
      <div className="page-header">
        <h1 className="welcome-title">LLM Testing & Evaluation</h1>
        <p className="welcome-subtitle">
          Compare model responses against predefined accounting test cases and evaluation criteria.
        </p>
      </div>

      <div className="test-case-card">
        <div className="test-header-actions">
          <div className="test-card-label">TEST CASE</div>
          <button className="btn-primary">Run Test</button>
        </div>

        <div className="test-case-header">
          <div className="test-case-id">TC-001</div>
          <div className="test-case-tag">Income tax</div>
          <div className="test-case-tag gray">FY 2025-26</div>
        </div>

        <div className="test-inputs-grid">
          <div className="field-group">
            <label>Prompt / Question</label>
            <textarea placeholder="What is the correct treatment for [example accounting scenario]?" />
          </div>
          <div className="field-group">
            <label>Expected Answer / Behaviour</label>
            <textarea placeholder="Known correct result / expected behaviour" />
          </div>
          <div className="field-group">
            <label>Model A</label>
            <select><option>Select Model ▼</option></select>
          </div>
          <div className="field-group">
            <label>Model B</label>
            <select><option>Select Model ▼</option></select>
          </div>
        </div>
      </div>

      <div className="model-compare-grid">
        <div className="model-card">
          <div className="model-card-header">
            <div>
              <div className="model-name">Model A</div>
              <div className="model-subtitle">Candidate Model A</div>
            </div>
            <div className="model-status-badge">Answer Returned</div>
          </div>
          <div className="model-card-body">
            <div className="field-group" style={{ marginBottom: 16 }}>
              <label>Generated answer</label>
              <div className="answer-box">Generated accounting answer with concise rationale...</div>
            </div>
            <div className="model-meta">
              Sources: [1] Internal Accounting Policy.pdf · [2] Tax Guidance.pdf<br />
              Latency: 1.8 sec · Est. cost: $0.00XX
            </div>
          </div>
        </div>

        <div className="model-card">
          <div className="model-card-header">
            <div>
              <div className="model-name">Model B</div>
              <div className="model-subtitle">Candidate Model B</div>
            </div>
            <div className="model-status-badge no-source">No Source</div>
          </div>
          <div className="model-card-body">
            <div className="field-group" style={{ marginBottom: 16 }}>
              <label>Generated answer</label>
              <div className="answer-box">Response returned without a verifiable retrieved source...</div>
            </div>
            <div className="model-meta">
              Sources: [1] Internal Accounting Policy.pdf · [2] Tax Guidance.pdf<br />
              Latency: 1.8 sec · Est. cost: $0.00XX
            </div>
          </div>
        </div>
      </div>

      <div className="metrics-section">
        <div className="metrics-title">EVALUATION METRICS · 15 TOTAL</div>
        <table className="metrics-table">
          <thead>
            <tr>
              <th>Evaluation Metric</th>
              <th>Model A</th>
              <th>Model B</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Metric 01</td>
              <td><input type="text" className="metric-input" placeholder="Score / evaluation input" /></td>
              <td><input type="text" className="metric-input" placeholder="Score / evaluation input" /></td>
            </tr>
            <tr>
              <td>Metric 02</td>
              <td><input type="text" className="metric-input" placeholder="Score / evaluation input" /></td>
              <td><input type="text" className="metric-input" placeholder="Score / evaluation input" /></td>
            </tr>
            <tr>
              <td>Temporal Precision</td>
              <td><input type="text" className="metric-input" placeholder="Calculated precision" /></td>
              <td><input type="text" className="metric-input" placeholder="Calculated precision" /></td>
            </tr>
            <tr>
              <td>Citation Support</td>
              <td><input type="text" className="metric-input" placeholder="[1] Supported ▼ / [2] Unsupported ▼" /></td>
              <td><input type="text" className="metric-input" placeholder="[1] Supported ▼ / [2] Unsupported ▼" /></td>
            </tr>
            <tr>
              <td>Refusal Recall</td>
              <td><input type="text" className="metric-input" placeholder="Input / score" /></td>
              <td><input type="text" className="metric-input" placeholder="Input / score" /></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="review-section">
        <h3>Reviewer Notes</h3>
        <textarea placeholder="Add observations about model accuracy, grounding, citations or behaviour..." />

        <div className="action-buttons">
          <button className="btn-secondary">Clear Test</button>
          <button className="btn-secondary">Run Again</button>
          <button className="btn-primary">Save Evaluation</button>
        </div>
      </div>
    </Layout>
  )
}
