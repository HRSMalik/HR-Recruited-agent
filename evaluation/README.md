# Evaluation

Three-agent evaluation using Ragas (post agent) + custom checks (parser, shortlist).

## Files

| File | Purpose |
|---|---|
| `eval_dataset.json` | Test data: 1 JD, 4 CVs, ground truth, expected bands |
| `eval_post.py` | Runs post agent → Ragas AspectCritic on 5 criteria |
| `eval_parser.py` | Runs parser on each CV → field-by-field accuracy |
| `eval_shortlist.py` | Scores each CV → band check + stability across 3 runs |
| `run_all.py` | Runs all three, saves `results_*.json` |

## Install

```powershell
pip install ragas datasets
```

## Run

From project root:

```powershell
cd d:\Hrmsagent\HR-Recruited-agent
.\.venv\Scripts\Activate.ps1
python evaluation\run_all.py
```

Or individually:

```powershell
python evaluation\eval_post.py
python evaluation\eval_parser.py
python evaluation\eval_shortlist.py
```

## Output

Each script prints PASS/FAIL per check and writes `results_<agent>.json`.

## Cleanup

Parser and shortlist evals write test CVs to Mongo with a tagged `jd_id` like `EVAL_RUN_xxxx`. To clean up:

```js
db.candidates_info.deleteMany({jd_id: /^EVAL_RUN_/})
db.processed_applications.deleteMany({jd_id: /^EVAL_RUN_/})
```
