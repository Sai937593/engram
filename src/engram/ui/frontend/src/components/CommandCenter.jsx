import { useEffect, useState } from 'react'
import KanbanBoard from './KanbanBoard'
import ActivityFeed from './ActivityFeed'

export default function CommandCenter({ projectId }) {
  const [tasks, setTasks] = useState([])
  const [memories, setMemories] = useState([])

  const refreshData = () => {
    fetch('/api/tasks')
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch tasks")
        return res.json()
      })
      .then(data => {
        setTasks(Array.isArray(data.tasks) ? data.tasks : [])
      })
      .catch(err => {
        console.error("Could not fetch tasks:", err)
        setTasks([])
      })

    fetch('/api/memories')
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch memories")
        return res.json()
      })
      .then(data => {
        setMemories(Array.isArray(data.memories) ? data.memories : [])
      })
      .catch(err => {
        console.error("Could not fetch memories:", err)
        setMemories([])
      })
  }

  useEffect(() => {
    refreshData()
    // Poll for changes
    const interval = setInterval(refreshData, 3000)
    return () => clearInterval(interval)
  }, [])

  const safeMemories = Array.isArray(memories) ? memories : []

  return (
    <div className="command-center">
      <div className="section">
        <div className="section-header">Knowledge Base</div>
        <div className="section-content" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {safeMemories.slice(0, 10).map(m => (
            <div key={m.id} style={{ fontSize: '0.9rem' }}>
              <div className="memory-type">{m.type}</div>
              <div style={{ fontWeight: 500 }}>{m.title}</div>
            </div>
          ))}
          {safeMemories.length === 0 && <div style={{ color: 'var(--text-muted)' }}>No memories found.</div>}
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
