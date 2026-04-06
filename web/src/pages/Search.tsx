import { useState, useCallback, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiFetch } from '@/lib/api'
import SearchBar from '@/components/SearchBar'
import FacetPanel, { type Facets, EMPTY_FACETS } from '@/components/FacetPanel'
import ResultStream, { type MessageResult } from '@/components/ResultStream'
import ContextDrawer from '@/components/ContextDrawer'
import type { Surface } from '@/components/SurfaceSwitcher'

/* ---------- API types ---------- */

interface QueryResponse {
  messages: MessageResult[]
  total_estimate: number
  has_more: boolean
  query: string
}

/* ---------- URL sync helpers ---------- */

function readParamsToState(params: URLSearchParams): {
  keyword: string
  surface: Surface
  facets: Facets
} {
  const surface = (params.get('surface') as Surface) || 'all'
  const msgTypesRaw = params.get('msg_type')
  return {
    keyword: params.get('q') || '',
    surface,
    facets: {
      since: params.get('since') || '',
      until: params.get('until') || '',
      contact: params.get('contact') || '',
      conversation: params.get('conversation') || '',
      msgTypes: msgTypesRaw ? new Set(msgTypesRaw.split(',')) : new Set<string>(),
      surface,
      hasAttachment: params.get('has_attachment') === '1',
    },
  }
}

function stateToParams(keyword: string, surface: Surface, facets: Facets): URLSearchParams {
  const p = new URLSearchParams()
  if (keyword) p.set('q', keyword)
  if (surface !== 'all') p.set('surface', surface)
  if (facets.since) p.set('since', facets.since)
  if (facets.until) p.set('until', facets.until)
  if (facets.contact) p.set('contact', facets.contact)
  if (facets.conversation) p.set('conversation', facets.conversation)
  if (facets.msgTypes.size > 0) p.set('msg_type', [...facets.msgTypes].join(','))
  if (facets.hasAttachment) p.set('has_attachment', '1')
  return p
}

/* ---------- Build request body ---------- */

function buildBody(
  keyword: string,
  surface: Surface,
  facets: Facets,
  limit: number,
  offset: number,
): Record<string, unknown> {
  const body: Record<string, unknown> = { keyword, limit, offset }
  if (surface !== 'all') body.surface = surface
  if (facets.since) body.since = facets.since
  if (facets.until) body.until = facets.until
  if (facets.contact) body.contact = facets.contact
  if (facets.conversation) body.conversation = facets.conversation
  if (facets.msgTypes.size > 0) body.msg_type = [...facets.msgTypes].join(',')
  if (facets.hasAttachment) body.has_attachment = true
  // Request attachment path resolution so we can show the icon
  body.attachments = 'path'
  return body
}

/* ---------- Page size ---------- */

const PAGE_SIZE = 30

/* ---------- Component ---------- */

