import { type DragEvent, useEffect, useRef, useState } from 'react'
import { Layout } from '../components/Layout'

// Port of templates/upload.html — same endpoints (POST /upload, GET
// /documents), same drag-drop + client-side search behaviour, now as React
// state instead of direct DOM manipulation.
interface Document {
  id: number
  filename: string
  source_label?: string
  status?: string
  uploaded_at?: string
}

export function Documents() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [query, setQuery] = useState('')
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchDocuments = async () => {
    try {
      const response = await fetch('/documents')
      if (!response.ok) throw new Error('Failed to retrieve documents')
      const data = await response.json()
      setDocuments(data.documents || [])
      setLoadError(null)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load documents')
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [])

  const uploadFile = async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    try {
      const response = await fetch('/upload', { method: 'POST', body: formData })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }
      if (fileInputRef.current) fileInputRef.current.value = ''
      await fetchDocuments()
    } catch (err) {
      window.alert('Upload error: ' + (err instanceof Error ? err.message : String(err)))
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragOver(false)
    if (event.dataTransfer.files.length > 0) {
      uploadFile(event.dataTransfer.files[0])
    }
  }

  const filtered = documents.filter((doc) => {
    const q = query.toLowerCase().trim()
    if (!q) return true
    return (
      doc.filename?.toLowerCase().includes(q) ||
      doc.source_label?.toLowerCase().includes(q)
    )
  })

  return (
    <Layout badge="Capstone Prototype">
      <h1 className="page-title">Documents</h1>
      <p className="page-subtitle">Upload documents for use within the system.</p>

      <div
        className="upload-zone"
        style={dragOver ? { borderColor: '#2563eb' } : undefined}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={(e) => {
          e.preventDefault()
          setDragOver(false)
        }}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: 'none' }}
          accept=".pdf,.docx,.txt"
          onChange={(e) => {
            if (e.target.files?.length) uploadFile(e.target.files[0])
          }}
        />
        <div className="upload-icon"><i className="fas fa-cloud-upload-alt" /></div>
        <div className="upload-title">Drag and drop files here</div>
        <div className="upload-desc">or select files from your computer</div>
        <button
          className="browse-btn"
          type="button"
          disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? 'Uploading...' : 'Browse Files'}
        </button>
        <div className="file-types">Supported file types: PDF · DOCX · TXT</div>
      </div>

      <div className="list-header">
        <h2 className="list-title">Uploaded Documents</h2>
        <div className="search-box">
          <i className="fas fa-search search-icon" />
          <input
            type="text"
            placeholder="Search documents"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>FILE NAME</th>
              <th>TYPE</th>
              <th>UPLOAD DATE</th>
              <th>STATUS</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loadError && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: '#e11d48', padding: 20 }}>
                  Failed to load documents: {loadError}
                </td>
              </tr>
            )}
            {!loadError && filtered.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: 24, color: '#888' }}>
                  No documents found.
                </td>
              </tr>
            )}
            {!loadError &&
              filtered.map((doc) => {
                const ext = doc.filename ? doc.filename.split('.').pop()!.toUpperCase() : 'FILE'
                const dateStr = doc.uploaded_at
                  ? new Date(doc.uploaded_at).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })
                  : '-'
                const status = (doc.status || 'pending').toLowerCase()
                const iconClass = ext === 'DOCX' ? 'docx' : ''

                return (
                  <tr key={doc.id}>
                    <td>
                      <div className="file-info">
                        <div className={`file-icon ${iconClass}`}>{ext}</div>
                        <div>
                          <div className="file-name">{doc.filename}</div>
                          <span className="file-sub">{doc.source_label || 'Uploaded document'}</span>
                        </div>
                      </div>
                    </td>
                    <td>{ext}</td>
                    <td>{dateStr}</td>
                    <td><span className={`status-badge ${status}`}>{doc.status || 'pending'}</span></td>
                    <td><button className="action-btn"><i className="fas fa-ellipsis-h" /></button></td>
                  </tr>
                )
              })}
          </tbody>
        </table>
      </div>
    </Layout>
  )
}
