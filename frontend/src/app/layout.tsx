import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Cortexa Labs — Cold Email Engine',
  description: 'AI-powered cold email automation for Cortexa Labs',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <Sidebar />
      <main style={{ flex: 1, padding: '32px', overflowY: 'auto' }}>
        {children}
      </main>
    </div>
  )
}

function Sidebar() {
  const links = [
    { href: '/', label: 'Dashboard', icon: '📊' },
    { href: '/campaigns', label: 'Campaigns', icon: '🚀' },
    { href: '/leads', label: 'Leads', icon: '👥' },
    { href: '/replies', label: 'Replies', icon: '🔥' },
    { href: '/inboxes', label: 'Inboxes', icon: '📬' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
  ]

  return (
    <aside style={{
      width: 220,
      minWidth: 220,
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border)',
      padding: '24px 0',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Logo */}
      <div style={{ padding: '0 20px 28px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16,
          }}>⚡</div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'white' }}>Cortexa</div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Cold Email Engine</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: '16px 12px', flex: 1 }}>
        {links.map(link => (
          <a
            key={link.href}
            href={link.href}
            className="nav-link"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '9px 12px',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 500,
              color: 'var(--text-secondary)',
              textDecoration: 'none',
              marginBottom: 2,
            }}
          >
            <span style={{ fontSize: 15 }}>{link.icon}</span>
            {link.label}
            {link.href === '/replies' && (
              <span style={{
                marginLeft: 'auto', background: '#ef4444',
                color: 'white', fontSize: 10, padding: '1px 6px',
                borderRadius: 999, fontWeight: 700,
              }}>LIVE</span>
            )}
          </a>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Cortexa Labs © 2026
        </div>
      </div>
    </aside>
  )
}
