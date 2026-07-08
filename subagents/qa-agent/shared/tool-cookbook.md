# Tool Cookbook — Concrete Command Idioms

Battle-tested command-level patterns flows use to actually execute tests. Abstract "use an HTTP client" is not enough — these are the exact idioms.

## curl (HTTP testing)

| Flag | Purpose |
|------|---------|
| `-s` | silent (suppress progress) |
| `-o /dev/null` | discard body (status-only tests) |
| `-w "%{http_code}"` | print the HTTP status code |
| `-w "\n%{http_code} %{time_total}s"` | status + latency |
| `-X POST/PUT/DELETE` | set method |
| `-H "Content-Type: application/json"` | request header |
| `-d '{"k":"v"}'` | JSON body |
| `-b <jar>` / `-c <jar>` | send / save cookies |
| `-sI` | headers only (content-type / security-header checks) |

## Inline JSON assertion (curl | python3)

Pipe the response into a one-liner that asserts on fields — fail loudly:

```bash
curl -s "$BASE/ranked-candidates?jd_id=jd-1" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'items' in d and 'total' in d, 'missing envelope'
scores = [c['composite_score'] for c in d['items']]
assert scores == sorted(scores, reverse=True), 'not sorted desc'
assert all(0 <= s <= 100 for s in scores), 'score out of range'
print('OK', len(scores))
"
```

## Concurrency (the ONLY way to test rate limits / pool exhaustion)

Sequential requests never trigger rate limiters or connection-pool limits. Fire N in parallel with bash `&` and tally the status codes:

```bash
for i in $(seq 1 70); do
  curl -s -o /dev/null -w "%{http_code}\n" "$BASE/endpoint" &
done | sort | uniq -c     # → counts of 200 / 429 / 500
```

Use this for `performance-load`, `stress-spike-soak`, and the rate-limit checks in `security`.

## grep — verify a fix landed (never trust "I changed it")

After a fix is claimed, confirm it's actually in the source:

```bash
grep -n "html.escape\|markupsafe" app.py        # XSS fix present?
grep -nE "INSERT|UPDATE|DELETE" services/db.py    # destructive SQL leaked in?
```

This is the basis of the `code-fix verification` step — grep, don't trust memory.

## CSV / export checks without downloading the file

```bash
curl -s "$BASE/export?format=csv" | head -1      # inspect header / column names
curl -s "$BASE/export?format=csv" | wc -l        # row count, no full load
```

## Headers / security checks

```bash
curl -sI "$BASE/book/$TOKEN" | grep -iE "content-security-policy|x-frame-options|strict-transport"
curl -si -X OPTIONS "$BASE/candidates" -H "Origin: https://evil.example.com" \
  -H "Access-Control-Request-Method: GET" | grep -i "access-control-allow"
```

## k6 — load testing with thresholds + checks (the pass/fail oracle)

Bash `&` concurrency tallies status codes but has no built-in pass/fail bar. k6 encodes the acceptance criteria *in the script* via `options.thresholds` — the process exits non-zero when a threshold is breached, so it gates a flow without any extra parsing. `checks` assert per-response; `thresholds` assert on the aggregate metric.

```javascript
// load.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 50,
  duration: '30s',
  thresholds: {
    http_req_failed:   ['rate<0.01'],            // <1% errors
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    checks:            ['rate>0.99'],             // >99% checks pass
  },
};

export default function () {
  const res = http.get(`${__ENV.BASE}/ranked-candidates?jd_id=jd-1`);
  check(res, {
    'status 200':       (r) => r.status === 200,
    'has items envelope': (r) => r.json('items') !== undefined,
  });
}
```

```bash
BASE="$BASE" k6 run load.js     # exit code != 0 ⇒ a threshold failed ⇒ flow FAILs
```

- Thresholds are the grounded oracle — read the acceptance bar from the ticket, encode it, let the exit code decide. Never eyeball the summary.
- A threshold breach can abort early with `abortOnFail: true` inside the threshold object — use for soak/spike where running to completion wastes time once the bar is blown.
- Read-only by default (GET). For write paths use a dedicated test/sandbox target, never prod data.
- Source: grafana.com k6 docs — *Thresholds* (`options.thresholds`) and *Checks*.

## Secret scanning — gitleaks / trufflehog (verified, no false positives)

Both scanners are read-only — they inspect the tree/history, never mutate it. Run in **verified / no-false-positive mode** so a finding means a *live, confirmed* secret, not a high-entropy string that looks scary but isn't. This keeps the oracle grounded: a non-empty report is real.

```bash
# gitleaks — scan working tree, report only, machine-readable, non-zero exit on a finding
gitleaks detect --source . --report-format json --report-path gitleaks.json --redact --no-banner

# trufflehog — --only-verified actively validates each credential against its provider
trufflehog filesystem . --only-verified --json
trufflehog git file://. --only-verified --json     # include history
```

- `--only-verified` (trufflehog) and a tuned `.gitleaks.toml` allowlist are what suppress false positives — without them every example key in a fixture fires. Treat an *unverified* hit as `Watch (do not gate)`, a *verified* hit as a hard FAIL.
- `--redact` (gitleaks) keeps the actual secret out of the report artifact — the report is evidence, not a second leak.
- Exit code is the gate: gitleaks exits non-zero when leaks are found; tally that, don't grep the JSON by hand for the verdict.

## ZAP — DAST via the Automation Framework (declarative YAML)

For dynamic scanning, drive OWASP ZAP with the **Automation Framework**: one YAML file describes context, the spider/active-scan jobs, and the pass/fail report. Declarative beats ad-hoc CLI flags — the plan *is* the test definition, reproducible and reviewable.

