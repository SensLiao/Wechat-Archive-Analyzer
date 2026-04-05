import { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/api'

interface HomeSummary {
  health: {
    db_status: string
    key_status: string
    cache_status: string
    last_sync: string | null
  }
  recent_searches: Array<{ query: string; timestamp: string; result_count: number }>
  recent_workspaces: Array<{ id: string; name: string; item_count: number; updated: string }>
  recent_exports: Array<{ id: string; format: string; record_count: number; created: string }>
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

  return (
    <div className="page page-home">
      <h1 className="page-title">工作台</h1>

      {/* Health Bar */}
      <section className="health-bar">
        <h2 className="section-title">系统状态</h2>
        {loading && <p className="text-muted">加载中...</p>}
        {error && <p className="text-error">无法连接后端: {error}</p>}
        {summary && (
          <div className="health-indicators">
            <div className={`health-chip ${summary.health.db_status === 'ok' ? 'health-ok' : 'health-warn'}`}>
              数据库: {summary.health.db_status}
            </div>
            <div className={`health-chip ${summary.health.key_status === 'ok' ? 'health-ok' : 'health-warn'}`}>
              密钥: {summary.health.key_status}
            </div>
            <div className={`health-chip ${summary.health.cache_status === 'ok' ? 'health-ok' : 'health-warn'}`}>
              缓存: {summary.health.cache_status}
            </div>
            {summary.health.last_sync && (
              <span className="text-muted">上次同步: {summary.health.last_sync}</span>
            )}
          </div>
        )}
      </section>

      {/* Quick Actions */}
      <section className="quick-actions">
        <h2 className="section-title">快捷操作</h2>
        <div className="action-grid">
          <button className="action-card" type="button">
            <span className="action-icon">&#128269;</span>
            <span>全文搜索</span>
          </button>
          <button className="action-card" type="button">
            <span className="action-icon">&#128230;</span>
            <span>导出聊天</span>
          </button>
          <button className="action-card" type="button">
            <span className="action-icon">&#128273;</span>
            <span>密钥管理</span>
          </button>
          <button className="action-card" type="button">
            <span className="action-icon">&#128451;</span>
            <span>缓存清理</span>
          </button>
        </div>
      </section>

      {/* Recent Searches */}
      <section className="recent-section">
        <h2 className="section-title">最近搜索</h2>
        {summary?.recent_searches.length ? (
          <ul className="recent-list">
            {summary.recent_searches.map((s, i) => (
              <li key={i} className="recent-item">
                <span className="recent-primary">{s.query}</span>
                <span className="recent-meta">{s.result_count} 条结果 &middot; {s.timestamp}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">暂无搜索记录</p>
        )}
      </section>

      {/* Recent Workspaces */}
      <section className="recent-section">
        <h2 className="section-title">最近工作区</h2>
        {summary?.recent_workspaces.length ? (
          <ul className="recent-list">
            {summary.recent_workspaces.map((w) => (
              <li key={w.id} className="recent-item">
                <span className="recent-primary">{w.name}</span>
                <span className="recent-meta">{w.item_count} 项 &middot; {w.updated}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">暂无工作区</p>
        )}
      </section>

      {/* Recent Exports */}
      <section className="recent-section">
        <h2 className="section-title">最近导出</h2>
        {summary?.recent_exports.length ? (
          <ul className="recent-list">
            {summary.recent_exports.map((e) => (
              <li key={e.id} className="recent-item">
                <span className="recent-primary">{e.format.toUpperCase()}</span>
                <span className="recent-meta">{e.record_count} 条 &middot; {e.created}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">暂无导出记录</p>
        )}
      </section>
    </div>
  )
}

export default Home
