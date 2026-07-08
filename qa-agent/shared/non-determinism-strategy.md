# Non-Determinism Strategy — Stable Gates on LLM Output

The prerequisite contract for **every** `60-ai-ml` flow. The suite's repro model is exact-match
on a fixed fixture; LLM output breaks that model — the same prompt yields different text run to
run. A flow that evaluates LLM/agent output and ignores this is invalid: it either flakes (fails a
good model on noise) or rubber-stamps (passes a regressed model that happened to land once). Honor
these rules or downgrade scope and say so.

Source: SitePoint, *Testing AI Agents: Deterministic Evaluation in a Non-Deterministic World*
(`https://www.sitepoint.com/testing-ai-agents-deterministic-evaluation-in-a-non-deterministic-world/`).

## 1. The hard truth — `temperature=0` is NOT deterministic
- Setting `temperature=0` (greedy decoding) reduces variance but does **not** guarantee identical
  output. It is a necessary knob, never the guarantee. Do not claim "we pinned temperature so it's
  deterministic" — that is false and a gate built on it is invalid.
- **Provider non-determinism** is the cause and it is outside your control: floating-point
  non-associativity across GPUs, batch-dependent kernel selection, mixture-of-experts routing that
  depends on co-batched requests, fused-multiply-add reordering, and silent model/version updates
  behind a stable endpoint. Identical inputs can take different code paths.
- Therefore: **never assert exact-string-equality on raw LLM output.** A flow that does is rejected
  at review. Treat every LLM call as a sample from a distribution, not a function return.

## 2. Run-N + pass-rate threshold (the core gate)
- Each assertion runs the same input **N times** (`run_n`, default 5; ≥10 for release-gating flows)
  and scores each output independently against the rubric/judge.
- The gate is a **pass-rate threshold**, not all-or-nothing: e.g. `pass_rate >= 0.8` over N runs.
  Record `N`, `passes`, and `pass_rate` in every finding so the repro is reconstructable.
- Pick the threshold from the cost of each failure mode: safety/PII/injection checks gate at
  `1.0` (any single failure is a finding); quality/format checks gate in the `0.8–0.9` band.
- A single green run is **not** evidence the gate holds — `N=1` on a non-deterministic system is
  banned for `60-ai-ml` flows.

## 3. Confidence intervals — is the pass-rate real or noise?
- A pass-rate is an estimate from N samples; report it with a **confidence interval**, not a bare
  point. With N=5 and 4 passes the 95% Wilson CI is roughly `[0.38, 0.96]` — too wide to gate on,
  which is itself the signal to raise N.
- **Gate on the lower CI bound, not the point estimate.** `lower_bound(pass_rate, 0.95) >= threshold`
  prevents a lucky run from passing a marginal model. Emit `pass_rate`, `ci_low`, `ci_high`, `N`.
- Use Wilson score interval (stable at small N and near 0/1), not the normal approximation.

## 4. Fixed seed — use it where supported, don't trust it alone
- Where the provider exposes a `seed` param, pin it **and** pin/record `system_fingerprint`. A seed
  narrows variance and aids local repro; it does **not** override §1 — the provider can still drift,
  and a changed fingerprint invalidates the cached baseline.
- Seed is a repro aid layered **on top of** run-N, never a replacement for it. No flow may drop
  run-N because "we set a seed."

## 5. Semantic similarity over exact-match
- Replace exact-match with **semantic equivalence**: embedding cosine-similarity against a golden
  reference (gate e.g. `cos_sim >= 0.85`), or an **LLM-as-judge** scoring against an explicit rubric.
- For structured output, assert on the **parsed shape and invariants** (valid JSON, required keys,
  value ranges, schema-validates) — never on byte-for-byte text.
- The judge is itself non-deterministic: it is subject to §2–§3 (run-N + threshold + CI) like any
  other LLM call. Use a cheap pinned judge model and log the rubric verdict per run.

## 6. Setting a stable gate on a non-deterministic system — checklist
A `60-ai-ml` flow's gate config MUST declare, and the finding MUST echo back:
- `run_n` (≥5; ≥10 for release) and the scoring method (semantic / judge / schema).
- `pass_rate` threshold **and** the CI method + confidence level it gates on.
- `seed` + `system_fingerprint` / model version when the provider supports them.
- `temperature` (0 for eval) — recorded as a variance-reduction knob, **not** a determinism claim.
- The golden fixture id (per the guardrails contract) so the baseline is pinned.

## 7. Gate-impact interaction
- A flaky/wide-CI result (CI spans the threshold) is **inconclusive**, not a pass — surface it and
  raise N before deciding. Maps to a `major` finding for release flows per the severity rubric.
- Safety/security assertions (PII leak, prompt injection, jailbreak) that fail on **any** of the N
  runs are `critical` and fail the gate — there is no pass-rate band for them.
