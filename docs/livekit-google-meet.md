# LiveKit + Google Meet Integration

## Short Answer

**LiveKit does not natively support joining Google Meet as a bot.**

Google Meet has no official API for third-party bots to join meetings. LiveKit's platform is focused on its own WebRTC rooms and SIP telephony — it has no connector or plugin for Google Meet, Zoom, or Microsoft Teams.

---

## What's Actually Possible

### Option A — Run Interviews on LiveKit's Own Frontend (Recommended)

Instead of joining Google Meet, you host the interview call directly in LiveKit. The candidate gets a link to a LiveKit room (like a custom video call page), and your AI agent joins that room automatically.

**How it works:**
1. Your backend creates a LiveKit room and generates a token for the candidate.
2. Candidate opens the link in their browser (you build a simple React/Next.js page using LiveKit's SDK).
3. Your AI interview agent joins the same room automatically.
4. Full audio is available to the agent — no scraping, no workarounds.

**What you need:**
- LiveKit Cloud account → `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- LiveKit React SDK: `npm install @livekit/components-react livekit-client`
- Simple frontend page to display the video call to the candidate

**Pros:** Fully supported, clean, agent has direct audio access.  
**Cons:** Candidate doesn't use Google Meet — they use your custom call page.

---

### Option B — Browser Automation Bot (Hacky, Unsupported)

You can run a headless Chromium browser (via Playwright) that joins a Google Meet link, captures audio via a virtual audio device, and pipes it into your agent.

**Stack required:**
- `playwright` (Python/Node)
- Virtual audio sink (`pulseaudio` on Linux or `BlackHole` on macOS)
- Custom audio bridge to feed captured audio to your STT pipeline

**Why this is problematic:**
- Violates Google Meet's Terms of Service
- Fragile — breaks whenever Google updates the Meet UI
- Requires a Linux server with a virtual display (Xvfb)
- No LiveKit support — you'd be building a custom audio pipeline entirely

**Not recommended for production.**

---

### Option C — Use Google Meet's Add-on SDK (Future Path)

Google has a [Meet Add-ons SDK](https://developers.google.com/meet/add-ons) for building in-meeting sidepanel apps — but it does not allow audio access or bot participants. It is UI-only and not suitable for an AI interviewer.

---

## Recommendation for This Project

Use **Option A**. Replace the interview invitation link (currently via Vapi) with a LiveKit room link. Build a minimal call page (Next.js or plain HTML) using the LiveKit React components — it takes about 30 minutes.

The experience for the candidate is identical to any video call link — they click it, allow mic access, and the interview begins.

---

## Required Accounts / Keys for Option A

| Key | Where to get it |
|-----|----------------|
| `LIVEKIT_URL` | [LiveKit Cloud](https://cloud.livekit.io) → Project Settings |
| `LIVEKIT_API_KEY` | Same as above |
| `LIVEKIT_API_SECRET` | Same as above |
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| `DEEPGRAM_API_KEY` | [console.deepgram.com](https://console.deepgram.com) |
| `CARTESIA_API_KEY` or `ELEVENLABS_API_KEY` | [cartesia.ai](https://cartesia.ai) / [elevenlabs.io](https://elevenlabs.io) |

---

## Minimal Frontend Code (Option A)

```tsx
// pages/interview/[roomName].tsx
import { LiveKitRoom, VideoConference } from "@livekit/components-react";
import "@livekit/components-styles";

export default function InterviewRoom({ token, roomName }) {
  return (
    <LiveKitRoom
      serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
      token={token}
      connect={true}
    >
      <VideoConference />
    </LiveKitRoom>
  );
}
```

Token generation (backend, Python):
```python
from livekit import api

def create_candidate_token(room_name: str, candidate_name: str) -> str:
    token = api.AccessToken(
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET")
    )
    token.with_identity(candidate_name).with_name(candidate_name)
    token.with_grants(api.VideoGrants(room_join=True, room=room_name))
    return token.to_jwt()
```
