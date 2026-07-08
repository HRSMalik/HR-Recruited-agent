import { useParams } from 'react-router-dom'

// Standalone (outside the app shell) — the Meet-style LiveKit room (BL-FE-11).
export default function InterviewRoom() {
  const { room } = useParams()
  return (
    <div style={{ padding: 32 }}>
      <p style={{ color: 'var(--text-muted)' }}>Interview room {room ? `· ${room}` : ''} — BL-FE-11.</p>
    </div>
  )
}
