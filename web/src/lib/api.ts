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

/**
 * Get the session token. The backend injects it into the HTML as
 * window.__WXTOOLS_TOKEN__ on every page load, so it's always fresh
 * and survives server restarts without stale-token issues.
 */
function getToken(): string {
  // Primary: injected by backend into index.html
  const injected = (window as unknown as Record<string, unknown>).__WXTOOLS_TOKEN__
  if (typeof injected === 'string' && injected) {
    return injected
  }
  // Fallback: URL param (for dev mode / direct API access)
  const params = new URLSearchParams(window.location.search)
  const urlToken = params.get('token')
  if (urlToken) {
    return urlToken
  }
  return ''
}

/**
 * Fetch an API endpoint and unwrap the ApiEnvelope.
 *
 * On success (ok=true), returns the `data` field typed as T.
 * On failure (ok=false), throws an ApiError with the error code and message.
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
    if (res.status === 401) {
      throw new ApiError('SESSION_EXPIRED', '会话已过期，请刷新页面')
    }
    throw new Error(res.statusText || `HTTP ${res.status}`)
  }

  // Handle session expiry: only if 401 AND response is NOT an ApiEnvelope
  // (ApiEnvelope responses are domain errors like KEY_NOT_FOUND, not token issues)
  if (
    res.status === 401 &&
    !(body !== null && typeof body === 'object' && 'ok' in (body as Record<string, unknown>))
  ) {
    throw new ApiError('SESSION_EXPIRED', '会话已过期，请刷新页面')
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
