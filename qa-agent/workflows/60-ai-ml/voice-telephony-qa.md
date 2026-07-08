# voice-telephony-qa

**Category:** 60-ai-ml
**Runs as:** subagent: ../.claude/agents/specialized-tester.md (voice/telephony sub-mode)
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Validate the CRITIC product-surface G1 Vapi voice agent end to end: transcription accuracy, speech intelligibility, conversational turn dynamics, telephony control paths, and whether a completed call actually achieved its booking goal. Answers — "on a labelled scenario set, does the voice agent hear, speak, take turns, survive telephony faults, and close the call's objective correctly?"

## Inputs & preconditions
- Required artifacts: a **labelled call-scenario set** (https://www.vapi.ai/) — each scenario carrying audio fixture(s), reference transcript, expected agent turns, expected DTMF/IVR path, and the expected **booking outcome** (goal achieved: appointment booked / declined / escalated). Plus the WER scoring config and per-metric thresholds.
- Target: a Vapi **test-mode / simulation** account or recorded-call replay harness — base URL + assistant id via env. Confirm the assistant is a non-production/sandbox assistant.
- Preconditions: assert **NON-PROD** assistant and **no real PSTN dialling** — STOP and `status:error` if a live outbound-call/real-phone-number path is wired. Scenario fixtures present (clean, multi-accent, background-noise, silence, drop, DTMF variants); transcript references normalized (lowercase, punctuation/filler stripped) before scoring.

## Oracle (source of truth)
The **labelled scenario set's reference transcripts + expected outcomes**, scored by standard **WER methodology** — `WER = (S + D + I) / N` (substitutions + deletions + insertions over reference words) on the normalized reference. Turn-taking, barge-in, DTMF path, and reconnect are judged against each scenario's expected event sequence; booking success against the scenario's expected outcome label. Never the agent's own self-reported confidence or "I booked it."

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate one case per scenario across the axes: ASR/WER (clean + multi-accent + background-noise), TTS intelligibility, **barge-in/interruption**, turn-taking + end-of-utterance detection, **DTMF/IVR navigation**, **call-drop + reconnect**, silence/timeout behaviour, and booking-outcome scenarios. Pin each case's reference transcript and expected outcome.
2. **Act** — replay/simulate one fixture at a time through the Vapi test-mode harness; capture the produced transcript, TTS audio/text, turn-event timeline, DTMF emissions, and final call state. Skip-and-continue on a single fixture's transport failure; honour Vapi rate limits.
3. **Verify** — score each case against the oracle: compute WER vs reference; check barge-in interrupted TTS within the latency bound; confirm end-of-utterance fired before agent reply (no talk-over, no dead-air stall); validate the DTMF/IVR path and post-drop reconnect/resume; assert silence/timeout fell back correctly; assert the final **booking outcome** matches the expected label. Capture evidence per failure.

## Assertions & exit gate
- **ASR:** mean WER ≤ threshold per noise/accent tier (e.g. clean ≤ 0.10, noisy/accented ≤ 0.20); no scenario exceeds its hard cap.
- **TTS:** output is intelligible and matches intended text (no truncation/garbling); pronunciation of names/numbers correct.
- **Barge-in:** user interruption stops agent TTS within the latency bound and the agent yields the turn — no talk-over.
- **Turn-taking:** end-of-utterance detected correctly; no premature cut-off, no >Ns dead-air stall.
- **DTMF/IVR:** correct tones emitted/recognized; menu navigated to the expected node.
- **Call-drop:** drop is detected and reconnect resumes context (no restart-from-zero, no double-booking).
- **Silence/timeout:** silence triggers the configured re-prompt/timeout, not a hang.
- **Booking outcome:** final outcome label == expected for every goal scenario.
- **Gate:** `wer_within_threshold_and_booking_goal_met` — passes when all WER tiers are within threshold AND every booking scenario reaches its expected outcome AND no barge-in/turn-taking/DTMF/reconnect assertion fails. Wrong booking outcome or barge-in talk-over → **critical**; WER over a tier cap, missed reconnect, or broken DTMF path → **major**; minor dead-air/timing drift within tolerance → **minor**.

## Output
Write `artifacts/voice-telephony-qa/report.json` per `shared/report-format.md`:
`{ flow:"voice-telephony-qa", status, summary{total,passed,failed,skipped}, findings[], gate{name:"wer_within_threshold_and_booking_goal_met",passed} }`.
Each finding (`QA-VOICE-NNN`) names the scenario id + reference (transcript/expected-outcome) in `oracle`, captures the fixture id, produced-vs-reference transcript, computed WER, turn/DTMF/reconnect timeline, and final outcome in `evidence`, and the remediation (tune VAD/end-of-utterance threshold, fix barge-in interrupt, correct DTMF map, add reconnect-resume) in `suggested_fix`.

## Guardrails
Per `shared/guardrails.md`: **non-destructive — recorded fixtures / Vapi test-mode only, never a real outbound call** to a real number (mark NOT RUN with a sandbox note otherwise); confirm NON-PROD assistant or `status:error`. Golden/synthesized audio only — no real caller PII; record the fixture/seed id in every finding for deterministic repro. Secrets (Vapi key, assistant id) via env, redacted from artifacts; honour rate limits, back off on 429; cap `maxTurns`.

> **Watch (do not gate):** EMERGING — emotion/sentiment-aware TTS prosody, streaming partial-transcript correction, and code-switching (mid-utterance language change) accuracy. Track as observations; do not fail the gate on these yet.
