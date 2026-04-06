const API_BASE = '/api'

/** Standard API envelope returned by all backend endpoints. */
export interface ApiEnvelope<T = unknown> {
  ok: boolean
  data: T | null
  error: { code: string; message: string; remediation?: string | null } | null
}

/** Error thrown when the backend returns an envelope with ok=false. */
export class ApiError extends Error {
  code: string
  remediation: string | null

  constructor(code: string, message: string, remediation?: string | null) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.remediation = remediation ?? null
  }
}

function getToken(): string {
  // Token is stored in localStorage by main.tsx at page load time.
  // Also check URL as fallback (e.g. if main.tsx extraction was skipped).
  const params = new URLSearchParams(window.location.search)
  const urlToken = params.get('token')
  if (urlToken) {
    localStorage.setItem('wxtools_token', urlToken)
    window.history.replaceState({}, '', window.location.pathname)
    return urlToken
  }
  return localStorage.getItem('wxtools_token') || ''
}

/**
 * Fetch an API endpoint and unwrap the ApiEnvelope.
 *
 * On success (ok=true), returns the `data` field typed as T.
 * On failure (ok=false), throws an ApiError with the error code and message.
 * On HTTP-level failures (non-JSON, network errors), falls back to the
 * previous error handling.
 */
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

  // Try to parse as JSON envelope
  let body: unknown
  try {
    body = await res.json()
  } catch {
    // Non-JSON 401 means the session token is invalid (not a domain error)
    if (res.status === 401) {
      handleSessionExpiry()
      throw new Error('Session expired — reloading')
    }
    throw new Error(res.statusText || `HTTP ${res.status}`)
  }

  // Handle session expiry: only if 401 AND response is NOT an ApiEnvelope
  // (ApiEnvelope responses are domain errors like KEY_NOT_FOUND, not token issues)
  if (
    res.status === 401 &&
    !(body !== null && typeof body === 'object' && 'ok' in (body as Record<string, unknown>))
  ) {
    handleSessionExpiry()
    throw new Error('Session expired — reloading')
  }

  // If the response matches the ApiEnvelope shape, unwrap it
  if (
    body !== null &&
    typeof body === 'object' &&
    'ok' in (body as Record<string, unknown>)
  ) {
    const envelope = body as ApiEnvelope<T>
    if (envelope.ok) {
      return envelope.data as T
    }
    // Error envelope
    const err = envelope.error
    throw new ApiError(
      err?.code ?? 'UNKNOWN',
      err?.message ?? 'Unknown error',
      err?.remediation,
    )
  }

  // Fallback: legacy response (not wrapped) — return as-is for backward compat
  if (!res.ok) {
    const detail =
      (body as Record<string, unknown>)?.detail ??
      (body as Record<string, unknown>)?.message ??
      res.statusText
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  return body as T
}

/** Handle session expiry by clearing stale token and reloading. */
function handleSessionExpiry(): void {
  const hadToken = localStorage.getItem('wxtools_token')
  localStorage.removeItem('wxtools_token')

  if (hadToken) {
    // Only alert if we actually had a token (avoids loop on first load without token)
    // Use a non-blocking approach: set a flag and reload
    sessionStorage.setItem('wxtools_session_expired', '1')
  }

  // Reload to get fresh token from server
  window.location.reload()
}

/** Check if we just recovered from a session expiry (call in App mount). */
export function checkSessionRecovery(): string | null {
  const expired = sessionStorage.getItem('wxtools_session_expired')
  if (expired) {
    sessionStorage.removeItem('wxtools_session_expired')
    return '会话已过期（服务器可能已重启），页面已自动刷新。'
  }
  return null
}
