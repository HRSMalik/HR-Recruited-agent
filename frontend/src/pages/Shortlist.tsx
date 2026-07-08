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
  type BadgeVariant,
} from '../components'
import { useShortlist } from '../stores/useShortlist'
import type { RankedCandidate, Recommendation } from '../lib/schemas'

const REC: Record<Recommendation, { variant: BadgeVariant; label: string }> = {
  strong_yes: { variant: 'strong', label: 'Strong yes' },
  yes: { variant: 'yes', label: 'Yes' },
  maybe: { variant: 'neutral', label: 'Maybe' },
  review: { variant: 'review', label: 'Review' },
  no: { variant: 'no', label: 'No' },
}

const DEMO: RankedCandidate[] = [
  { candidate_id: '1', name: 'Amara Okafor', email: 'amara.okafor@mail.com', fit_percent: 92, interview_score: 89, composite_score: 90, recommendation: 'strong_yes', red_flags: [], rank: 1 },
  { candidate_id: '2', name: 'Diego Martins', email: 'd.martins@mail.com', fit_percent: 85, interview_score: 83, composite_score: 84, recommendation: 'strong_yes', red_flags: [], rank: 2 },
  { candidate_id: '3', name: 'Priya Nair', email: 'priya.nair@mail.com', fit_percent: 78, interview_score: 75, composite_score: 76, recommendation: 'yes', red_flags: [], rank: 3 },
  { candidate_id: '4', name: 'Lucas Bianchi', email: 'lucas.b@mail.com', fit_percent: 81, interview_score: 68, composite_score: 73, recommendation: 'review', red_flags: [{ type: 'tenure', label: 'Tenure gap' }], rank: 4 },
  { candidate_id: '5', name: 'Sara Haddad', email: 's.haddad@mail.com', fit_percent: 72, interview_score: 64, composite_score: 67, recommendation: 'yes', red_flags: [], rank: 5 },
  { candidate_id: '6', name: 'Wei Chen', email: 'wei.chen@mail.com', fit_percent: 69, interview_score: 58, composite_score: 62, recommendation: 'review', red_flags: [{ type: 'claim', label: 'Unverified claim' }], rank: 6 },
]

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
  const load = useShortlist((s) => s.load)
  const reRank = useShortlist((s) => s.reRank)
  const stored = useShortlist((s) => s.candidates)
  const [filter, setFilter] = useState<Filter>('all')
  const [rrOpen, setRrOpen] = useState(false)
  const [cv, setCv] = useState(40)
  const [iv, setIv] = useState(60)

  useEffect(() => {
    load('sbe')
  }, [load])

  const candidates = stored.length ? stored : DEMO
  const rows = candidates.filter((c) =>
    filter === 'all' ? true : filter === 'flags' ? c.red_flags.length > 0 : c.recommendation === filter,
  )

  const applyReRank = () => {
    setRrOpen(false)
    reRank({ cv: cv / 100, interview: iv / 100 }).catch(() => {
      /* sample mode / offline */
    })
  }

  return (
    <div className="page">
      <PageBanner
        title="Shortlist"
        subtitle="Senior Backend Engineer · 41 scored · 9 recommended"
        actions={<Button variant="ghost" icon="rerank" onClick={() => setRrOpen(true)}>Re-rank</Button>}
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
