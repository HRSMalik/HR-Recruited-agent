# component-library

**Group:** 10-tokens-systems
**Runs as:** subagent: ../.claude/agents/design-system-keeper.md
**Mode:** build (writer + verify loop) · audit (reuse + coverage scan)   ·   **Default model:** sonnet

## Purpose
Own the reusable component set: design and audit components so each has a complete variant × state matrix with docs, one responsibility apiece, and nothing is reinvented inline when a component already exists.

## Inputs & preconditions
- From `project-design-config.md`: components dir, available components (reuse before inventing), token source, style-object source, colour rule, **chosen headless primitive lib** (the project's declared React Aria / Radix / Base UI choice — read it before building any interactive widget).
- Target: the component(s) under design + the screens that consume them.
- Preconditions: components dir grepped first; existing component read before extending or building a new one; for any custom interactive widget, the declared headless lib confirmed in `project-design-config.md` before hand-rolling behaviour.

## Oracle (source of truth)
The standard component library contract (`project-design-config.md`) + single-responsibility + reuse-before-invent + headless-primitive-before-hand-rolled-a11y (the WAI-ARIA Authoring Practices implemented for you — React Aria, react-spectrum.adobe.com/react-aria; Radix Primitives; Base UI).
- **hard:** nothing reinvented inline — grep the components dir; if the JSX structure exists as a component, it must be used, not copy-pasted (two identical inline structures = a fail). Every component consumes tokens, no hardcoded values. Any custom interactive widget that maps to an APG pattern (menu, listbox/combobox, dialog, tabs, disclosure, slider, switch, tooltip, etc.) is built on the project's declared headless primitive — not hand-rolled keyboard/focus/ARIA wiring (re-implementing roving tabindex, focus trapping, `aria-*` state by hand when the declared lib ships it = a fail); the headless lib is declared in `project-design-config.md` (a custom interactive widget with no declared lib = a fail).
- **soft:** each component documents *all* its variants and states; one responsibility per component; props are minimal and named clearly; component APIs favour composition — compound-component + slot (`asChild`/`render`) patterns so consumers compose parts and pass through their own element, rather than a wall of boolean/config props.

## Standards & techniques
- **Variant axis:** the component's kinds (Button: primary/secondary/danger/ghost; Badge: status hues).
- **State axis:** default / hover / focus / active / disabled / loading / empty / error / success — every interactive component covers the full set.
- **One responsibility:** a component does one thing; if it does two, split it. New components land in the components dir, new style tokens in the style-object source — both documented.
- Reuse first: check the dir before writing any JSX (`PageBanner`, `Card`/`CardHeader`/`CardBody`/`CardFooter`, `Input`, `Select`, `Button`, `AlertBanner`, `Badge`, `Table`, …).

## Headless primitives & composable APIs
For any custom interactive widget, build on an APG-implemented **headless primitive** and shape the public API for composition — don't hand-roll accessibility and don't bolt behaviour onto a monolithic prop bag.

- **Prefer a headless primitive over hand-rolled a11y:** a menu, listbox/combobox, dialog, tabs, disclosure/accordion, slider, switch, popover, or tooltip is a solved WAI-ARIA Authoring Practices (APG) pattern — keyboard model, roving tabindex, focus management/trapping, `aria-*` wiring and edge cases are all easy to get subtly wrong by hand. Use a headless lib that ships the behaviour unstyled and let it own the interaction layer; you own only the markup and tokens on top. Default to **React Aria** (react-spectrum.adobe.com/react-aria — Adobe's APG-conformant hook/primitive set), or **Radix Primitives** / **Base UI** where the project already standardizes on one. Hand-rolling the keyboard/focus/ARIA layer when the declared lib provides it is a fail, not a style nit.
- **Declare the choice once:** the chosen headless lib is recorded in `project-design-config.md` (Component library section) so every flow resolves the same primitive set instead of mixing libraries per component. A custom interactive widget with no declared lib backing it is a gap to surface.
- **Compound-component + slot APIs:** design component APIs for composition, not configuration. Expose **compound components** — a parent plus named part sub-components the consumer assembles (`<Menu><Menu.Trigger/><Menu.Items><Menu.Item/></Menu.Items></Menu>`) — instead of one component driven by a wide boolean/config prop bag. Pair this with a **slot / `asChild`** escape hatch (Radix `asChild`, React Aria `render`-prop slots) so a consumer can swap in their own element/component and have behaviour, refs, and `aria-*` forwarded onto it — composition over a `as`/`component` prop explosion. This keeps each part single-responsibility and lets screens compose the primitive with project tokens without forking it.
- Cross-link `aria-widget-patterns.md` for the per-pattern APG keyboard-interaction and `aria-*` contracts each headless primitive must satisfy — that file is the role/state/key spec; this file governs *which* primitive backs the widget and how its API composes.

### Primitive map (resolve the APG pattern → the declared lib's primitive)
Once `project-design-config.md` declares the headless lib, every APG-pattern widget resolves to that lib's named primitive — don't reach for a second lib per widget. Default to **React Aria** (react-spectrum.adobe.com/react-aria) unless the project standardizes on Radix or Base UI.

| APG pattern | React Aria | Radix Primitives | Base UI |
| --- | --- | --- | --- |
| Menu | `useMenu`/`Menu` | `DropdownMenu` | `Menu` |
| Listbox / Combobox | `useListBox` / `useComboBox` | (`Select` for listbox) | `Select` / `Autocomplete` |
| Dialog (modal) | `useDialog` + `Modal` | `Dialog` (`asChild` trigger) | `Dialog` |
| Tabs | `useTabList`/`Tabs` | `Tabs` | `Tabs` |
| Disclosure / Accordion | `Disclosure` | `Accordion` / `Collapsible` | `Accordion` / `Collapsible` |
| Slider | `useSlider` | `Slider` | `Slider` |
| Switch | `useSwitch` | `Switch` | `Switch` |
| Tooltip | `useTooltip` | `Tooltip` | `Tooltip` |
| Popover | `usePopover`/`Popover` | `Popover` | `Popover` |

A widget that maps to a row above but is hand-rolled (or backed by a lib *other* than the one declared in `project-design-config.md`) is the hard finding — the keyboard/focus/`aria-*` contract from `aria-widget-patterns.md` is the lib's job, not the consumer's.

### Slot / `asChild` decision rule
Reach for the slot escape hatch (`asChild` in Radix, `render` slots in React Aria) only when a consumer must supply their *own* element — a routing `<Link>` as a menu item, a project `Button` as a dialog trigger — so behaviour, refs, and `aria-*` forward onto it. For everything else, expose **compound parts** the consumer assembles; never widen the prop bag with a boolean per variant when a sub-component or a slot already covers it. One part = one responsibility; the slot forwards, it doesn't fork.

**Watch (do not gate):** cross-lib **primitive parity** is still uneven — Base UI is pre-1.0 and React Aria vs Radix diverge on combobox/`selectlist` and `asChild`-vs-`render` slot ergonomics, so the map above is a starting resolution, not a guarantee the same primitive exists 1:1 in every lib. Where the declared lib lacks a row's primitive, surface the gap (and the closest available primitive) — treat parity as EMERGING, never a hard oracle, and never a reason to swap in a second lib mid-project.

**Watch (do not gate):** the React **`useId`-free / built-in primitives** trend — native `<dialog>` (+ `popover` / `popovertarget` attribute, Invokers/`command`) and `<selectlist>`/customizable `<select>` moving APG behaviour into the platform — is EMERGING. Where baseline, it can shrink or replace a headless dependency, but cross-browser focus/`aria`/styling behaviour isn't settled — note it as an option to track and feature-detect, never a hard oracle and never a reason to skip the declared headless primitive today.

## Step sequence
- **audit:** grep the components dir → scan screens for inline JSX that duplicates an existing component → check each component's documented variant × state matrix for gaps → emit findings (read-only).
- **build:** Explore (read-only; confirm no existing component covers it, sketch the variant × state matrix, and — for an interactive widget — resolve the declared headless primitive from `project-design-config.md` and the APG pattern it maps to) → Judge (reuse + responsibility + matrix-completeness + headless-primitive-and-composable-API rubric, order-swapped) → Implement (one writer; build/extend the component in the components dir on the declared headless primitive, expose compound parts + a slot/`asChild` escape hatch, wire to tokens, document the matrix) → Verify (Playwright screenshots every variant × state @ breakpoints; axe + manual keyboard pass on the primitive's APG interactions + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- No inline duplication of an existing component (grep confirms).
- Every interactive component documents and renders all required states; every variant present.
- One responsibility per component; tokens used, no hardcoded values.
- Every custom interactive widget that maps to an APG pattern is built on the project's declared headless primitive (no hand-rolled keyboard/focus/`aria-*` wiring); the lib is declared in `project-design-config.md`.
- Interactive component APIs are composable — compound parts + a slot/`asChild` escape hatch, not a monolithic config-prop bag.
- **Gate:** hard oracles green (no reinvention, token conformance, headless primitive backs every APG-pattern widget) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/component-library/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: token`/`visual`, `oracle: hard` for inline reinvention, a hand-rolled APG-pattern widget bypassing the declared headless primitive, or a custom interactive widget with no declared lib in `project-design-config.md`; `oracle: soft` for a missing documented state or a non-composable interactive API — monolithic config-prop bag instead of compound parts + slot/`asChild`), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: reuse before invention — check the components dir first; extract a repeated structure immediately. For any interactive widget, build on the declared headless primitive (React Aria / Radix / Base UI) — never hand-roll APG keyboard/focus/`aria-*` wiring — and shape its API as compound parts + a slot/`asChild` escape hatch; declare the lib in `project-design-config.md`. Preserve logic byte-for-byte (style/markup only). Read-only audit makes no edits; one writer for build.
