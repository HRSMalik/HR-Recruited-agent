import { PageBanner, Button } from '../components'

export default function JobPosts() {
  return (
    <div className="page">
      <PageBanner title="Job posts" subtitle="3 posts" actions={<Button icon="plus">New job post</Button>} />
      <p className="page__placeholder">Job list + criteria editor (BL-FE-06).</p>
    </div>
  )
}
