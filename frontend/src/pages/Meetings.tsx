import { useNavigate } from 'react-router-dom'
import { PageBanner, Button, Icon } from '../components'

// Scheduled interviews (booked meetings). Sample data until the backend exposes
// a recruiter meetings list; Join opens the LiveKit interview room (BL-FE-11).
type Meeting = {
  room: string
  time: string
  ampm: string
  dur: string
  name: string
  role: string
  status: 'confirmed' | 'awaiting'
}
const DAYS: { label: string; meetings: Meeting[] }[] = [
  {
    label: 'Today · Mon 8 Jul',
    meetings: [
      { room: 'amara-okafor', time: '10:00', ampm: 'AM', dur: '30 min', name: 'Amara Okafor', role: 'Senior Backend Engineer · composite 90', status: 'confirmed' },
      { room: 'diego-martins', time: '2:30', ampm: 'PM', dur: '30 min', name: 'Diego Martins', role: 'Senior Backend Engineer · composite 84', status: 'confirmed' },
    ],
  },
  {
    label: 'Tomorrow · Tue 9 Jul',
    meetings: [
      { room: 'priya-nair', time: '11:00', ampm: 'AM', dur: '30 min', name: 'Priya Nair', role: 'Senior Backend Engineer · composite 76', status: 'confirmed' },
      { room: 'sara-haddad', time: '3:00', ampm: 'PM', dur: '30 min', name: 'Sara Haddad', role: 'Senior Backend Engineer · composite 67', status: 'awaiting' },
    ],
  },
]

const initials = (n: string) => n.split(' ').map((p) => p[0]).slice(0, 2).join('')
const count = DAYS.reduce((a, d) => a + d.meetings.length, 0)

export default function Meetings() {
  const navigate = useNavigate()
  return (
    <div className="page mt-page">
      <PageBanner
        title="Meetings"
        subtitle={`Scheduled interviews · ${count} upcoming`}
        actions={
          <span className="mt-seg">
            <button className="on">Upcoming</button>
            <button>Past</button>
          </span>
        }
      />

      {DAYS.map((day) => (
        <div className="mt-day" key={day.label}>
          <div className="dh">{day.label}</div>
          <div className="mt-card">
            {day.meetings.map((m) => (
              <div className="mt-meet" key={m.room}>
                <div className="mt-tm">
                  <div className="t">{m.time}<span>{m.ampm}</span></div>
                  <div className="d">{m.dur}</div>
                </div>
                <div className="mt-who">
                  <span className="av">{initials(m.name)}</span>
                  <div>
                    <div className="nm">{m.name}</div>
                    <div className="ro">{m.role}</div>
                  </div>
                </div>
                <span className={`mt-badge ${m.status === 'confirmed' ? 'ok' : 'wait'}`}>
                  <span className="dot" />
                  {m.status === 'confirmed' ? 'Confirmed' : 'Awaiting candidate'}
                </span>
                <div className="mt-acts">
                  {m.status === 'confirmed' ? (
                    <Button icon="video" onClick={() => navigate(`/interview/${m.room}`)}>Join</Button>
                  ) : (
                    <Button variant="ghost" disabled>Join</Button>
                  )}
                  <Button variant="ghost" aria-label="More">
                    <Icon name={m.status === 'confirmed' ? 'calendar' : 'more'} size={15} />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
