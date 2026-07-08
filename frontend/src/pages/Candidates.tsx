import { useEffect } from 'react'
import {
  PageBanner,
  Card,
  Table,
  Badge,
  Icon,
  EmptyState,
  type BadgeVariant,
} from '../components'
import { useCandidates } from '../stores/useCandidates'
import { useJobs } from '../stores/useJobs'
import type { Recommendation } from '../lib/schemas'

const REC: Record<Recommendation, { variant: BadgeVariant; label: string }> = {
  strong_yes: { variant: 'strong', label: 'Strong yes' },
  yes: { variant: 'yes', label: 'Yes' },
  maybe: { variant: 'neutral', label: 'Maybe' },
  review: { variant: 'review', label: 'Review' },
  no: { variant: 'no', label: 'No' },
}

const initials = (n: string) => n.split(' ').map((p) => p[0]).slice(0, 2).join('')

export default function Candidates() {
  const load = useCandidates((s) => s.load)
  const candidates = useCandidates((s) => s.candidates)
  const loaded = useCandidates((s) => s.loaded)
  const error = useCandidates((s) => s.error)
  const loadJobs = useJobs((s) => s.load)
  const jobs = useJobs((s) => s.jobs)

  useEffect(() => {
    load()
    loadJobs()
  }, [load, loadJobs])

  const jobTitle = (jdId?: string) => (jdId ? jobs.find((j) => j.jd_id === jdId)?.title ?? jdId : '—')

  return (
    <div className="page">
      <PageBanner title="Candidates" subtitle={`${candidates.length} candidate${candidates.length === 1 ? '' : 's'}`} />

      <Card>
        {error ? (
          <EmptyState icon="alert" title="Couldn't load candidates" hint={error} />
        ) : !loaded ? (
          <EmptyState icon="users" title="Loading candidates…" />
        ) : candidates.length === 0 ? (
          <EmptyState icon="users" title="No candidates yet" hint="Applicants appear here once their CV is ingested and parsed." />
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Job</th>
                <th className="r" style={{ width: 80 }}>CV fit</th>
                <th className="r" style={{ width: 110 }}>Composite</th>
                <th style={{ width: 130 }}>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c) => (
                <tr key={c.candidate_id}>
                  <td>
                    <div className="sl-cand">
                      <span className="av">{initials(c.name)}</span>
                      <div>
                        <div className="nm">{c.name}</div>
                        {c.email && <div className="em">{c.email}</div>}
                      </div>
                    </div>
                  </td>
                  <td style={{ color: 'var(--text-2)' }}>{jobTitle(c.jd_id)}</td>
                  <td className="r num">{c.fit_percent ?? '—'}</td>
                  <td className="r num">{c.composite_score != null ? Math.round(c.composite_score) : '—'}</td>
                  <td>
                    {c.recommendation ? (
                      <Badge variant={REC[c.recommendation].variant}>{REC[c.recommendation].label}</Badge>
                    ) : (
                      <span className="sl-none"><Icon name="clock" size={13} /> Not ranked</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  )
}
