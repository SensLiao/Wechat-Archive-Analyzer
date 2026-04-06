import { useState, useMemo } from 'react'
import WorkspaceItemCard from './WorkspaceItemCard'
import type { WorkspaceItemData } from './WorkspaceItemCard'

interface WorkspaceMeta {
  id: string
  name: string
  description: string
  item_count: number
  created_at: string
  updated_at: string
}

type SortKey = 'time' | 'type'
type ViewMode = 'timeline' | 'group' | 'list'

interface WorkspaceBoardProps {
  workspace: WorkspaceMeta | null
  items: WorkspaceItemData[]
  selectedItem: WorkspaceItemData | null
  onSelectItem: (item: WorkspaceItemData) => void
  onRemoveItem: (itemId: string) => void
  onEditNotes: (itemId: string, notes: string) => void
  onExportWorkspace: () => void
}

function WorkspaceBoard({
  workspace,
  items,
  selectedItem,
  onSelectItem,
  onRemoveItem,
  onEditNotes,
  onExportWorkspace,
}: WorkspaceBoardProps) {
  const [sortKey, setSortKey] = useState<SortKey>('time')
  const [viewMode, setViewMode] = useState<ViewMode>('timeline')
  const [tagFilter, setTagFilter] = useState<string>('')

  // Collect all unique tags
  const allTags = useMemo(() => {
    const tagSet = new Set<string>()
    for (const item of items) {
      if (item.tags) {
        for (const t of item.tags) tagSet.add(t)
      }
    }
    return Array.from(tagSet).sort()
  }, [items])

  // Filter and sort
  const displayItems = useMemo(() => {
    const filtered = tagFilter
      ? items.filter((it) => it.tags?.includes(tagFilter))
      : items

    const sorted = [...filtered]
    if (sortKey === 'time') {
      sorted.sort((a, b) => (b.created || '').localeCompare(a.created || ''))
    } else {
      sorted.sort((a, b) => a.type.localeCompare(b.type))
    }
    return sorted
  }, [items, tagFilter, sortKey])

  // Group items by type for group view
  const groupedItems = useMemo(() => {
    if (viewMode !== 'group') return null
    const groups: Record<string, WorkspaceItemData[]> = {}
    for (const item of displayItems) {
      const key = item.type
      if (!groups[key]) groups[key] = []
      groups[key].push(item)
    }
    return groups
  }, [displayItems, viewMode])

  if (!workspace) {
    return (
      <section className="col-results ws-board-empty">
        <p className="text-muted">选择工作区或创建新工作区</p>
      </section>
    )
  }

  return (
    <section className="col-results ws-board">
      {/* Header */}
      <div className="ws-board-header">
        <div>
          <h3 className="ws-board-name">{workspace.name}</h3>
          {workspace.description && (
            <p className="ws-board-desc">{workspace.description}</p>
          )}
          <span className="ws-board-count">{workspace.item_count} 项</span>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onExportWorkspace}
        >
          导出工作区
        </button>
      </div>

      {/* Toolbar */}
      <div className="ws-board-toolbar">
        {/* Tag filter */}
        <div className="ws-toolbar-segment">
          <select
            className="facet-input ws-tag-select"
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
          >
            <option value="">全部标签</option>
            {allTags.map((tag) => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
        </div>

        {/* Sort */}
        <div className="ws-toolbar-segment">
          <button
            type="button"
            className={`ws-toolbar-btn ${sortKey === 'time' ? 'ws-toolbar-btn-active' : ''}`}
            onClick={() => setSortKey('time')}
          >
            按时间
          </button>
          <button
            type="button"
            className={`ws-toolbar-btn ${sortKey === 'type' ? 'ws-toolbar-btn-active' : ''}`}
            onClick={() => setSortKey('type')}
          >
            按类型
          </button>
        </div>

        {/* View toggle */}
        <div className="ws-toolbar-segment">
          <button
            type="button"
            className={`ws-toolbar-btn ${viewMode === 'timeline' ? 'ws-toolbar-btn-active' : ''}`}
            onClick={() => setViewMode('timeline')}
            title="时间线"
          >
            │
          </button>
          <button
            type="button"
            className={`ws-toolbar-btn ${viewMode === 'group' ? 'ws-toolbar-btn-active' : ''}`}
            onClick={() => setViewMode('group')}
            title="分组"
          >
            ▦
          </button>
          <button
            type="button"
            className={`ws-toolbar-btn ${viewMode === 'list' ? 'ws-toolbar-btn-active' : ''}`}
            onClick={() => setViewMode('list')}
            title="列表"
          >
            ☰
          </button>
        </div>
      </div>

      {/* Items */}
      {displayItems.length === 0 ? (
        <div className="ws-board-empty-items">
          <p className="text-muted">从搜索结果中添加内容到工作区</p>
        </div>
      ) : viewMode === 'group' && groupedItems ? (
        <div className="ws-item-groups">
          {Object.entries(groupedItems).map(([type, groupItems]) => (
            <div key={type} className="ws-item-group">
              <h4 className="ws-item-group-title">{type}</h4>
              <div className={`ws-item-list ws-view-${viewMode}`}>
                {groupItems.map((item) => (
                  <WorkspaceItemCard
                    key={item.id}
                    item={item}
                    selected={selectedItem?.id === item.id}
                    onSelect={onSelectItem}
                    onRemove={onRemoveItem}
                    onEditNotes={onEditNotes}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className={`ws-item-list ws-view-${viewMode}`}>
          {displayItems.map((item) => (
            <WorkspaceItemCard
              key={item.id}
              item={item}
              selected={selectedItem?.id === item.id}
              onSelect={onSelectItem}
              onRemove={onRemoveItem}
              onEditNotes={onEditNotes}
            />
          ))}
        </div>
      )}
    </section>
  )
}

export default WorkspaceBoard
