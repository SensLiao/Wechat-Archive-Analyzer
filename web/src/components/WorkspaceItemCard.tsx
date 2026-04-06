import { useState } from 'react'

export interface WorkspaceItemData {
  id: string
  type: 'message' | 'article' | 'moment' | 'note'
  title: string
  source_id?: string
  surface?: string
  content_preview?: string
  tags?: string[]
  notes?: string
  created?: string
}

interface WorkspaceItemCardProps {
  item: WorkspaceItemData
  selected?: boolean
  onSelect: (item: WorkspaceItemData) => void
  onRemove: (itemId: string) => void
  onEditNotes: (itemId: string, notes: string) => void
}

const TYPE_ICONS: Record<WorkspaceItemData['type'], string> = {
  message: '✉',   // envelope
  article: '\u{1F4C4}', // page facing up
  moment: '\u{1F4F7}',  // camera
  note: '\u{1F4DD}',    // memo
}

const TYPE_LABELS: Record<WorkspaceItemData['type'], string> = {
  message: '消息',
  article: '文章',
  moment: '朋友圈',
  note: '笔记',
}

const SURFACE_COLORS: Record<string, string> = {
  chat: 'surface-chat',
  group: 'surface-group',
  moment: 'surface-moment',
  channel: 'surface-channel',
}

function WorkspaceItemCard({
  item,
  selected = false,
  onSelect,
  onRemove,
  onEditNotes,
}: WorkspaceItemCardProps) {
  const [hovered, setHovered] = useState(false)
  const [editingNotes, setEditingNotes] = useState(false)
  const [noteDraft, setNoteDraft] = useState(item.notes || '')

  const handleSaveNotes = () => {
    onEditNotes(item.id, noteDraft)
    setEditingNotes(false)
  }

  const handleCancelNotes = () => {
    setNoteDraft(item.notes || '')
    setEditingNotes(false)
  }

  return (
    <div
      className={`ws-item-card ${selected ? 'ws-item-card-selected' : ''}`}
      onClick={() => onSelect(item)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Header row: type icon + title + actions */}
      <div className="ws-item-card-header">
        <span className="ws-item-type-icon" title={TYPE_LABELS[item.type]}>
          {TYPE_ICONS[item.type]}
        </span>
        <span className="ws-item-title">{item.title}</span>
        {hovered && (
          <span className="ws-item-actions">
            <button
              type="button"
              className="ws-item-action-btn"
              title="编辑备注"
              onClick={(e) => {
                e.stopPropagation()
                setEditingNotes(true)
              }}
            >
              ✏
            </button>
            <button
              type="button"
              className="ws-item-action-btn ws-item-action-danger"
              title="移除"
              onClick={(e) => {
                e.stopPropagation()
                onRemove(item.id)
              }}
            >
              ✕
            </button>
          </span>
        )}
      </div>

      {/* Surface tag */}
      {item.surface && (
        <span className={`ws-item-surface ${SURFACE_COLORS[item.surface] || ''}`}>
          {item.surface}
        </span>
      )}

      {/* Content preview */}
      {item.content_preview && (
        <p className="ws-item-preview">{item.content_preview}</p>
      )}

      {/* Full preview on hover */}
      {hovered && item.content_preview && item.content_preview.length > 80 && (
        <div className="ws-item-full-preview">
          {item.content_preview}
        </div>
      )}

      {/* Timestamp */}
      {item.created && (
        <span className="ws-item-time">{item.created}</span>
      )}

      {/* Tags */}
      {item.tags && item.tags.length > 0 && (
        <div className="ws-item-tags">
          {item.tags.map((tag) => (
            <span key={tag} className="ws-item-tag">{tag}</span>
          ))}
        </div>
      )}

      {/* Notes */}
      {editingNotes ? (
        <div className="ws-item-note-editor" onClick={(e) => e.stopPropagation()}>
          <textarea
            className="ws-item-note-input"
            value={noteDraft}
            onChange={(e) => setNoteDraft(e.target.value)}
            placeholder="添加备注..."
            rows={2}
          />
          <div className="btn-group">
            <button type="button" className="btn btn-primary" onClick={handleSaveNotes}>
              保存
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleCancelNotes}>
              取消
            </button>
          </div>
        </div>
      ) : (
        item.notes && <p className="ws-item-note">{item.notes}</p>
      )}
    </div>
  )
}

export default WorkspaceItemCard
