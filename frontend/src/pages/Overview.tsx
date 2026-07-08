import { useEffect } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import { PageBanner, Card, CardHeader, CardBody, SectionHeader, Icon, AlertBanner, type IconName } from '../components'
import { useCalls } from '../stores/useCalls'
import type { CallStats } from '../lib/schemas'

// Funnel + attention come from a pipeline endpoint once exposed; sample values
// until then. Screening-call numbers are live from /call-stats via the store.
const DEMO_STATS: CallStats = { total: 34, completed: 27, no_show: 4, incomplete: 3, retry_queue: 3 }

const FUNNEL = [
  { label: 'Applied', n: 86, pct: 100 },
  { label: 'CV passed', n: 41, pct: 48 },
  { label: 'Interviewed', n: 27, pct: 31 },
  { label: 'Booked', n: 12, pct: 14 },
  { label: 'Shortlisted', n: 9, pct: 10 },
]

const ATTENTION: { icon: IconName; tt: string; ds: string; cta: string }[] = [
  { icon: 'list', tt: '2 job criteria awaiting review', ds: 'AI drafted criteria for Product Designer & DevOps — confirm before they lock.', cta: 'Review criteria' },
  { icon: 'calendar', tt: '3 candidates ready to book', ds: 'Amara Okafor, Diego Martins and Priya Nair cleared the interview gate.', cta: 'Book calls' },
  { icon: 'clock', tt: '3 calls need a retry decision', ds: 'Screening calls stalled — choose retry now or close for each.', cta: 'Review retries' },
]

export default function Overview() {
  const load = useCalls((s) => s.load)
  const stats = useCalls((s) => s.stats)
  const error = useCalls((s) => s.error)
  useEffect(() => {
    load()
  }, [load])

  const s = stats ?? DEMO_STATS
  const total = s.total || 1
  const pct = Math.round((s.completed / total) * 100)
  const donut = [
    { name: 'Completed', value: s.completed, color: 'var(--accent)' },
    { name: 'No-show', value: s.no_show, color: '#c7ccd3' },
    { name: 'Incomplete', value: s.incomplete, color: '#e2b4ae' },
  ]

  return (
    <div className="page">
      <PageBanner title="Overview" subtitle="3 active posts · 86 applicants in pipeline" />
      {error && !stats && (
        <AlertBanner variant="info">
          Showing sample data — set VITE_API_BASE_URL to connect the backend for live numbers.
        </AlertBanner>
      )}

      <div className="ov-stats">
        <div className="ov-stat">
          <div className="lbl"><Icon name="barChart" />Applicants</div>
          <div className="val">86</div>
          <div className="delta up"><Icon name="trendingUp" />+12 this week</div>
        </div>
        <div className="ov-stat">
          <div className="lbl"><Icon name="list" />Shortlisted</div>
          <div className="val">9</div>
          <div className="delta">ready to book</div>
        </div>
        <div className="ov-stat">
          <div className="lbl"><Icon name="interviews" />Interviews done</div>
          <div className="val">{s.completed}<small> / {s.total}</small></div>
          <div className="delta">calls completed</div>
        </div>
        <div className="ov-stat">
          <div className="lbl"><Icon name="clock" />Retry queue</div>
          <div className="val">{s.retry_queue ?? 3}</div>
          <div className="delta warn">needs review</div>
        </div>
      </div>

      <div className="ov-grid">
        <Card>
          <CardHeader><SectionHeader title="Recruitment funnel" subtitle="Applied → shortlisted" /></CardHeader>
          <CardBody>
            <div className="ov-funnel">
              {FUNNEL.map((f) => (
                <div className="ov-frow" key={f.label}>
                  <span className="fl">{f.label}</span>
                  <span className="ov-track"><i style={{ width: `${f.pct}%` }} /></span>
                  <span className="fn"><b>{f.n}</b><span>{f.pct}%</span></span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)' }}>
              CV gate at fit 70 · interview gate at 60
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader><SectionHeader title="Screening calls" subtitle={`${s.total} total`} /></CardHeader>
          <CardBody>
            <div className="ov-donut">
              <div className="chart">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={donut}
                      dataKey="value"
                      innerRadius={54}
                      outerRadius={72}
                      startAngle={90}
                      endAngle={-270}
                      paddingAngle={2}
                      stroke="none"
                      isAnimationActive={false}
                    >
                      {donut.map((d) => (
                        <Cell key={d.name} fill={d.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="ctr"><b>{pct}%</b><small>completed</small></div>
              </div>
              <div className="ov-legend">
                {donut.map((d) => (
                  <div className="ov-leg" key={d.name}>
                    <span className="k" style={{ background: d.color }} />
                    <span className="nm">{d.name}</span>
                    <span className="v">{d.value}</span>
                    <span className="pc">{Math.round((d.value / total) * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      <Card className="ov-att">
        <CardHeader><SectionHeader title="Needs your attention" subtitle="3 decisions waiting" /></CardHeader>
        <CardBody>
          {ATTENTION.map((a) => (
            <div className="row" key={a.tt}>
              <span className="ic"><Icon name={a.icon} /></span>
              <div className="tx">
                <div className="tt">{a.tt}</div>
                <div className="ds">{a.ds}</div>
              </div>
              <button className="go">{a.cta}</button>
            </div>
          ))}
        </CardBody>
      </Card>
    </div>
  )
}
