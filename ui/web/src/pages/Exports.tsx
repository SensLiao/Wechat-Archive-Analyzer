import { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/api'

interface ExportRecord {
  id: string
  format: string
  source: string
  record_count: number
  file_size: string
  created: string
  status: string
}

type ExportFormat = 'json' | 'csv' | 'html'
type ExportSource = 'search' | 'workspace' | 'chat'

function Exports() {
  const [recentExports, setRecentExports] = useState<ExportRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Export form state
  const [source, setSource] = useState<ExportSource>('search')
  const [format, setFormat] = useState<ExportFormat>('json')
  const [sourceId, setSourceId] = useState('')
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    apiFetch<{ exports: ExportRecord[] }>('/exports')
      .then((data) => setRecentExports(data.exports))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const handleExport = async () => {
    if (!sourceId.trim()) return
    setExporting(true)
    setError(null)
    try {
      const result = await apiFetch<ExportRecord>('/exports', {
        method: 'POST',
        body: JSON.stringify({ source, source_id: sourceId, format }),
      })
      setRecentExports((prev) => [result, ...prev])
      setSourceId('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '导出失败')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="page page-exports">
      <h1 className="page-title">导出</h1>

      {error && <p className="text-error">{error}</p>}

      {/* Export Flow */}
      <section className="export-flow">
        <div className="export-step">
          <h3 className="section-title">1. 选择来源</h3>
          <div className="radio-group">
            <label className="radio-label">
              <input
                type="radio"
                name="source"
                value="search"
                checked={source === 'search'}
                onChange={() => setSource('search')}
              />
              搜索结果
            </label>
            <label className="radio-label">
              <input
                type="radio"
                name="source"
                value="workspace"
                checked={source === 'workspace'}
                onChange={() => setSource('workspace')}
              />
              工作区
            </label>
            <label className="radio-label">
              <input
                type="radio"
                name="source"
                value="chat"
                checked={source === 'chat'}
                onChange={() => setSource('chat')}
              />
              会话
            </label>
          </div>
          <input
            type="text"
            className="facet-input"
            placeholder={`输入${source === 'search' ? '搜索ID' : source === 'workspace' ? '工作区ID' : '会话名称'}...`}
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
          />
        </div>

        <div className="export-step">
          <h3 className="section-title">2. 选择格式</h3>
          <div className="radio-group">
            <label className="radio-label">
              <input
                type="radio"
                name="format"
                value="json"
                checked={format === 'json'}
                onChange={() => setFormat('json')}
              />
              JSON
            </label>
            <label className="radio-label">
              <input
                type="radio"
                name="format"
                value="csv"
                checked={format === 'csv'}
                onChange={() => setFormat('csv')}
              />
              CSV
            </label>
            <label className="radio-label">
              <input
                type="radio"
                name="format"
                value="html"
                checked={format === 'html'}
                onChange={() => setFormat('html')}
              />
              HTML
            </label>
          </div>
        </div>

        <div className="export-step">
          <button
            className="btn btn-primary"
            type="button"
            onClick={handleExport}
            disabled={exporting || !sourceId.trim()}
          >
            {exporting ? '导出中...' : '开始导出'}
          </button>
        </div>
      </section>

      {/* Recent Exports */}
      <section className="recent-section">
        <h2 className="section-title">导出历史</h2>
        {loading && <p className="text-muted">加载中...</p>}
        {recentExports.length === 0 && !loading && (
          <p className="text-muted">暂无导出记录</p>
        )}
        <div className="export-table-wrap">
          {recentExports.length > 0 && (
            <table className="export-table">
              <thead>
                <tr>
                  <th>格式</th>
                  <th>来源</th>
                  <th>记录数</th>
                  <th>文件大小</th>
                  <th>状态</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                {recentExports.map((exp) => (
                  <tr key={exp.id}>
                    <td>{exp.format.toUpperCase()}</td>
                    <td>{exp.source}</td>
                    <td>{exp.record_count}</td>
                    <td>{exp.file_size}</td>
                    <td>
                      <span className={`status-badge status-${exp.status}`}>
                        {exp.status}
                      </span>
                    </td>
                    <td>{exp.created}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  )
}

export default Exports
