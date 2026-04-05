const API_BASE = '/api'

function getToken(): string {
  // Token can come from URL param on first load or localStorage
  const params = new URLSearchParams(window.location.search)
  const urlToken = params.get('token')
  if (urlToken) {
    localStorage.setItem('wxtools_token', urlToken)
    // Clean URL
    window.history.replaceState({}, '', window.location.pathname)
    return urlToken
  }
  return localStorage.getItem('wxtools_token') || ''
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Token': token,
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail?.message || err.detail || res.statusText)
  }
  return res.json()
}
