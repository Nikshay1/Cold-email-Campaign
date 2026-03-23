'use client'

import { useEffect, useState, useRef } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Reply {
  reply_id: string
  classification: 'INTERESTED' | 'NOT_NOW' | 'WRONG_PERSON' | 'UNSUBSCRIBE' | 'OTHER'
  confidence: number
  ai_summary: string
  talking_points: string[]
  raw_text_preview: string
  needs_human_reply: boolean
  received_at: string
  lead: {
    id: string
    name: string
    email: string
    title: string
    company: string
    funding_stage: string
  }
}

const CLASSIFICATION_CONFIG = {
  INTERESTED:   { label: 'Interested',   color: '#f87171', bg: 'rgba(239,68,68,0.1)',   emoji: '🔥' },
  NOT_NOW:      { label: 'Not Now',      color: '#facc15', bg: 'rgba(234,179,8,0.1)',   emoji: '🟡' },
  WRONG_PERSON: { label: 'Wrong Person', color: '#60a5fa', bg: 'rgba(96,165,250,0.1)', emoji: '🔀' },
  UNSUBSCRIBE:  { label: 'Unsubscribe',  color: '#a1a1aa', bg: 'rgba(161,161,170,0.1)',emoji: '🚫' },
  OTHER:        { label: 'Other',        color: '#818cf8', bg: 'rgba(129,140,248,0.1)','emoji': '💬' },
}

