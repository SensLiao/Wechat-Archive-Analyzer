import { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/api'
import { SearchIcon, ExportIcon, FolderPlusIcon, KeyIcon, FolderIcon } from '@/components/Icons'
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
      <h1 className="page-title">工作台</h1>

      {/* Health Bar */}
      <section className="health-bar">
        <h2 className="section-title">系统状态</h2>
        {loading && <p className="text-muted">加载中...</p>}
        {error && <p className="text-error">无法连接后端: {error}</p>}
        {summary && health && (
          <div className="health-indicators">
            <div className={`health-chip ${health.dbStatus === 'ok' ? 'health-ok' : 'health-warn'}`}>
              数据库: {health.dbStatus === 'ok' ? `${summary.accounts.count} 个账号` : '未发现'}
            </div>
            <div className={`health-chip ${health.keyStatus === 'ok' ? 'health-ok' : 'health-warn'}`}>
              密钥: {health.keyStatus === 'ok' ? `${summary.keys.stored} 已存储 / ${summary.keys.verified} 已验证` : '未配置'}
            </div>
            <div className={`health-chip ${health.cacheStatus === 'ok' ? 'health-ok' : 'health-warn'}`}>
              缓存: {health.cacheStatus === 'ok' ? summary.cache.size_human : '无缓存'}
            </div>
          </div>
        )}
      </section>

      {/* Quick Actions */}
      <section className="quick-actions">
        <h2 className="section-title">快捷操作</h2>
        <div className="action-grid">
          <a href="/search" className="action-card">
            <span className="action-icon"><SearchIcon size={28} /></span>
            <span>全文搜索</span>
          </a>
          <a href="/exports" className="action-card">
            <span className="action-icon"><ExportIcon size={28} /></span>
            <span>导出聊天</span>
          </a>
          <a href="/workspace" className="action-card action-card-accent">
            <span className="action-icon"><FolderPlusIcon size={28} /></span>
            <span>新建工作区</span>
          </a>
          <a href="/settings" className="action-card">
            <span className="action-icon"><KeyIcon size={28} /></span>
            <span>密钥管理</span>
          </a>
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
        <div className="home-section-header">
          <h2 className="section-title">最近工作区</h2>
          <a href="/workspace" className="home-section-link">查看全部</a>
        </div>
        {summary?.recent_workspaces.length ? (
          <div className="home-ws-grid">
            {summary.recent_workspaces.map((w) => (
              <a key={w.id} href={`/workspace?id=${w.id}`} className="home-ws-card">
                <span className="home-ws-card-icon"><FolderIcon size={20} /></span>
                <span className="home-ws-card-name">{w.name}</span>
                <span className="home-ws-card-meta">{w.item_count} 项 &middot; {w.updated}</span>
              </a>
            ))}
          </div>
        ) : (
          <p className="text-muted">暂无工作区</p>
        )}
      </section>

      {/* Recent Exports */}
      <section className="recent-section">
        <div className="home-section-header">
          <h2 className="section-title">最近导出</h2>
          <a href="/exports" className="home-section-link">查看全部</a>
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
