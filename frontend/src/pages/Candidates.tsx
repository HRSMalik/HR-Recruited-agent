import {
  PageBanner,
  Button,
  Card,
  CardHeader,
  CardBody,
  SectionHeader,
  Badge,
} from '../components'

// Single-candidate detail. Composed from candidates_info + criteria_scores +
// interview_insights; sample data until a /candidates/{id} detail endpoint is wired.
const CRITERIA = [
  { cn: 'Distributed systems / event-driven', imp: 'Must have', v: 94 },
  { cn: 'Python + FastAPI depth', imp: 'Must have', v: 90 },
  { cn: 'Database performance tuning', imp: 'Very important', v: 86 },
  { cn: 'Cloud / infra (AWS)', imp: 'Important', v: 78 },
  { cn: 'Domain: fintech', imp: 'Good to have', v: 60 },
]
const SKILLS = ['Python', 'FastAPI', 'Kafka', 'PostgreSQL', 'AWS', 'Redis', 'Docker']

export default function Candidates() {
  return (
    <div className="page">
      <PageBanner
        title="Amara Okafor"
        subtitle="Senior Backend Engineer · applied 3d ago"
        actions={<Badge variant="strong">Strong yes</Badge>}
      />

      <div className="cd-grid">
        <div className="cd-col">
          <Card>
            <CardBody>
              <div className="cd-head">
                <span className="av">AO</span>
                <div className="who">
                  <div className="nm">Amara Okafor</div>
                  <div className="mt">amara.okafor@mail.com · +1 (415) 555-0142</div>
                </div>
                <div className="score">
                  <div className="v">90</div>
                  <div className="l">composite · CV 40% + interview 60%</div>
                </div>
              </div>
              <div className="cd-decide">
                <Button icon="calendar">Advance to booking</Button>
                <Button variant="ghost">Hold for review</Button>
                <Button variant="danger">Reject</Button>
                <span className="note">AI recommends. A recruiter makes the final call — this decision is logged.</span>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader><SectionHeader title="Fit by criterion" /></CardHeader>
            <CardBody>
              <div className="cd-crit">
                {CRITERIA.map((c) => (
                  <div className="cd-crow" key={c.cn}>
                    <span className="cn">{c.cn}<span className="imp">{c.imp}</span></span>
                    <span className="cb"><i style={{ width: `${c.v}%` }} /></span>
                    <span className="cv">{c.v}</span>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader><SectionHeader title="Interview" /></CardHeader>
            <CardBody>
              <div className="cd-insight" style={{ marginBottom: 14 }}>
                Clear, structured communicator. Strong on idempotency and event ordering; gave a concrete
                production example of diagnosing a slow query. Slightly light on team-leadership signals.
              </div>
              <div className="cd-script">
                <div className="cd-line ai">
                  <div className="w">AI INTERVIEWER</div>
                  <p>How did you handle idempotency when a consumer re-processed an event?</p>
                </div>
                <div className="cd-line">
                  <div className="w">AMARA OKAFOR</div>
                  <p>We keyed each event by a deterministic id and claimed it in a dedupe table before any side effect.</p>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>

        <div className="cd-col">
          <Card>
            <CardHeader><SectionHeader title="CV summary" /></CardHeader>
            <CardBody>
              <div className="cd-kv">
                <div className="r"><span className="k">Experience</span><span className="v">6 yrs professional</span></div>
                <div className="r"><span className="k">Last role</span><span className="v">Sr. Backend Eng · Fintech</span></div>
                <div className="r"><span className="k">Education</span><span className="v">BSc Computer Science</span></div>
              </div>
              <div className="cd-skills">
                {SKILLS.map((s) => (
                  <span className="cd-sk" key={s}>{s}</span>
                ))}
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardHeader><SectionHeader title="Screening call" /></CardHeader>
            <CardBody>
              <div className="cd-kv">
                <div className="r"><span className="k">Outcome</span><span className="v" style={{ color: 'var(--accent-text)' }}>Completed</span></div>
                <div className="r"><span className="k">Duration</span><span className="v">9m 04s</span></div>
                <div className="r"><span className="k">Interview score</span><span className="v">89</span></div>
                <div className="r"><span className="k">Red flags</span><span className="v">None</span></div>
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
