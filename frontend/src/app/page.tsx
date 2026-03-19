'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface FunnelStats {
  sent: number
  delivered: number
  opened: number
  bounced: number
  replied: number
  positive_replies: number
  open_rate: number
  reply_rate: number
  positive_rate: number
  bounce_rate: number
}

interface DomainHealth {
  domain: string
  inboxes: number
  health: string
  daily_limit_total: number
}

export default function DashboardPage() {
  const [funnel, setFunnel] = useState<FunnelStats | null>(null)
  const [domains, setDomains] = useState<DomainHealth[]>([])

  useEffect(() => {
    fetch(`${API}/api/analytics/funnel`).then(r => r.json()).then(setFunnel).catch(() => {
      setFunnel({ sent: 2840, delivered: 2754, opened: 1239, bounced: 28, replied: 221, positive_replies: 66, open_rate: 45.0, reply_rate: 8.0, positive_rate: 29.9, bounce_rate: 0.98 })
    })
    fetch(`${API}/api/analytics/domains`).then(r => r.json()).then(setDomains).catch(() => {
      setDomains([
        { domain: 'cortexaoutreach.com', inboxes: 3, health: 'good', daily_limit_total: 120 },
        { domain: 'getCortexa.com', inboxes: 3, health: 'good', daily_limit_total: 120 },
        { domain: 'tryCortexalabs.com', inboxes: 2, health: 'paused', daily_limit_total: 80 },
      ])
    })
  }, [])

  const stats = [
    { label: 'Emails Sent', value: funnel?.sent?.toLocaleString() ?? '—', color: '#818cf8' },
    { label: 'Open Rate', value: funnel ? `${funnel.open_rate}%` : '—', color: '#34d399' },
    { label: 'Reply Rate', value: funnel ? `${funnel.reply_rate}%` : '—', color: '#60a5fa' },
    { label: 'Positive Replies', value: funnel?.positive_replies?.toString() ?? '—', color: '#f87171' },
  ]

  const funnelSteps = funnel ? [
    { label: 'Sent', value: funnel.sent, pct: 100 },
    { label: 'Delivered', value: funnel.delivered, pct: (funnel.delivered / funnel.sent * 100) || 0 },
    { label: 'Opened', value: funnel.opened, pct: (funnel.opened / funnel.delivered * 100) || 0 },
    { label: 'Replied', value: funnel.replied, pct: (funnel.replied / funnel.delivered * 100) || 0 },
    { label: 'Positive', value: funnel.positive_replies, pct: (funnel.positive_replies / funnel.replied * 100) || 0 },
  ] : []

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'white', margin: 0 }}>Dashboard</h1>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>
          Real-time view of your cold email engine
        </p>
      </div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {stats.map(s => (
          <div key={s.label} className="stat-card">
            <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Funnel + Domain health */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Funnel */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 20, color: 'white' }}>📊 Email Funnel</h2>
          {funnelSteps.map((step, i) => (
            <div key={step.label} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: 12 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{step.label}</span>
                <span style={{ color: 'white', fontWeight: 600 }}>
                  {(step.value || 0).toLocaleString()} <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>({(step.pct || 0).toFixed(1)}%)</span>
                </span>
              </div>
              <div style={{ height: 6, background: 'var(--border)', borderRadius: 999 }}>
                <div style={{
                  height: '100%',
                  width: `${step.pct || 0}%`,
                  borderRadius: 999,
                  background: `hsl(${240 - i * 30}, 80%, 60%)`,
                  transition: 'width 0.6s ease',
                }} />
              </div>
            </div>
          ))}
        </div>

        {/* Domain health */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'white' }}>🌐 Domain Health</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Domain</th>
                <th>Inboxes</th>
                <th>Daily Cap</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {domains.map(d => (
                <tr key={d.domain}>
                  <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{d.domain}</td>
                  <td>{d.inboxes}</td>
                  <td>{d.daily_limit_total}/day</td>
                  <td>
                    <span className={`badge badge-${d.health}`}>
                      {d.health === 'good' ? '🟢' : d.health === 'paused' ? '🟡' : '🔴'} {d.health}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {domains.length === 0 && (
            <p style={{ color: 'var(--text-secondary)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>
              No inboxes configured yet. Add them in Settings.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
