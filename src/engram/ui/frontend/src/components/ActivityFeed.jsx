import { useEffect, useState } from 'react'

export default function ActivityFeed() {
  const [events, setEvents] = useState([])

  const fetchAudit = () => {
    fetch('/api/audit')
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch audit feed")
        return res.json()
      })
      .then(data => {
        setEvents(Array.isArray(data.audit_events) ? data.audit_events : [])
      })
      .catch(err => {
        console.error("Could not fetch audit events:", err)
        setEvents([])
      })
  }

  useEffect(() => {
    fetchAudit()
    const interval = setInterval(fetchAudit, 3000)
    return () => clearInterval(interval)
  }, [])

  const formatTime = (ts) => {
    if (!ts) return ''
    // Convert SQLite standard "YYYY-MM-DD HH:MM:SS" space format to "T" so it is fully compliant in Safari/older browsers
    const isoStr = ts.includes(' ') ? ts.replace(' ', 'T') : ts
    const d = new Date(isoStr)
    return isNaN(d.getTime()) ? ts : d.toLocaleTimeString()
  }

  const safeEvents = Array.isArray(events) ? events : []

  if (safeEvents.length === 0) {
    return <div style={{ color: 'var(--text-muted)' }}>No recent activity.</div>
  }

  return (
    <div>
      {safeEvents.map((ev, i) => {
        if (!ev) return null
        const table = ev.target_table || 'item'
        const label = table.endsWith('s') ? table.slice(0, -1) : table

        return (
          <div key={i} className="activity-item">
            <div className="activity-meta">
              <span>{formatTime(ev.timestamp)}</span>
              <span style={{ textTransform: 'uppercase', fontSize: '0.7rem', fontWeight: 600 }}>{table}</span>
            </div>
            <div className="activity-title">
              {ev.operation === 'create' && `Created ${label} #${ev.target_id || ''}`}
              {ev.operation === 'update' && `Updated ${ev.field || 'field'} to "${ev.new_value || ''}" on #${ev.target_id || ''}`}
              {ev.operation === 'delete' && `Deleted ${label} #${ev.target_id || ''}`}
            </div>
          </div>
        )
      })}
    </div>
  )
}
