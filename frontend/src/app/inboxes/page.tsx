'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Inbox {
  id: string
  email: string
  display_name: string
  domain: string
  daily_limit: number
  health: string
  created_at: string
}

export default function InboxesPage() {
  const [inboxes, setInboxes] = useState<Inbox[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)

  // Form state
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [domain, setDomain] = useState('')

  useEffect(() => {
    fetchInboxes()
  }, [])

  const fetchInboxes = async () => {
    try {
      const res = await fetch(`${API}/api/inboxes/`)
      if (res.ok) {
        const data = await res.json()
        setInboxes(data)
      }
    } catch (e) {
      console.error("Failed to fetch inboxes:", e)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateAndConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      // 1. Create the Inbox record in DB
      const res = await fetch(`${API}/api/inboxes/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          display_name: displayName,
          domain,
          daily_limit: 40 // Default warmup
        })
      })

      if (!res.ok) throw new Error('Failed to create inbox')
      
      const newInbox = await res.json()

      // 2. Redirect to Google OAuth
      window.location.href = `${API}/auth/google/authorize?inbox_id=${newInbox.id}`
      
    } catch (e) {
      alert("Error adding inbox. Is the backend running?")
    }
  }

  const handleDelete = async (inboxId: string) => {
    if (!confirm('Are you sure you want to delete this inbox?')) return
    try {
      const res = await fetch(`${API}/api/inboxes/${inboxId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      setInboxes(prev => prev.filter(ibx => ibx.id !== inboxId))
    } catch (e) {
      alert("Error deleting inbox")
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'white', margin: 0 }}>Sending Inboxes</h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>
            Connect Gmail Workspace accounts to send emails
          </p>
        </div>
        <button 
          className="btn btn-primary"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          {showAddForm ? 'Cancel' : '+ Connect Gmail'}
        </button>
      </div>

      {showAddForm && (
        <div className="card glow-indigo" style={{ marginBottom: 24, maxWidth: 600 }}>
          <h2 style={{ fontSize: 16, color: 'white', marginBottom: 16 }}>Register New Inbox</h2>
          <form onSubmit={handleCreateAndConnect}>
            <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>Email Address</label>
                <input 
                  type="email" 
                  className="input" 
                  placeholder="name@company.com" 
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required 
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>Sender Name</label>
                <input 
                  type="text" 
                  className="input" 
                  placeholder="Nikshay from Cortexa" 
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  required 
                />
              </div>
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>Domain</label>
              <input 
                type="text" 
                className="input" 
                placeholder="company.com" 
                value={domain}
                onChange={e => setDomain(e.target.value)}
                required 
              />
            </div>
            
            <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
              <span style={{ fontSize: 16 }}>G</span> Continue to Google OAuth
            </button>
            <p style={{ fontSize: 11, color: 'var(--text-secondary)', textAlign: 'center', marginTop: 12 }}>
              You will be redirected to Google to grant Gmail sending permissions.
            </p>
          </form>
        </div>
      )}

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Account</th>
              <th>Domain</th>
              <th>Status</th>
              <th>Daily Limit</th>
              <th>Added</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading...</td></tr>
            ) : inboxes.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)' }}>
                  No inboxes connected yet. Click "Connect Gmail" to add one.
                </td>
              </tr>
            ) : inboxes.map(inbox => (
              <tr key={inbox.id}>
                <td>
                  <div style={{ fontWeight: 600, color: 'white', fontSize: 13 }}>{inbox.display_name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{inbox.email}</div>
                </td>
                <td style={{ fontFamily: 'monospace' }}>{inbox.domain}</td>
                <td>
                  <span className={`badge badge-${inbox.health.toLowerCase()}`}>
                    {inbox.health === 'GOOD' ? '🟢' : inbox.health === 'PAUSED' ? '🟡' : '🔴'} {inbox.health}
                  </span>
                </td>
                <td>{inbox.daily_limit} / day</td>
                <td style={{ fontSize: 11 }}>{new Date(inbox.created_at).toLocaleDateString()}</td>
                <td style={{ textAlign: 'right' }}>
                  <button 
                    onClick={() => handleDelete(inbox.id)}
                    style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px 8px', borderRadius: 4 }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
