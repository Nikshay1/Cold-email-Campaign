'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Campaign {
  id: string
  name: string
  status: string
  sequence_type: string
  is_vc_campaign: boolean
  total_leads: number
  sent_count: number
  reply_count: number
  created_at: string
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    name: '', description: '', sequence_type: 'tier1',
    is_vc_campaign: true, value_proposition: '', pain_point: '',
  })
  const [launching, setLaunching] = useState<string | null>(null)

  const fetchCampaigns = async () => {
    try {
      const r = await fetch(`${API}/api/campaigns`)
      setCampaigns(await r.json())
    } catch {
      setCampaigns([
        { id: '1', name: 'India VC Pitch — Seed Round', status: 'active', sequence_type: 'tier1', is_vc_campaign: true, total_leads: 45, sent_count: 32, reply_count: 5, created_at: new Date().toISOString() },
        { id: '2', name: 'Series A VCs Outreach', status: 'draft', sequence_type: 'tier2', is_vc_campaign: true, total_leads: 72, sent_count: 0, reply_count: 0, created_at: new Date().toISOString() },
      ])
    }
  }

  useEffect(() => { fetchCampaigns() }, [])

  const createCampaign = async () => {
    try {
      const r = await fetch(`${API}/api/campaigns`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      if (r.ok) { setShowCreate(false); fetchCampaigns() }
    } catch { alert('Failed to create campaign') }
  }

  const launchCampaign = async (id: string) => {
    setLaunching(id)
    try {
      await fetch(`${API}/api/campaigns/${id}/launch`, { method: 'POST' })
      await fetchCampaigns()
    } catch { alert('Launch failed') } finally { setLaunching(null) }
  }

  const statusColor = (s: string) => ({ active: '#4ade80', draft: '#818cf8', paused: '#facc15', completed: '#a1a1aa' }[s] || '#a1a1aa')

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'white', margin: 0 }}>Campaigns</h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>Launch and manage your VC outreach sequences</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Campaign</button>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="card" style={{ width: 480, maxHeight: '80vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: 'white', margin: 0 }}>New Campaign</h2>
              <button className="btn btn-secondary" style={{ padding: '4px 10px' }} onClick={() => setShowCreate(false)}>✕</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Campaign Name *</label>
                <input className="input" placeholder="e.g., India VC Pitch — Seed Round" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Sequence</label>
                <select className="input" value={form.sequence_type} onChange={e => setForm(p => ({ ...p, sequence_type: e.target.value }))}>
                  <option value="tier1">Tier 1 — 5 emails (premium, highly personalized)</option>
                  <option value="tier2">Tier 2 — 3 emails</option>
                  <option value="tier3">Tier 3 — 2 emails</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Value Proposition *</label>
                <textarea className="input" rows={2} placeholder="What does Cortexa do? In 1-2 sentences..." value={form.value_proposition} onChange={e => setForm(p => ({ ...p, value_proposition: e.target.value }))} />
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Pain Point We Solve *</label>
                <textarea className="input" rows={2} placeholder="What problem does your target face?" value={form.pain_point} onChange={e => setForm(p => ({ ...p, pain_point: e.target.value }))} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="checkbox" id="vc" checked={form.is_vc_campaign} onChange={e => setForm(p => ({ ...p, is_vc_campaign: e.target.checked }))} />
                <label htmlFor="vc" style={{ fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  🔥 VC Campaign mode — all replies routed to you personally, no AI auto-response
                </label>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button className="btn btn-primary" style={{ flex: 1 }} onClick={createCampaign} disabled={!form.name || !form.value_proposition}>
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
                  {c.is_vc_campaign && (
                    <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 999, background: 'rgba(99,102,241,0.15)', color: '#818cf8', fontWeight: 600 }}>
                      VC MODE
                    </span>
                  )}
                  <span style={{ fontSize: 11, padding: '2px 7px', borderRadius: 999, background: `${statusColor(c.status)}20`, color: statusColor(c.status), fontWeight: 600 }}>
                    {c.status.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                  {c.sequence_type} sequence · Created {new Date(c.created_at).toLocaleDateString('en-IN')}
                </div>
                {/* Stats row */}
                <div style={{ display: 'flex', gap: 24 }}>
                  {[
                    { label: 'Leads', value: c.total_leads },
                    { label: 'Sent', value: c.sent_count },
                    { label: 'Replies', value: c.reply_count },
                    { label: 'Reply Rate', value: c.sent_count ? `${((c.reply_count / c.sent_count) * 100).toFixed(1)}%` : '—' },
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
                    {launching === c.id ? '⏳ Launching...' : '🚀 Launch'}
                  </button>
                )}
                {c.status === 'active' && (
                  <button className="btn btn-secondary" style={{ fontSize: 12 }} onClick={async () => {
                    await fetch(`${API}/api/campaigns/${c.id}/pause`, { method: 'PATCH' })
                    fetchCampaigns()
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
            <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 16 }}>Create your first campaign to start reaching VCs</div>
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ Create Campaign</button>
          </div>
        )}
      </div>
    </div>
  )
}
