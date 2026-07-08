# Severity vs Priority Rubric

**Severity = technical impact (the agent sets this, objectively). Priority = business urgency to fix (a human finalizes).** They are independent: a critical-severity crash on an internal admin page can be low priority; a trivial typo of the company name on the homepage can be high priority.

## Severity (agent decides)

| Severity | Definition | Examples |
|----------|------------|----------|
| **blocker** | Testing/usage cannot proceed; environment or core path down | server won't boot, auth totally broken, data loss on every write |
| **critical** | Core function broken or security/data-integrity breach, no workaround | unauth access to PII, payment fails, injection/RCE, data corruption |
| **major** | Important feature broken, workaround exists | a primary endpoint 500s on valid input, broken pagination, XSS surface |
| **minor** | Non-critical defect, limited impact | misleading status code, off-by-one in a label, slow but within SLO |
| **trivial** | Cosmetic / wording | typo, spacing, inconsistent casing |

Decision aid: **impact × scope**. "Does it break a core capability?" → critical/blocker. "Important but avoidable?" → major. "Annoyance?" → minor. "Cosmetic?" → trivial. Security findings that are exploitable default to **critical** (or **major** if mitigated/low-likelihood).

## Priority (agent proposes, human finalizes)

| Priority | Meaning |
|----------|---------|
| P1 | Fix now — blocks release |
| P2 | Fix this cycle |
| P3 | Scheduled backlog |
| P4 | Nice to have |
| P5 | Won't fix / wontfix-candidate |

Agents emit `"priority": "proposed"` plus a `suggested_priority` rationale; the orchestrator/human assigns the final P-level. Map for a first-pass proposal: blocker/critical exploitable → P1; major → P2; minor → P3; trivial → P4.

## Gate impact
- Any **open blocker or critical** finding → **gate fails** (deploy blocked).
- **major** findings fail the gate by default for release flows; configurable to "warn" for PR flows.
- minor/trivial → reported, do not fail the gate.