export default function RepliesPage() {
  const [replies, setReplies] = useState<Reply[]>([])
  const [selected, setSelected] = useState<Reply | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('ALL')
  const pollRef = useRef<NodeJS.Timeout>()

  const fetchReplies = async () => {
    try {
      const r = await fetch(`${API}/api/analytics/replies?handled=false`)
      const data = await r.json()
      setReplies(data)
    } catch {
      console.error("Failed to fetch replies")
    } finally {
      setLoading(false)
    }
  }

  const handleForceSync = async () => {
    setLoading(true)
    try {
      await fetch(`${API}/api/analytics/replies/sync`, { method: 'POST' })
    } catch (e) {
      console.error(e)
    }
    await fetchReplies()
  }

  useEffect(() => {
    fetchReplies()
    // Auto-refresh every 30 seconds
    pollRef.current = setInterval(fetchReplies, 30000)
    return () => clearInterval(pollRef.current)
  }, [])

  const markHandled = async (replyId: string) => {
    await fetch(`${API}/api/analytics/replies/${replyId}/handled`, { method: 'POST' })
    setReplies(prev => prev.filter(r => r.reply_id !== replyId))
    if (selected?.reply_id === replyId) setSelected(null)
  }

  const filtered = filter === 'ALL' ? replies : replies.filter(r => r.classification === filter)
  const unreadCount = replies.filter(r => r.classification === 'INTERESTED').length

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'white', margin: 0 }}>Reply Inbox</h1>
          {unreadCount > 0 && (
            <span style={{
              background: '#ef4444', color: 'white', fontSize: 11,
              padding: '2px 8px', borderRadius: 999, fontWeight: 700,
            }}>{unreadCount} need reply</span>
          )}
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          All VC replies — AI classified, awaiting your personal response. You reply directly from Gmail.
        </p>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['ALL', 'INTERESTED', 'NOT_NOW', 'OTHER'].map(f => (
          <button
            key={f}
            className={`btn ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter(f)}
            style={{ fontSize: 12 }}
          >
            {f === 'ALL' ? '📋 All' : CLASSIFICATION_CONFIG[f as keyof typeof CLASSIFICATION_CONFIG].emoji + ' ' + CLASSIFICATION_CONFIG[f as keyof typeof CLASSIFICATION_CONFIG].label}
          </button>
        ))}
        <button className="btn btn-secondary" style={{ marginLeft: 'auto', fontSize: 12 }} onClick={handleForceSync}>
          🔄 Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 1.6fr' : '1fr', gap: 16 }}>
        {/* Reply list */}
        <div>
          {loading && <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Loading replies...</p>}
          {!loading && filtered.length === 0 && (
            <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🎉</div>
              <div style={{ color: 'white', fontWeight: 600, marginBottom: 6 }}>All caught up!</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>No pending replies in this category.</div>
            </div>
          )}
          {filtered.map(reply => {
            const cfg = CLASSIFICATION_CONFIG[reply.classification]
            const isSelected = selected?.reply_id === reply.reply_id
            return (
              <div
                key={reply.reply_id}
                onClick={() => setSelected(isSelected ? null : reply)}
                style={{
                  background: isSelected ? 'rgba(99,102,241,0.08)' : 'var(--bg-card)',
                  border: `1px solid ${isSelected ? '#6366f1' : 'var(--border)'}`,
                  borderRadius: 10,
                  padding: 16,
                  marginBottom: 10,
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => {
                  if (!isSelected) (e.currentTarget as HTMLElement).style.borderColor = '#3f3f46'
                }}
                onMouseLeave={e => {
                  if (!isSelected) (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 13, color: 'white' }}>{reply.lead.name}</span>
                      <span style={{
                        fontSize: 10, padding: '2px 7px', borderRadius: 999,
                        background: cfg.bg, color: cfg.color, fontWeight: 600,
                      }}>{cfg.emoji} {cfg.label}</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6 }}>
                      {reply.lead.title} · {reply.lead.company}
                    </div>
                    <div style={{
                      fontSize: 12, color: '#d4d4d8', overflow: 'hidden',
                      display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                    }}>
                      {reply.raw_text_preview}
                    </div>
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-secondary)', whiteSpace: 'nowrap', marginTop: 2 }}>
                    {new Date(reply.received_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Reply detail panel */}
        {selected && (
          <div className="card" style={{ position: 'sticky', top: 0, height: 'fit-content' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div>
                <div style={{ fontWeight: 700, color: 'white', fontSize: 15 }}>{selected.lead.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{selected.lead.title} · {selected.lead.company}</div>
              </div>
              <button onClick={() => setSelected(null)} className="btn btn-secondary" style={{ fontSize: 11, padding: '4px 10px' }}>✕</button>
            </div>

            {/* Classification badge */}
            <div style={{ marginBottom: 14 }}>
              {(() => {
                const cfg = CLASSIFICATION_CONFIG[selected.classification]
                return (
                  <span style={{
                    fontSize: 12, padding: '4px 12px', borderRadius: 999,
                    background: cfg.bg, color: cfg.color, fontWeight: 600,
                  }}>{cfg.emoji} {cfg.label} — {Math.round(selected.confidence * 100)}% confidence</span>
                )
              })()}
            </div>

            {/* AI Summary */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>AI Summary</div>
              <div style={{ fontSize: 13, color: '#d4d4d8', lineHeight: 1.5 }}>{selected.ai_summary}</div>
            </div>

            {/* Talking points */}
            {selected.talking_points.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>💡 Talking Points for Your Reply</div>
                {selected.talking_points.map((pt, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6, fontSize: 12, color: '#e4e4e7' }}>
                    <span style={{ color: '#6366f1', fontWeight: 700 }}>→</span>
                    <span>{pt}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Original reply */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Their Reply</div>
              <div style={{
                background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                borderRadius: 8, padding: '12px 14px', fontSize: 12,
                color: '#d4d4d8', lineHeight: 1.6, maxHeight: 180, overflowY: 'auto',
              }}>
                {selected.raw_text_preview}
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 8 }}>
              <a
                href={`mailto:${selected.lead.email}`}
                className="btn btn-primary"
                style={{ flex: 1, justifyContent: 'center', textDecoration: 'none' }}
              >
                ✍️ Reply in Gmail
              </a>
              <button
                className="btn btn-success"
                onClick={() => markHandled(selected.reply_id)}
                style={{ whiteSpace: 'nowrap' }}
              >
                ✅ Mark Handled
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
