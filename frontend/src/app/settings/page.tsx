'use client'
import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('llama-3.3-70b-versatile')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const MODELS = [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'mixtral-8x7b-32768',
    'gemma2-9b-it'
  ]

  useEffect(() => {
    fetch(`${API}/api/settings`)
      .then(r => r.json())
      .then(data => {
        setApiKey(data.groq_api_key || '')
        setModel(data.groq_model || 'llama-3.3-70b-versatile')
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      const res = await fetch(`${API}/api/settings/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          groq_api_key: apiKey,
          groq_model: model
        })
      })
      if (res.ok) {
        setMessage('✅ Settings saved successfully!')
      } else {
        setMessage('❌ Failed to save settings')
      }
    } catch (err) {
      setMessage('❌ Failed to connect to backend')
    } finally {
      setSaving(false)
      setTimeout(() => setMessage(''), 3000)
    }
  }

  if (loading) return <div style={{ color: 'white', padding: 40 }}>Loading configurations...</div>

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'white', margin: 0 }}>Settings</h1>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>
          System configuration and AI Models
        </p>
      </div>

      <div className="card" style={{ maxWidth: 600 }}>
        <h2 style={{ fontSize: 16, color: 'white', marginBottom: 16, fontWeight: 600 }}>🤖 AI Configuration (Groq)</h2>
        
        <form onSubmit={handleSave}>
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
              Groq API Key
            </label>
            <input 
              type="text" 
              className="input" 
              placeholder="gsk_..." 
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
            />
            <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>
              Get your free key from <a href="https://console.groq.com/keys" target="_blank" style={{ color: '#60a5fa', textDecoration: 'none' }}>console.groq.com</a>
            </p>
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
              AI Model
            </label>
            <select 
              className="input" 
              value={model}
              onChange={e => setModel(e.target.value)}
              style={{ paddingRight: 40, cursor: 'pointer' }}
            >
              {MODELS.map(m => (
                <option key={m} value={m} style={{ background: '#1e1e2e', color: 'white' }}>{m}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
            {message && <span style={{ fontSize: 13, color: 'white' }}>{message}</span>}
          </div>
        </form>
      </div>
      
      <div className="card" style={{ maxWidth: 600, marginTop: 24 }}>
         <h2 style={{ fontSize: 16, color: 'white', marginBottom: 12, fontWeight: 600 }}>🌐 Google OAuth Configuration</h2>
         <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
           To connect authentic Gmail inboxes, you must configure a Google Cloud app with the Gmail API enabled.
           Open your project's <code>.env</code> file directly to configure:<br/><br/>
           <code style={{ background: 'var(--bg-secondary)', padding: '4px 8px', borderRadius: 4, fontFamily: 'monospace' }}>GOOGLE_CLIENT_ID</code><br/>
           <code style={{ background: 'var(--bg-secondary)', padding: '4px 8px', borderRadius: 4, display: 'inline-block', marginTop: 8, fontFamily: 'monospace' }}>GOOGLE_CLIENT_SECRET</code>
         </p>
      </div>
    </div>
  )
}
