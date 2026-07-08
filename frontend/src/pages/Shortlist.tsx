import { useEffect, useState } from 'react'
import {
  PageBanner,
  Button,
  Card,
  Table,
  Badge,
  Icon,
  Modal,
  Input,
  Select,
  EmptyState,
  type BadgeVariant,
} from '../components'
import { useShortlist } from '../stores/useShortlist'
import { useJobs } from '../stores/useJobs'
import type { Recommendation } from '../lib/schemas'

const REC: Record<Recommendation, { variant: BadgeVariant; label: string }> = {
  strong_yes: { variant: 'strong', label: 'Strong yes' },
  yes: { variant: 'yes', label: 'Yes' },
  maybe: { variant: 'neutral', label: 'Maybe' },
  review: { variant: 'review', label: 'Review' },
  no: { variant: 'no', label: 'No' },
}

type Filter = 'all' | 'strong_yes' | 'yes' | 'review' | 'flags'
const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'strong_yes', label: 'Strong yes' },
  { key: 'yes', label: 'Yes' },
  { key: 'review', label: 'Review' },
  { key: 'flags', label: 'Has red flags' },
]

const initials = (n: string) => n.split(' ').map((p) => p[0]).slice(0, 2).join('')

export default function Shortlist() {
  const loadJobs = useJobs((s) => s.load)
  const jobs = useJobs((s) => s.jobs)
  const load = useShortlist((s) => s.load)
  const reRank = useShortlist((s) => s.reRank)
  const candidates = useShortlist((s) => s.candidates)
  const loaded = useShortlist((s) => s.loaded)
  const error = useShortlist((s) => s.error)
  const [selected, setSelected] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [rrOpen, setRrOpen] = useState(false)
  const [cv, setCv] = useState(40)
  const [iv, setIv] = useState(60)

  useEffect(() => {
    loadJobs()
  }, [loadJobs])

  useEffect(() => {
    if (jobs.length && !jobs.some((j) => j.jd_id === selected)) {
      setSelected(jobs[0].jd_id)
    }
  }, [jobs, selected])

  useEffect(() => {
    if (selected) load(selected)
  }, [selected, load])

  const rows = candidates.filter((c) =>
    filter === 'all' ? true : filter === 'flags' ? c.red_flags.length > 0 : c.recommendation === filter,
  )
  const recommended = candidates.filter((c) => c.recommendation === 'strong_yes' || c.recommendation === 'yes').length
  const selectedTitle = jobs.find((j) => j.jd_id === selected)?.title ?? 'Shortlist'

  const applyReRank = () => {
    setRrOpen(false)
    reRank({ cv: cv / 100, interview: iv / 100 }).catch(() => {
      /* surfaced via store error on reload */
    })
  }

  return (
    <div className="page">
      <PageBanner
        title="Shortlist"
        subtitle={`${selectedTitle} · ${candidates.length} scored · ${recommended} recommended`}
        actions={
          <>
            {jobs.length > 0 && (
              <Select
                aria-label="Select job"
                value={selected}
                onChange={(e) => setSelected(e.target.value)}
                options={jobs.map((j) => ({ value: j.jd_id, label: j.title }))}
              />
            )}
            <Button variant="ghost" icon="rerank" onClick={() => setRrOpen(true)} disabled={!candidates.length}>Re-rank</Button>
          </>
        }
      />

      <div className="sl-filters">
        {FILTERS.map((f) => (
          <button key={f.key} className={`sl-chip ${filter === f.key ? 'on' : ''}`} onClick={() => setFilter(f.key)}>
            {f.label}
          </button>
        ))}
        <span className="spacer">Weights: CV {cv}% · Interview {iv}%</span>
      </div>

      <Card>
        {error ? (
          <EmptyState icon="alert" title="Couldn't load the shortlist" hint={error} />
        ) : !loaded ? (
          <EmptyState icon="users" title="Loading shortlist…" />
        ) : candidates.length === 0 ? (
          <EmptyState
            icon="users"
            title="No ranked candidates yet"
            hint="Candidates are ranked automatically once they complete screening. Ranked results for this job will appear here."
          />
        ) : (
          <Table>
            <thead>
              <tr>
                <th style={{ width: 44 }}>#</th>
                <th>Candidate</th>
                <th className="r" style={{ width: 64 }}>CV</th>
                <th className="r" style={{ width: 84 }}>Interview</th>
                <th className="r" style={{ width: 140 }}>Composite</th>
                <th style={{ width: 130 }}>Recommendation</th>
                <th>Flags</th>
                <th style={{ width: 44 }}></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.candidate_id}>
                  <td className="sl-rk">{c.rank}</td>
                  <td>
                    <div className="sl-cand">
                      <span className="av">{initials(c.name)}</span>
                      <div>
                        <div className="nm">{c.name}</div>
                        {c.email && <div className="em">{c.email}</div>}
                      </div>
                    </div>
                  </td>
                  <td className="r num">{c.fit_percent ?? '—'}</td>
                  <td className="r num">{c.interview_score ?? '—'}</td>
                  <td className="r">
                    <div className="sl-comp">
                      <span className="bar"><i style={{ width: `${Math.min(100, c.composite_score)}%` }} /></span>
                      <b>{Math.round(c.composite_score)}</b>
                    </div>
                  </td>
                  <td>
                    <Badge variant={REC[c.recommendation].variant}>{REC[c.recommendation].label}</Badge>
                  </td>
                  <td>
                    {c.red_flags.length ? (
                      <div className="sl-flags">
                        {c.red_flags.map((f) => (
                          <span className="sl-flag" key={f.type}><Icon name="flag" />{f.label}</span>
                        ))}
                      </div>
                    ) : (
                      <span className="sl-none">—</span>
                    )}
                  </td>
                  <td>
                    <button className="sl-view" aria-label={`View ${c.name}`}><Icon name="chevronRight" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Modal
        open={rrOpen}
        title="Re-rank shortlist"
        onClose={() => setRrOpen(false)}
        footer={
          <>
            <Button variant="ghost" onClick={() => setRrOpen(false)}>Cancel</Button>
            <Button icon="rerank" onClick={applyReRank}>Apply weights</Button>
          </>
        }
      >
        <div className="rr-weights">
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Composite = CV × weight + interview × weight. Weights should sum to 100.
          </p>
          <Input label="CV weight (%)" type="number" value={cv} onChange={(e) => setCv(Number(e.target.value))} />
          <Input label="Interview weight (%)" type="number" value={iv} onChange={(e) => setIv(Number(e.target.value))} />
        </div>
      </Modal>
    </div>
  )
}
