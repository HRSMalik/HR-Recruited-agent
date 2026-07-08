# Wardley Map Template — Build-vs-Buy-vs-Rent Positioning

A Wardley map is a **value-chain × evolution** positioning tool (Simon Wardley) that gives the architecture fleet a shared visual language for sourcing strategy. It surfaces *where each component sits on the commodity curve* so that build-vs-buy-vs-rent recommendations are grounded in that component's evolutionary stage, not in fashion or familiarity. The map is a **soft/advisory input** — it informs the `architecture-explorer`'s option-generation and the `60-evaluation/architecture-evaluation-atam.md` Wardley-placement validity pass (embedded within the ATAM approach-analysis step), but it is never a hard gate. Qualitative judgement and facilitation context are required to place components accurately; where placement is contested, that uncertainty is surfaced as a finding, not resolved by assertion.

---

## The Two Axes

### Axis 1 — Value Chain (vertical, top → bottom)

The vertical axis represents **visibility to the user need**.

- **Top (visible):** the components the user directly experiences — the user-facing capability anchoring the map. Every chain starts here. This is *not* the UI per se; it is the expressed user need (e.g. "customer submits an order" or "manager views an account's status"). The concrete anchor for the current project is defined per-engagement — see `project-architecture-config.md`.
- **Bottom (invisible):** the foundational components that enable the visible ones but which the user never sees directly (compute, storage, network, identity primitives, power).

**Construction rule:** start by naming the **anchor user need** at the top. Stack the components below it in dependency order — "what does this component depend on to function?" — until you reach commodity infrastructure. A component that appears higher in the chain is *more visible* and often *more differentiating*; a component that appears lower is *more foundational* and often *more commoditized*.

Draw explicit dependency arrows: *Component A depends on Component B* means A sits above B on the chain. Circular dependencies are a mapping error and a design smell — surface them.

### Axis 2 — Evolution (horizontal, left → right)

The horizontal axis represents **how evolved the component is across the industry**, moving through four stages:

| Stage | Label | Characteristics | Typical sourcing signal |
|---|---|---|---|
| I | **Genesis** | Novel, experimental, poorly understood, uncertain interfaces, no standards | Build — externally sourced alternatives don't exist or are immature |
| II | **Custom-built** | Understood by practitioners, hand-crafted per project, improving but not standardized | Build — differentiating; or commission (bespoke vendor) |
| III | **Product / Rental** | Available as products or SaaS/managed services with defined APIs; still has meaningful variation between offerings | Buy (license/product) or Rent (SaaS/managed); evaluate fit |
| IV | **Commodity / Utility** | Standardized, interchangeable, consumed as a metered utility (electricity model); switching cost is low | Rent/utility — building is waste unless a driver demands it |

**Placement rule:** position based on *industry maturity*, not on your team's familiarity with it. A component your team built in-house is not automatically Genesis — if the same capability is widely available as a managed service with a published API, it is already Product/Commodity on the industry axis. Honest placement is what makes the map useful.

---

## Reading Sourcing Strategy from Position

The map translates position into a **default sourcing recommendation** — a starting hypothesis, not a mandate:

```
Genesis / early Custom-built  →  BUILD (or research/spike; no viable external option)
Late Custom-built              →  BUILD if differentiating, COMMISSION if not
Product / Rental               →  BUY (license) or RENT (SaaS/managed); evaluate TCO + lock-in
Commodity / Utility            →  RENT / utility-consume; building is accidental complexity
```

**Key interpretive rules:**

1. **Differentiation test.** A component that is Custom-built *and* is the system's source of competitive or functional differentiation stays BUILD even as the market matures. A component that is Custom-built but is *undifferentiated plumbing* (e.g. email delivery, object storage, auth) is a Buy/Rent candidate regardless of how it was originally built.