```yaml
# zap-plan.yaml
env:
  contexts:
    - name: app
      urls: [ "https://app-staging.example.net" ]    # staging/sandbox target — never prod
jobs:
  - type: spider
    parameters: { context: app, maxDuration: 5 }
  - type: activeScan
    parameters: { context: app, policy: "Default Policy" }
  - type: report
    parameters: { template: traditional-json, reportFile: zap-report.json }
  - type: exitStatus               # turns findings into the process exit code (the gate)
    parameters: { errorLevel: High, warnLevel: Medium }
```

```bash
zap.sh -cmd -autorun zap-plan.yaml     # exit status set by the exitStatus job ⇒ flow gate
```

- Active scan sends crafted payloads — only ever point it at a **staging/sandbox** target you own, never production. This preserves the non-destructive convention at the environment level.
- `exitStatus` job is the oracle: `errorLevel: High` fails the run on any High alert; Medium is surfaced as a warning (`Watch (do not gate)`), not a gate.
- The JSON report is the evidence artifact — attach it, don't paraphrase the alerts.

## Semantic-similarity assertion (LLM / free-text outputs)

Exact-match assertions break on LLM or any free-text output — the response is correct but phrased differently every run. Assert on **embedding cosine similarity ≥ threshold** against a reference answer instead of string equality. The reference answer + threshold is the grounded oracle; nothing about the model itself is trusted.

```python
import sys, json
from openai import OpenAI   # or any embeddings provider

THRESHOLD = 0.85
ref = "Candidate ranked highest due to 8 years of relevant Python and FastAPI experience."

client = OpenAI()
def embed(t): return client.embeddings.create(model="text-embedding-3-small", input=t).data[0].embedding
def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5; nb = sum(y*y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0

got = json.load(sys.stdin)["explanation"]
sim = cosine(embed(got), embed(ref))
assert sim >= THRESHOLD, f"semantic drift: cosine {sim:.3f} < {THRESHOLD}\n got: {got!r}"
print(f"OK cosine={sim:.3f}")
```

```bash
curl -s "$BASE/explain?cand_id=c-1" | python3 semantic_assert.py
```

- Pick the threshold from a calibration set (known-good vs known-bad pairs), not by guessing — record it next to the test so the bar is auditable.
- Embeddings are read-only computation; this asserts, it never writes back to the app under test.
- Treat `THRESHOLD - 0.05 ≤ sim < THRESHOLD` as a `Watch (do not gate)` soft zone worth a human glance, but only `sim < THRESHOLD` FAILs the flow.
- Use this only where exact-match genuinely can't apply (explanations, summaries, rewrites). Keep exact-match for structured fields — semantic similarity is laxer by design.

## Browser driving — HEADLESS by default, HEADED only on request

Drive the real deployed UI in a real browser when a check needs the rendered DOM / actual network calls (catches frontend-only illusions unit tests miss). Use **puppeteer-core** against the **system Chrome** (don't download one).

**Mode policy (important):** run **headless by default**. Only run **headed** (a visible window) when **explicitly asked** ("watch it", "show me", "do it in front of me", a live/UAT walkthrough) **or when visual confirmation is genuinely required**. Headed is slower and needs a display — never the default.

```javascript
import puppeteer from 'puppeteer-core'
// Generic Chrome discovery — first match wins; override with $CHROME.
const CHROME = process.env.CHROME || ['/usr/bin/google-chrome','/usr/bin/google-chrome-stable','/usr/bin/chromium','/usr/bin/chromium-browser'].find(p => { try { return require('fs').existsSync(p) } catch { return false } })
const HEADED = process.env.HEADED === '1'   // opt-in per run: HEADED=1 → visible window
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: HEADED ? false : 'new',
  slowMo: HEADED ? 40 : 0,                  // slow enough to watch only when headed
  defaultViewport: HEADED ? null : { width: 1440, height: 900 },
  args: ['--no-sandbox'].concat(HEADED ? ['--start-maximized'] : []),
})
```

```bash
node driver.mjs             # headless (default)
HEADED=1 DISPLAY=:1 node driver.mjs   # headed: visible window on the given X11 display
```

- **Headed needs a display** — pass `DISPLAY` (e.g. `:1`); without it a headed launch has nowhere to render.
- Form-fill by field type: **controlled React** (`value`+`onChange`) needs real keystrokes (`page.type` / click+type) — native `.value` set is ignored; **uncontrolled / react-hook-form** accepts a fast bulk native-setter + `input`/`change`/`blur` events. `type=time`/`date` often reject `page.type` (use native-set); include `type=password` in fill sets; radios → click an option; selects → `page.select`.
- **Verify persistence, not the toast** — confirm a create via the real `POST → 2xx` (capture `page.on('response')`) or a **page reload**; a success toast alone can be a frontend-only fake.
- **Live-data safety** — namespace throwaway rows (`SMOKE-<id>` / `smoke+…@example.com`), delete via API in `finally`, never touch pre-existing data; some records are un-deletable by design (know before you create).
- When headed, drop screenshots at each step + an on-page caption banner so the run is watchable and reviewable.

## Notes
- Always capture BOTH status and body on a failure — the body is the evidence.
- For multi-field checks, prefer the `python3 -c` block over chained greps.
- Never hardcode secrets in these commands — read from env (`"$TOKEN"`, `"$BASE"`).
- Aggregate-bar tools (k6, ZAP, gitleaks) gate via **process exit code** — tally the exit code, never paraphrase the summary.
