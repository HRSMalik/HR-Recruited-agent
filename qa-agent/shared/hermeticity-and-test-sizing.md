# Hermeticity & Test Sizing — The Prevention Contract

Binding upstream of flake handling. Detect-and-quarantine is the *cure*; this doc is the
*prevention*. A test that honors hermeticity, correct sizing, and order-independence does not
become flaky in the first place. Referenced by `test-strategy-plan` and `ci-quality-gates`.

Source: Google, *Software Engineering at Google*, ch.11 "Testing Overview"
(https://abseil.io/resources/swe-book/html/ch11.html).

## 1. Hermeticity — the core invariant
A **hermetic** test "contains all of the information necessary to set up, execute, and tear down
its environment" and "assumes as little as possible about the outside environment." Enforce:
- **No external dependencies.** No shared/production DB, no third-party host, no live network the
  test does not itself stand up and tear down. Bring your own fixture (see `guardrails.md` §2).
- **No shared mutable state** across tests — no global singletons, on-disk temp files, or DB rows
  left behind. Each test sets up and tears down its own world.
- **No ambient nondeterminism** — wall-clock `now()`, random seeds, locale/timezone, and iteration
  order over unordered collections are all injected or pinned, never read from the environment.
- Teardown is **mandatory and confirmed**, even on failure — a leaked fixture poisons the next run.

## 2. Test sizing — the Google taxonomy
Size is defined by **resources the test may touch**, not by line count. Enforced by the harness.

| Size | Process | Network | May do | Must NOT do |
|------|---------|---------|--------|-------------|
| **small** | single process, often single-threaded | none | pure compute, in-memory fakes | sleep, blocking calls, any I/O, file/network/DB access |
| **medium** | multiple processes/threads | **localhost only** | local DB, local service, in-proc integration | reach off-machine; depend on external/remote hosts |
| **large** | multi-machine | unrestricted | full system end-to-end, legacy paths unfit for doubles | run by default in fast/PR gates (slow + flake-prone) |

Rules:
- **Smaller is better.** Pick the smallest size that still exercises the behavior. Reach for medium
  only for genuine cross-process integration, large only for true end-to-end.
- **Declare the size explicitly** on every test; the gate uses it to choose the run tier and the
  enforcement sandbox (small forbids I/O, medium forbids off-localhost).
- **Target mix (pyramid):** ~**80% small**, ~**15% medium**, ~**5% large**. A suite inverted toward
  large/end-to-end is a smell — flag it in the strategy plan.

## 3. Order-independence — the primary flake reducer
The single highest-leverage rule: **a test must pass regardless of the order tests run in, and
regardless of what ran before it.** Most flakes are a shared-state or ordering leak in disguise.
- No test may depend on a sibling having run first (no implicit setup, no "test A seeds for test B").
- No reliance on dict/set/map iteration order or filesystem listing order — sort or assert as sets.
- The strategy plan **shuffles test order** in CI; a suite that only passes in declaration order is
  defective, not unlucky.
- Run a suspect test in **isolation** and **repeated** (e.g. ×100) — if it passes alone but fails in
  a batch, the defect is shared state, fix the test, do not just re-run.

## 4. Flakiness budget — when prevention has failed
- Google holds **flakiness ≈ 0.15%**; **"as you approach 1% flakiness, the tests begin to lose
  value"** because engineers stop trusting red. Treat **1% as the hard ceiling** for any suite.
- A flake is a **bug in the test** until proven a bug in the system — never "just a flake."
- Above budget: the suite is **gate-blocking** (see `ci-quality-gates`); newly flaky tests are
  quarantined per the flake doctrine, then root-caused back to a §1–§3 violation here.

## 5. Enforcement
- Sizing is machine-enforced: small tests run in a sandbox that **denies I/O/network**, medium
  denies **off-localhost**, mirroring the §1 ban on external deps.
- CI runs the suite with **shuffled order** and a **repeat pass** on changed tests to surface
  ordering/state leaks before merge.
- A test that cannot be made hermetic at its declared size is **re-sized up and labeled**, never
  left lying about what it touches.
