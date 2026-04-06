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
    if (res.status === 401 && localStorage.getItem('wxtools_token')) {
      localStorage.removeItem('wxtools_token')
      window.alert(
        'Session expired (server may have restarted). The page will reload to obtain a new token.',
      )
      window.location.reload()
      throw new Error('Session expired — reloading')
    }
    throw new Error(res.statusText || `HTTP ${res.status}`)
  }

  // Handle session expiry: only if 401 AND response is NOT an ApiEnvelope
  // (ApiEnvelope 401s are domain errors like KEY_PASSWORD_WRONG, not token issues)
  if (
    res.status === 401 &&
    localStorage.getItem('wxtools_token') &&
    !(body !== null && typeof body === 'object' && 'ok' in (body as Record<string, unknown>))
  ) {
    localStorage.removeItem('wxtools_token')
    window.alert(
      'Session expired (server may have restarted). The page will reload to obtain a new token.',
    )
    window.location.reload()
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
