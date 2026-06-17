# HR Recruited — Autonomous AI Recruitment System

**Product Requirements Document**
**Date Created:** May 20, 2026

---

## Executive Summary

HR Recruited is a fully autonomous, AGI-based multi-agent system that replaces the entire function of a human HR recruiter. The system handles every step of the recruitment process end-to-end — from generating a job description to publishing it, parsing and evaluating CVs from candidates who apply, conducting interviews, and delivering a final ranked shortlist — without any human involvement in the middle.

The system is **inbound-only**: candidates discover roles and apply themselves through the Google Form attached to each job post. The system never sources or approaches candidates — there is no outbound scraping or outreach.

The goal is not to assist a recruiter. The goal is to be the recruiter.

Each capability is owned by a dedicated autonomous agent. Agents communicate through a shared state pipeline, make independent decisions within their domain, and hand off to the next agent without waiting for human input. The system is designed to operate continuously — processing new job openings, evaluating incoming applications, and maintaining a live candidate pipeline at all times.

The build strategy is deliberate: one agent at a time, fully operational before the next is added. This ensures every link in the chain is reliable before the chain is complete. The first agent (Job Post) is already partially built. Each subsequent agent extends the system's autonomy further until no human touchpoint remains in the process.

The end state is a system where a company inputs a hiring need and receives a ready-to-interview shortlist — fully handled by AI.

---

## Scope

- Fully autonomous multi-agent recruitment pipeline — no human required between job input and candidate shortlist.
- Human touchpoints limited to: (1) initial job requirements input, (2) final hire decision.
- AGI-oriented design — agents reason, adapt, and handle edge cases without hardcoded rules.
- One agent built and validated at a time; system grows incrementally toward full autonomy.
- REST API as the system backbone; Streamlit UI as the recruiter-facing control surface.
- LinkedIn as the primary job **distribution** channel — for publishing openings only, not for sourcing candidates.
- Inbound-only intake: candidates apply themselves via the Google Form attached to each job post. No outbound sourcing, scraping, or direct outreach.
- All agent decisions are explainable — transparent scoring with plain-language reasoning.
- Modular architecture — each agent is independently deployable, replaceable, and scalable.

---

## Agent Pipeline Architecture

The full pipeline consists of 5 agents executed in sequence. Each agent receives the output of the previous and passes a structured result to the next. Candidates enter the pipeline by applying through the Google Form on a published job post — there is no sourcing step.

```
Job Description
    → [Agent 1: Job Post Agent]
    → [ candidates apply via Google Form ]
    → [Agent 2: Resume Parser Agent]
    → [Agent 3: Matching Agent]
    → [Agent 4: Interview Agent]
    → [Agent 5: Ranking Agent]
    → Recruiter Shortlist
```

| #  | Agent                | Responsibility                                       | Status                   |
|----|----------------------|------------------------------------------------------|--------------------------|
| 1  | Job Post Agent       | Generates and publishes job descriptions to LinkedIn | Built — needs bug fixes  |
| 2  | Resume Parser Agent  | Extracts skills, experience, education from CVs      | Built — disconnected     |
| 3  | Matching Agent       | Scores candidate CV against job description          | Built — JD-aware scoring |
| 4  | Interview Agent      | Conducts structured AI voice interview + booking     | Built — JD-aware scoring |
| 5  | Ranking Agent        | Produces final scored shortlist with reasoning       | Not built                |

---

## Functional Specifications (Features)

### Agent 1: Job Post Agent

**Description:** Takes a job description form input, generates a formatted LinkedIn post using GPT-4o, routes it through a human review step, and publishes it upon approval.

**Inputs:**

- Job title
- Company name
- Required skills
- Experience level
- Location / remote policy
- Compensation range (optional)
- Google Forms link (attached to post for candidate intake)

**Outputs:**

- Formatted LinkedIn post (generated)
- Published LinkedIn post (after approval)
- thread_id for async review flow

**Workflow:**