function Search() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initial = readParamsToState(searchParams)

  const [keyword, setKeyword] = useState(initial.keyword)
  const [surface, setSurface] = useState<Surface>(initial.surface)
  const [facets, setFacets] = useState<Facets>(initial.facets)

  const [results, setResults] = useState<MessageResult[]>([])
  const [totalEstimate, setTotalEstimate] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [selectedMsg, setSelectedMsg] = useState<MessageResult | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Add-to-workspace dialog
  const [wsPickerMsg, setWsPickerMsg] = useState<MessageResult | null>(null)
  const [wsList, setWsList] = useState<{ id: string; name: string }[]>([])
  const [wsAdding, setWsAdding] = useState(false)

  const offsetRef = useRef(0)

  /* ---- Fetch results ---- */

  const fetchResults = useCallback(
    async (kw: string, surf: Surface, f: Facets, offset: number, append: boolean) => {
      if (!kw.trim() && !f.contact && !f.conversation) return
      setLoading(true)
      setError(null)
      try {
        const body = buildBody(kw, surf, f, PAGE_SIZE, offset)
        const data = await apiFetch<QueryResponse>('/query', {
          method: 'POST',
          body: JSON.stringify(body),
        })
        const msgs = data.messages ?? []
        if (append) {
          setResults((prev) => [...prev, ...msgs])
        } else {
          setResults(msgs)
        }
        setTotalEstimate(data.total_estimate ?? 0)
        setHasMore(data.has_more ?? false)
        offsetRef.current = offset + msgs.length
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : '搜索失败')
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  /* ---- Trigger search on keyword / surface change ---- */

  useEffect(() => {
    const params = stateToParams(keyword, surface, facets)
    setSearchParams(params, { replace: true })

    offsetRef.current = 0
    fetchResults(keyword, surface, facets, 0, false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyword, surface])

  /* ---- Handlers ---- */

  const handleKeywordChange = useCallback((kw: string) => {
    setKeyword(kw)
  }, [])

  const handleSurfaceChange = useCallback((s: Surface) => {
    setSurface(s)
    setFacets((prev) => ({ ...prev, surface: s }))
  }, [])

  const handleFacetsChange = useCallback((f: Facets) => {
    setFacets(f)
  }, [])

  const handleApplyFacets = useCallback(() => {
    const params = stateToParams(keyword, surface, facets)
    setSearchParams(params, { replace: true })
    offsetRef.current = 0
    fetchResults(keyword, surface, facets, 0, false)
  }, [keyword, surface, facets, setSearchParams, fetchResults])

  const handleClearFacets = useCallback(() => {
    setFacets(EMPTY_FACETS)
    setSurface('all')
    const params = stateToParams(keyword, 'all', EMPTY_FACETS)
    setSearchParams(params, { replace: true })
    offsetRef.current = 0
    fetchResults(keyword, 'all', EMPTY_FACETS, 0, false)
  }, [keyword, setSearchParams, fetchResults])

  const handleLoadMore = useCallback(() => {
    fetchResults(keyword, surface, facets, offsetRef.current, true)
  }, [keyword, surface, facets, fetchResults])

  const handleSelectResult = useCallback((msg: MessageResult) => {
    setSelectedMsg(msg)
    setDrawerOpen(true)
  }, [])

  const handleCloseDrawer = useCallback(() => {
    setDrawerOpen(false)
  }, [])

  const handleAddToWorkspace = useCallback((msg: MessageResult) => {
    setWsPickerMsg(msg)
    apiFetch<{ id: string; name: string }[]>('/workspaces')
      .then((data) => setWsList(Array.isArray(data) ? data : []))
      .catch(() => setWsList([]))
  }, [])

  const handlePickWorkspace = useCallback(async (wsId: string) => {
    if (!wsPickerMsg) return
    setWsAdding(true)
    try {
      await apiFetch(`/workspaces/${wsId}/items`, {
        method: 'POST',
        body: JSON.stringify({
          items: [{
            type: 'message',
            title: `${wsPickerMsg.sender_name}: ${wsPickerMsg.content.slice(0, 60)}`,
            source_id: wsPickerMsg.id,
            surface: wsPickerMsg.surface,
            content_preview: wsPickerMsg.content,
            timestamp: wsPickerMsg.timestamp,
          }],
        }),
      })
      setWsPickerMsg(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '添加到工作区失败')
    } finally {
      setWsAdding(false)
    }
  }, [wsPickerMsg])

  return (
    <div className="page page-search-v2">
      {/* Global search bar */}
      <SearchBar
        keyword={keyword}
        surface={surface}
        onKeywordChange={handleKeywordChange}
        onSurfaceChange={handleSurfaceChange}
      />

      {error && <p className="text-error">{error}</p>}

      {/* Three-column layout */}
      <div className="search-columns">
        <FacetPanel
          facets={facets}
          onChange={handleFacetsChange}
          onApply={handleApplyFacets}
          onClear={handleClearFacets}
        />

        <ResultStream
          results={results}
          totalEstimate={totalEstimate}
          hasMore={hasMore}
          loading={loading}
          selectedId={selectedMsg?.id ?? null}
          keyword={keyword}
          onSelect={handleSelectResult}
          onLoadMore={handleLoadMore}
          onAddToWorkspace={handleAddToWorkspace}
        />

        <ContextDrawer
          message={selectedMsg}
          open={drawerOpen}
          onClose={handleCloseDrawer}
          onAddToWorkspace={handleAddToWorkspace}
        />
      </div>

      {/* Workspace picker dialog */}
      {wsPickerMsg && (
        <div className="ws-dialog-overlay" onClick={() => setWsPickerMsg(null)}>
          <div className="ws-dialog" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title">添加到工作区</h3>
            <p className="text-muted" style={{ marginBottom: 'var(--space-sm, 8px)' }}>
              {wsPickerMsg.sender_name}: {wsPickerMsg.content.slice(0, 80)}
              {wsPickerMsg.content.length > 80 ? '...' : ''}
            </p>
            {wsList.length === 0 ? (
              <p className="text-muted">暂无工作区，请先创建一个。</p>
            ) : (
              <ul className="ws-list" style={{ maxHeight: '240px', overflow: 'auto' }}>
                {wsList.map((ws) => (
                  <li
                    key={ws.id}
                    className="ws-item"
                    style={{ cursor: wsAdding ? 'wait' : 'pointer' }}
                    onClick={() => !wsAdding && handlePickWorkspace(ws.id)}
                  >
                    <span className="ws-name">{ws.name}</span>
                  </li>
                ))}
              </ul>
            )}
            <div className="btn-group" style={{ marginTop: 'var(--space-sm, 8px)' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setWsPickerMsg(null)}
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Search
