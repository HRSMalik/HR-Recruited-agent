import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Room, RoomEvent, Track, createLocalTracks, type RemoteTrack, type LocalTrack } from 'livekit-client'

// Meet-style LiveKit interview room. Connects when VITE_LIVEKIT_URL + a per-room
// token are configured (the token should come from a backend /interview/{room}/token
// endpoint); otherwise it renders a preview of the live experience.
type Line = { who: 'ai' | 'cand'; t: string }
const SAMPLE_LINES: Line[] = [
  { who: 'ai', t: 'Thanks for joining, Amara. Could you tell me about your experience with distributed systems?' },
  { who: 'cand', t: 'Sure. I owned the order-processing service — event-driven, Kafka-backed, ~4k events a second.' },
  { who: 'ai', t: 'How did you handle idempotency when a consumer re-processed an event?' },
  { who: 'cand', t: 'We keyed each event by a deterministic id and claimed it in a dedupe table before any side effect.' },
  { who: 'ai', t: 'Walk me through a time you diagnosed and fixed a slow database query in production.' },
]

export default function InterviewRoom() {
  const { room: roomName } = useParams()
  const navigate = useNavigate()
  const roomRef = useRef<Room | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [connected, setConnected] = useState(false)
  const [micOn, setMicOn] = useState(true)
  const [camOn, setCamOn] = useState(false)
  const [elapsed, setElapsed] = useState(504)
  const lines = SAMPLE_LINES

  useEffect(() => {
    const id = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const url = import.meta.env.VITE_LIVEKIT_URL
    const token = import.meta.env.VITE_LIVEKIT_TOKEN
    if (!url || !token) return // preview mode — no LiveKit server configured
    const rm = new Room()
    roomRef.current = rm
    rm.on(RoomEvent.Connected, () => setConnected(true))
    rm.on(RoomEvent.Disconnected, () => setConnected(false))
    rm.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
      if (track.kind === Track.Kind.Audio) track.attach()
    })
    let cancelled = false
    void (async () => {
      try {
        await rm.connect(url, token)
        if (cancelled) return
        const tracks = await createLocalTracks({ audio: true, video: false })
        tracks.forEach((t: LocalTrack) => rm.localParticipant.publishTrack(t))
      } catch {
        /* offline / preview */
      }
    })()
    return () => {
      cancelled = true
      rm.disconnect()
    }
  }, [roomName])

  const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
  const toggleMic = () => {
    const n = !micOn
    setMicOn(n)
    roomRef.current?.localParticipant.setMicrophoneEnabled(n).catch(() => {})
  }
  const toggleCam = () => {
    const n = !camOn
    setCamOn(n)
    roomRef.current?.localParticipant.setCameraEnabled(n).catch(() => {})
  }
  const leave = () => {
    roomRef.current?.disconnect()
    navigate('/meetings')
  }

  return (
    <div className="room">
      <div className="room-top">
        <div className="room-brand">
          <span className="sq">R</span>
          <span className="nm">TekHqs<small>Recruited</small></span>
        </div>
        <span className={`room-live ${connected ? '' : 'off'}`}>
          <span className="dot" />
          {connected ? 'Live interview' : 'Preview'}
        </span>
        <div className="room-meta">
          <span>Candidate <b>Amara Okafor</b></span>
          <span>Role <b>Senior Backend Engineer</b></span>
          <span className="room-timer">{fmt(elapsed)}</span>
          <span>{connected ? 'Connected · LiveKit' : `Room ${roomName ?? ''}`}</span>
        </div>
      </div>

      <div className="room-stage">
        <div className="room-vcol">
          <div className="room-tiles">
            <div className="room-tile ai">
              <span className="room-tag">AI · AUDIO</span>
              <div className="room-orb">
                <svg viewBox="0 0 24 24"><path d="M12 3v18M8 7v10M16 7v10M4 10v4M20 10v4" /></svg>
              </div>
              <div className="room-wave"><i /><i /><i /><i /><i /><i /><i /></div>
              <div className="room-name"><span className="mic" />AI Interviewer · speaking</div>
            </div>
            <div className="room-tile cam">
              <span className="room-tag">{camOn ? 'CAMERA ON' : 'CAMERA OFF'}</span>
              {camOn ? (
                <video ref={videoRef} autoPlay muted playsInline />
              ) : (
                <div className="room-figure">
                  <svg viewBox="0 0 24 24"><circle cx="12" cy="8.5" r="4" /><path d="M4 20a8 8 0 0 1 16 0" /></svg>
                </div>
              )}
              <div className="room-name"><span className={`mic ${micOn ? '' : 'off'}`} />Amara Okafor (you)</div>
            </div>
          </div>
          <div className="room-qbar">
            <div className="qn">QUESTION 3 / 6</div>
            <div className="qt">"Walk me through a time you diagnosed and fixed a slow database query in production."</div>
            <div className="room-qprog"><i className="done" /><i className="done" /><i className="cur" /><i /><i /><i /></div>
          </div>
        </div>

        <aside className="room-panel">
          <h3>LIVE TRANSCRIPT<b>Auto-captured both sides</b></h3>
          <div className="room-log">
            {lines.map((l, i) => (
              <div className={`room-line ${l.who}`} key={i}>
                <div className="w">{l.who === 'ai' ? 'AI INTERVIEWER' : 'AMARA OKAFOR'}</div>
                <p>{l.t}</p>
              </div>
            ))}
          </div>
        </aside>
      </div>

      <div className="room-controls">
        <div className="room-cwrap">
          <button className={`room-ctrl ${micOn ? '' : 'active-off'}`} onClick={toggleMic} aria-label="Toggle microphone">
            <svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
          </button>
          {micOn ? 'Mute' : 'Unmute'}
        </div>
        <div className="room-cwrap">
          <button className={`room-ctrl ${camOn ? '' : 'active-off'}`} onClick={toggleCam} aria-label="Toggle camera">
            <svg viewBox="0 0 24 24"><rect x="3" y="6" width="13" height="12" rx="2" /><path d="M16 10l5-3v10l-5-3" /></svg>
          </button>
          Camera
        </div>
        <div className="room-cwrap">
          <button className="room-ctrl" aria-label="Captions">
            <svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M7 11h3M8 14h6M14 11h3" /></svg>
          </button>
          Captions
        </div>
        <div className="room-cwrap">
          <button className="room-ctrl leave" onClick={leave}>
            <svg viewBox="0 0 24 24"><path d="M14 4h5v16h-5" /><path d="M10 12H3M7 8l-4 4 4 4" /></svg>
            Leave
          </button>
          <span>&nbsp;</span>
        </div>
      </div>
    </div>
  )
}