2. **Evolution gap finding.** If a component is Commodity/Utility on the industry axis but the team is building or operating it in-house, that is a **map gap** — a soft finding (`finding-schema.md`, `type:"cost"` or `type:"operability"`, `oracle:"soft"`). The recommendation is to evaluate the managed/utility option against TCO (including operational toil, fallacy #7 transport cost, and the build-vs-buy tradeoff — `shared/fallacies-and-tradeoffs.md`).

3. **Inertia flag.** A component resisting movement rightward (e.g. a custom auth stack when a managed OIDC service exists at Product/Commodity) despite no differentiating driver is **inertia** — an organizational or legacy constraint holding cost and risk that the map makes visible. Name it; do not accept it silently.

4. **Emerging commoditization.** A component moving from Custom-built toward Product is a **watch** item — the sourcing recommendation may flip within the planning horizon. Flag it as time-sensitive; the ADR for it carries a review date.

5. **Anchor clarity.** If the user-need anchor is vague or contested, the entire chain is suspect. Clarify the anchor before placing components — "the system" is not an anchor; "a senior agent submits a request and receives an assignment decision" is.

---

## Producing the Map

**Format:** a simple 2D grid is sufficient — the tool is the thinking, not the tooling. Acceptable representations:

- A text grid (component name | evolution stage | chain level) when diagramming tooling is unavailable.
- A Mermaid or PlantUML diagram following `shared/diagramming-standards.md` for inclusion in the architecture artifact folder (`architecture/<slug>/`).
- A drawn SVG or whiteboard photograph annotated with component labels, evolution positions, and dependency arrows — acceptable in facilitated sessions; a text representation is added to the artifact for traceability.

**Minimum content per map:**

1. **Anchor user need** — named at top-center.
2. **All architecturally significant components** placed on the grid — every component that appears in the utility tree (`00-drivers/quality-attribute-scenarios.md`) or in the C4 container/component diagram (`50-infrastructure/deployment-topology.md`) must appear on the map. Components not in either are out of scope unless they are material dependencies.
3. **Dependency arrows** — explicit directed edges: A → B means A depends on B.
4. **Evolution placement** — each component labelled with its stage (I–IV) and the rationale in one clause (e.g. "managed MongoDB Atlas: widely available managed service, defined API, strong market — Stage III/Product").
5. **Sourcing recommendation per component** — build / buy / rent / watch, with the primary driver (differentiating? commodity? inertia?).
6. **Contested placements** — components where reasonable practitioners would disagree on stage are flagged with the range (e.g. "Stage II–III: team-built today, managed alternatives exist but lack feature X required by QAS-DATA-01") and the uncertainty is carried as a soft finding.

---

## Feeding Architecture-Explorer: Build-vs-Buy as a Design Input

The completed map is consumed by `architecture-explorer` during the **Explore** step (`shared/workflow-template.md`) as a **build-vs-buy-vs-rent posture constraint**:

- Components at Stage III–IV with no differentiating driver → the explorer's option set includes a managed/utility variant; options that build these from scratch must justify the deviation (name the driver that demands it).
- Components at Stage I–II that are differentiating → the explorer's options include a build path; an option that outsources a Genesis differentiator must justify it.
- Inertia-flagged components → the explorer surfaces a "remove inertia" option alongside the status-quo option so the tradeoff is explicit.

The map does **not** constrain the explorer to a single path — it scopes the option space and ensures the rationale is driver-grounded, not convention-grounded.

Cross-reference: `60-evaluation/architecture-evaluation-atam.md` runs a structured evaluation pass over the map itself (placement validity, inertia flags, evolution-gap findings) as part of its approach-analysis step — any contested or inertia-flagged placement is scored as a sensitivity or tradeoff point within the ATAM analysis. `90-specialized/cost-finops-architecture.md` consumes the sourcing recommendations as a primary input to the **build-vs-buy / managed-TCO** computation — the map provides the positioning hypothesis; cost-finops provides the TCO number that confirms or overrides it.

---

## Qualitative Limits — The Soft-Input Compact

**The map is not a hard oracle.** Its findings are `oracle:"soft"` (`finding-schema.md`):

- **Facilitation-dependent.** Placement accuracy depends on the participants' knowledge of the industry landscape. A map produced without domain and market knowledge is a sketch, not a finding.
- **Point-in-time.** Evolution moves rightward over time. A map that is more than one planning cycle old may misplace components that have commoditized since it was drawn. Date the map; retire stale versions.
- **Not a cost model.** "This component should be rented" is a hypothesis. The TCO confirmation comes from `90-specialized/cost-finops-architecture.md`. A sourcing recommendation from the map that contradicts a grounded TCO model yields to the TCO model — cost evidence beats positional hypothesis.
- **Not a team-topology prescription.** The map surfaces what to build vs buy; Conway's law analysis (`shared/fallacies-and-tradeoffs.md`) determines who owns it. These are separate questions addressed sequentially.
- **No single authority on Genesis.** A component labelled Genesis because the team hasn't seen external alternatives may actually be Custom-built or Product — market research is required. Label it "Genesis (unverified)" until verified.

A soft finding from the map that has no TCO confirmation and no traced driver (`finding-schema.md` — `driver_ref` required) is **advisory only** and does not block the evaluation gate (`shared/quality-attribute-rubric.md`).

---

## Sourcing Recommendation Format

Each component's sourcing recommendation is a brief structured entry — machine-readable for traceability:

```
component: <name>
chain_level: <visible | intermediate | foundational>
evolution_stage: <I-Genesis | II-Custom | III-Product | IV-Commodity>
placement_confidence: <high | medium | low (contested)>
differentiating: <yes | no | partial>
inertia_flag: <yes | no>
sourcing_recommendation: <build | buy | rent | watch | commission>
primary_driver: <the quality-attribute scenario or constraint, or "none — commodity default">
soft_finding_ref: <ARCH-WARD-NNN if a gap/inertia finding is raised, else none>
cross_ref_cost_model: <yes | pending | n/a>
```

Group entries by chain level (visible → foundational). The full set of entries, plus the map artifact, goes into `architecture/<slug>/wardley-map.md`.

---

## Cross-References

- `60-evaluation/architecture-evaluation-atam.md` — the ATAM approach-analysis step evaluates this map's placements and sourcing recommendations (placement validity, inertia flags, evolution-gap findings) as sensitivity and tradeoff points; runs before the map feeds architecture-explorer.
- `90-specialized/cost-finops-architecture.md` — consumes sourcing recommendations to compute build-vs-buy TCO (sticker + operational toil + egress over the horizon); the TCO result confirms or overrides the map's positional hypothesis.
- `shared/fallacies-and-tradeoffs.md` → *Build ↔ Buy* tradeoff (the canonical statement this map operationalizes); fallacy #7 (transport cost is not zero, relevant when a rented managed service crosses a boundary).
- `shared/evaluation-method.md` → CBAM (the cost-benefit method that acts on the TCO the cost-finops flow produces from the map's sourcing recommendations).
- `shared/finding-schema.md` → `type:"cost"` / `type:"operability"`, `oracle:"soft"` for evolution-gap and inertia findings from the map.
- `00-drivers/quality-attribute-scenarios.md` — the utility tree that must be fully covered in the map (every component in a `(H,*)` scenario appears on the map).
