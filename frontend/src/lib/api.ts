// Central HTTP client — every API call goes through apiFetch().
// Backend uses X-API-Key auth (verify_api_key); base URL is the FastAPI host
// (VITE_API_BASE_URL in prod, localhost:8000 in dev).

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
    return localStorage.getItem(API_KEY_STORAGE) || ''
  } catch {
    return ''
  }
}

export async function apiFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey(),
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
