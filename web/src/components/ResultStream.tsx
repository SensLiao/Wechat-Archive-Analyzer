import { useCallback, useMemo } from 'react'
import { EyeIcon, PlusIcon } from './Icons'
import type { Surface } from './SurfaceSwitcher'

export interface MessageResult {
  id: string
  sender_name: string
  content: string
  timestamp: string
  conversation_title: string
  surface: Surface
  type: string
  attachment_path: string | null
}

interface ResultStreamProps {
  results: MessageResult[]
  totalEstimate: number
  hasMore: boolean
  loading: boolean
  selectedId: string | null
  keyword: string
  onSelect: (msg: MessageResult) => void
  onLoadMore: () => void
  onAddToWorkspace?: (msg: MessageResult) => void
}

const SURFACE_LABELS: Record<string, string> = {
  chat: '聊天',
  public: '公众号',
  moments: '朋友圈',
  all: '全部',
}

function surfaceClass(surface: Surface): string {
  switch (surface) {
    case 'chat': return 'surface-tag--chat'
    case 'public': return 'surface-tag--public'
    case 'moments': return 'surface-tag--moments'
    default: return 'surface-tag--all'
  }
}

function highlightKeyword(text: string, keyword: string): React.ReactNode {
  if (!keyword.trim()) return text
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  const parts = text.split(regex)
  return parts.map((part, i) =>
    regex.test(part) ? (
      <mark key={i} className="highlight">{part}</mark>
    ) : (
      part
    ),
  )
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ts
  }
}

function SkeletonCard() {
  return (
    <div className="result-card result-card--skeleton">
      <div className="skeleton-line skeleton-line--short" />
      <div className="skeleton-line skeleton-line--long" />
      <div className="skeleton-line skeleton-line--medium" />
    </div>
  )
}

function ResultStream({
  results,
  totalEstimate,
  hasMore,
  loading,
  selectedId,
  keyword,
  onSelect,
  onLoadMore,
  onAddToWorkspace,
}: ResultStreamProps) {
  const handleSelect = useCallback(
    (msg: MessageResult) => () => onSelect(msg),
    [onSelect],
  )

  const skeletons = useMemo(
    () => Array.from({ length: 6 }, (_, i) => <SkeletonCard key={`sk-${i}`} />),
    [],
  )

  // Empty state
  if (!loading && results.length === 0) {
    return (
      <section className="result-stream">
        <div className="result-stream__empty">
          <h3>开始搜索</h3>
          <p>在上方输入关键词搜索你的消息记录。</p>
          <div className="result-stream__suggestions">
            <span className="suggestion-chip">试试联系人名字</span>
            <span className="suggestion-chip">试试日期范围</span>
            <span className="suggestion-chip">试试关键词</span>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="result-stream">
      {/* Count header */}
      {totalEstimate > 0 && (
        <div className="result-stream__header">
          <span className="result-stream__count">
            约 {totalEstimate.toLocaleString()} 条结果
          </span>
        </div>
      )}

      {/* Loading skeletons */}
      {loading && results.length === 0 && (
        <div className="result-stream__list">{skeletons}</div>
      )}

      {/* Result cards */}
      <div className="result-stream__list">
        {results.map((msg) => (
          <article
            key={msg.id}
            className={`result-card ${selectedId === msg.id ? 'result-card--selected' : ''}`}
            onClick={handleSelect(msg)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onSelect(msg)
              }
            }}
          >
            <div className="result-card__top">
              <span className="result-card__time">{formatTimestamp(msg.timestamp)}</span>
              <span className={`surface-tag ${surfaceClass(msg.surface)}`}>
                {SURFACE_LABELS[msg.surface] || msg.surface}
              </span>
            </div>
            <div className="result-card__meta">
              <span className="result-card__sender">{msg.sender_name}</span>
              <span className="result-card__sep">/</span>
              <span className="result-card__conversation">{msg.conversation_title}</span>
              {msg.attachment_path && (
                <span className="result-card__attachment-icon" title="包含附件">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </span>
              )}
            </div>
            <p className="result-card__content">
              {highlightKeyword(msg.content, keyword)}
            </p>
            {/* Always-visible primary action + hover secondary */}
            <div className="result-card__actions result-card__actions--visible">
              <button type="button" className="result-card__action result-card__action--primary" onClick={(e) => { e.stopPropagation(); onSelect(msg) }}>
                <EyeIcon size={14} /> 查看上下文
              </button>
              <button
                type="button"
                className="result-card__action"
                title="添加到工作区"
                onClick={(e) => { e.stopPropagation(); onAddToWorkspace?.(msg) }}
              >
                <PlusIcon size={14} /> 收藏
              </button>
            </div>
          </article>
        ))}
      </div>

      {/* Loading indicator for "load more" */}
      {loading && results.length > 0 && (
        <div className="result-stream__loading">加载更多中...</div>
      )}

      {/* Load more */}
      {hasMore && !loading && (
        <div className="result-stream__footer">
          <button type="button" className="btn btn-secondary" onClick={onLoadMore}>
            加载更多结果
          </button>
        </div>
      )}
    </section>
  )
}

export default ResultStream
