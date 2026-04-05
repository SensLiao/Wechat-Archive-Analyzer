import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '@/lib/api'
import WorkspaceBoard from '@/components/WorkspaceBoard'
import type { WorkspaceItemData } from '@/components/WorkspaceItemCard'

interface WorkspaceMeta {
  id: string
  name: string
  description: string
  item_count: number
  created: string
  updated: string
}

interface WorkspaceDetail extends WorkspaceMeta {
  items: WorkspaceItemData[]
}

function Workspace() {
  const [workspaces, setWorkspaces] = useState<WorkspaceMeta[]>([])
  const [activeWs, setActiveWs] = useState<string | null>(null)
  const [detail, setDetail] = useState<WorkspaceDetail | null>(null)
  const [selectedItem, setSelectedItem] = useState<WorkspaceItemData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create workspace dialog
  const [showCreate, setShowCreate] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createDesc, setCreateDesc] = useState('')
  const [creating, setCreating] = useState(false)

  // Delete confirmation
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // Note editing in detail panel
  const [editingNote, setEditingNote] = useState(false)
  const [noteDraft, setNoteDraft] = useState('')

  // Tag editing in detail panel
  const [editingTags, setEditingTags] = useState(false)
  const [tagDraft, setTagDraft] = useState('')

  // Load workspace list
  useEffect(() => {
    apiFetch<{ workspaces: WorkspaceMeta[] }>('/workspaces')
      .then((data) => {
        setWorkspaces(data.workspaces)
        if (data.workspaces.length > 0 && !activeWs) {
          setActiveWs(data.workspaces[0].id)
        }
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Load workspace detail when selection changes
  useEffect(() => {
    if (!activeWs) {
      setDetail(null)
      return
    }
    setSelectedItem(null)
    apiFetch<WorkspaceDetail>(`/workspaces/${activeWs}`)
      .then(setDetail)
      .catch((err: Error) => setError(err.message))
  }, [activeWs])

  const refreshList = useCallback(() => {
    apiFetch<{ workspaces: WorkspaceMeta[] }>('/workspaces')
      .then((data) => setWorkspaces(data.workspaces))
      .catch(() => { /* swallow */ })
  }, [])

  // Create workspace
  const handleCreate = async () => {
    if (!createName.trim()) return
    setCreating(true)
    setError(null)
    try {
      const ws = await apiFetch<WorkspaceMeta>('/workspaces', {
        method: 'POST',
        body: JSON.stringify({ name: createName.trim(), description: createDesc.trim() || undefined }),
      })
      setWorkspaces((prev) => [...prev, ws])
      setActiveWs(ws.id)
      setShowCreate(false)
      setCreateName('')
      setCreateDesc('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '\u521B\u5EFA\u5931\u8D25')
    } finally {
      setCreating(false)
    }
  }

  // Delete workspace
  const handleDelete = async () => {
    if (!activeWs) return
    setDeleting(true)
    setError(null)
    try {
      await apiFetch(`/workspaces/${activeWs}`, { method: 'DELETE' })
      setWorkspaces((prev) => prev.filter((w) => w.id !== activeWs))
      setActiveWs(workspaces.length > 1 ? workspaces.find((w) => w.id !== activeWs)?.id || null : null)
      setDetail(null)
      setSelectedItem(null)
      setShowDelete(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : '\u5220\u9664\u5931\u8D25')
    } finally {
      setDeleting(false)
    }
  }

  // Remove item from workspace
  const handleRemoveItem = async (itemId: string) => {
    if (!activeWs) return
    try {
      await apiFetch(`/workspaces/${activeWs}/items/${itemId}`, { method: 'DELETE' })
      setDetail((prev) =>
        prev ? { ...prev, items: prev.items.filter((it) => it.id !== itemId), item_count: prev.item_count - 1 } : prev
      )
      if (selectedItem?.id === itemId) setSelectedItem(null)
      refreshList()
    } catch (err) {
      setError(err instanceof Error ? err.message : '\u79FB\u9664\u5931\u8D25')
    }
  }

  // Edit notes (optimistic update then persist)
  const handleEditNotes = async (itemId: string, notes: string) => {
    if (!activeWs || !detail) return
    const updatedItems = detail.items.map((it) =>
      it.id === itemId ? { ...it, notes } : it
    )
    setDetail({ ...detail, items: updatedItems })
    if (selectedItem?.id === itemId) {
      setSelectedItem({ ...selectedItem, notes })
    }
    // Persist via adding the item again with notes — API may support PATCH
    // For now, this is a local-only optimistic update
  }

  const handleSelectItem = (item: WorkspaceItemData) => {
    setSelectedItem(item)
    setEditingNote(false)
    setEditingTags(false)
    setNoteDraft(item.notes || '')
    setTagDraft(item.tags?.join(', ') || '')
  }

  const handleSaveNote = () => {
    if (!selectedItem) return
    handleEditNotes(selectedItem.id, noteDraft)
    setEditingNote(false)
  }

  const handleSaveTags = () => {
    if (!selectedItem || !detail) return
    const newTags = tagDraft.split(',').map((t) => t.trim()).filter(Boolean)
    const updatedItems = detail.items.map((it) =>
      it.id === selectedItem.id ? { ...it, tags: newTags } : it
    )
    setDetail({ ...detail, items: updatedItems })
    setSelectedItem({ ...selectedItem, tags: newTags })
    setEditingTags(false)
  }

  const handleExportWorkspace = () => {
    // Navigate to exports page with workspace pre-selected
    window.location.hash = ''
    window.location.href = '/exports?source=workspace&source_id=' + activeWs
  }

  const activeWorkspace = workspaces.find((w) => w.id === activeWs) || null

  return (
    <div className="page page-workspace">
      <div className="ws-page-header">
        <h1 className="page-title">\u5DE5\u4F5C\u533A</h1>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setShowCreate(true)}
        >
          + \u65B0\u5EFA\u5DE5\u4F5C\u533A
        </button>
      </div>

      {error && <p className="text-error">{error}</p>}

      {/* Create dialog */}
      {showCreate && (
        <div className="ws-dialog-overlay" onClick={() => setShowCreate(false)}>
          <div className="ws-dialog" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title">\u65B0\u5EFA\u5DE5\u4F5C\u533A</h3>
            <label className="facet-label">
              \u540D\u79F0
              <input
                type="text"
                className="facet-input"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder="\u8F93\u5165\u5DE5\u4F5C\u533A\u540D\u79F0..."
                autoFocus
              />
            </label>
            <label className="facet-label">
              \u63CF\u8FF0 (\u53EF\u9009)
              <textarea
                className="facet-input ws-dialog-textarea"
                value={createDesc}
                onChange={(e) => setCreateDesc(e.target.value)}
                placeholder="\u63CF\u8FF0\u8FD9\u4E2A\u5DE5\u4F5C\u533A\u7684\u7528\u9014..."
                rows={3}
              />
            </label>
            <div className="btn-group">
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleCreate}
                disabled={creating || !createName.trim()}
              >
                {creating ? '\u521B\u5EFA\u4E2D...' : '\u521B\u5EFA'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCreate(false)}
              >
                \u53D6\u6D88
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation dialog */}
      {showDelete && (
        <div className="ws-dialog-overlay" onClick={() => setShowDelete(false)}>
          <div className="ws-dialog" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title">\u5220\u9664\u5DE5\u4F5C\u533A</h3>
            <p className="text-muted">
              \u786E\u5B9A\u8981\u5220\u9664\u201C{activeWorkspace?.name}\u201D\u5417\uFF1F\u6B64\u64CD\u4F5C\u4E0D\u53EF\u64A4\u9500\u3002
            </p>
            <div className="btn-group" style={{ marginTop: 'var(--space-md)' }}>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? '\u5220\u9664\u4E2D...' : '\u786E\u8BA4\u5220\u9664'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowDelete(false)}
              >
                \u53D6\u6D88
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="three-col">
        {/* Left: Workspace list */}
        <aside className="col-facets">
          <h3 className="col-title">\u5DE5\u4F5C\u533A\u5217\u8868</h3>
          {loading && <p className="text-muted">\u52A0\u8F7D\u4E2D...</p>}
          <ul className="ws-list">
            {workspaces.map((ws) => (
              <li
                key={ws.id}
                className={`ws-item ${activeWs === ws.id ? 'ws-active' : ''}`}
                onClick={() => setActiveWs(ws.id)}
              >
                <span className="ws-name">{ws.name}</span>
                <span className="ws-meta">{ws.item_count} \u9879</span>
              </li>
            ))}
          </ul>
          {!loading && workspaces.length === 0 && (
            <p className="text-muted">\u6682\u65E0\u5DE5\u4F5C\u533A</p>
          )}
          {activeWs && (
            <button
              type="button"
              className="btn btn-danger ws-delete-btn"
              onClick={() => setShowDelete(true)}
            >
              \u5220\u9664\u5DE5\u4F5C\u533A
            </button>
          )}
        </aside>

        {/* Center: WorkspaceBoard */}
        <WorkspaceBoard
          workspace={activeWorkspace ? { ...activeWorkspace, description: activeWorkspace.description || '' } : null}
          items={detail?.items || []}
          selectedItem={selectedItem}
          onSelectItem={handleSelectItem}
          onRemoveItem={handleRemoveItem}
          onEditNotes={handleEditNotes}
          onExportWorkspace={handleExportWorkspace}
        />

        {/* Right: Item detail panel */}
        <aside className="col-context">
          <h3 className="col-title">\u8BE6\u60C5</h3>
          {selectedItem ? (
            <div className="context-detail">
              <p><strong>\u7C7B\u578B:</strong> {selectedItem.type}</p>
              <p><strong>\u6807\u9898:</strong> {selectedItem.title}</p>
              {selectedItem.surface && (
                <p><strong>\u6765\u6E90:</strong> {selectedItem.surface}</p>
              )}
              {selectedItem.created && (
                <p><strong>\u65F6\u95F4:</strong> {selectedItem.created}</p>
              )}
              <hr className="divider" />

              {/* Content preview */}
              {selectedItem.content_preview && (
                <p className="context-body">{selectedItem.content_preview}</p>
              )}

              <hr className="divider" />

              {/* Tags */}
              <div className="ws-detail-section">
                <div className="ws-detail-section-header">
                  <strong>\u6807\u7B7E:</strong>
                  <button
                    type="button"
                    className="ws-item-action-btn"
                    onClick={() => {
                      setEditingTags(true)
                      setTagDraft(selectedItem.tags?.join(', ') || '')
                    }}
                  >
                    \u270F
                  </button>
                </div>
                {editingTags ? (
                  <div className="ws-detail-editor">
                    <input
                      type="text"
                      className="facet-input"
                      value={tagDraft}
                      onChange={(e) => setTagDraft(e.target.value)}
                      placeholder="\u6807\u7B7E1, \u6807\u7B7E2..."
                    />
                    <div className="btn-group">
                      <button type="button" className="btn btn-primary" onClick={handleSaveTags}>\u4FDD\u5B58</button>
                      <button type="button" className="btn btn-secondary" onClick={() => setEditingTags(false)}>\u53D6\u6D88</button>
                    </div>
                  </div>
                ) : (
                  <div className="ws-item-tags">
                    {selectedItem.tags?.length ? (
                      selectedItem.tags.map((tag) => (
                        <span key={tag} className="ws-item-tag">{tag}</span>
                      ))
                    ) : (
                      <span className="text-muted">\u65E0\u6807\u7B7E</span>
                    )}
                  </div>
                )}
              </div>

              <hr className="divider" />

              {/* Notes */}
              <div className="ws-detail-section">
                <div className="ws-detail-section-header">
                  <strong>\u5907\u6CE8:</strong>
                  <button
                    type="button"
                    className="ws-item-action-btn"
                    onClick={() => {
                      setEditingNote(true)
                      setNoteDraft(selectedItem.notes || '')
                    }}
                  >
                    \u270F
                  </button>
                </div>
                {editingNote ? (
                  <div className="ws-detail-editor">
                    <textarea
                      className="facet-input ws-dialog-textarea"
                      value={noteDraft}
                      onChange={(e) => setNoteDraft(e.target.value)}
                      placeholder="\u6DFB\u52A0\u5907\u6CE8..."
                      rows={3}
                    />
                    <div className="btn-group">
                      <button type="button" className="btn btn-primary" onClick={handleSaveNote}>\u4FDD\u5B58</button>
                      <button type="button" className="btn btn-secondary" onClick={() => setEditingNote(false)}>\u53D6\u6D88</button>
                    </div>
                  </div>
                ) : (
                  <p className="context-body">
                    {selectedItem.notes || <span className="text-muted">\u65E0\u5907\u6CE8</span>}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <p className="text-muted">\u70B9\u51FB\u6761\u76EE\u67E5\u770B\u8BE6\u60C5</p>
          )}
        </aside>
      </div>
    </div>
  )
}

export default Workspace
