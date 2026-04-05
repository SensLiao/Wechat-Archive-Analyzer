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
  completed: '\u5DF2\u5B8C\u6210',
  in_progress: '\u8FDB\u884C\u4E2D',
  failed: '\u5931\u8D25',
}

function RecentExports({
  exports: records,
  loading = false,
  onReExport,
  onOpenDir,
  compact = false,
}: RecentExportsProps) {
  if (loading) {
    return <p className="text-muted">\u52A0\u8F7D\u4E2D...</p>
  }

  if (records.length === 0) {
    return <p className="text-muted">\u6682\u65E0\u5BFC\u51FA\u8BB0\u5F55</p>
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
            <th>\u6A21\u677F</th>
            <th>\u683C\u5F0F</th>
            <th>\u65F6\u95F4</th>
            <th>\u72B6\u6001</th>
            <th>\u6587\u4EF6\u6570</th>
            <th>\u64CD\u4F5C</th>
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
                      \u6253\u5F00\u76EE\u5F55
                    </button>
                  )}
                  {onReExport && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => onReExport(rec)}
                    >
                      \u91CD\u65B0\u5BFC\u51FA
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
