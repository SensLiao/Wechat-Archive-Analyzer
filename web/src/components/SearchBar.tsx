import { useState, useEffect, useRef, useCallback } from 'react'
import SurfaceSwitcher, { type Surface } from './SurfaceSwitcher'

interface SearchBarProps {
  keyword: string
  surface: Surface
  onKeywordChange: (keyword: string) => void
  onSurfaceChange: (surface: Surface) => void
}

function SearchBar({
  keyword,
  surface,
  onKeywordChange,
  onSurfaceChange,
}: SearchBarProps) {
  const [localValue, setLocalValue] = useState(keyword)
  const inputRef = useRef<HTMLInputElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync external keyword changes (e.g. URL restore)
  useEffect(() => {
    setLocalValue(keyword)
  }, [keyword])

  // Debounced propagation
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      if (localValue !== keyword) {
        onKeywordChange(localValue)
      }
    }, 300)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [localValue, keyword, onKeywordChange])

  // Global Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalValue(e.target.value)
  }, [])

  return (
    <div className="search-bar-v2">
      <div className="search-bar-v2__input-wrap">
        <svg
          className="search-bar-v2__icon"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          className="search-bar-v2__input"
          placeholder="搜索消息..."
          value={localValue}
          onChange={handleChange}
          aria-label="搜索消息"
        />
        <kbd className="search-bar-v2__kbd">Ctrl+K</kbd>
      </div>
      <SurfaceSwitcher value={surface} onChange={onSurfaceChange} />
    </div>
  )
}

export default SearchBar
