# JD Evaluation Criteria Feature — Implementation Plan

## Overview

After a Job Description is approved (before it is posted), the system generates a set of evaluation criteria. HR can review, edit, reorder, and add criteria before confirming. Each criterion carries an **importance level** and is flagged for which evaluation stage it applies to (CV screening, AI interview, or both). These criteria then drive scoring in `shortlisting_agent.py` and `voice_agent.py` instead of the current generic JD-text-based extraction.

---

## Workflow Change

```
Current:
  JD Created → Human Approval → Posted → Candidates Scored (against raw JD text)

New:
  JD Created → Human Approval → Criteria Generated → HR Reviews Criteria
             → Criteria Confirmed → Posted → Candidates Scored (against criteria)
```

The new "Criteria Review" step sits between JD approval and posting.

---

## Data Model

### New Collection: `job_criteria`

One document per JD, keyed by `jd_id`.

```json
{
  "_id": "<jd_id>",
  "status": "draft | confirmed",
  "criteria": [
    {
      "id": "uuid",
      "criteria": "Machine Learning Expertise",
      "description": "Deep understanding of ML algorithms (supervised, unsupervised, RL), model development, training, evaluation, and deployment. Familiarity with TensorFlow, PyTorch, scikit-learn.",
      "importance": "must_have",
      "applies_to_cv": true,
      "applies_to_interview": true
    }
  ],
  "generated_at": "ISO datetime",
  "confirmed_at": "ISO datetime | null"
}
```

### New Pydantic Schemas (`schemas.py`)

```python
class CriterionImportance(str, Enum):
    must_have       = "must_have"
    very_important  = "very_important"
    important       = "important"
    good_to_have    = "good_to_have"

class Criterion(BaseModel):
    id: str                            # uuid, generated on creation
    criteria: str                      # title
    description: str = Field(max_length=1000)
    importance: CriterionImportance
    applies_to_cv: bool = True
    applies_to_interview: bool = True

class JobCriteriaDoc(BaseModel):
    jd_id: str
    status: Literal["draft", "confirmed"]
    criteria: List[Criterion]

class CriteriaUpdateRequest(BaseModel):
    criteria: List[Criterion]          # full replacement list

class CriteriaConfirmRequest(BaseModel):
    pass                               # explicit confirmation step
```

---

## Backend

### 1. New file: `criteria_agent.py`

**`generate_criteria(jd_id, jd_text) -> JobCriteriaDoc`**
- Calls LLM with structured output to produce a list of `Criterion` objects from the JD text.
- LLM prompt asks it to produce 6–10 criteria, each with title, description, importance, and which stages it applies to.
- Saves to `job_criteria` collection with `status = "draft"`.
- Returns the document.

**`get_criteria(jd_id) -> JobCriteriaDoc | None`**
- Fetches from `job_criteria` by `jd_id`.

**`update_criteria(jd_id, criteria: List[Criterion]) -> JobCriteriaDoc`**
- Full replacement of the criteria list. Keeps `status = "draft"`.

**`confirm_criteria(jd_id) -> JobCriteriaDoc`**
- Sets `status = "confirmed"`, sets `confirmed_at`.
- Only confirmed criteria are used in scoring.

### 2. New API endpoints (`app.py`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/jobs/{jd_id}/criteria/generate` | Trigger LLM generation, returns draft |
| `GET`  | `/jobs/{jd_id}/criteria` | Fetch current criteria (draft or confirmed) |
| `PUT`  | `/jobs/{jd_id}/criteria` | Replace full criteria list |
| `POST` | `/jobs/{jd_id}/criteria/confirm` | Confirm and lock for scoring |

### 3. Workflow hook in `job_post.py`

After the JD approval node, add a node that calls `generate_criteria(jd_id, jd_text)`. The interrupt mechanism already used for HR review of the JD text is reused here — the graph pauses, HR reviews criteria via the frontend, then resumes via `POST /jobs/{jd_id}/criteria/confirm`.

---

## Scoring Integration

### Importance weights

| Importance | Weight |
|---|---|
| `must_have` | 4 |
| `very_important` | 3 |
| `important` | 2 |
| `good_to_have` | 1 |

### New scoring approach

For each applicable criterion, the LLM scores `0.0 | 0.5 | 1.0` (present / partial / absent). The final score is a weighted average:

```
score = Σ(criterion_score × weight) / Σ(weights) × 100
```

A `must_have` criterion scored `0.0` applies an additional hard penalty: score is capped at 40.

### Changes to `shortlisting_agent.py`

- `_extract_jd_requirements()` and the generic `CandidateEvaluation` fields are replaced.
- New function `_score_candidate_against_criteria(candidate, criteria: List[Criterion])` that scores each `applies_to_cv=True` criterion separately using `with_structured_output`.
- New Pydantic model `CriterionScore` with `score: Literal[0.0, 0.5, 1.0]` and `evidence: str`.
- Experience score (`_calc_experience_score`) stays as-is — criteria don't replace it.

### Changes to `voice_agent.py`

- `_score_interview()` fetches `applies_to_interview=True` criteria from `job_criteria`.
- Same `CriterionScore` model, same weighted average formula.

---

## Frontend

### Criteria Review Page

- Shown after JD approval, before the "Post to LinkedIn" button becomes active.
- Each card shows: criterion title (editable), description (editable, char counter), importance selector (4 options with colour coding), two checkboxes (CV / Interview).
- "Add Criterion" button appends a blank card.
- Delete icon on each card.
- "Confirm Criteria" button → calls `POST /jobs/{jd_id}/criteria/confirm` → unlocks JD posting.

### Importance colour coding

| Level | Colour |
|---|---|
| Must Have | Red `#D94F3D` |
| Very Important | Yellow `#E8A838` |
| Important | Green `#4CAF7D` |
| Good to Have | Blue `#4A8FCC` |

---

## Implementation Phases

### Phase 1 — Data layer
- [ ] Add `Criterion`, `JobCriteriaDoc`, `CriteriaUpdateRequest` to `schemas.py`
- [ ] Create `criteria_agent.py` with generate / get / update / confirm functions
- [ ] Wire the four API endpoints in `app.py`

### Phase 2 — Workflow hook
- [ ] Add criteria generation node to `job_post.py` LangGraph after JD approval
- [ ] Add interrupt + resume flow so HR can confirm before posting proceeds

### Phase 3 — Scoring integration
- [ ] Add `CriterionScore` to `schemas.py`
- [ ] Rewrite `shortlisting_agent.py` to score per-criterion with weighted average
- [ ] Update `voice_agent.py` to load and score per-criterion for interview
- [ ] Add hard cap logic for `must_have` misses

### Phase 4 — Frontend
- [ ] Criteria review page with cards, importance selector, add/delete
- [ ] Resume JD posting only after `status = "confirmed"`

---

## Open Questions

1. **Fallback**: If HR never confirms criteria (e.g. old JDs), should scoring fall back to the current JD-text approach or block scoring entirely?
2. **Regeneration**: Should HR be able to regenerate criteria with a feedback prompt (mirrors the JD regeneration flow)?
3. **Per-criterion experience**: Does experience scoring stay flat (current gap-based function) or should some criteria carry their own experience sub-requirement?
