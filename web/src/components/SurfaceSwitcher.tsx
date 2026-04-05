import { useCallback } from 'react'

export type Surface = 'all' | 'chat' | 'public' | 'moments'

interface SurfaceSwitcherProps {
  value: Surface
  onChange: (surface: Surface) => void
  counts?: Partial<Record<Surface, number>>
}

const SURFACES: readonly { key: Surface; label: string; className: string }[] = [
  { key: 'all', label: 'All', className: 'surface-pill--all' },
  { key: 'chat', label: 'Chat', className: 'surface-pill--chat' },
  { key: 'public', label: 'Public', className: 'surface-pill--public' },
  { key: 'moments', label: 'Moments', className: 'surface-pill--moments' },
]

function SurfaceSwitcher({ value, onChange, counts }: SurfaceSwitcherProps) {
  const handleClick = useCallback(
    (surface: Surface) => () => onChange(surface),
    [onChange],
  )

  return (
    <div className="surface-switcher" role="tablist" aria-label="Surface filter">
      {SURFACES.map((s) => (
        <button
          key={s.key}
          type="button"
          role="tab"
          aria-selected={value === s.key}
          className={`surface-pill ${s.className} ${value === s.key ? 'surface-pill--active' : ''}`}
          onClick={handleClick(s.key)}
        >
          {s.label}
          {counts?.[s.key] != null && (
            <span className="surface-pill__count">{counts[s.key]}</span>
          )}
        </button>
      ))}
    </div>
  )
}

export default SurfaceSwitcher
