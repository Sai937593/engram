import { useEffect, useState } from 'react'

export default function ActivityFeed() {
  const [events, setEvents] = useState([])

  const fetchAudit = () => {
    fetch('/api/audit')
      .then(res => res.json())
      .then(data => setEvents(data.audit_events))
  }

  useEffect(() => {
    fetchAudit()
    const interval = setInterval(fetchAudit, 3000)
    return () => clearInterval(interval)
  }, [])

  if (events.length === 0) {
    return <div style={{ color: 'var(--text-muted)' }}>No recent activity.</div>
  }

  return (
    <div>
      {events.map((ev, i) => (
        <div key={i} className="activity-item">
          <div className="activity-meta">
            <span>{new Date(ev.timestamp).toLocaleTimeString()}</span>
            <span style={{ textTransform: 'uppercase', fontSize: '0.7rem', fontWeight: 600 }}>{ev.target_table}</span>
          </div>
          <div className="activity-title">
            {ev.operation === 'create' && `Created ${ev.target_table.slice(0,-1)} #${ev.target_id}`}
            {ev.operation === 'update' && `Updated ${ev.field} to "${ev.new_value}" on #${ev.target_id}`}
            {ev.operation === 'delete' && `Deleted ${ev.target_table.slice(0,-1)} #${ev.target_id}`}
          </div>
        </div>
      ))}
    </div>
  )
}
