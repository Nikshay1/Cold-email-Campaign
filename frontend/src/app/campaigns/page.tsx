'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Campaign {
  id: string
  name: string
  status: string
  total_leads: number
  sent_count: number
  reply_count: number
  created_at: string
}

interface Inbox {
  id: string
  email: string
  health: string
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [inboxes, setInboxes] = useState<Inbox[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    name: '', 
    description: '', 
    subject: '', 
    body_template: '', 
    selected_inbox_ids: [] as string[]
  })
  const [launching, setLaunching] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      const r = await fetch(`${API}/api/campaigns/`)
      setCampaigns(await r.json())
      
      const i = await fetch(`${API}/api/inboxes/`)
      setInboxes(await i.json())
    } catch {
      console.error('Failed to fetch dashboard data')
    }
  }

  useEffect(() => { 
    fetchData() 
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const createCampaign = async () => {
    if (form.selected_inbox_ids.length === 0) {
      alert("Please select at least one Sender Email ID.");
      return;
    }
    try {
      const r = await fetch(`${API}/api/campaigns`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(form) 
      })
      if (r.ok) { 
        setShowCreate(false)
        fetchData() 
      } else {
        alert('Failed to create campaign')
      }
    } catch { 
      alert('Failed to create campaign') 
    }
  }

  const launchCampaign = async (id: string) => {
    setLaunching(id)
    try {
      const r = await fetch(`${API}/api/campaigns/${id}/launch`, { method: 'POST' })
      if (!r.ok) alert('No eligible leads to launch, or missing inboxes.');
      await fetchData()
    } catch { alert('Launch failed') } finally { setLaunching(null) }
  }

  const toggleInbox = (id: string) => {
    setForm(p => ({
      ...p,
      selected_inbox_ids: p.selected_inbox_ids.includes(id) 
        ? p.selected_inbox_ids.filter(x => x !== id)
        : [...p.selected_inbox_ids, id]
    }))
  }

  const statusColor = (s: string) => ({ active: '#4ade80', draft: '#818cf8', paused: '#facc15', completed: '#a1a1aa' }[s] || '#a1a1aa')

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'white', margin: 0 }}>Campaigns</h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>Launch and distribute templated sequences</p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn btn-secondary" onClick={() => window.open(`${API}/api/campaigns/follow-up-csv`)}>
            📥 Download Follow-Ups CSV
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Campaign</button>
        </div>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="card" style={{ width: 520, maxHeight: '85vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: 'white', margin: 0 }}>New Template Campaign</h2>
              <button className="btn btn-secondary" style={{ padding: '4px 10px' }} onClick={() => setShowCreate(false)}>✕</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Campaign Name *</label>
                <input className="input" placeholder="e.g., VC Outreach 2026" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
              </div>

              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Sender Email IDs *
                </label>
                <div style={{ background: '#1f1f23', padding: 12, borderRadius: 6, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {inboxes.length === 0 ? (
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>No inboxes connected yet. Go to Inboxes tab first.</span>
                  ) : inboxes.map(i => (
                    <label key={i.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'white', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={form.selected_inbox_ids.includes(i.id)} 
                        onChange={() => toggleInbox(i.id)} 
                      />
                      {i.email}
                      {i.health !== 'GOOD' && <span style={{ color: 'red', fontSize: 11 }}>(Needs Action)</span>}
                    </label>
                  ))}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>
                  Emails will be distributed round-robin evenly across these checked accounts.
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Subject Line *</label>
                <input className="input" placeholder="Action Required: [NAME] - Follow up" value={form.subject} onChange={e => setForm(p => ({ ...p, subject: e.target.value }))} />
              </div>

              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Email Body *</label>
                <textarea 
                  className="input" 
                  rows={6} 
                  placeholder="Hi [NAME],\n\nI noticed [COMPANY] is expanding...\n\nThanks,\nCortexa Team" 
                  value={form.body_template} 
                  onChange={e => setForm(p => ({ ...p, body_template: e.target.value }))} 
                />
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>
                  Available Placeholders: <code style={{color:'#818cf8'}}>[NAME]</code>, <code style={{color:'#818cf8'}}>[FIRST_NAME]</code>, <code style={{color:'#818cf8'}}>[LAST_NAME]</code>, <code style={{color:'#818cf8'}}>[COMPANY]</code>, <code style={{color:'#818cf8'}}>[TITLE]</code>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button className="btn btn-primary" style={{ flex: 1 }} onClick={createCampaign} disabled={!form.name || !form.subject || !form.body_template}>
                  Create Campaign
                </button>
                <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Campaign cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {campaigns.map(c => (
          <div key={c.id} className="card">
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: 'white' }}>{c.name}</span>
                  <span style={{ fontSize: 11, padding: '2px 7px', borderRadius: 999, background: `${statusColor(c.status)}20`, color: statusColor(c.status), fontWeight: 600 }}>
                    {c.status.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                  Templated Blast · Created {new Date(c.created_at).toLocaleDateString('en-IN')}
                </div>
                {/* Stats row */}
                <div style={{ display: 'flex', gap: 24 }}>
                  {[
                    { label: 'Total Leads', value: c.total_leads },
                    { label: 'Sent Safely', value: c.sent_count },
                    { label: 'Replies', value: c.reply_count },
                  ].map(s => (
                    <div key={s.label}>
                      <div style={{ fontSize: 16, fontWeight: 700, color: 'white' }}>{s.value}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, marginLeft: 16 }}>
                {c.status === 'draft' && (
                  <button
                    className="btn btn-primary"
                    onClick={() => launchCampaign(c.id)}
                    disabled={launching === c.id}
                    style={{ fontSize: 12 }}
                  >
                    {launching === c.id ? '⏳ Distributing...' : '🚀 Launch Sequence'}
                  </button>
                )}
                {c.status === 'active' && (
                  <button className="btn btn-secondary" style={{ fontSize: 12 }} onClick={async () => {
                    await fetch(`${API}/api/campaigns/${c.id}/pause`, { method: 'PATCH' })
                    fetchData()
                  }}>⏸ Pause</button>
                )}
              </div>
            </div>
          </div>
        ))}
        {campaigns.length === 0 && (
          <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🚀</div>
            <div style={{ color: 'white', fontWeight: 600, marginBottom: 6 }}>No campaigns yet</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 16 }}>Create your first campaign to distribute standard emails.</div>
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ Create Campaign</button>
          </div>
        )}
      </div>
    </div>
  )
}
