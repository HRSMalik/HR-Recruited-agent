# LiveKit SIP / Phone Calls (Outbound Interviews via Phone)

## Overview

LiveKit SIP lets your AI agent dial a candidate's phone number directly. The candidate answers on their regular phone — no app, no link required.

**Architecture:**
```
Your Backend
    ↓ CreateSIPParticipant API
LiveKit Server  ←→  LiveKit SIP Service  ←→  SIP Provider (Twilio/Telnyx)
                                                    ↓
                                             Candidate's Phone
```

---

## What You Need

### 1. LiveKit Cloud Account
- Sign up at [cloud.livekit.io](https://cloud.livekit.io)
- Get: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- SIP Service is included — no separate setup needed on LiveKit Cloud

### 2. A SIP Provider (choose one)

| Provider | Best for | Where to sign up |
|----------|----------|-----------------|
| **Telnyx** | Cheapest, international numbers | [telnyx.com](https://telnyx.com) |
| **Twilio** | Most documentation, reliable | [twilio.com](https://twilio.com) |
| **Plivo** | Asia/Middle East coverage | [plivo.com](https://plivo.com) |
| **LiveKit Phone Numbers** | Simplest setup (US only) | LiveKit Cloud Dashboard |

> **Easiest start:** LiveKit Phone Numbers (no separate SIP provider account needed, US numbers only).  
> **For Pakistan/international:** Use Telnyx or Twilio.

### 3. AI Model Keys
| Key | Provider |
|-----|----------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| `DEEPGRAM_API_KEY` | [console.deepgram.com](https://console.deepgram.com) — STT |
| `CARTESIA_API_KEY` | [cartesia.ai](https://cartesia.ai) — TTS (or ElevenLabs) |

---

## Setup: Option A — LiveKit Phone Numbers (US Only, Easiest)

1. Go to LiveKit Cloud Dashboard → **Phone Numbers** → Buy a number
2. Create a **Dispatch Rule** pointing to your agent
3. Done — no trunk config needed

Outbound calls still require an outbound trunk (see Option B below for the trunk part).

---

## Setup: Option B — Telnyx (Recommended for International)

### Step 1 — Telnyx Account Setup
1. Sign up at telnyx.com
2. Go to **Voice** → **SIP Trunks** → Create a trunk
3. Set **Origination** (for outbound): add LiveKit's SIP URI as a destination
   - LiveKit SIP URI: `sip.livekit.cloud` (shown in your LiveKit dashboard)
4. Purchase a phone number and assign it to the trunk
5. Copy: **Telnyx API Key**, **SIP username/password**, **phone number**

### Step 2 — Create LiveKit Outbound Trunk

```python
from livekit import api
import asyncio

async def create_outbound_trunk():
    lk = api.LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    trunk = await lk.sip.create_sip_outbound_trunk(
        api.CreateSIPOutboundTrunkRequest(
            trunk=api.SIPOutboundTrunkInfo(
                name="telnyx-outbound",
                address="sip.telnyx.com",
                numbers=["+1XXXXXXXXXX"],   # your Telnyx number
                auth_username="your_telnyx_sip_username",
                auth_password="your_telnyx_sip_password",
            )
        )
    )
    print(f"Trunk created: {trunk.sip_trunk_id}")
    # Save this trunk ID to .env as LIVEKIT_SIP_TRUNK_ID
```

Run this **once** to register the trunk. Save the returned `sip_trunk_id`.

---

## Making an Outbound Call

```python
from livekit import api

async def call_candidate(phone_number: str, room_name: str, candidate_name: str):
    lk = api.LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    # First ensure the room exists
    await lk.room.create_room(api.CreateRoomRequest(name=room_name))

    # Dial out to the candidate
    participant = await lk.sip.create_sip_participant(
        api.CreateSIPParticipantRequest(
            sip_trunk_id=os.getenv("LIVEKIT_SIP_TRUNK_ID"),
            sip_call_to=phone_number,       # e.g. "+923001234567"
            room_name=room_name,
            participant_identity=f"phone_{phone_number}",
            participant_name=candidate_name,
            play_ringtone=True,
        )
    )
    return participant
```

---

## Full Agent: Voice Interview via Phone

```python
# interview_agent.py
import os
import asyncio
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.agents import cli, WorkerOptions
from livekit.plugins import openai, deepgram, cartesia
from livekit import rtc, api

SYSTEM_PROMPT = """You are an AI interviewer for a technical role. 
Ask the candidate about their experience, assess their skills, and take notes.
Be professional, concise, and follow up on vague answers."""

class InterviewAgent(Agent):
    def __init__(self):
        super().__init__(instructions=SYSTEM_PROMPT)

async def entrypoint(ctx):
    session = AgentSession(
        stt=deepgram.STT(model="nova-2"),
        llm=openai.LLM(model="gpt-4o"),
        tts=cartesia.TTS(voice="sonic"),
    )
    await session.start(
        room=ctx.room,
        agent=InterviewAgent(),
        room_input_options=RoomInputOptions(noise_cancellation=True),
    )
    await session.generate_reply(
        instructions="Greet the candidate and begin the interview."
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

---

## .env Variables Required

```env
# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
LIVEKIT_SIP_TRUNK_ID=ST_xxxxxxxxxxxxxxxx   # from trunk creation step

# AI Models
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=...

# SIP Provider (Telnyx example)
TELNYX_API_KEY=KEY...
TELNYX_SIP_USERNAME=...
TELNYX_SIP_PASSWORD=...
TELNYX_PHONE_NUMBER=+1XXXXXXXXXX
```

---

## Running Locally (Dev Mode)

```bash
# Terminal 1 — LiveKit server
livekit-server --dev

# Terminal 2 — Your agent (points to local server)
LIVEKIT_URL=ws://localhost:7880 \
LIVEKIT_API_KEY=devkey \
LIVEKIT_API_SECRET=secret \
python interview_agent.py dev
```

> **Note:** SIP calls require LiveKit Cloud or a self-hosted SIP service — the local `--dev` server doesn't include SIP. Use local mode only for testing the agent logic with a browser-based test participant (LiveKit Agent Console).

---

## Integration with This Project

To wire this into the existing `voice_agent.py` and `booking_agent.py`:

1. Replace Vapi call initiation in `booking_agent.py` with `call_candidate()` above
2. Rewrite `voice_agent.py` to use `InterviewAgent` class (LiveKit) instead of Vapi webhooks
3. The transcript will come back via LiveKit transcription events instead of Vapi's callback — update `call_logs.py` accordingly
4. Interview scoring logic in `shortlisting_agent.py` stays the same — it only needs the final transcript text

---

## Cost Estimate

| Service | Cost |
|---------|------|
| LiveKit Cloud | Free tier available; ~$0.002/min after |
| Telnyx outbound calls | ~$0.005–0.01/min (varies by country) |
| Deepgram STT | ~$0.0043/min |
| OpenAI GPT-4o | ~$0.005/min of conversation |
| Cartesia TTS | ~$0.002/1k chars |

**Estimated per 30-min interview: ~$0.50–$1.00** (vs Vapi ~$0.05–0.10/min = $1.50–3.00)
