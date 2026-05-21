import { useEffect, useState } from 'react'
import CommandCenter from './components/CommandCenter'
import './index.css'

function App() {
  const [uiState, setUiState] = useState(null)

  useEffect(() => {
    fetch('/api/ui-state')
      .then(res => res.json())
      .then(data => setUiState(data))
      .catch(err => console.error("Could not fetch UI state:", err))
  }, [])

  if (!uiState) {
    return <div style={{ padding: 20 }}>Loading Engram Context...</div>
  }

  return (
    <div className="container">
      <header className="header">
        <div>
          <div className="title">Engram Command Center</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Project: <strong>{uiState.project_name}</strong> ({uiState.project_id.slice(0,8)}) &mdash; {uiState.repo_path}
          </div>
        </div>
      </header>
      <CommandCenter projectId={uiState.project_id} />
    </div>
  )
}

export default App
