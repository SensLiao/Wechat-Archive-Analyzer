import { useState, useMemo } from 'react'
import WorkspaceItemCard from './WorkspaceItemCard'
import type { WorkspaceItemData } from './WorkspaceItemCard'

interface WorkspaceMeta {
  id: string
  name: string
  description: string
  item_count: number
  created: string
  updated: string
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
        <p className="text-muted">\u9009\u62E9\u5DE5\u4F5C\u533A\u6216\u521B\u5EFA\u65B0\u5DE5\u4F5C\u533A</p>
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
          <span className="ws-board-count">{workspace.item_count} \u9879</span>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onExportWorkspace}
        >
          \u5BFC\u51FA\u5DE5\u4F5C\u533A
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
            <option value="">\u5168\u90E8\u6807\u7B7E</option>
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
            \u6309\u65F6\u95F4
          </button>
          <button
            type="button"
            className={`ws-toolbar-btn ${sortKey === 'type' ? 'ws-toolbar-btn-active' : ''}`}
            onClick={() => setSortKey('type')}
          >
            \u6309\u7C7B\u578B
          </button>
        </div>

        {/* View toggle */}
        <div className="ws-toolbar-segment">
          <button
            type="button"
            className={`ws-toolbar-btn ${viewMode === 'timeline' ? 'ws-toolbar-btn-active' : ''}`}
            onClick={() => setViewMode('timeline')}
            title="\u65F6\u95F4\u7EBF"
          >
            \u2502
          </button>
          <button
            type="button"
            className={`ws-toolbar-btn ${viewMode === 'group' ? 'ws-toolbar-btn-active' : ''}`}
            onClick={() => setViewMode('group')}
            title="\u5206\u7EC4"
          >
            \u25A6
          </button>
          <button
            type="button"
            className={`ws-toolbar-btn ${viewMode === 'list' ? 'ws-toolbar-btn-active' : ''}`}
            onClick={() => setViewMode('list')}
            title="\u5217\u8868"
          >
            \u2630
          </button>
        </div>
      </div>

      {/* Items */}
      {displayItems.length === 0 ? (
        <div className="ws-board-empty-items">
          <p className="text-muted">\u4ECE\u641C\u7D22\u7ED3\u679C\u4E2D\u6DFB\u52A0\u5185\u5BB9\u5230\u5DE5\u4F5C\u533A</p>
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
