import { z } from 'zod'

// Response shapes validated at the API boundary. Field names track the backend
// (candidates_info / ranked_candidates / job_descriptions / job_criteria /
// call_logs); reconciled against the live API when each screen is wired.

export const Recommendation = z.enum(['strong_yes', 'yes', 'maybe', 'review', 'no'])
export type Recommendation = z.infer<typeof Recommendation>

export const Importance = z.enum(['must_have', 'very_important', 'important', 'good_to_have'])
export type Importance = z.infer<typeof Importance>

export const RedFlag = z.object({ type: z.string(), label: z.string() })
export type RedFlag = z.infer<typeof RedFlag>

export const RankedCandidate = z.object({
  candidate_id: z.string(),
  name: z.string(),
  email: z.string().optional(),
  fit_percent: z.number().nullable().optional(),
  interview_score: z.number().nullable().optional(),
  composite_score: z.number(),
  recommendation: Recommendation,
  red_flags: z.array(RedFlag).default([]),
  rank: z.number().optional(),
})
export type RankedCandidate = z.infer<typeof RankedCandidate>

export const JobPost = z.object({
  jd_id: z.string(),
  title: z.string(),
  status: z.string().optional(),
  applicants: z.number().optional(),
  shortlisted: z.number().optional(),
  criteria_status: z.enum(['draft', 'confirmed']).optional(),
})
export type JobPost = z.infer<typeof JobPost>

export const Criterion = z.object({
  id: z.string().optional(),
  criterion: z.string(),
  importance: Importance,
})
export type Criterion = z.infer<typeof Criterion>

export const CriteriaSet = z.object({
  status: z.enum(['draft', 'confirmed']),
  criteria: z.array(Criterion),
})
export type CriteriaSet = z.infer<typeof CriteriaSet>

export const CallLog = z.object({
  candidate_id: z.string().optional(),
  name: z.string(),
  jd_id: z.string().optional(),
  category: z.string(),
  status: z.string().optional(),
  attempt_number: z.number(),
  duration_seconds: z.number().nullable().optional(),
  started_at: z.string().optional(),
})
export type CallLog = z.infer<typeof CallLog>

export const CallStats = z.object({
  total: z.number(),
  completed: z.number(),
  no_show: z.number(),
  incomplete: z.number(),
  avg_duration_seconds: z.number().optional(),
  retry_queue: z.number().optional(),
})
export type CallStats = z.infer<typeof CallStats>

export const Meeting = z.object({
  candidate_id: z.string().optional(),
  name: z.string(),
  role: z.string().optional(),
  start_time: z.string(),
  duration_min: z.number().optional(),
  status: z.string(),
  meet_link: z.string().optional(),
})
export type Meeting = z.infer<typeof Meeting>
