import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import { PageBanner, Card, CardHeader, CardBody, SectionHeader, Icon, EmptyState } from '../components'
import { useCalls } from '../stores/useCalls'
import { useJobs } from '../stores/useJobs'

// Every number on this page is live from the backend (/call-stats, /job-posts).
// No sample data: while loading we show a placeholder, on error we surface it,
// and empty collections render honest empty states.
export default function Overview() {
  const navigate = useNavigate()
  const loadCalls = useCalls((s) => s.load)
  const stats = useCalls((s) => s.stats)
  const loaded = useCalls((s) => s.loaded)
  const error = useCalls((s) => s.error)
  const loadJobs = useJobs((s) => s.load)
  const jobs = useJobs((s) => s.jobs)

  useEffect(() => {
    loadCalls()
    loadJobs()
  }, [loadCalls, loadJobs])

  if (error) {
    return (
      <div className="page">
        <PageBanner title="Overview" />
        <Card><EmptyState icon="alert" title="Couldn't load live data" hint={error} /></Card>
      </div>
    )
  }
  if (!loaded || !stats) {
    return (
      <div className="page">
        <PageBanner title="Overview" />
        <Card><EmptyState icon="barChart" title="Loading dashboard…" /></Card>
      </div>
    )
  }

  const s = stats
  const total = s.total || 1
  const pct = Math.round((s.completed / total) * 100)
  const retry = s.retry_queue ?? 0
  const donut = [
    { name: 'Completed', value: s.completed, color: 'var(--accent)' },
    { name: 'No-show', value: s.no_show, color: '#c7ccd3' },
    { name: 'Incomplete', value: s.incomplete, color: '#e2b4ae' },
  ]
  const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`

  return (
    <div className="page">
      <PageBanner title="Overview" subtitle={`${plural(jobs.length, 'job post')} · ${plural(s.total, 'screening call')}`} />

      <div className="ov-stats">
        <div className="ov-stat">
          <div className="lbl"><Icon name="briefcase" />Job posts</div>
          <div className="val">{jobs.length}</div>
          <div className="delta">on the board</div>
        </div>
        <div className="ov-stat">
          <div className="lbl"><Icon name="interviews" />Screening calls</div>
          <div className="val">{s.total}</div>
          <div className="delta">logged</div>
        </div>
        <div className="ov-stat">
          <div className="lbl"><Icon name="check" />Interviews done</div>
          <div className="val">{s.completed}<small> / {s.total}</small></div>
          <div className="delta">completed</div>
        </div>
        <div className="ov-stat">
          <div className="lbl"><Icon name="clock" />Retry queue</div>
          <div className="val">{retry}</div>
          <div className="delta warn">needs review</div>
        </div>
      </div>

      <div className="ov-grid">
        <Card className="ov-att">
          <CardHeader>
            <SectionHeader title="Needs your attention" subtitle={retry > 0 ? `${plural(retry, 'decision')} waiting` : 'All clear'} />
          </CardHeader>
          <CardBody>
            {retry > 0 ? (
              <div className="row">
                <span className="ic"><Icon name="clock" /></span>
                <div className="tx">
                  <div className="tt">{plural(retry, 'call')} need a retry decision</div>
                  <div className="ds">Screening calls stalled — choose retry now or close for each.</div>
                </div>
                <button className="go" onClick={() => navigate('/interviews')}>Review retries</button>
              </div>
            ) : (
              <EmptyState icon="check" title="Nothing needs attention" hint="Retry decisions and reviews show up here as candidates move through screening." />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader><SectionHeader title="Screening calls" subtitle={`${s.total} total`} /></CardHeader>
          <CardBody>
            {s.total === 0 ? (
              <EmptyState icon="interviews" title="No screening calls yet" hint="Outcomes appear here once candidates complete their AI screening." />
            ) : (
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
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
