# Design Finding / Recommendation Schema

Every issue a design flow reports uses this object — machine-readable (gate), human-readable (review), and traceable to a screen/file/selector + a token/WCAG ref.

```json
{
  "id": "UX-<FLOW>-<NNN>",
  "type": "accessibility | visual | interaction | token | heuristic | content | responsive | performance | ethics | i18n",
  "severity": "critical | major | minor | cosmetic",
  "oracle": "hard | soft",
  "wcag_ref": "1.4.3 Contrast (Minimum)",
  "heuristic": "Nielsen #1 Visibility of system status",
  "screen": "claims/list",
  "viewport": "1440x900",
  "file": "src/components/ClaimsTable.tsx",
  "selector": "tr.claim-row .sla-cell",
  "issue": "<one sentence — what's wrong vs the principle/standard>",
  "evidence": "screenshots/claims-list-1440.png | the offending style/markup",
  "fix": "<the concrete change, in token/spacing-system terms>",
  "status": "open"
}
```

**Rules**
- **`id`**: `UX-` + flow short-code + counter (e.g. `UX-A11Y-003`, `UX-TABLE-001`).
- **`oracle`**: `hard` = deterministic gate failure (contrast, axe, console, overflow, hardcoded token, logic changed); `soft` = rubric/craft judgement. Hard findings block; soft findings are advisory above the rubric threshold.
- **`wcag_ref`** required for accessibility findings (cite the exact SC); `heuristic` for usability findings (cite the Nielsen number); `null` otherwise.
- **`evidence`** mandatory for every finding — a screenshot path (with viewport) or the exact offending style/markup. No evidence → it's a note, not a finding.
- **`fix`** in design-system terms — name the token / spacing-scale value / component, e.g. "use `color.text.onPrimary` → 5.2:1", "cap the column at 460px, centre it in a grid frame, field gap 16→12".
- Reproduction must name the **screen + viewport** so it's verifiable by re-screenshot.

## Audit output (a flow that reviews rather than builds)
Group findings by `type` then `severity`; return a prioritized list (critical → cosmetic). A behavioural/heuristic audit returns findings only (read-only) — it never edits.
