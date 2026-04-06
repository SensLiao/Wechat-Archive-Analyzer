export interface ExportRecord {
  id: string
  template?: string
  format: string
  source: string
  record_count: number
  file_count?: number
  file_size?: string
  created: string
  status: 'completed' | 'in_progress' | 'failed'
  output_dir?: string
}

interface RecentExportsProps {
  exports: ExportRecord[]
  loading?: boolean
  onReExport?: (record: ExportRecord) => void
  onOpenDir?: (dir: string) => void
  compact?: boolean
}

const STATUS_LABELS: Record<string, string> = {
  completed: '已完成',
  in_progress: '进行中',
  failed: '失败',
}

function RecentExports({
  exports: records,
  loading = false,
  onReExport,
  onOpenDir,
  compact = false,
}: RecentExportsProps) {
  if (loading) {
    return <p className="text-muted">加载中...</p>
  }

  if (records.length === 0) {
    return <p className="text-muted">暂无导出记录</p>
  }

  if (compact) {
    return (
      <ul className="recent-list">
        {records.slice(0, 5).map((rec) => (
          <li key={rec.id} className="recent-item">
            <span className="recent-primary">
              {rec.template || rec.format.toUpperCase()}
            </span>
            <span className="recent-meta">
              <span className={`status-badge status-${rec.status === 'in_progress' ? 'pending' : rec.status === 'completed' ? 'complete' : 'failed'}`}>
                {STATUS_LABELS[rec.status]}
              </span>
              {' '}{rec.created}
            </span>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <div className="export-table-wrap">
      <table className="export-table">
        <thead>
          <tr>
            <th>模板</th>
            <th>格式</th>
            <th>时间</th>
            <th>状态</th>
            <th>文件数</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {records.map((rec) => (
            <tr key={rec.id}>
              <td>{rec.template || '-'}</td>
              <td>{rec.format.toUpperCase()}</td>
              <td>{rec.created}</td>
              <td>
                <span className={`status-badge status-${rec.status === 'in_progress' ? 'pending' : rec.status === 'completed' ? 'complete' : 'failed'}`}>
                  {STATUS_LABELS[rec.status]}
                </span>
              </td>
              <td>{rec.file_count ?? rec.record_count}</td>
              <td>
                <div className="btn-group">
                  {rec.output_dir && onOpenDir && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => onOpenDir(rec.output_dir!)}
                    >
                      打开目录
                    </button>
                  )}
                  {onReExport && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => onReExport(rec)}
                    >
                      重新导出
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default RecentExports
