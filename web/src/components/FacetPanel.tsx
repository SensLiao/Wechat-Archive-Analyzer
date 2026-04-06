import { useCallback, useState } from 'react'
import { FilterIcon, XIcon } from './Icons'
import type { Surface } from './SurfaceSwitcher'

export interface Facets {
  since: string
  until: string
  contact: string
  conversation: string
  msgTypes: Set<string>
  surface: Surface
  hasAttachment: boolean
}

export const EMPTY_FACETS: Facets = {
  since: '',
  until: '',
  contact: '',
  conversation: '',
  msgTypes: new Set(),
  surface: 'all',
  hasAttachment: false,
}

interface FacetPanelProps {
  facets: Facets
  onChange: (facets: Facets) => void
  onApply: () => void
  onClear: () => void
}

const MSG_TYPES = [
  { value: 'text', label: '文字' },
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
  { value: 'file', label: '文件' },
  { value: 'link', label: '链接' },
] as const

/** Count how many filters are active */
function activeFilterCount(facets: Facets): number {
  let count = 0
  if (facets.since) count++
  if (facets.until) count++
  if (facets.contact) count++
  if (facets.conversation) count++
  if (facets.msgTypes.size > 0) count++
  if (facets.hasAttachment) count++
  return count
}

function FacetPanel({ facets, onChange, onApply, onClear }: FacetPanelProps) {
  const [mobileOpen, setMobileOpen] = useState(false)

  const update = useCallback(
    <K extends keyof Facets>(key: K, value: Facets[K]) => {
      onChange({ ...facets, [key]: value })
    },
    [facets, onChange],
  )

  const toggleMsgType = useCallback(
    (type: string) => {
      const next = new Set(facets.msgTypes)
      if (next.has(type)) {
        next.delete(type)
      } else {
        next.add(type)
      }
      onChange({ ...facets, msgTypes: next })
    },
    [facets, onChange],
  )

  const filterCount = activeFilterCount(facets)

  const panelContent = (
    <>
      {/* Time range */}
      <fieldset className="facet-group">
        <legend className="facet-group__legend">时间范围</legend>
        <label className="facet-label">
          开始
          <input
            type="date"
            className="facet-input"
            value={facets.since}
            onChange={(e) => update('since', e.target.value)}
          />
        </label>
        <label className="facet-label">
          结束
          <input
            type="date"
            className="facet-input"
            value={facets.until}
            onChange={(e) => update('until', e.target.value)}
          />
        </label>
      </fieldset>

      {/* Contact */}
      <fieldset className="facet-group">
        <legend className="facet-group__legend">联系人</legend>
        <input
          type="text"
          className="facet-input"
          placeholder="按联系人筛选..."
          value={facets.contact}
          onChange={(e) => update('contact', e.target.value)}
        />
      </fieldset>

      {/* Conversation */}
      <fieldset className="facet-group">
        <legend className="facet-group__legend">会话</legend>
        <input
          type="text"
          className="facet-input"
          placeholder="按会话筛选..."
          value={facets.conversation}
          onChange={(e) => update('conversation', e.target.value)}
        />
      </fieldset>

      {/* Message type checkboxes */}
      <fieldset className="facet-group">
        <legend className="facet-group__legend">消息类型</legend>
        <div className="facet-checkboxes">
          {MSG_TYPES.map((mt) => (
            <label key={mt.value} className="facet-checkbox">
              <input
                type="checkbox"
                checked={facets.msgTypes.has(mt.value)}
                onChange={() => toggleMsgType(mt.value)}
              />
              <span>{mt.label}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Has attachment toggle */}
      <fieldset className="facet-group">
        <legend className="facet-group__legend">附件</legend>
        <label className="facet-toggle">
          <input
            type="checkbox"
            checked={facets.hasAttachment}
            onChange={(e) => update('hasAttachment', e.target.checked)}
          />
          <span>包含附件</span>
        </label>
      </fieldset>

      {/* Actions */}
      <div className="facet-actions">
        <button type="button" className="btn btn-secondary" onClick={() => { onClear(); setMobileOpen(false) }}>
          清除全部
        </button>
        <button type="button" className="btn btn-primary" onClick={() => { onApply(); setMobileOpen(false) }}>
          应用筛选
        </button>
      </div>
    </>
  )

  return (
    <>
      {/* Mobile filter toggle button */}
      <button
        type="button"
        className="facet-mobile-toggle"
        onClick={() => setMobileOpen(true)}
      >
        <FilterIcon size={16} />
        <span>筛选</span>
        {filterCount > 0 && <span className="facet-mobile-badge">{filterCount}</span>}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="facet-mobile-overlay" onClick={() => setMobileOpen(false)}>
          <div className="facet-mobile-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="facet-mobile-sheet-header">
              <h3 className="col-title">筛选条件</h3>
              <button
                type="button"
                className="facet-mobile-close"
                onClick={() => setMobileOpen(false)}
              >
                <XIcon size={20} />
              </button>
            </div>
            {panelContent}
          </div>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="facet-panel">
        <h3 className="col-title">筛选条件</h3>
        {panelContent}
      </aside>
    </>
  )
}

export default FacetPanel
