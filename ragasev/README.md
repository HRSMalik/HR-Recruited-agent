# Ragas-based Evaluation (ragasev)

Three-agent evaluation using **Ragas 0.2.15** (`AspectCritic` LLM-as-judge).

## Why this folder

`evaluation/` uses custom direct-OpenAI calls because Ragas's async layer is broken on Python 3.14.
This folder uses **Python 3.10 venv (`.venv-ragas`)** where Ragas works natively.

## Files

| File | Purpose |
|---|---|
| `eval_dataset.json` | Same dataset as evaluation/ (1 JD + 10 CVs + ground truth + bands) |
| `eval_post_ragas.py` | Ragas AspectCritic on the generated job post (4 criteria) |
| `eval_parser_ragas.py` | Ragas AspectCritic on parsed CV vs ground truth (5 criteria x 10 CVs) |
| `eval_shortlist_ragas.py` | Ragas AspectCritic on shortlist scores (band + stability, 10 CVs) |
| `run_all_ragas.py` | Runs all three, saves `results_*_ragas.json` |

## Setup (one-time)

```powershell
# Create Python 3.10 venv at d:\Hrmsagent\.venv-ragas (already done)
py -3.10 -m venv d:\Hrmsagent\.venv-ragas

# Install dependencies
d:\Hrmsagent\.venv-ragas\Scripts\python.exe -m pip install ragas==0.2.15 datasets `
    langchain langchain-openai langgraph langgraph-checkpoint-sqlite==2.0.10 `
    pymongo python-dotenv openai==1.97.0 pymupdf `
    google-auth-oauthlib google-api-python-client fastapi
```

## Run

From project root:

```powershell
cd d:\Hrmsagent\HR-Recruited-agent
d:\Hrmsagent\.venv-ragas\Scripts\python.exe ragasev\run_all_ragas.py
```

Or individually:

```powershell
d:\Hrmsagent\.venv-ragas\Scripts\python.exe ragasev\eval_post_ragas.py
d:\Hrmsagent\.venv-ragas\Scripts\python.exe ragasev\eval_parser_ragas.py
d:\Hrmsagent\.venv-ragas\Scripts\python.exe ragasev\eval_shortlist_ragas.py
```

## Output

Each script writes `results_<agent>_ragas.json` with the framework explicitly tagged.

## Cleanup

Test CVs are tagged with `jd_id=RAGASEV_xxx` in MongoDB. Remove with:

```js
db.candidates_info.deleteMany({jd_id: /^RAGASEV_/})
db.processed_applications.deleteMany({jd_id: /^RAGASEV_/})
```
