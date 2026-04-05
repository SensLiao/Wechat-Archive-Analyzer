import { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/api'
import RecentExports from '@/components/RecentExports'
import type { ExportRecord } from '@/components/RecentExports'

interface HomeSummary {
  accounts: {
    discovered: string[]
    count: number
    active: string | null
  }
  keys: {
    stored: number
    verified: number
    accounts: string[]
  }
  cache: {
    exists: boolean
    size_bytes: number
    size_human: string
    account_count: number
  }
  recent_searches: Array<{ query: string; timestamp: string; result_count: number }>
  recent_workspaces: Array<{ id: string; name: string; item_count: number; updated: string }>
  recent_exports: Array<{ id: string; format: string; record_count: number; created: string; status?: string }>
}

function deriveHealth(summary: HomeSummary) {
  const dbStatus = summary.accounts.count > 0 ? 'ok' : 'warn'
  const keyStatus = summary.keys.stored > 0 ? 'ok' : 'warn'
  const cacheStatus = summary.cache.exists ? 'ok' : 'warn'
  return { dbStatus, keyStatus, cacheStatus }
}

function Home() {
  const [summary, setSummary] = useState<HomeSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch<HomeSummary>('/home/summary')
      .then(setSummary)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const health = summary ? deriveHealth(summary) : null

  const recentExportRecords: ExportRecord[] = (summary?.recent_exports || []).map((e) => ({
    id: e.id,
    format: e.format,
    source: '',
    record_count: e.record_count,
    created: e.created,
    status: (e.status as ExportRecord['status']) || 'completed',
  }))

  return (
    <div className="page page-home">
      <h1 className="page-title">\u5DE5\u4F5C\u53F0</h1>

      {/* Health Bar */}
      <section className="health-bar">
        <h2 className="section-title">\u7CFB\u7EDF\u72B6\u6001</h2>
        {loading && <p className="text-muted">\u52A0\u8F7D\u4E2D...</p>}
        {error && <p className="text-error">\u65E0\u6CD5\u8FDE\u63A5\u540E\u7AEF: {error}</p>}
        {summary && health && (
          <div className="health-indicators">
            <div className={`health-chip ${health.dbStatus === 'ok' ? 'health-ok' : 'health-warn'}`}>
              \u6570\u636E\u5E93: {health.dbStatus === 'ok' ? `${summary.accounts.count} \u4E2A\u8D26\u53F7` : '\u672A\u53D1\u73B0'}
            </div>
            <div className={`health-chip ${health.keyStatus === 'ok' ? 'health-ok' : 'health-warn'}`}>
              \u5BC6\u94A5: {health.keyStatus === 'ok' ? `${summary.keys.stored} \u5DF2\u5B58\u50A8 / ${summary.keys.verified} \u5DF2\u9A8C\u8BC1` : '\u672A\u914D\u7F6E'}
            </div>
            <div className={`health-chip ${health.cacheStatus === 'ok' ? 'health-ok' : 'health-warn'}`}>
              \u7F13\u5B58: {health.cacheStatus === 'ok' ? summary.cache.size_human : '\u65E0\u7F13\u5B58'}
            </div>
          </div>
        )}
      </section>

      {/* Quick Actions */}
      <section className="quick-actions">
        <h2 className="section-title">\u5FEB\u6377\u64CD\u4F5C</h2>
        <div className="action-grid">
          <a href="/search" className="action-card">
            <span className="action-icon">{'\ud83d\udd0d'}</span>
            <span>{'\u5168\u6587\u641C\u7D22'}</span>
          </a>
          <a href="/exports" className="action-card">
            <span className="action-icon">{'\ud83d\udce6'}</span>
            <span>{'\u5BFC\u51FA\u804A\u5929'}</span>
          </a>
          <a href="/workspace" className="action-card action-card-accent">
            <span className="action-icon">{'\ud83d\udcc2'}</span>
            <span>{'\u65B0\u5EFA\u5DE5\u4F5C\u533A'}</span>
          </a>
          <a href="/settings" className="action-card">
            <span className="action-icon">{'\ud83d\udd11'}</span>
            <span>{'\u5BC6\u94A5\u7BA1\u7406'}</span>
          </a>
        </div>
      </section>

      {/* Recent Searches */}
      <section className="recent-section">
        <h2 className="section-title">\u6700\u8FD1\u641C\u7D22</h2>
        {summary?.recent_searches.length ? (
          <ul className="recent-list">
            {summary.recent_searches.map((s, i) => (
              <li key={i} className="recent-item">
                <span className="recent-primary">{s.query}</span>
                <span className="recent-meta">{s.result_count} \u6761\u7ED3\u679C &middot; {s.timestamp}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">\u6682\u65E0\u641C\u7D22\u8BB0\u5F55</p>
        )}
      </section>

      {/* Recent Workspaces */}
      <section className="recent-section">
        <div className="home-section-header">
          <h2 className="section-title">\u6700\u8FD1\u5DE5\u4F5C\u533A</h2>
          <a href="/workspace" className="home-section-link">\u67E5\u770B\u5168\u90E8</a>
        </div>
        {summary?.recent_workspaces.length ? (
          <div className="home-ws-grid">
            {summary.recent_workspaces.map((w) => (
              <a key={w.id} href={`/workspace?id=${w.id}`} className="home-ws-card">
                <span className="home-ws-card-icon">{'\ud83d\udcc2'}</span>
                <span className="home-ws-card-name">{w.name}</span>
                <span className="home-ws-card-meta">{w.item_count} \u9879 &middot; {w.updated}</span>
              </a>
            ))}
          </div>
        ) : (
          <p className="text-muted">\u6682\u65E0\u5DE5\u4F5C\u533A</p>
        )}
      </section>

      {/* Recent Exports */}
      <section className="recent-section">
        <div className="home-section-header">
          <h2 className="section-title">\u6700\u8FD1\u5BFC\u51FA</h2>
          <a href="/exports" className="home-section-link">\u67E5\u770B\u5168\u90E8</a>
        </div>
        <RecentExports
          exports={recentExportRecords}
          loading={loading}
          compact
        />
      </section>
    </div>
  )
}

export default Home
