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
  type BadgeVariant,
} from '../components'
import { useCalls } from '../stores/useCalls'
import type { CallLog, CallStats } from '../lib/schemas'

const DEMO_STATS: CallStats = { total: 34, completed: 27, no_show: 4, incomplete: 3, retry_queue: 3 }
const DEMO_LOGS: CallLog[] = [
  { candidate_id: '1', name: 'Amara Okafor', category: 'completed', attempt_number: 1, duration_seconds: 544, started_at: 'Today 09:12' },
  { candidate_id: '2', name: 'Diego Martins', category: 'completed', attempt_number: 1, duration_seconds: 520, started_at: 'Today 08:50' },
  { candidate_id: '3', name: 'Tom Reilly', category: 'no_show', attempt_number: 1, started_at: 'Today 08:20' },
  { candidate_id: '4', name: 'Lucas Bianchi', category: 'pending_retry', attempt_number: 2, started_at: 'Today 07:45' },
  { candidate_id: '5', name: 'Sara Haddad', category: 'incomplete', attempt_number: 1, duration_seconds: 190, started_at: 'Yest 17:30' },
  { candidate_id: '6', name: 'Priya Nair', category: 'retried', attempt_number: 2, duration_seconds: 475, started_at: 'Yest 15:10' },
  { candidate_id: '7', name: 'Wei Chen', category: 'exhausted', attempt_number: 3, started_at: 'Yest 16:00' },
]

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
  const storedLogs = useCalls((s) => s.logs)
  const storedStats = useCalls((s) => s.stats)

  useEffect(() => {
    load()
  }, [load])

  const logs = storedLogs.length ? storedLogs : DEMO_LOGS
  const s = storedStats ?? DEMO_STATS
  const total = s.total || 1
  const pct = Math.round((s.completed / total) * 100)
  const donut = [
    { name: 'Completed', value: s.completed, color: 'var(--accent)' },
    { name: 'No-show', value: s.no_show, color: '#c7ccd3' },
    { name: 'Incomplete', value: s.incomplete, color: '#e2b4ae' },
  ]
  const queue = logs.filter((l) => (OUTCOME[l.category]?.retryable ?? false) && l.attempt_number < 3)
  const act = (l: CallLog, retryIt: boolean) => {
    const id = l.candidate_id ?? l.name
    ;(retryIt ? retry(id) : close(id)).catch(() => {
      /* sample mode / offline */
    })
  }

  return (
    <div className="page">
      <PageBanner title="Interviews" subtitle={`AI screening calls · ${s.total} total · ${s.completed} completed · ${queue.length} pending retry`} />

      <div className="iv-stats">
        <div className="ov-stat"><div className="lbl">Completed</div><div className="val">{s.completed}</div></div>
        <div className="ov-stat"><div className="lbl">No-show</div><div className="val">{s.no_show}</div></div>
        <div className="ov-stat"><div className="lbl">Incomplete</div><div className="val">{s.incomplete}</div></div>
        <div className="ov-stat"><div className="lbl">Avg duration</div><div className="val">8m 12s</div></div>
        <div className="ov-stat"><div className="lbl">Retry queue</div><div className="val" style={{ color: 'var(--review-tx)' }}>{queue.length}</div></div>
      </div>

      <div className="iv-grid">
        <Card>
          <CardHeader><SectionHeader title="Call log" subtitle="All screening calls" /></CardHeader>
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
        </Card>

        <div className="iv-side">
          <Card>
            <CardHeader><SectionHeader title="Outcomes" subtitle={`${s.total} calls`} /></CardHeader>
            <CardBody>
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
            </CardBody>
          </Card>

          <Card>
            <CardHeader><SectionHeader title="Retry queue" subtitle={`${queue.length} pending`} /></CardHeader>
            <CardBody>
              <div className="iv-retry">
                {queue.map((l) => (
                  <div className="iv-rr" key={l.candidate_id ?? l.name}>
                    <span className="nm">{l.name}<small>attempt {l.attempt_number} of 3</small></span>
                    <button className="iv-lnk" onClick={() => act(l, true)}>Retry</button>
                    <button className="iv-lnk mut" onClick={() => act(l, false)}>Close</button>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
