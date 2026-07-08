# booking-calendar-qa

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/booking-calendar-qa.md
**Default model:** sonnet   ·   **Mode:** mutating-sandbox

## Purpose
Validate the interview-booking surface (CRITIC product surface G4): timezone/DST correctness, double-booking and conflict detection, slot-availability race conditions, the cancellation/reschedule/no-show flows, invite delivery, and round-trip consistency between the agent's internal booking state and the external calendar. Answers: "does a booked slot land on the right wall-clock time everywhere, stay conflict-free under contention, and match the calendar exactly?"

## Inputs & preconditions
- Required artifacts: the booking business rules (slot length, buffer, working-hours window, allowed reschedule/cancel transitions, no-show policy), the agent's booking-state schema, and the calendar provider contract (Google Calendar / M365 Graph).
- Target: agent booking API base URL + auth (env); a **sandbox calendar** — a dedicated test calendar ID / test-tenant mailbox, never an interviewer's real calendar.
- Preconditions: assert the calendar target is the sandbox ID and the host is NON-PROD before any create/update/delete; seed a known set of free/busy blocks + one pre-existing event; clock/timezone fixtures available (interviewer TZ, candidate TZ, a DST-boundary date).

## Oracle (source of truth)
The **expected calendar state derived from the booking rules** — computed independently from inputs (slot start/end in UTC + each party's local wall-clock, conflict verdict, allowed next states), NOT the agent's own confirmation message. For round-trip, the **provider's event record** (start/end/attendees/status fetched back from the calendar) is the oracle for what was actually written. Timezone math is checked against the IANA `tz` database, never the SUT's offset claim.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate cases: book across TZ pairs; book on/around a DST spring-forward and fall-back boundary; book into an already-occupied slot (expect conflict); two concurrent bookings of the same slot (race); cancel → reschedule → no-show transitions and illegal transitions (e.g. reschedule a cancelled booking); invite payload + delivery; and an internal-state vs calendar round-trip after each mutation.
2. **Act** — against the sandbox calendar only, one case at a time: call the booking API, then fetch the event back from the provider. For the race case, fire two near-simultaneous book requests for the same slot. Skip-and-continue on a single case's failure; tag every created event for teardown.
3. **Verify** — recompute the expected UTC instant + each party's wall-clock from the input and `tz` rules and compare to both the agent state and the fetched event; assert conflicts are rejected; assert exactly one of two racing bookings wins; assert only allowed transitions succeed; assert internal state == calendar event field-by-field.

## Assertions & exit gate
- Stored start/end UTC instant matches the independently computed value; each party's displayed wall-clock is correct across the TZ pair and across the DST boundary (no off-by-one-hour).
- A booking into an occupied/buffer-violating slot is rejected with a conflict; no overlapping events exist on the sandbox calendar.
- Under two concurrent same-slot requests, exactly one succeeds and one is rejected — never two confirmed events (no lost-update / double-book).
- Cancel/reschedule/no-show follow the allowed state machine; illegal transitions are refused; invite payload (attendees, time, join link) is well-formed and queued/delivered.
- Round-trip: agent internal booking state equals the fetched calendar event (start, end, attendees, status) after every mutation.
- **Gate:** `booking_calendar_consistent` — 0 timezone/DST errors, 0 double-books or race-induced overlaps, 0 illegal-transition successes, AND internal state reconciles with the calendar.

## Output
Write `artifacts/booking-calendar-qa/report.json` per `shared/report-format.md`:
`{ flow, status, summary{...}, findings[], gate{name:"booking_calendar_consistent",passed} }`.
Each finding follows `shared/finding-schema.md`; `oracle` = the booking rule / `tz`-computed instant / fetched provider event (e.g. `rules.md: slot=45m+15m buffer`, `tz: America/New_York DST 2026-03-08`). Evidence = the request, the agent state, and the fetched event (event ids + UTC + per-TZ wall-clock); for the race case both responses and the resulting event count; record the seed/fixture id + sandbox calendar id. A double-book or wrong-TZ instant is `critical` (data-integrity / candidate misses interview); illegal-transition success is `major`.

## Guardrails
Per `shared/guardrails.md`: mutating flow — runs ONLY against the confirmed sandbox calendar / test tenant; assert sandbox id + NON-PROD host first or STOP with `status:error`. Calendar create/update/delete is a real external side effect — invites must go to seeded test attendees only, never real interviewers/candidates; suppress or sandbox-route invite email/SMS. Tear down every event created (delete tagged events; confirm teardown in the report). For the race case, cap concurrency and rate; back off on 429. Provider tokens via env, redacted from artifacts. No real candidate PII in evidence. Cap turns.

## Watch (do not gate)
Recurring-interview series and all-day events (expansion + per-instance edits), free/busy across overlapping secondary calendars, and provider webhook/push-notification echo lag — note observations but do not fail the gate on these yet.
