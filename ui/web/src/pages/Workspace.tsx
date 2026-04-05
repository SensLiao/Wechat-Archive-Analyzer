import { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/api'

interface WorkspaceItem {
  id: string
  msg_id: string
  sender: string
  content: string
  timestamp: string
  note: string
}

interface WorkspaceMeta {
  id: string
  name: string
  description: string
  item_count: number
  created: string
  updated: string
}

function Workspace() {
  const [workspaces, setWorkspaces] = useState<WorkspaceMeta[]>([])
  const [activeWs, setActiveWs] = useState<string | null>(null)
  const [items, setItems] = useState<WorkspaceItem[]>([])
  const [selectedItem, setSelectedItem] = useState<WorkspaceItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load workspace list
  useEffect(() => {
    apiFetch<{ workspaces: WorkspaceMeta[] }>('/workspaces')
      .then((data) => {
        setWorkspaces(data.workspaces)
        if (data.workspaces.length > 0) {
          setActiveWs(data.workspaces[0].id)
        }
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  // Load items when workspace changes
  useEffect(() => {
    if (!activeWs) return
    setItems([])
    setSelectedItem(null)
    apiFetch<{ items: WorkspaceItem[] }>(`/workspaces/${activeWs}/items`)
      .then((data) => setItems(data.items))
      .catch((err: Error) => setError(err.message))
  }, [activeWs])

  const activeWorkspace = workspaces.find((w) => w.id === activeWs)

  return (
    <div className="page page-workspace">
      <h1 className="page-title">工作区</h1>

      {error && <p className="text-error">{error}</p>}

      <div className="three-col">
        {/* Left: Workspace list */}
        <aside className="col-facets">
          <h3 className="col-title">工作区列表</h3>
          {loading && <p className="text-muted">加载中...</p>}
          <ul className="ws-list">
            {workspaces.map((ws) => (
              <li
                key={ws.id}
                className={`ws-item ${activeWs === ws.id ? 'ws-active' : ''}`}
                onClick={() => setActiveWs(ws.id)}
              >
                <span className="ws-name">{ws.name}</span>
                <span className="ws-meta">{ws.item_count} 项</span>
              </li>
            ))}
          </ul>
          {!loading && workspaces.length === 0 && (
            <p className="text-muted">暂无工作区，从搜索结果中收藏消息以创建</p>
          )}
        </aside>

        {/* Center: Items in workspace */}
        <section className="col-results">
          <h3 className="col-title">
            {activeWorkspace ? activeWorkspace.name : '选择工作区'}
          </h3>
          {activeWorkspace && (
            <p className="text-muted ws-desc">{activeWorkspace.description}</p>
          )}
          <ul className="result-list">
            {items.map((item) => (
              <li
                key={item.id}
                className={`result-item ${selectedItem?.id === item.id ? 'result-selected' : ''}`}
                onClick={() => setSelectedItem(item)}
              >
                <div className="result-header">
                  <span className="result-sender">{item.sender}</span>
                  <span className="result-time">{item.timestamp}</span>
                </div>
                <p className="result-content">{item.content}</p>
                {item.note && <p className="ws-note">{item.note}</p>}
              </li>
            ))}
          </ul>
          {activeWs && items.length === 0 && (
            <p className="text-muted">此工作区暂无内容</p>
          )}
        </section>

        {/* Right: Item detail */}
        <aside className="col-context">
          <h3 className="col-title">详情</h3>
          {selectedItem ? (
            <div className="context-detail">
              <p><strong>发送者:</strong> {selectedItem.sender}</p>
              <p><strong>时间:</strong> {selectedItem.timestamp}</p>
              <hr className="divider" />
              <p className="context-body">{selectedItem.content}</p>
              {selectedItem.note && (
                <>
                  <hr className="divider" />
                  <p><strong>备注:</strong></p>
                  <p className="context-body">{selectedItem.note}</p>
                </>
              )}
            </div>
          ) : (
            <p className="text-muted">点击条目查看详情</p>
          )}
        </aside>
      </div>
    </div>
  )
}

export default Workspace
