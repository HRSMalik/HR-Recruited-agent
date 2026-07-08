import { z } from 'zod'
import { apiFetch } from './api'
import {
  RankedCandidate,
  JobPost,
  CriteriaSet,
  CallLog,
  CallStats,
  type Importance,
} from './schemas'

// Typed calls; responses are Zod-validated so a shape drift surfaces at the
// boundary rather than as an undefined deep in a component.

export const getRankedCandidates = (jdId: string) =>
  apiFetch<unknown>(`/ranked-candidates?jd_id=${encodeURIComponent(jdId)}`).then((d) =>
    z.array(RankedCandidate).parse(d),
  )

export const getJobPosts = () =>
  apiFetch<unknown>('/job-posts').then((d) => z.array(JobPost).parse(d))

export const getCriteria = (jdId: string) =>
  apiFetch<unknown>(`/jobs/${encodeURIComponent(jdId)}/criteria`).then((d) => CriteriaSet.parse(d))

export const generateCriteria = (jdId: string) =>
  apiFetch<unknown>(`/jobs/${encodeURIComponent(jdId)}/criteria/generate`, { method: 'POST' }).then(
    (d) => CriteriaSet.parse(d),
  )

export const updateCriteria = (jdId: string, criteria: { criterion: string; importance: Importance }[]) =>
  apiFetch(`/jobs/${encodeURIComponent(jdId)}/criteria`, {
    method: 'PUT',
    body: JSON.stringify({ criteria }),
  })

export const confirmCriteria = (jdId: string) =>
  apiFetch(`/jobs/${encodeURIComponent(jdId)}/criteria/confirm`, { method: 'POST' })

export const rerank = (jdId: string, weights: { cv: number; interview: number }) =>
  apiFetch(`/jobs/${encodeURIComponent(jdId)}/rerank`, {
    method: 'POST',
    body: JSON.stringify(weights),
  })

export const getCallLogs = () =>
  apiFetch<unknown>('/call-logs').then((d) => z.array(CallLog).parse(d))

export const getCallStats = () =>
  apiFetch<unknown>('/call-stats').then((d) => CallStats.parse(d))

export const retryCall = (logId: string) =>
  apiFetch(`/call-logs/${encodeURIComponent(logId)}/retry-now`, { method: 'POST' })

export const closeCall = (logId: string) =>
  apiFetch(`/call-logs/${encodeURIComponent(logId)}/close`, { method: 'POST' })
