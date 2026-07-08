# email-deliverability-qa

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/email-deliverability-qa.md
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Validate CRITIC's outbound transactional comms (offer, shortlist, interview-invite, rejection emails) against their template spec and compliance rules — capturing every message in a TEST-DOUBLE MAIL SINK so nothing is ever live-sent to a real recipient.

## Inputs & preconditions
- Required artifacts: template spec (merge-field list, subject/body, CTA targets), compliance ruleset (CAN-SPAM, TCPA, quiet-hours/throttling policy), DNS records for the sending domain (SPF, DKIM selector, DMARC policy), idempotency-key contract for transactional sends.
- Target: a seeded NON-PROD CRITIC instance with SMTP repointed at a mail sink (Mailpit / Mailhog / a seeded provider sandbox); the sink's HTTP API base URL for message capture.
- Preconditions: SMTP host resolves to the sink, NOT a real relay — assert before acting; sink reachable and empty (purge); seeded recipient fixtures with synthetic addresses (`@example.test`); STOP with `status:error` if any real provider/relay host or production CRITIC host is detected.

## Oracle (source of truth)
The **template spec** (expected merge-field substitutions, subject, CTA URLs), the **compliance ruleset** (mandatory unsubscribe/physical-address per CAN-SPAM, consent + quiet-hours per TCPA), and the **DNS records** (SPF/DKIM/DMARC alignment) — checked against the **captured message in the sink**. NEVER infer correctness from "the app sent it, so it's right."

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate cases per template: merge-field render (full vs missing/null field), link/CTA validity, unsubscribe + CAN-SPAM footer presence, SPF/DKIM/DMARC alignment, bounce + complaint handling, spam-score, quiet-hours/throttle adherence, and idempotency (trigger the same offer/shortlist event twice).
2. **Act** — fire one seeded trigger event at a time through CRITIC; let it deliver into the sink; pull the captured message via the sink API. For idempotency, replay the identical event/idempotency-key. For bounce/complaint, configure the sink to return a hard-bounce/FBL response and re-trigger.
3. **Verify** — assert each captured message against the oracle; on failure capture the raw message (headers + HTML), the seed/fixture id, and the trigger event id as evidence.

## Assertions & exit gate
- Merge fields fully resolved — no literal `{{name}}`/`{{role}}` or empty-token leakage in subject or body.
- Every link/CTA resolves to a spec-listed target (no broken, placeholder, or wrong-tenant URL).
- Unsubscribe link present and functional; physical mailing address + accurate "from" present per CAN-SPAM; TCPA consent + quiet-hours window honored (no send outside the allowed local-time window); throttle/rate cap not exceeded.
- SPF pass, DKIM signature valid for the selector, DMARC alignment holds against the captured headers.
- Bounce → suppression list updated, no retry storm; complaint/FBL → recipient suppressed.
- Spam-score under the configured threshold.
- **Idempotency:** replaying the same offer/shortlist event produces exactly ONE captured email — never a duplicate.
- **Gate:** `email_comms_compliant` — render + link + compliance + auth-alignment + idempotency assertions all pass; any open blocker/critical (e.g. live send, merge-field PII leak, duplicate offer) fails the gate.

## Output
Write `artifacts/email-deliverability-qa/report.json` per `shared/report-format.md`:
`{ flow, status, summary{...}, findings[], gate{name:"email_comms_compliant",passed} }`.
Each finding follows `shared/finding-schema.md`; include the seed/fixture id, trigger event id, and template id for deterministic repro. `oracle` = template-spec section / compliance-rule id / DNS record. Evidence = captured sink message (redacted headers + rendered HTML), CTA URL, idempotency key. Redact any token/address per guardrails.

## Guardrails
Per `shared/guardrails.md` §3 (external side-effects) — **mail-sink pattern: outbound email is NEVER live-sent.** SMTP is repointed at a Mailpit/Mailhog/seeded-provider sink confirmed NON-PROD before acting; if a real relay is detected, mark NOT RUN / `status:error`. Seeded sandbox CRITIC only; synthetic recipients (`@example.test`), no real PII. Secrets (SMTP creds, provider keys) via env, never in fixtures or `report.json`. Purge the sink before and after the run; confirm teardown in the report. Cap turns; respect provider sandbox rate limits.

> **Watch (do not gate):** AI-personalized email bodies (LLM-drafted outreach) may need a separate hallucination/tone check — track under 60-ai-ml, do not gate here.
