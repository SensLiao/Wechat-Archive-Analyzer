import { useCallback } from 'react'
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
  { value: 'text', label: 'Text' },
  { value: 'image', label: 'Image' },
  { value: 'video', label: 'Video' },
  { value: 'file', label: 'File' },
  { value: 'link', label: 'Link' },
] as const

function FacetPanel({ facets, onChange, onApply, onClear }: FacetPanelProps) {
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

  return (
    <aside className="facet-panel">
      <h3 className="col-title">Filters</h3>

      {/* Time range */}
      <fieldset className="facet-group">
        <legend className="facet-group__legend">Time range</legend>
        <label className="facet-label">
          Since
          <input
            type="date"
            className="facet-input"
            value={facets.since}
            onChange={(e) => update('since', e.target.value)}
          />
        </label>
        <label className="facet-label">
          Until
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
        <legend className="facet-group__legend">Contact</legend>
        <input
          type="text"
          className="facet-input"
          placeholder="Filter by contact..."
          value={facets.contact}
          onChange={(e) => update('contact', e.target.value)}
        />
      </fieldset>

      {/* Conversation */}
      <fieldset className="facet-group">
        <legend className="facet-group__legend">Conversation</legend>
        <input
          type="text"
          className="facet-input"
          placeholder="Filter by conversation..."
          value={facets.conversation}
          onChange={(e) => update('conversation', e.target.value)}
        />
      </fieldset>

      {/* Message type checkboxes */}
      <fieldset className="facet-group">
        <legend className="facet-group__legend">Message type</legend>
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
        <legend className="facet-group__legend">Attachments</legend>
        <label className="facet-toggle">
          <input
            type="checkbox"
            checked={facets.hasAttachment}
            onChange={(e) => update('hasAttachment', e.target.checked)}
          />
          <span>Has attachment</span>
        </label>
      </fieldset>

      {/* Saved views placeholder */}
      <fieldset className="facet-group">
        <legend className="facet-group__legend">Saved views</legend>
        <p className="text-muted">No saved views yet</p>
      </fieldset>

      {/* Actions */}
      <div className="facet-actions">
        <button type="button" className="btn btn-secondary" onClick={onClear}>
          Clear all
        </button>
        <button type="button" className="btn btn-primary" onClick={onApply}>
          Apply
        </button>
      </div>
    </aside>
  )
}

export default FacetPanel
