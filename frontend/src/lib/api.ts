// Central HTTP client — every API call goes through apiFetch().
// Backend auth is `Authorization: Bearer <API_KEY>` (utils/auth.py). The key
// comes from VITE_API_KEY (dev) or localStorage; base URL is the FastAPI host.

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_KEY_STORAGE = 'hr_api_key'

export class ApiError extends Error {
  status: number
  detail?: string
  constructor(status: number, message: string, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function apiKey(): string {
  try {
    return localStorage.getItem(API_KEY_STORAGE) || import.meta.env.VITE_API_KEY || ''
  } catch {
    return import.meta.env.VITE_API_KEY || ''
  }
}

export async function apiFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const key = apiKey()
  const res = await fetch(BASE + path, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(key ? { Authorization: `Bearer ${key}` } : {}),
      ...(opts.headers || {}),
    },
  })
  if (!res.ok) {
    let detail: string | undefined
    try {
      detail = ((await res.json()) as { detail?: string })?.detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail || `Request failed (${res.status})`, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const API_KEY_KEY = API_KEY_STORAGE
