import { useEffect } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import {
  PageBanner,
  Card,
  CardHeader,
  CardBody,
  SectionHeader,
  Table,
  Badge,
  EmptyState,
  type BadgeVariant,
} from '../components'
import { useCalls } from '../stores/useCalls'
import type { CallLog } from '../lib/schemas'

const OUTCOME: Record<string, { variant: BadgeVariant; label: string; retryable: boolean }> = {
  completed: { variant: 'strong', label: 'Completed', retryable: false },
  no_show: { variant: 'neutral', label: 'No-show', retryable: true },
  incomplete: { variant: 'no', label: 'Incomplete', retryable: true },
  pending_retry: { variant: 'review', label: 'Pending retry', retryable: true },
  retried: { variant: 'yes', label: 'Retried', retryable: false },
  exhausted: { variant: 'no', label: 'Exhausted', retryable: false },
}

const fmtDur = (s?: number | null) =>
  s == null ? '—' : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`

export default function Interviews() {
  const load = useCalls((s) => s.load)
  const retry = useCalls((s) => s.retry)
  const close = useCalls((s) => s.close)
  const logs = useCalls((s) => s.logs)
  const stats = useCalls((s) => s.stats)
  const loaded = useCalls((s) => s.loaded)
  const error = useCalls((s) => s.error)

  useEffect(() => {
    load()
  }, [load])

  if (error) {
    return (
      <div className="page">
        <PageBanner title="Interviews" />
        <Card><EmptyState icon="alert" title="Couldn't load call data" hint={error} /></Card>
      </div>
    )
  }
  if (!loaded || !stats) {
    return (
      <div className="page">
        <PageBanner title="Interviews" />
        <Card><EmptyState icon="interviews" title="Loading call log…" /></Card>
      </div>
    )
  }

  const s = stats
  const total = s.total || 1
  const pct = Math.round((s.completed / total) * 100)
  const donut = [
    { name: 'Completed', value: s.completed, color: 'var(--accent)' },
    { name: 'No-show', value: s.no_show, color: '#c7ccd3' },
    { name: 'Incomplete', value: s.incomplete, color: '#e2b4ae' },
  ]
  const queue = logs.filter((l) => (OUTCOME[l.category]?.retryable ?? false) && l.attempt_number < 3)
  const durs = logs.map((l) => l.duration_seconds).filter((d): d is number => d != null)
  const avgDur = durs.length ? Math.round(durs.reduce((a, b) => a + b, 0) / durs.length) : null
  const act = (l: CallLog, retryIt: boolean) => {
    const id = l.candidate_id ?? l.name
    ;(retryIt ? retry(id) : close(id)).catch(() => {
      /* surfaced via store error on reload */
    })
  }

  return (
    <div className="page">
      <PageBanner title="Interviews" subtitle={`AI screening calls · ${s.total} total · ${s.completed} completed · ${queue.length} pending retry`} />

      <div className="iv-stats">
        <div className="ov-stat"><div className="lbl">Completed</div><div className="val">{s.completed}</div></div>
        <div className="ov-stat"><div className="lbl">No-show</div><div className="val">{s.no_show}</div></div>
        <div className="ov-stat"><div className="lbl">Incomplete</div><div className="val">{s.incomplete}</div></div>
        <div className="ov-stat"><div className="lbl">Avg duration</div><div className="val">{fmtDur(avgDur)}</div></div>
        <div className="ov-stat"><div className="lbl">Retry queue</div><div className="val" style={{ color: 'var(--review-tx)' }}>{queue.length}</div></div>
      </div>

      <div className="iv-grid">
        <Card>
          <CardHeader><SectionHeader title="Call log" subtitle="All screening calls" /></CardHeader>
          {logs.length === 0 ? (
            <EmptyState icon="interviews" title="No screening calls yet" hint="Each candidate's AI screening call is logged here with its outcome." />
          ) : (
            <Table>
              <thead>
                <tr><th>Candidate</th><th>Outcome</th><th>Duration</th><th>Attempts</th><th>Started</th><th></th></tr>
              </thead>
              <tbody>
                {logs.map((l) => {
                  const o = OUTCOME[l.category] ?? { variant: 'neutral' as BadgeVariant, label: l.category, retryable: false }
                  return (
                    <tr key={l.candidate_id ?? l.name}>
                      <td style={{ fontWeight: 600 }}>{l.name}</td>
                      <td><Badge variant={o.variant}>{o.label}</Badge></td>
                      <td className="num">{fmtDur(l.duration_seconds)}</td>
                      <td className="num">{l.attempt_number}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{l.started_at ?? '—'}</td>
                      <td>
                        {o.retryable ? (
                          <button className="iv-lnk" onClick={() => act(l, true)}>Retry now</button>
                        ) : (
                          <button className="iv-lnk mut" onClick={() => act(l, false)}>Close</button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </Table>
          )}
        </Card>

        <div className="iv-side">
          <Card>
            <CardHeader><SectionHeader title="Outcomes" subtitle={`${s.total} calls`} /></CardHeader>
            <CardBody>
              {s.total === 0 ? (
                <EmptyState icon="barChart" title="No outcomes yet" />
              ) : (
                <div className="ov-donut">
                  <div className="chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={donut} dataKey="value" innerRadius={54} outerRadius={72} startAngle={90} endAngle={-270} paddingAngle={2} stroke="none" isAnimationActive={false}>
                          {donut.map((d) => (<Cell key={d.name} fill={d.color} />))}
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

          <Card>
            <CardHeader><SectionHeader title="Retry queue" subtitle={`${queue.length} pending`} /></CardHeader>
            <CardBody>
              {queue.length === 0 ? (
                <EmptyState icon="check" title="Queue is empty" hint="Stalled calls waiting on a retry decision appear here." />
              ) : (
                <div className="iv-retry">
                  {queue.map((l) => (
                    <div className="iv-rr" key={l.candidate_id ?? l.name}>
                      <span className="nm">{l.name}<small>attempt {l.attempt_number} of 3</small></span>
                      <button className="iv-lnk" onClick={() => act(l, true)}>Retry</button>
                      <button className="iv-lnk mut" onClick={() => act(l, false)}>Close</button>
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
