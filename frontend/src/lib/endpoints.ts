import { apiFetch } from './api'
import type {
  RankedCandidate,
  Candidate,
  JobPost,
  CriteriaSet,
  CallLog,
  CallStats,
  Recommendation,
  Importance,
  RedFlag,
} from './schemas'

// Backend list endpoints return { items, total, skip, limit } with items as raw
// Mongo docs. We unwrap + map defensively so shape drift degrades gracefully
// rather than throwing deep in a component.
type Rec = Record<string, unknown>
const rows = (d: unknown): Rec[] => {
  const items = (d as { items?: unknown })?.items
  return Array.isArray(items) ? (items as Rec[]) : Array.isArray(d) ? (d as Rec[]) : []
}
const n = (v: unknown, def = 0): number => (typeof v === 'number' ? v : v != null && !isNaN(Number(v)) ? Number(v) : def)
const nn = (v: unknown): number | null => (v == null || isNaN(Number(v)) ? null : Number(v))
const s = (v: unknown, def = ''): string => (v == null ? def : String(v))

const REC_VALUES = ['strong_yes', 'yes', 'maybe', 'review', 'no']
const normRec = (v: unknown): Recommendation => (REC_VALUES.includes(String(v)) ? (String(v) as Recommendation) : 'review')
const normFlags = (v: unknown): RedFlag[] =>
  Array.isArray(v)
    ? v.map((f) =>
        typeof f === 'string'
          ? { type: f, label: f }
          : { type: s((f as Rec).type, 'flag'), label: s((f as Rec).label ?? (f as Rec).type, 'flag') },
      )
    : []

export const getJobPosts = (): Promise<JobPost[]> =>
  apiFetch<unknown>('/job-posts').then((d) =>
    rows(d).map((r) => ({
      jd_id: s(r._id ?? r.jd_id),
      title: s(r.title, '(untitled)'),
      status: r.status ? s(r.status) : undefined,
      applicants: r.applicants != null ? n(r.applicants) : undefined,
      shortlisted: r.shortlisted != null ? n(r.shortlisted) : undefined,
      criteria_status: r.criteria_status === 'confirmed' ? 'confirmed' : r.criteria_status === 'draft' ? 'draft' : undefined,
    })),
  )

export const getRankedCandidates = (jdId: string): Promise<RankedCandidate[]> =>
  apiFetch<unknown>(`/ranked-candidates?jd_id=${encodeURIComponent(jdId)}&limit=100`).then((d) =>
    rows(d).map((r) => ({
      candidate_id: s(r._id ?? r.candidate_id ?? r.cv_id),
      name: s(r.name, 'Unknown'),
      email: r.email ? s(r.email) : undefined,
      fit_percent: nn(r.fit_percent ?? r.cv_score ?? r.fit),
      interview_score: nn(r.interview_score),
      composite_score: n(r.composite_score ?? r.composite),
      recommendation: normRec(r.recommendation),
      red_flags: normFlags(r.red_flags),
      rank: r.rank != null ? n(r.rank) : undefined,
    })),
  )

// /shortlisted-candidates = candidates that have been CV-scored (fit_percent set),
// sorted best-first — the meaningful recruiter view. (/candidates is the opposite:
// only new applicants not yet scored.)
export const getCandidates = (): Promise<Candidate[]> =>
  apiFetch<unknown>('/shortlisted-candidates?limit=100').then((d) =>
    rows(d).map((r) => ({
      candidate_id: s(r._id ?? r.candidate_id ?? r.cv_id),
      name: s(r.name, 'Unknown'),
      email: r.email ? s(r.email) : undefined,
      jd_id: r.jd_id ? s(r.jd_id) : undefined,
      fit_percent: nn(r.fit_percent ?? r.cv_score ?? r.fit),
      composite_score: nn(r.composite_score ?? r.composite),
      recommendation: REC_VALUES.includes(String(r.recommendation)) ? (String(r.recommendation) as Recommendation) : undefined,
      status: r.status ? s(r.status) : undefined,
    })),
  )

export const getCriteria = (jdId: string): Promise<CriteriaSet> =>
  apiFetch<unknown>(`/jobs/${encodeURIComponent(jdId)}/criteria`).then((d) => {
    const raw = d as Rec
    const list = (raw.criteria ?? raw.items ?? []) as Rec[]
    return {
      status: raw.status === 'confirmed' ? 'confirmed' : 'draft',
      criteria: (Array.isArray(list) ? list : []).map((c) => ({
        criterion: s(c.criteria ?? c.criterion),
        importance: (['must_have', 'very_important', 'important', 'good_to_have'].includes(String(c.importance))
          ? String(c.importance)
          : 'important') as Importance,
      })),
    }
  })

export const generateCriteria = (jdId: string) =>
  apiFetch(`/jobs/${encodeURIComponent(jdId)}/criteria/generate`, { method: 'POST' })
export const updateCriteria = (jdId: string, criteria: { criterion: string; importance: Importance }[]) =>
  apiFetch(`/jobs/${encodeURIComponent(jdId)}/criteria`, { method: 'PUT', body: JSON.stringify({ criteria }) })
export const confirmCriteria = (jdId: string) =>
  apiFetch(`/jobs/${encodeURIComponent(jdId)}/criteria/confirm`, { method: 'POST' })

export const rerank = (jdId: string, weights: { cv: number; interview: number }) =>
  apiFetch(`/jobs/${encodeURIComponent(jdId)}/rerank`, {
    method: 'POST',
    body: JSON.stringify({ cv_weight: weights.cv, interview_weight: weights.interview }),
  })

export const getCallLogs = (): Promise<CallLog[]> =>
  apiFetch<unknown>('/call-logs').then((d) =>
    rows(d).map((r) => ({
      candidate_id: s(r._id ?? r.candidate_id),
      name: s(r.name ?? r.candidate_name, 'Unknown'),
      jd_id: r.jd_id ? s(r.jd_id) : undefined,
      category: s(r.category, 'unknown'),
      status: r.status ? s(r.status) : undefined,
      attempt_number: n(r.attempt_number, 1),
      duration_seconds: nn(r.duration_seconds ?? r.duration),
      started_at: r.started_at ? s(r.started_at) : r.created_at ? s(r.created_at) : undefined,
    })),
  )

export const getCallStats = (): Promise<CallStats> =>
  apiFetch<unknown>('/call-stats').then((d) => {
    const r = d as Rec
    return {
      total: n(r.total),
      completed: n(r.completed),
      no_show: n(r.no_show),
      incomplete: n(r.incomplete),
      retry_queue: n(r.pending_retry ?? r.retry_queue),
    }
  })

export const retryCall = (logId: string) =>
  apiFetch(`/call-logs/${encodeURIComponent(logId)}/retry-now`, { method: 'POST' })
export const closeCall = (logId: string) =>
  apiFetch(`/call-logs/${encodeURIComponent(logId)}/close`, { method: 'POST' })
