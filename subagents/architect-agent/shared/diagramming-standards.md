# Diagramming Standards — C4 + Diagrams-as-Code

How architecture diagrams are produced so they are **consistent, reviewable, version-controllable, and compile-checked**. This is the architecture analog of the design fleet's design-tokens — the shared visual grammar that keeps every diagram legible across the fleet. The hard oracle: **every diagram is diagrams-as-code and renders without error** (`quality-attribute-rubric.md` → *Diagram compiles*). A pasted PNG is not an architecture artifact — it rots, can't be diffed, and hides errors.

## The C4 model (the levels — use the right zoom)

Diagram at the level the audience needs; don't cram four levels into one picture. (Simon Brown's C4.)

1. **Level 1 — System Context.** The system as one box, its **people/roles** and **external systems** around it. Audience: everyone, incl. non-technical. Answers "what is this and who/what does it touch?" Scope = one software system.
2. **Level 2 — Container.** Inside the system: the deployable/runnable units — apps, services, SPAs, databases, queues, caches (a "container" = a separately deployable thing, not a Docker container specifically). Shows the major tech choices and how containers talk (sync/async, protocol). This is the **workhorse view** for most reviews.
3. **Level 3 — Component.** Inside one container: its major components/modules and their responsibilities + relationships. Draw only for containers complex enough to warrant it.
4. **Level 4 — Code.** Class/sequence detail. Usually generated on demand from code, rarely hand-maintained — author only when a specific mechanism needs it.

**Supplementary views (draw when the drivers demand):**
- **Deployment** (C4 deployment view) — containers mapped onto infrastructure nodes/regions/AZs; the topology the availability & scale scenarios are argued against.
- **Dynamic / sequence** — a specific scenario's runtime flow (e.g. the checkout saga, the failover path).
- **System landscape** — multiple systems in an enterprise, for context above L1.

## Diagrams-as-code (the required toolchain — tiered)

Author diagrams in a **text DSL** that compiles to an image, checked into the repo next to the design doc. Tools split into a **Tier-1 (compile-gated)** set — the only ones that may back the *diagram-compile hard oracle* — and a **Tier-2 (soft-use)** set for quick inline sketches that never gate.

**Tier-1 — compile-gated (use for the hard oracle):**
- **Structurizr DSL** — purpose-built for C4; one model, many auto-laid-out views; the most faithful C4 tool. `structurizr export` / a render step must exit 0.
- **LikeC4** — C4-native, actively maintained; interactive drill-down, `likec4 build` as the compile gate, `likec4 diff` for model↔code drift, and an **MCP server** the fleet's own agents can query for the model. Preferred where an agent needs to *read* the architecture model.
- **PlantUML** (with the **C4-PlantUML** stdlib) — `!include <C4/C4_Container>`; ubiquitous, renders anywhere via the PlantUML jar/CLI.

**Tier-2 — soft-use only (prose/PR sketches, never a compile gate):**
- **Mermaid** — `C4Context` is **officially experimental** (per mermaid.js docs) and its layout/output is not stable; use Mermaid only for lightweight inline `graph`/`sequenceDiagram` sketches embedded in markdown, **never** as the diagram-compile oracle.
- **D2** — clean auto-layout, good for quick topology sketches; promote to Tier-1 only if a project standardizes on it with a CI render gate.

The choice is per project (`project-architecture-config.md`); the **rule is invariant: it must be text, it must compile under a Tier-1 tool, and it must live in `architecture/<slug>/diagrams/`.** Verify it renders (the diagram-compile hard oracle) before counting the artifact done. A C4 diagram backed only by an experimental renderer does **not** satisfy the oracle.

## Notation conventions (consistency = the shared grammar)
- **Every element labeled** with name + type + a one-line responsibility (`[Container: Spring Boot]`, "handles order lifecycle"). An unlabeled box fails review.
- **Every relationship labeled and directed** — the verb + the protocol/style: "places order via, JSON/HTTPS", "publishes OrderPlaced to, Kafka (async)". An unlabeled arrow hides the integration contract.
- **Sync vs async visually distinct** — solid line for synchronous request/response, dashed for asynchronous/event. The reader must see coupling at a glance.
- **Trust boundaries drawn** where they exist (a boundary box / a dashed security perimeter) — they anchor the threat model.
- **Agent-interop boundaries annotated** — any agent↔agent or agent↔tool relationship is drawn as a distinct boundary type labeled with its **protocol (MCP / A2A), auth model, and trust scope** (an LLM/agent edge is a trust boundary, not a plain call). See `30-integration/agent-interop-protocol.md`.
- **Consistent across levels** — every Container in the L2 view that's drilled into has an L3; names match the ADRs and the design doc exactly. Drift between diagram and doc is a finding.
- **Legend included** when notation isn't self-evident (sync/async, boundary, data store shapes).
- **No orphan elements** — every box connects; every external system in L1 reappears as the other end of a relationship in L2.

## Diagram review checklist (the hard checks)
- It **compiles/renders** (run the tool; a syntax error = broken artifact).
- C4 **levels are consistent** — containers ↔ components ↔ deployment line up; names match the ADRs/design-doc.
- Every element + every relationship is **labeled and typed**; sync/async distinguished.
- **Trust boundaries** present where the threat model has them.
- The diagram is **traceable** — the containers/relationships it shows correspond to decisions (ADRs) and the scenarios they serve. A box with no decision behind it is accidental complexity made visible.
