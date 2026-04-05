import { useCallback, useMemo } from 'react'
import type { Surface } from './SurfaceSwitcher'

export interface MessageResult {
  id: string
  sender: string
  content: string
  timestamp: string
  conversation: string
  surface: Surface
  msg_type: string
  has_attachment: boolean
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
          <h3>Start searching</h3>
          <p>Enter keywords above to search your message archive.</p>
          <div className="result-stream__suggestions">
            <span className="suggestion-chip">Try a contact name</span>
            <span className="suggestion-chip">Try a date range</span>
            <span className="suggestion-chip">Try a keyword</span>
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
            Found ~{totalEstimate.toLocaleString()} results
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
                {msg.surface}
              </span>
            </div>
            <div className="result-card__meta">
              <span className="result-card__sender">{msg.sender}</span>
              <span className="result-card__sep">/</span>
              <span className="result-card__conversation">{msg.conversation}</span>
              {msg.has_attachment && (
                <span className="result-card__attachment-icon" title="Has attachment">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </span>
              )}
            </div>
            <p className="result-card__content">
              {highlightKeyword(msg.content, keyword)}
            </p>
            <div className="result-card__actions">
              <button type="button" className="result-card__action" onClick={(e) => { e.stopPropagation(); onSelect(msg) }}>
                View context
              </button>
              <button type="button" className="result-card__action" title="Add to workspace">
                + Workspace
              </button>
              <button type="button" className="result-card__action" title="Export this message">
                Export
              </button>
            </div>
          </article>
        ))}
      </div>

      {/* Loading indicator for "load more" */}
      {loading && results.length > 0 && (
        <div className="result-stream__loading">Loading more...</div>
      )}

      {/* Load more */}
      {hasMore && !loading && (
        <div className="result-stream__footer">
          <button type="button" className="btn btn-secondary" onClick={onLoadMore}>
            Load more results
          </button>
        </div>
      )}
    </section>
  )
}

export default ResultStream
