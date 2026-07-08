# data-table-design

**Group:** 30-layout-ia
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (proposer references it; one writer applies)
**Mode:** audit (table-craft scan) · build (re-layout + verify)   ·   **Default model:** sonnet

## Purpose
Lay out data tables (e.g. the recruiter candidate/applications list) so they scan fast and act on bulk — correct alignment per data type, sticky reference rows/columns, the right scroll/paginate strategy, and useful empty states.

## Inputs & preconditions
- From `project-design-config.md`: the `Table` component + supporting components, token source, column-alignment locked rules, breakpoints.
- Target: the table(s) under review at every configured viewport; the standard (Pencil&Paper / LogRocket table guidance).
- Preconditions: dev server reachable; existing `Table` component read before re-laying-out — reuse, don't reinvent the grid.

## Oracle (source of truth)
Established data-table conventions (Pencil&Paper, LogRocket) + the project's locked column-alignment rules + the WebAIM tables accessibility techniques (webaim.org/techniques/tables).
- **hard:** text columns left-aligned, numeric columns right-aligned with tabular figures, icon/indicator columns centred; header (and first/identity column where it scrolls) sticky; no horizontal overflow without `overflow-x:auto` + a scroll affordance.
- **hard (TABLE-SEMANTICS):** tabular data uses real `<table>` semantics — a native `<table>` (or full `role="table"/row/cell/columnheader` set), a `<caption>` (or `aria-label`) naming the table, and `<th>` for true headers only (header *cells*, not visual styling); `<td>` styled to look bold is not a header. Header↔data association is explicit: `scope="col"`/`scope="row"` on simple tables, `headers`/`id` on complex/multi-level ones. The caveat: `overflow-x` reflow and row **virtualization** break the accessibility tree — rows that are not in the DOM do not exist for assistive tech, so a virtualized list reads as a fraction of the real row count. When a11y matters, prefer **pagination over virtualization** (every rendered page is fully in the DOM), or manage the a11y tree explicitly (correct `aria-rowcount`/`aria-rowindex` plus a focus/announcement strategy for off-DOM rows) — never ship raw virtualization as the only path. Source: webaim.org/techniques/tables.
- **soft:** the scroll/paginate choice fits the volume; bulk-select + toolbar present where bulk actions exist; filtered empty states are helpful.
- **Watch (do not gate):** emerging CSS `display:contents` / `role`-rewritten grid tables and ARIA grid-row virtualization helpers — note where semantics or the a11y tree look at risk, but do not gate on them; the hard bar stays native `<table>` + scope/headers + pagination-or-managed-tree.

## Standards & techniques
- **Table semantics (WebAIM):** use a native `<table>` for tabular data; `<caption>` names it; `<th>` for header cells only, never to bold a `<td>`. Associate headers with data — `scope="col"`/`scope="row"` for simple grids, `headers`/`id` pairs for multi-level/spanning headers. Don't fake a table with stacked `<div>`s and visual lines; don't use a real table for non-tabular layout.
- **Virtualization vs the a11y tree:** rows not in the DOM are invisible to assistive tech, so `overflow-x` reflow and row virtualization silently shrink the perceived table. Choose pagination over virtualization when a11y matters (each page is fully in the DOM), or, if virtualization is required for volume, manage the tree explicitly — `aria-rowcount`/`aria-rowindex`, and a focus/announcement plan for rows that scroll out of the DOM.
- **Alignment by type:** left-align text; right-align numbers (tabular figures so digits line up); centre icons/indicators; identity columns stay left.
- **Sticky reference:** sticky header always; sticky first/identity column when the table scrolls horizontally.
- **Volume strategy:** pagination for structured jumping (known page sizes); virtual scroll for thousands of rows; don't paginate a 12-row table.
- **Bulk + inline affordances:** checkbox bulk-select → an action toolbar; inline edit and row expansion for detail without leaving the row.
- **Crowded tables:** condense/merge low-priority columns, then `overflow-x:auto` + a scroll-shadow when content exceeds ~1300–1500px.
- **Filtered empty state:** show the active filters + a Clear action — never a bare "No results".

## Step sequence
- **audit:** drive the live table @ breakpoints → check real `<table>` semantics (caption, `<th>`+scope/headers associations, no faked-table divs and no `<td>`-as-header), virtualization vs DOM row count, per-column alignment + tabular figures, sticky header/first-column, scroll vs paginate fit, bulk toolbar, crowded-overflow handling, filtered empty state → emit findings (read-only, no edits).
- **build:** Explore (≥2 column/alignment + density layouts, read-only) → Judge (semantics + alignment + sticky + empty-state rubric, order-swapped) → Implement (one writer; re-layout the `Table` markup/style only — keep/repair native semantics: caption, `<th scope>`/`headers`-`id`; choose pagination over virtualization or wire `aria-rowcount`/`aria-rowindex`; apply locked alignment rules, add scroll-shadow/toolbar from existing components) → Verify (Playwright screenshots default/crowded/empty/filtered @ breakpoints; assert no overflow without scroll affordance; assert DOM row count matches reported row count under virtualization; axe checks table-structure rules + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Real `<table>` semantics: `<caption>`/`aria-label` present, `<th>` for true headers only with `scope`/`headers`-`id` associations, no faked-table markup, no `<td>`-styled-as-header.
- Virtualization does not orphan the a11y tree: pagination chosen where a11y matters, or `aria-rowcount`/`aria-rowindex` + off-DOM focus handling in place; DOM row count is reconcilable with reported total.
- Text left, numbers right with tabular figures, icons centred; header (and identity column on h-scroll) sticky.
- Volume strategy fits; bulk toolbar where actions exist; filtered empty state shows active filters + Clear.
- **Gate:** hard oracles green (TABLE-SEMANTICS: caption + `<th>`/scope/headers + pagination-or-managed-tree; alignment; sticky; no un-handled overflow) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/data-table-design/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: visual`/`responsive`/`a11y`, `oracle: hard` for missing/invalid table semantics — no caption, `<td>`-as-header, missing scope/headers associations, virtualization that orphans the a11y tree — and for mis-aligned numbers / missing sticky / un-handled overflow; `viewport` named), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: never touch sort/filter/data-fetch logic — re-layout the `Table` markup/style only. Reuse the `Table` and supporting components; apply the locked alignment rules, don't re-derive them. Read-only audit makes no edits; one writer. Trust the screenshot over the diff.
