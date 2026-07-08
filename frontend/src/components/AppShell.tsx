import { NavLink, Outlet } from 'react-router-dom'
import { Icon, type IconName } from './Icon'
import { useSession } from '../stores/session'

const NAV: { to: string; label: string; icon: IconName; end?: boolean }[] = [
  { to: '/', label: 'Overview', icon: 'home', end: true },
  { to: '/jobs', label: 'Job posts', icon: 'briefcase' },
  { to: '/shortlist', label: 'Shortlist', icon: 'list' },
  { to: '/candidates', label: 'Candidates', icon: 'users' },
  { to: '/interviews', label: 'Interviews', icon: 'interviews' },
  { to: '/meetings', label: 'Meetings', icon: 'calendar' },
]

export function AppShell() {
  const theme = useSession((s) => s.theme)
  const toggleTheme = useSession((s) => s.toggleTheme)
  return (
    <div className="app-shell">
      <aside className="side">
        <div className="side__brand">
          <span className="sq">R</span>
          <span className="nm">
            TekHqs<small>Recruited</small>
          </span>
        </div>
        <nav className="side__nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) => (isActive ? 'nav-link on' : 'nav-link')}
            >
              <Icon name={n.icon} />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="side__foot">
          <span className="av">RM</span>
          <span className="who">
            Rana Malik<small>Recruiter</small>
          </span>
          <button
            className="ui-icon-btn theme"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          >
            <Icon name={theme === 'light' ? 'moon' : 'sun'} size={16} />
          </button>
        </div>
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
