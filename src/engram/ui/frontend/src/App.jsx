import { useEffect, useState } from 'react'
import CommandCenter from './components/CommandCenter'
import './index.css'

function App() {
  const [uiState, setUiState] = useState(null)

  useEffect(() => {
    fetch('/api/ui-state')
      .then(res => {
        if (!res.ok) {
          throw new Error("Failed to fetch UI state")
        }
        return res.json()
      })
      .then(data => setUiState(data))
      .catch(err => {
        console.error("Could not fetch UI state:", err)
        setUiState({ error: err.message || "Unknown error" })
      })
  }, [])

  if (!uiState) {
    return <div style={{ padding: 20 }}>Loading Engram Context...</div>
  }

  if (uiState.error || uiState.detail) {
    return (
      <div style={{ padding: 20, maxWidth: 600, margin: '40px auto', background: '#2a2222', border: '1px solid #ff5555', borderRadius: 8, color: '#ffaaaa' }}>
        <h3 style={{ marginTop: 0 }}>Error Loading Engram UI</h3>
        <p>{uiState.error || uiState.detail}</p>
        <p style={{ fontSize: '0.9rem', color: '#ffcccc' }}>
          Please make sure the Engram project is initialized and you ran <code>engram ui</code> from a registered repository.
        </p>
      </div>
    )
  }

  const projId = uiState.project_id || ""
  const displayId = projId ? projId.slice(0, 8) : "unknown"

  return (
    <div className="container">
      <header className="header">
        <div>
          <div className="title">Engram Command Center</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Project: <strong>{uiState.project_name || "Unknown"}</strong> ({displayId}) &mdash; {uiState.repo_path || "Unknown"}
          </div>
        </div>
      </header>
      <CommandCenter projectId={projId} />
    </div>
  )
}

export default App
