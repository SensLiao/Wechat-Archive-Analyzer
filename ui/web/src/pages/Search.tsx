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
      hasAttachment: params.get('attachments') === '1',
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
  if (facets.hasAttachment) p.set('attachments', '1')
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
  if (facets.hasAttachment) body.attachments = true
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
        setError(err instanceof Error ? err.message : 'Search failed')
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

  const handleSaveView = useCallback(() => {
    // Placeholder: save current query as a named view
    // TODO: persist to local storage or backend
  }, [])

  return (
    <div className="page page-search-v2">
      {/* Global search bar */}
      <SearchBar
        keyword={keyword}
        surface={surface}
        onKeywordChange={handleKeywordChange}
        onSurfaceChange={handleSurfaceChange}
        onSaveView={handleSaveView}
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
        />

        <ContextDrawer
          message={selectedMsg}
          open={drawerOpen}
          onClose={handleCloseDrawer}
        />
      </div>
    </div>
  )
}

export default Search
