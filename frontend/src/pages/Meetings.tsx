import { PageBanner, Card, EmptyState } from '../components'

// Scheduled interviews (booked meetings). No recruiter meetings-list endpoint
// exists on the backend yet, so this shows an honest empty state rather than
// sample data. Once a /meetings list is exposed, wire it here; Join opens the
// LiveKit interview room at /interview/:room.
export default function Meetings() {
  return (
    <div className="page mt-page">
      <PageBanner title="Meetings" subtitle="Scheduled interviews" />
      <Card>
        <EmptyState
          icon="calendar"
          title="No scheduled meetings"
          hint="Booked interviews will appear here once candidates pick a slot. Joining opens the live interview room."
        />
      </Card>
    </div>
  )
}