1. Recruiter submits job details via Streamlit UI or POST /job-posts
2. Agent generates formatted post via LLM
3. System pauses for human review — post returned with status: needs_review
4. Recruiter approves, edits, or requests regeneration via PUT /job-posts/{thread_id}/review
5. On approval, MCP server publishes post to LinkedIn via Playwright automation
6. Result returned: linkedin_posted: true

**Current Bugs to Fix Before Next Agent:**

- LinkedIn post button click is commented out — post never actually publishes
- Browser/Playwright context is never closed — process leak on every call
- CORS wildcard + allow_credentials=True is an invalid and insecure combination
- All API routes are unauthenticated

---

### Agent 2: Resume Parser Agent

**Description:** Accepts a PDF resume/CV and extracts structured candidate information using GPT-4 Vision. Returns a normalized JSON candidate profile.

**Inputs:**

- PDF file (single or multi-page resume)

**Outputs:**

```
name, email, phone, skills, experience_years,
last_job_title, last_company, last_education_degree,
university, summary
```

**Workflow:**

1. PDF uploaded via API or UI
2. PDF rendered to images (one per page)
3. Each page sent to GPT-4 Vision with structured extraction prompt
4. Results merged across pages into single candidate profile
5. Profile stored and passed to Matching Agent

**Fixes Required Before Integration:**

- Wire into app.py — currently a standalone script, never imported
- Fix page ordering — os.listdir() returns unsorted, pages processed randomly
- Fix MIME type map — .jpg/.jpeg fall back to image/png
- Output file data.json must be per-request, not a shared hardcoded filename

---

### Agent 3: Matching Agent

**Description:** Compares a parsed candidate profile against a job description and produces a structured match score with reasoning.

**Inputs:**

- Candidate profile (from Resume Parser Agent)
- Job description (structured form data)

**Outputs:**

```
candidate_id, match_score (0-100), skill_match [],
skill_gaps [], experience_match (bool), reasoning
```

**Scoring Dimensions:**

- Required skills coverage (% of JD skills found in CV)
- Years of experience vs. requirement
- Job title relevance
- Education alignment (if specified)
- Location / remote compatibility

**Threshold:** Candidates scoring below a configurable cutoff (default: 60%) are filtered and do not proceed to the Interview Agent.

---

### Agent 4: Interview Agent

**Description:** Conducts a structured asynchronous text-based screening interview with shortlisted candidates. Questions are dynamically generated based on the job description and candidate profile.

**Inputs:**

- Candidate profile
- Job description
- Match score and skill gaps (from Matching Agent)

**Outputs:**

- Interview transcript
- Per-answer quality scores
- Overall interview score (0–100)
- Red flags identified

**Interview Structure:**

1. 2–3 role-specific technical questions (generated from JD)
2. 1–2 gap-targeted questions (based on skill gaps from Matching Agent)
3. 1 behavioral question
4. 1 availability / logistics question

**Delivery:** Async — candidate receives a link and completes at their own pace. Responses evaluated by LLM against a structured rubric.

---

### Agent 5: Ranking Agent

**Description:** Aggregates scores from all previous agents and produces a final ranked shortlist with transparent reasoning for each candidate.

**Inputs:**

- Match score (from Matching Agent)
- Interview score (from Interview Agent)
- Candidate profile

**Outputs:**

```
rank, candidate_name, composite_score,
score_breakdown { cv_match, interview },
recommendation, flags []
```

**Scoring Weights (configurable):**

- CV Match: 40%
- Interview: 60%

**Shortlist:** Top N candidates (default: 5) delivered to recruiter for final decision.

---

### Recruiter Dashboard (Streamlit UI)

**Description:** Web interface for recruiters to interact with the pipeline — submit job descriptions, review generated posts, upload CVs, and view candidate shortlists.

**Job Post Page**

- Form: job title, company, skills, experience, location, compensation
- Preview generated post before publishing
- Approve / Edit / Regenerate controls
- LinkedIn publish status indicator

**Candidate Pipeline Page**

- Upload CVs (bulk or single)
- View parsed candidate profiles
- View match scores per candidate per job
- Trigger interview for selected candidates
- View interview transcripts and scores

**Shortlist Page**

- Ranked list of candidates per job
- Score breakdown per candidate
- Download shortlist as CSV
- One-click recruiter notes per candidate

