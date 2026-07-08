import { PageBanner } from '../components'

export default function Overview() {
  return (
    <div className="page">
      <PageBanner title="Overview" subtitle="Recruiter dashboard" />
      <p className="page__placeholder">Overview — funnel, screening calls, needs-your-attention (BL-FE-05).</p>
    </div>
  )
}
