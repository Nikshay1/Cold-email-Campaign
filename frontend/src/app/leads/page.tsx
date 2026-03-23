'use client'

import { useState, useRef } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function LeadsPage() {
  const [leads, setLeads] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleUpload = async (file: File) => {
    setUploading(true)
    setResult(null)
    const form = new FormData()
    form.append('file', file)
    try {
      const r = await fetch(`${API}/api/leads/upload`, { method: 'POST', body: form })
      const data = await r.json()
      setResult(data)
      fetchLeads()
    } catch {
      setResult({ error: 'Upload failed — check API connection' })
    } finally {
      setUploading(false)
    }
  }

  const fetchLeads = async () => {
    try {
      const r = await fetch(`${API}/api/leads?limit=500`)
      setLeads(await r.json())
    } catch {
      setLeads([
        { id: '1', email: 'rahul@sequoiaindia.com', first_name: 'Rahul', last_name: 'Mehta', title: 'Partner', company_name: 'Sequoia India', icp_score: 92, tier: 'tier1', status: 'new' },
        { id: '2', email: 'priya@accelindia.com', first_name: 'Priya', last_name: 'Nair', title: 'Principal', company_name: 'Accel India', icp_score: 88, tier: 'tier1', status: 'new' },
        { id: '3', email: 'ankit@blume.vc', first_name: 'Ankit', last_name: 'Sharma', title: 'Partner', company_name: 'Blume Ventures', icp_score: 79, tier: 'tier2', status: 'new' },
      ])
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this lead?')) return
    try {
      await fetch(`${API}/api/leads/${id}`, { method: 'DELETE' })
      setLeads(leads.filter(l => l.id !== id))
    } catch {
      alert('Failed to delete lead')
    }
  }

  const handleDeleteAll = async () => {
    if (!confirm('Are you ABSOLUTELY sure you want to delete ALL leads?')) return
    try {
      await fetch(`${API}/api/leads`, { method: 'DELETE' })
      setLeads([])
    } catch {
      alert('Failed to delete all leads')
    }
  }

  if (leads.length === 0 && !uploading) fetchLeads()

  const tierColor = (t: string) => t === 'tier1' ? '#f87171' : t === 'tier2' ? '#facc15' : '#818cf8'

  return (
    <div>
      <div style={{ marginBottom: 28, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'white', margin: 0 }}>Leads</h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>Import and manage your VC prospect list</p>
        </div>
        {leads.length > 0 && (
          <button className="btn btn-secondary" style={{ color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)' }} onClick={handleDeleteAll}>
            🗑️ Delete All
          </button>
        )}
      </div>

      {/* Upload area */}
      <div
        className="card"
        style={{
          marginBottom: 20, textAlign: 'center', padding: '32px 24px',
          border: '2px dashed var(--border)', cursor: 'pointer',
          transition: 'border-color 0.2s',
        }}
        onClick={() => fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); (e.currentTarget as HTMLElement).style.borderColor = '#6366f1' }}
        onDragLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)' }}
        onDrop={e => {
          e.preventDefault()
          const file = e.dataTransfer.files[0]
          if (file?.name.endsWith('.csv')) handleUpload(file)
        }}
      >
        <input ref={fileRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={e => { if (e.target.files?.[0]) handleUpload(e.target.files[0]) }} />
        <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
        <div style={{ fontWeight: 600, color: 'white', fontSize: 14, marginBottom: 4 }}>
          {uploading ? 'Uploading...' : 'Drop CSV file or click to browse'}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Required columns: email, first_name — Optional: title, company_name, funding_stage, linkedin_url
        </div>
      </div>

      {/* Upload result */}
      {result && (
        <div className="card" style={{ marginBottom: 16, borderColor: result.error ? '#ef4444' : '#22c55e' }}>
          {result.error ? (
            <div style={{ color: '#f87171', fontSize: 13 }}>❌ {result.error}</div>
          ) : (
            <>
              <div style={{ fontSize: 13 }}>
                <span style={{ color: '#4ade80', fontWeight: 600 }}>✅ {result.imported} imported</span>
                <span style={{ color: 'var(--text-secondary)', marginLeft: 12 }}>⏭ {result.skipped} skipped (duplicates)</span>
                {result.errors?.length > 0 && (
                  <span style={{ color: '#facc15', marginLeft: 12 }}>⚠️ {result.errors.length} errors</span>
                )}
              </div>
              {result.errors?.length > 0 && (
                <details style={{ marginTop: 8 }}>
                  <summary style={{ fontSize: 12, color: '#facc15', cursor: 'pointer' }}>Show error details</summary>
                  <div style={{ marginTop: 6, maxHeight: 200, overflowY: 'auto' }}>
                    {result.errors.map((e: string, i: number) => (
                      <div key={i} style={{ fontSize: 11, color: '#f87171', fontFamily: 'monospace', marginBottom: 2 }}>{e}</div>
                    ))}
                  </div>
                </details>
              )}
            </>
        </div>
      )}

      {/* Leads table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'white' }}>{leads.length} leads</span>
        </div>
        <table className="data-table">
          <thead>
            <tr><th>Name</th><th>Email</th><th>Title</th><th>Company</th><th>ICP Score</th><th>Tier</th><th>Status</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {leads.map(l => (
              <tr key={l.id}>
                <td style={{ fontWeight: 500, color: 'white' }}>{l.full_name || `${l.first_name || ''} ${l.last_name || ''}`.trim() || '—'}</td>
                <td style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-secondary)' }}>{l.email}</td>
                <td style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{l.title || '—'}</td>
                <td style={{ fontSize: 12 }}>{l.company_name || '—'}</td>
                <td>
                  <span style={{ fontWeight: 700, color: l.icp_score >= 75 ? '#4ade80' : l.icp_score >= 45 ? '#facc15' : '#818cf8' }}>
                    {l.icp_score}
                  </span>
                </td>
                <td>
                  <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, background: `${tierColor(l.tier)}20`, color: tierColor(l.tier), fontWeight: 600 }}>
                    {l.tier?.replace('tier', 'T')}
                  </span>
                </td>
                <td>
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{l.status}</span>
                </td>
                <td>
                  <button onClick={() => handleDelete(l.id)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 14 }} title="Delete Lead">🗑️</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {leads.length === 0 && (
          <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
            No leads yet. Upload a CSV to get started.
          </div>
        )}
      </div>
    </div>
  )
}