**Job Posts History**

- List of all published job posts
- Status: published / pending / failed
- Link to live LinkedIn post

---

## User Stories

**Recruiter**

- As a recruiter, I want to input a job description and receive a formatted LinkedIn post so that I can publish open roles without writing copy manually.
- As a recruiter, I want to upload a batch of CVs and receive a ranked shortlist so that I don't have to manually screen hundreds of applications.
- As a recruiter, I want to see a score breakdown per candidate so that I can explain my shortlist decisions to hiring managers.
- As a recruiter, I want to approve or edit an AI-generated post before it goes live so that I maintain control over what is published.

**Hiring Manager**

- As a hiring manager, I want to receive a shortlist of pre-screened, pre-interviewed candidates so that I only spend time on candidates worth talking to.
- As a hiring manager, I want each candidate to have a reasoning summary so that I can quickly understand why they were ranked where they were.

**Candidate**

- As a candidate, I want to complete an interview at my own pace asynchronously so that I can respond thoughtfully without scheduling pressure.

---

## Use Cases

- **Job Post Flow:** Recruiter fills form → Agent generates post → Recruiter reviews → Approves → Agent publishes to LinkedIn → Confirmation returned.
- **CV Screening Flow:** Recruiter uploads CVs → Parser extracts profiles → Matching Agent scores each against JD → Below-threshold candidates filtered → Remaining passed to Interview Agent.
- **Interview Flow:** Candidate receives interview link → Completes async text interview → Agent evaluates responses → Score added to candidate record.
- **Shortlist Flow:** Ranking Agent aggregates all scores → Produces ranked list → Recruiter views shortlist in dashboard → Downloads CSV or takes notes.
- **Re-ranking Flow:** Recruiter adjusts scoring weights → Ranking Agent re-scores → Updated shortlist returned instantly.

---

## Non-Functional Features

**Security:**

- API key authentication required on all endpoints.
- No credentials, tokens, or secrets stored in code or git history.
- LinkedIn credentials sourced exclusively from environment variables.
- CORS restricted to known origins — no wildcard in production.

**Performance:**

- CV parsing: 10 seconds or less per resume.
- Match scoring: 3 seconds or less per candidate.
- Interview evaluation: 15 seconds or less per transcript.
- Shortlist generation (10 candidates): 5 seconds or less.

**Scalability:**

- Each agent stateless and independently scalable.
- LangGraph checkpointer backed by persistent storage (SQLite for dev, MongoDB for prod).
- Pipeline designed to process batches of 50+ CVs without manual intervention.

**Reliability:**

- Multi-method fallback on all external API calls.
- Failed agent steps logged with full context — no silent failures.
- Human override available at every stage.

**Usability:**

- Streamlit UI requires no technical training to operate.
- All AI decisions come with plain-language reasoning.
- Shortlist exportable as CSV at any time.

---

## Technical Requirements

| Component             | Technology                                    |
|-----------------------|-----------------------------------------------|
| Runtime               | Python 3.11+                                  |
| API Framework         | FastAPI                                       |
| Agent Orchestration   | LangGraph (StateGraph + SQLite checkpointer)  |
| LLM                   | GPT-4o (post, matching, interview, ranking)   |
| CV Parsing            | GPT-4 Vision                                  |
| Browser Automation    | Playwright via MCP server                     |
| Frontend              | Streamlit                                     |
| Database              | SQLite (dev) / MongoDB (prod)                 |
| Authentication        | API key via X-API-Key header                  |
| Deployment            | Docker + Uvicorn                              |

---

## Feature Prioritization (MVP)

1. Fix Job Post Agent (uncomment post button, close browser, add auth, fix CORS)
2. Wire Resume Parser Agent into API (POST /candidates/parse)
3. Build Matching Agent (CV vs JD scoring)
4. Connect Parser to Matching — return scored candidate list
5. Build Recruiter Dashboard: Candidate Pipeline page
6. Build Interview Agent (async text interview flow)
7. Build Ranking Agent (composite score + shortlist output)
8. Build Shortlist page in dashboard
