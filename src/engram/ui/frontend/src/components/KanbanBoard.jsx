import { useState } from 'react'

export default function KanbanBoard({ tasks, onTaskUpdated }) {
  const [dragging, setDragging] = useState(null)

  const columns = [
    { id: 'todo', title: 'To Do' },
    { id: 'in-progress', title: 'In Progress' },
    { id: 'blocked', title: 'Blocked' },
    { id: 'done', title: 'Done' }
  ]

  const handleDragStart = (e, task) => {
    setDragging(task)
    e.dataTransfer.effectAllowed = "move"
  }

  const handleDrop = async (e, status) => {
    e.preventDefault()
    if (!dragging || dragging.status === status) return

    // Optimistic update would go here, but let's just make the API call for simplicity
    try {
      const res = await fetch(`/api/tasks/${dragging.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      })
      if (res.ok) {
        onTaskUpdated()
      }
    } catch (err) {
      console.error("Failed to update status", err)
    }
    setDragging(null)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "move"
  }

  return (
    <div className="kanban-board">
      {columns.map(col => (
        <div
          key={col.id}
          className="kanban-col"
          onDragOver={handleDragOver}
          onDrop={(e) => handleDrop(e, col.id)}
        >
          <div className="kanban-col-header">
            {col.title}
            <span>{tasks.filter(t => t.status === col.id).length}</span>
          </div>
          <div className="kanban-cards">
            {tasks.filter(t => t.status === col.id).map(task => (
              <div
                key={task.id}
                className="task-card"
                draggable
                onDragStart={(e) => handleDragStart(e, task)}
              >
                <div className="task-id">#{task.id}</div>
                <div className="task-title">{task.title}</div>
                {task.tags && task.tags.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {task.tags.map(tag => (
                      <span key={tag} className="tag">{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
