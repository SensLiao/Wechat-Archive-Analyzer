import { useState } from 'react'
import { apiFetch } from '@/lib/api'

interface SearchResult {
  msg_id: string
  sender: string
  content: string
  timestamp: string
  chat_name: string
  msg_type: number
}

interface SearchResponse {
  results: SearchResult[]
  total: number
  page: number
  page_size: number
}

interface SearchFacets {
  chat_name: string | null
  msg_type: number | null
  date_from: string
  date_to: string
}

function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<SearchResult | null>(null)
  const [facets, setFacets] = useState<SearchFacets>({
    chat_name: null,
    msg_type: null,
    date_from: '',
    date_to: '',
  })

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ q: query, page: '1', page_size: '50' })
      if (facets.chat_name) params.set('chat_name', facets.chat_name)
      if (facets.msg_type !== null) params.set('msg_type', String(facets.msg_type))
      if (facets.date_from) params.set('date_from', facets.date_from)
      if (facets.date_to) params.set('date_to', facets.date_to)

      const data = await apiFetch<SearchResponse>(`/search?${params.toString()}`)
      setResults(data.results)
      setTotal(data.total)
      setSelected(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '搜索失败')
    } finally {
      setLoading(false)
    }
  }

  const updateFacet = <K extends keyof SearchFacets>(key: K, value: SearchFacets[K]) => {
    setFacets((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="page page-search">
      <h1 className="page-title">搜索</h1>

      {/* Search Bar */}
      <div className="search-bar">
        <input
          type="text"
          className="search-input"
          placeholder="输入关键词搜索聊天记录..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn btn-primary" type="button" onClick={handleSearch} disabled={loading}>
          {loading ? '搜索中...' : '搜索'}
        </button>
      </div>

      {error && <p className="text-error">{error}</p>}

      {/* Three-column layout */}
      <div className="three-col">
        {/* Left: Facets */}
        <aside className="col-facets">
          <h3 className="col-title">筛选</h3>
          <label className="facet-label">
            会话名称
            <input
              type="text"
              className="facet-input"
              placeholder="按会话筛选"
              value={facets.chat_name || ''}
              onChange={(e) => updateFacet('chat_name', e.target.value || null)}
            />
          </label>
          <label className="facet-label">
            消息类型
            <select
              className="facet-input"
              value={facets.msg_type ?? ''}
              onChange={(e) => updateFacet('msg_type', e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">全部</option>
              <option value="1">文本</option>
              <option value="3">图片</option>
              <option value="34">语音</option>
              <option value="43">视频</option>
              <option value="49">链接/文件</option>
            </select>
          </label>
          <label className="facet-label">
            开始日期
            <input
              type="date"
              className="facet-input"
              value={facets.date_from}
              onChange={(e) => updateFacet('date_from', e.target.value)}
            />
          </label>
          <label className="facet-label">
            结束日期
            <input
              type="date"
              className="facet-input"
              value={facets.date_to}
              onChange={(e) => updateFacet('date_to', e.target.value)}
            />
          </label>
        </aside>

        {/* Center: Results */}
        <section className="col-results">
          <h3 className="col-title">
            结果 {total > 0 && <span className="result-count">({total} 条)</span>}
          </h3>
          {results.length === 0 && !loading && (
            <p className="text-muted">输入关键词开始搜索</p>
          )}
          <ul className="result-list">
            {results.map((r) => (
              <li
                key={r.msg_id}
                className={`result-item ${selected?.msg_id === r.msg_id ? 'result-selected' : ''}`}
                onClick={() => setSelected(r)}
              >
                <div className="result-header">
                  <span className="result-sender">{r.sender}</span>
                  <span className="result-chat">{r.chat_name}</span>
                </div>
                <p className="result-content">{r.content}</p>
                <span className="result-time">{r.timestamp}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Right: Context Drawer */}
        <aside className="col-context">
          <h3 className="col-title">上下文</h3>
          {selected ? (
            <div className="context-detail">
              <p><strong>发送者:</strong> {selected.sender}</p>
              <p><strong>会话:</strong> {selected.chat_name}</p>
              <p><strong>时间:</strong> {selected.timestamp}</p>
              <p><strong>类型:</strong> {selected.msg_type}</p>
              <hr className="divider" />
              <p className="context-body">{selected.content}</p>
            </div>
          ) : (
            <p className="text-muted">点击搜索结果查看详情</p>
          )}
        </aside>
      </div>
    </div>
  )
}

export default Search
