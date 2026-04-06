import { useEffect, useState, useCallback } from 'react'
import { apiFetch } from '@/lib/api'
import AttachmentPreview from './AttachmentPreview'
import type { Attachment } from './AttachmentPreview'
import type { MessageResult } from './ResultStream'

interface ContextMessage {
  id: string
  sender_name: string
  content: string
  timestamp: string
  type: string
  attachments?: Attachment[]
}

interface ContextResponse {
  target: ContextMessage
  before: ContextMessage[]
  after: ContextMessage[]
}

interface ContextDrawerProps {
  message: MessageResult | null
  open: boolean
  onClose: () => void
  onAddToWorkspace?: (msg: MessageResult) => void
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ts
  }
}

function ContextDrawer({ message, open, onClose, onAddToWorkspace }: ContextDrawerProps) {
  const [context, setContext] = useState<ContextResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch context when message changes
  useEffect(() => {
    if (!message) {
      setContext(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)

    apiFetch<ContextResponse>('/query/context', {
      method: 'POST',
      body: JSON.stringify({ message_id: message.id, window: 10 }),
    })
      .then((data) => {
        if (!cancelled) setContext(data)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载上下文失败')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [message])

  const handleExportContext = useCallback(() => {
    if (!context) return
    const allMessages = [...context.before, context.target, ...context.after]
    const text = allMessages
      .map((m) => `[${m.timestamp}] ${m.sender_name}: ${m.content}`)
      .join('\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `context-${context.target.id}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }, [context])

  return (
    <aside className={`context-drawer ${open ? 'context-drawer--open' : ''}`}>
      <div className="context-drawer__header">
        <h3 className="col-title">上下文</h3>
        <button type="button" className="context-drawer__close" onClick={onClose} aria-label="关闭">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {!message && (
        <p className="text-muted context-drawer__placeholder">
          点击搜索结果查看上下文
        </p>
      )}

      {loading && (
        <div className="context-drawer__loading">
          <div className="skeleton-line skeleton-line--long" />
          <div className="skeleton-line skeleton-line--medium" />
          <div className="skeleton-line skeleton-line--short" />
        </div>
      )}

      {error && <p className="text-error">{error}</p>}

      {context && !loading && (
        <>
          {/* Conversation info */}
          <div className="context-drawer__conv-info">
            <span className="context-drawer__conv-name">{message?.conversation_title}</span>
            <span className={`surface-tag surface-tag--${message?.surface ?? 'all'}`}>
              {message?.surface}
            </span>
          </div>

          {/* Message thread */}
          <div className="context-drawer__thread">
            {context.before.map((m) => (
              <div key={m.id} className="context-msg">
                <div className="context-msg__meta">
                  <span className="context-msg__sender">{m.sender_name}</span>
                  <span className="context-msg__time">{formatTime(m.timestamp)}</span>
                </div>
                <p className="context-msg__body">{m.content}</p>
              </div>
            ))}

            {/* Target — highlighted */}
            <div className="context-msg context-msg--target">
              <div className="context-msg__meta">
                <span className="context-msg__sender">{context.target.sender_name}</span>
                <span className="context-msg__time">{formatTime(context.target.timestamp)}</span>
              </div>
              <p className="context-msg__body">{context.target.content}</p>
              {/* Attachment previews */}
              {context.target.attachments && context.target.attachments.length > 0 && (
                <div className="context-msg__attachments">
                  {context.target.attachments.map((att, i) => (
                    <AttachmentPreview key={i} attachment={att} />
                  ))}
                </div>
              )}
            </div>

            {context.after.map((m) => (
              <div key={m.id} className="context-msg">
                <div className="context-msg__meta">
                  <span className="context-msg__sender">{m.sender_name}</span>
                  <span className="context-msg__time">{formatTime(m.timestamp)}</span>
                </div>
                <p className="context-msg__body">{m.content}</p>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="context-drawer__actions">
            <button
              type="button"
              className="btn btn-secondary"
              title="添加到工作区"
              onClick={() => message && onAddToWorkspace?.(message)}
            >
              + 添加到工作区
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleExportContext}>
              导出上下文
            </button>
          </div>
        </>
      )}
    </aside>
  )
}

export default ContextDrawer
