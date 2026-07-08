import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import Overview from './pages/Overview'
import JobPosts from './pages/JobPosts'
import Shortlist from './pages/Shortlist'
import Candidates from './pages/Candidates'
import Interviews from './pages/Interviews'
import Meetings from './pages/Meetings'
import InterviewRoom from './pages/InterviewRoom'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Overview />} />
          <Route path="jobs" element={<JobPosts />} />
          <Route path="shortlist" element={<Shortlist />} />
          <Route path="candidates" element={<Candidates />} />
          <Route path="interviews" element={<Interviews />} />
          <Route path="meetings" element={<Meetings />} />
        </Route>
        <Route path="/interview/:room" element={<InterviewRoom />} />
      </Routes>
    </BrowserRouter>
  )
}
