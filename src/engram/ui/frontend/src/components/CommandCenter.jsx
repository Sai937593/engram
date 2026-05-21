import { useEffect, useState } from 'react'
import KanbanBoard from './KanbanBoard'
import ActivityFeed from './ActivityFeed'

export default function CommandCenter({ projectId }) {
  const [tasks, setTasks] = useState([])
  const [memories, setMemories] = useState([])

  const refreshData = () => {
    fetch('/api/tasks')
      .then(res => res.json())
      .then(data => setTasks(data.tasks))

    fetch('/api/memories')
      .then(res => res.json())
      .then(data => setMemories(data.memories))
  }

  useEffect(() => {
    refreshData()
    // Poll for changes
    const interval = setInterval(refreshData, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="command-center">
      <div className="section">
        <div className="section-header">Knowledge Base</div>
        <div className="section-content" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {memories.slice(0, 10).map(m => (
            <div key={m.id} style={{ fontSize: '0.9rem' }}>
              <div className="memory-type">{m.type}</div>
              <div style={{ fontWeight: 500 }}>{m.title}</div>
            </div>
          ))}
          {memories.length === 0 && <div style={{ color: 'var(--text-muted)' }}>No memories found.</div>}
        </div>
      </div>

      <div className="section" style={{ overflow: 'hidden' }}>
        <div className="section-header">Tasks</div>
        <div className="section-content" style={{ padding: 0 }}>
          <KanbanBoard tasks={tasks} onTaskUpdated={refreshData} />
        </div>
      </div>

      <div className="section">
        <div className="section-header">Activity Feed</div>
        <div className="section-content">
          <ActivityFeed />
        </div>
      </div>
    </div>
  )
}
