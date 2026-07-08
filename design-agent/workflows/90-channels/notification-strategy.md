# notification-strategy

**Group:** 90-channels
**Runs as:** subagent: ../.claude/agents/interaction-designer.md
**Mode:** build (writer + verify loop) · audit (notification-system scan)   ·   **Default model:** sonnet

## Purpose
Own the cross-channel notification system (in-app + push + email): a taxonomy by intent, frequency/batching/digest rules that prevent fatigue, a preference center with granular opt-out, quiet-hours timing, and one consistent in-app inbox/badge pattern — so the product informs without nagging.

## Inputs & preconditions
- From `project-design-config.md`: component library (inbox/badge, `AlertBanner`, toast, preference-center form controls — reuse before inventing), token source + names, breakpoints, theme, locked rules, and the configured channels/providers (grep — never assume push/email is wired).
- Target: every system-initiated message — application status changes, interview scheduling, recruiter actions, reminders, marketing/digest — across each live channel and the in-app inbox.
- Preconditions: dev server reachable; existing notification components + preference store read before adding any; never invent a channel the project hasn't configured.

## Oracle (source of truth)
NN/g, *Indicators, Validations, and Notifications* (https://www.nngroup.com/articles/indicators-validations-notifications/) — a notification is a system-initiated, often out-of-context message; its weight must match its urgency, and the user must stay in control.
- **hard:** every notification declares a **purpose** (one taxonomy class: transactional / digest / marketing), a **channel** (in-app / push / email — chosen by urgency, not "all of them"), a **frequency cap** (a batching/digest rule, not per-event firehose), and an **opt-out** reachable from a preference center. Marketing/digest is **opt-out-able** and **never the only path** to a transactional outcome.
- **hard:** defaults are **respectful** — high-interruption channels (push) default ON only for time-critical transactional events; digest/marketing default to a **batched** cadence, never per-event; quiet-hours suppress non-critical pushes; the in-app **badge count is accurate** and clears on read (no phantom/stale counts). Any transient in-app announcement rides a pre-mounted live region (`role="status"`/`alert`).
- **soft:** taxonomy is clean (no marketing smuggled as transactional); batching/digest granularity feels considered; preference center is discoverable and granular per-type-per-channel; inbox/badge pattern is consistent across the app.

## Standards & techniques
- **Taxonomy → channel + cadence:** *transactional* (status change, interview booked, action required) → in-app + push/email, immediate, capped against duplicates; *digest* (activity rollups, new-match summaries) → email/in-app, batched daily/weekly, one message not N; *marketing* (announcements, re-engagement) → email-only by default, opt-out, frequency-capped.
- **Anti-fatigue:** batch related events into one notification; collapse a burst into a digest; cap per channel per window; de-dupe so one event never fires the same message twice. Match interruption weight to urgency — push is the most intrusive, reserve it.
- **Preference center + opt-out:** a granular preference center (per type × per channel toggles), reachable in ≤2 clicks; every notification (esp. email) carries a working unsubscribe/manage-preferences path; opting out of marketing must not disable transactional safety messages.
- **Timing / quiet-hours:** respect a quiet-hours window (and timezone) — defer or drop non-critical pushes; only genuinely time-critical transactional messages may break quiet hours.
- **In-app inbox/badge:** one consistent inbox surface + a badge that shows an accurate unread count, clears on read, and never shows a phantom count; read/unread state persists; status colour always paired with an icon/label.
- **Watch (do not gate):** the **Push API + Declarative Web Push / Notification Triggers** for time-based local scheduling are EMERGING and uneven across the configured targets — feature-detect (`'Notification' in window`, `'showTrigger' in ...`) and keep a server-scheduled fallback. Track it; never make cadence/quiet-hours depend on it as a hard oracle.

## Step sequence
- **audit:** enumerate every system message → classify each into the taxonomy → for each assert purpose + channel-fit + a frequency cap/batching rule + a reachable opt-out; check defaults are respectful (push off for non-critical, digest/marketing batched, quiet-hours honoured) and the badge count is accurate/clears on read → flag missing caps, mis-channeled or untyped messages, missing opt-outs, aggressive defaults → emit findings (read-only, no edits).
- **build:** Explore (≥2 taxonomy-to-channel/cadence mappings from existing components, read-only) → Judge (purpose/channel/cap/opt-out + respectful-defaults + inbox-consistency rubric, order-swapped) → Implement (one writer; build the preference center + inbox/badge from existing components/tokens, wire the taxonomy/cadence as config — markup/style/copy only) → Verify (Playwright drives each notification path + the preference center @ breakpoints, screenshots inbox/badge/quiet-hours states; axe-core + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every notification has a taxonomy class, a single justified channel, a frequency cap/batching rule, and a preference-center opt-out; marketing/digest is opt-out-able and never the sole transactional path.
- Defaults respectful: push off for non-critical, digest/marketing batched not per-event, quiet-hours suppress non-critical pushes; badge count accurate and clears on read; transient in-app announcements fire through a pre-mounted live region.
- Preference center, inbox, and badge built from existing components; all colour/spacing resolves to tokens; status colour paired with icon/label.
- **Gate:** hard oracles green (purpose + channel + cap + opt-out + respectful defaults + accurate badge + axe + console) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/notification-strategy/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: heuristic`, `oracle: hard` for a missing cap/opt-out, mis-channeled or untyped message, or aggressive default; `heuristic` Nielsen #3 User control and freedom / #1 Visibility of system status), plus the verification block (a screenshot per notification surface + the preference center + inbox/badge states @ breakpoints + hard-oracle results + rubric score) for build mode.

## Guardrails
Per `shared/guardrails.md`: reuse the inbox/badge/`AlertBanner`/preference-center components before inventing; never guess a token name — grep the source; never invent an unconfigured channel. Preserve logic byte-for-byte (markup/style/copy/config only — not the send/dispatch or subscription logic); if respectful defaults need a send-logic change, stop and flag it. Read-only audit makes no edits; one writer for build; trust the screenshot over the diff.
