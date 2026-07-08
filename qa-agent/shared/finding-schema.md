# Finding / Defect Schema

Every issue any flow reports uses this object. Designed to be machine-readable (CI), human-readable (triage), and convertible to JUnit XML.

```json
{
  "id": "QA-<FLOW>-<NNN>",
  "title": "<one-sentence summary of the defect>",
  "flow": "api-contract",
  "severity": "blocker|critical|major|minor|trivial",
  "priority": "P1|P2|P3|P4|P5|proposed",
  "status": "open",
  "environment": {
    "sut": "<base URL / host>",
    "build": "<commit / version>",
    "account": "<role / auth context, if any>",
    "extra": "<browser/device/OS/locale where relevant>"
  },
  "steps_to_reproduce": ["<numbered, exact steps or the curl/command>"],
  "expected": "<what the oracle says should happen>",
  "actual": "<what was observed>",
  "evidence": ["<request/response | log line | screenshot path | order id | console error>"],
  "oracle": "<spec section / requirement id / SLO / WCAG criterion used>",
  "suggested_fix": "<optional one-liner>",
  "assigned_to": null
}
```

**Rules**
- **`id`**: `QA-` + flow short-code + zero-padded counter (e.g. `QA-SEC-003`).
- **`severity`** is set by the agent (objective — technical impact). See `severity-priority-rubric.md`.
- **`priority`** defaults to `proposed`; a human finalizes P1–P5. Agents may *recommend* but not finalize.
- **`evidence`** is mandatory for every failed finding — at minimum the exact request/response or command output. No evidence → not a finding, it's a note.
- **`oracle`** must name the external source of truth the assertion came from (never "the API returned X so X is correct").
- Reproduction must be deterministic: include the seed/fixture id if the flow used a seeded sandbox.

## Failure classification (triage every failed assertion)

Before a failure becomes a finding, classify it — this prevents re-reporting known issues and, critically, catches bad test assertions (LLM-written assertions often encode current behavior rather than intended behavior):

| `failure_class` | Meaning | Action |
| --- | --- | --- |
| `real_bug` | The system behaves incorrectly vs the oracle | Emit a finding (this schema) |
| `known_expected` | Already an open finding / backlog item | Reference the existing id; do NOT re-card |
| `test_assertion_issue` | The assertion itself was wrong, not the system | Fix the assertion; do NOT card as a product bug |

Add `"failure_class"` to the finding object. If `known_expected`, set `"duplicate_of": "<existing-id>"`. If `test_assertion_issue`, the item is a test fix, not a defect — keep it out of the severity tally.
