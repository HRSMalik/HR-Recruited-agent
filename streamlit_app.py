import os
import uuid as _uuid

import streamlit as st
import pandas as pd
import requests
from requests import Response
from dotenv import load_dotenv

load_dotenv()

API_BASE = "http://localhost:8000"

# Authenticated session: every API call carries the bearer key (QA-01 auth).
_sess = requests.Session()
_api_key = os.getenv("API_KEY")
if _api_key:
    _sess.headers["Authorization"] = f"Bearer {_api_key}"


st.set_page_config(
    page_title="Recruitment Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# MODERN STYLING
# -----------------------------

st.markdown("""
<style>
    /* Page padding */
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }

    /* Headings */
    h1 { font-weight: 700 !important; letter-spacing: -0.02em; }
    h2, h3 { font-weight: 600 !important; letter-spacing: -0.01em; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] h1 {
        font-size: 1.15rem !important;
        padding-bottom: 0.5rem;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #ffffff;
        padding: 1rem 1.25rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stMetric"] label {
        color: #64748b !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        border: 1px solid #e2e8f0;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: #6366f1;
        color: #6366f1;
    }
    .stButton > button:active {
        transform: scale(0.96);
        border-color: #4f46e5;
        transition: transform 0.08s ease;
    }

    /* Containers with borders look like cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border-color: #e2e8f0 !important;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    /* Tables */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }

    /* Subtle dividers */
    hr { margin: 1.5rem 0; opacity: 0.4; }

    /* Caption */
    .stCaption, p.caption-text {
        color: #64748b !important;
        font-size: 0.875rem;
    }

    /* Candidate processing status badges */
    @keyframes pulse-badge {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.45; }
    }
    .processing-badge {
        display: inline-block;
        background: #dbeafe; color: #1e40af;
        padding: 4px 12px; border-radius: 999px;
        font-weight: 600; font-size: 0.8rem;
        animation: pulse-badge 1.2s ease-in-out infinite;
    }
    .pending-badge {
        display: inline-block;
        background: #f1f5f9; color: #475569;
        padding: 4px 12px; border-radius: 999px;
        font-weight: 600; font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------
# HELPERS
# -----------------------------

def _parse_json_response(resp: Response) -> dict | None:
    try:
        data = resp.json()
    except ValueError:
        st.error(f"API returned non-JSON response (HTTP {resp.status_code}).")
        st.code(resp.text)
        return None

    if not isinstance(data, dict):
        st.error(f"API returned unexpected JSON type: {type(data).__name__} (HTTP {resp.status_code}).")
        st.write(data)
        return None

    if resp.status_code >= 400:
        st.error(f"API error (HTTP {resp.status_code}).")
        st.write(data)
        return None

    return data


def _fetch_list(path: str, skip: int, limit: int) -> dict | None:
    try:
        resp = _sess.get(
            f"{API_BASE}{path}",
            params={"skip": skip, "limit": limit},
            timeout=30,
        )
    except requests.RequestException as e:
        st.error("Failed to call API.")
        st.write(str(e))
        return None
    return _parse_json_response(resp)


def _fit_pill(pct: int) -> str:
    if pct >= 80:
        bg, fg = "#dcfce7", "#166534"
    elif pct >= 50:
        bg, fg = "#fef3c7", "#92400e"
    else:
        bg, fg = "#fee2e2", "#991b1b"
    return (
        f'<span style="background:{bg};color:{fg};padding:4px 12px;'
        f'border-radius:999px;font-weight:600;font-size:0.85rem;'
        f'display:inline-block;">{pct}%</span>'
    )


def _short_id(value: str | None, length: int = 8) -> str:
    if not value:
        return "—"
    return str(value)[:length]


def _per_page_selector(state_key: str):
    col_spacer, col_select = st.columns([4, 1])
    with col_select:
        st.selectbox(
            "Per page",
            [10, 25, 50],
            key=state_key,
            label_visibility="collapsed",
        )


def _paginator(state_key: str, total: int, limit: int):
    skip = st.session_state.get(state_key, 0)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Prev", key=f"{state_key}_prev", disabled=skip <= 0, use_container_width=True):
            st.session_state[state_key] = max(0, skip - limit)
            st.rerun()
    with col2:
        last_shown = min(skip + limit, total)
        first_shown = skip + 1 if total > 0 else 0
        st.markdown(
            f"<p style='text-align:center;color:#64748b;margin-top:0.5rem;'>"
            f"Showing <b>{first_shown}–{last_shown}</b> of <b>{total}</b></p>",
            unsafe_allow_html=True,
        )
    with col3:
        if st.button("Next →", key=f"{state_key}_next", disabled=skip + limit >= total, use_container_width=True):
            st.session_state[state_key] = skip + limit
            st.rerun()


def _page_header(title: str, subtitle: str | None = None):
    st.markdown(f"<h1 style='margin-bottom:0.25rem;'>{title}</h1>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(
            f"<p style='color:#64748b;font-size:0.95rem;margin-top:0;margin-bottom:1.5rem;'>{subtitle}</p>",
            unsafe_allow_html=True,
        )


def _render_candidate_detail(c: dict):
    """Full candidate profile with scoring breakdown inside an expander."""
    with st.expander("📋 View Full Profile"):
        pct = int(c.get("fit_percent") or 0)
        criteria_scores = c.get("criteria_scores") or []
        doc_prof = c.get("document_professionalism") or {}
        prof_profile = c.get("professional_profile") or {}
        red_flags = c.get("red_flags") or {}

        ci1, ci2 = st.columns(2)
        with ci1:
            st.markdown("**Contact**")
            st.write(f"📧 {c.get('email') or '—'}")
            st.write(f"📞 {c.get('phone') or c.get('phone_e164') or '—'}")
        with ci2:
            st.markdown("**Background**")
            inst = c.get("last_education_institution") or ""
            deg = c.get("last_education_degree") or "—"
            st.write(f"🎓 {deg}{' — ' + inst if inst else ''}")
            exp = c.get("experience_years") or 0
            free = c.get("freelance_experience_years") or 0
            st.write(f"💼 {exp} yrs exp{f' · {free} yrs freelance' if free else ''}")

        is_scored = bool(criteria_scores or doc_prof or prof_profile)

        if not is_scored:
            raw = (c.get("raw_cv_text") or "").strip()
            if raw:
                st.markdown("---")
                st.markdown("**Resume Text**")
                st.text(raw[:2500])
            return

        st.markdown("---")
        st.markdown(
            f"<h4 style='margin-bottom:0.75rem;'>Overall Score &nbsp; {_fit_pill(pct)}</h4>",
            unsafe_allow_html=True,
        )

        if criteria_scores:
            st.markdown("##### Technical Criteria — 70%")
            rows = [
                {
                    "Criterion": cs.get("criterion_name", ""),
                    "Score": cs.get("score", 0),
                    "Evidence": cs.get("evidence", ""),
                }
                for cs in criteria_scores
            ]
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score": st.column_config.ProgressColumn("Score", min_value=1, max_value=10, format="%d/10"),
                    "Evidence": st.column_config.TextColumn("Evidence", width="large"),
                },
            )

        if doc_prof or prof_profile:
            st.markdown("##### Professional Assessment — 20%")
            prof_rows = []
            if doc_prof:
                prof_rows += [
                    {"Dimension": "Attention to Detail", "Category": "Document Professionalism",
                     "Score": doc_prof.get("attention_to_detail", 0), "Evidence": doc_prof.get("attention_evidence", "")},
                    {"Dimension": "Clarity & Completion", "Category": "Document Professionalism",
                     "Score": doc_prof.get("clarity_completion", 0), "Evidence": doc_prof.get("clarity_evidence", "")},
                ]
            if prof_profile:
                managerial_counted = c.get("managerial_experience_counted", True)
                managerial_label = (
                    "Managerial Experience" if managerial_counted
                    else "Managerial Experience (not counted — non-senior role)"
                )
                prof_rows += [
                    {"Dimension": "Strategic Focus", "Category": "Professional Profile",
                     "Score": prof_profile.get("strategic_focus", 0), "Evidence": prof_profile.get("strategic_evidence", "")},
                    {"Dimension": "Intellectual Ability", "Category": "Professional Profile",
                     "Score": prof_profile.get("intellectual_ability", 0), "Evidence": prof_profile.get("intellectual_evidence", "")},
                    {"Dimension": managerial_label, "Category": "Professional Profile",
                     "Score": prof_profile.get("managerial_experience", 0), "Evidence": prof_profile.get("managerial_evidence", "")},
                    {"Dimension": "Recognized Accomplishments", "Category": "Professional Profile",
                     "Score": prof_profile.get("recognized_accomplishments", 0), "Evidence": prof_profile.get("accomplishments_evidence", "")},
                    {"Dimension": "Critical Thinking", "Category": "Professional Profile",
                     "Score": prof_profile.get("critical_thinking", 0), "Evidence": prof_profile.get("critical_thinking_evidence", "")},
                ]
            st.dataframe(
                pd.DataFrame(prof_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score": st.column_config.ProgressColumn("Score", min_value=1, max_value=10, format="%d/10"),
                    "Evidence": st.column_config.TextColumn("Evidence", width="large"),
                },
            )

        exp_score = c.get("experience_score")
        if exp_score is not None:
            st.markdown("##### Experience Fit — 10%")
            req_years = c.get("experience_required_years") or 0
            candidate_exp = (c.get("experience_years") or 0) + (c.get("freelance_experience_years") or 0)
            ec1, ec2, ec3 = st.columns(3)
            ec1.metric("Candidate Years", f"{candidate_exp} yrs")
            ec2.metric("Required Years", f"{req_years} yrs" if req_years else "Not stated")
            ec3.metric("Experience Score", f"{exp_score}/10")

        if red_flags:
            st.markdown("##### Red Flags")
            rf1, rf2, rf3 = st.columns(3)

            def _flag_cell(col, flag: bool, label: str, evidence: str = ""):
                bg = "#fee2e2" if flag else "#dcfce7"
                fg = "#991b1b" if flag else "#166534"
                icon = "🚩" if flag else "✅"
                ev_html = f"<div style='font-size:0.78rem;margin-top:4px;'>{evidence}</div>" if evidence else ""
                col.markdown(
                    f'<div style="background:{bg};color:{fg};padding:10px 14px;border-radius:8px;">'
                    f'<div style="font-weight:600;font-size:0.85rem;">{icon} {label}</div>'
                    f'{ev_html}</div>',
                    unsafe_allow_html=True,
                )

            _flag_cell(rf1, red_flags.get("timeline_tenure", False), "Timeline / Tenure", red_flags.get("timeline_evidence", ""))
            _flag_cell(rf2, red_flags.get("experience_misrepresentation", False), "Experience Integrity", red_flags.get("representation_evidence", ""))
            _flag_cell(rf3, red_flags.get("unprofessional_email", False), "Professional Email")


# -----------------------------
# PAGE: OPEN JOBS
# -----------------------------

_IMPORTANCE_BADGE_COLOR = {
    "must_have": "#991b1b",
    "very_important": "#c2410c",
    "important": "#1e40af",
    "good_to_have": "#166534",
}


def _render_job_criteria_table(jd_id: str):
    """Full-width, non-truncating criteria display — one card per criterion so
    long descriptions are always fully readable (a dataframe/popover cuts them off)."""
    try:
        resp = _sess.get(f"{API_BASE}/jobs/{jd_id}/criteria", timeout=15)
    except requests.RequestException as e:
        st.error(f"Failed to fetch criteria: {e}")
        return
    if resp.status_code == 404:
        st.info("No evaluation criteria generated yet for this job.")
        return
    if resp.status_code != 200:
        st.error(f"Failed to fetch criteria (HTTP {resp.status_code})")
        return

    doc = resp.json()
    status = doc.get("status", "draft")
    st.caption("✅ Confirmed" if status == "confirmed" else "📝 Draft")

    criteria = doc.get("criteria", [])
    if not criteria:
        st.info("Criteria list is empty.")
        return

    for i, c in enumerate(criteria, 1):
        importance = c.get("importance", "")
        color = _IMPORTANCE_BADGE_COLOR.get(importance, "#475569")
        st.markdown(
            f"**{i}. {c.get('criteria', '')}** "
            f"<span style='background:{color}1a;color:{color};padding:2px 10px;"
            f"border-radius:6px;font-size:0.75rem;font-weight:600;margin-left:6px;'>"
            f"{importance.replace('_', ' ').title()}</span>",
            unsafe_allow_html=True,
        )
        if c.get("description"):
            st.caption(c["description"])
        tags = []
        if c.get("applies_to_cv"):
            tags.append("📄 Scored from CV")
        if c.get("applies_to_interview"):
            tags.append("🎤 Probed in interview")
        if tags:
            st.caption(" · ".join(tags))
        if i < len(criteria):
            st.divider()


def render_open_jobs():
    _page_header("Open Jobs", "All job posts that have been published to LinkedIn.")

    limit = st.session_state.get("open_jobs_limit", 10)
    skip = st.session_state.get("open_jobs_skip", 0)
    data = _fetch_list("/job-posts", skip, limit)
    if data is None:
        return

    items = data.get("items", [])
    total = data.get("total", 0)

    st.metric("Total Jobs", total)
    st.write("")

    if not items:
        st.info("No open jobs yet. Create one from **Create New Job Post**.")
        return

    for job in items:
        job_id = job.get("_id", "?")
        jd_text = job.get("job_description", "")
        first_line = jd_text.strip().split("\n", 1)[0][:80] or "(no description)"

        with st.container(border=True):
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(f"**{first_line}**")
                st.caption(f"Job ID: `{_short_id(job_id, 16)}…`")
            with col_b:
                with st.popover("View JD", use_container_width=True):
                    st.code(jd_text, language=None)

            with st.expander("📋 View Evaluation Criteria"):
                _render_job_criteria_table(job_id)

    st.write("")
    _paginator("open_jobs_skip", total, limit)
    _per_page_selector("open_jobs_limit")


# -----------------------------
# PAGE: CANDIDATES (unscored)
# -----------------------------

def render_candidates():
    _page_header("Candidates", "Applicants who haven't been scored yet by the shortlisting agent.")

    limit = st.session_state.get("candidates_limit", 10)
    skip = st.session_state.get("candidates_skip", 0)
    data = _fetch_list("/candidates", skip, limit)
    if data is None:
        return

    items = data.get("items", [])
    total = data.get("total", 0)

    st.metric("Pending Review", total)
    st.write("")

    if not items:
        st.info("No unscored candidates. They'll appear here as applications come in.")
        return

    for c in items:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1.2])
            with col1:
                st.markdown(f"### {c.get('name') or '—'}")
                st.caption(f"{c.get('email') or '—'} · {c.get('phone') or '—'}")
            with col2:
                st.markdown(
                    f"**Experience:** {c.get('experience_years') or '—'} yrs  \n"
                    f"**Degree:** {c.get('last_education_degree') or '—'}"
                )
            with col3:
                if c.get("processing"):
                    st.markdown(
                        "<div style='text-align:right;margin-top:0.5rem;'>"
                        "<span class='processing-badge'>⏳ Processing…</span></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='text-align:right;margin-top:0.5rem;'>"
                        "<span class='pending-badge'>🕓 Pending</span></div>",
                        unsafe_allow_html=True,
                    )
            st.caption(
                f"Job ID: `{_short_id(c.get('jd_id'), 16)}…` · "
                f"CV ID: `{_short_id(c.get('_id'), 8)}…`"
            )
            _render_candidate_detail(c)

    st.write("")
    _paginator("candidates_skip", total, limit)
    _per_page_selector("candidates_limit")


# -----------------------------
# PAGE: SHORTLISTED CANDIDATES
# -----------------------------

def render_shortlisted():
    _page_header("Shortlisted Candidates", "Sorted by fit percent — highest first.")

    limit = st.session_state.get("shortlisted_limit", 10)
    skip = st.session_state.get("shortlisted_skip", 0)
    data = _fetch_list("/shortlisted-candidates", skip, limit)
    if data is None:
        return

    items = data.get("items", [])
    total = data.get("total", 0)

    strong_fit = sum(1 for c in items if (c.get("fit_percent") or 0) >= 80)

    m1, m2 = st.columns(2)
    m1.metric("Total Scored", total)
    m2.metric("Strong Fits (≥ 80%)", f"{strong_fit} on this page")
    st.write("")

    if not items:
        st.info("No shortlisted candidates yet. Wait for the scheduler to run, or trigger it manually.")
        return

    for c in items:
        pct = int(c.get("fit_percent") or 0)
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {c.get('name') or '—'}")
                st.caption(
                    f"Job ID: `{_short_id(c.get('jd_id'), 16)}…` · "
                    f"CV ID: `{_short_id(c.get('_id'), 8)}…`"
                )
            with col2:
                st.markdown(
                    f"<div style='text-align:right;margin-top:0.75rem;'>{_fit_pill(pct)}</div>",
                    unsafe_allow_html=True,
                )
            st.progress(pct / 100.0)
            _render_candidate_detail(c)

    st.write("")
    _paginator("shortlisted_skip", total, limit)
    _per_page_selector("shortlisted_limit")


# -----------------------------
# PAGE: SCREENED CANDIDATES
# -----------------------------

RECOMMENDATION_ICON = {
    "strong_yes": "🌟",
    "yes": "✅",
    "maybe": "🤔",
    "review": "👀",
    "no": "❌",
}


def _fmt_meeting_time(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        from datetime import datetime as _dt
        return _dt.fromisoformat(iso.replace("Z", "+00:00")).strftime("%a, %d %b %Y · %I:%M %p")
    except Exception:
        return iso


def render_screened():
    _page_header("Screened Candidates", "Phone-screened candidates with interview insights and scheduled meetings.")

    f1, f2 = st.columns([2, 3])
    with f1:
        status_choice = st.selectbox("Status", ["All", "completed", "calling"], key="screened_status")
    with f2:
        min_score = st.slider("Min Interview Score", 0, 100, 0, 5, key="screened_min_score")

    limit = st.session_state.get("screened_limit", 10)
    skip = st.session_state.get("screened_skip", 0)
    params = {"skip": skip, "limit": limit}
    if status_choice != "All":
        params["status"] = status_choice
    if min_score > 0:
        params["min_score"] = min_score

    try:
        resp = _sess.get(f"{API_BASE}/screened_candidates", params=params, timeout=30)
    except requests.RequestException as e:
        st.error("Failed to call API."); st.write(str(e)); return
    data = _parse_json_response(resp)
    if data is None:
        return

    items = data.get("items", [])
    total = data.get("total", 0)
    completed = sum(1 for c in items if c.get("status") == "completed")
    with_meeting = sum(1 for c in items if c.get("meeting"))

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Screened", total)
    m2.metric("Completed (this page)", completed)
    m3.metric("Meetings Scheduled (this page)", with_meeting)
    st.write("")

    if not items:
        st.info("No screened candidates match these filters yet.")
        return

    for c in items:
        with st.container(border=True):
            top1, top2 = st.columns([4, 1])
            with top1:
                st.markdown(f"### {c.get('name') or '—'}")
                st.caption(
                    f"📧 {c.get('email') or '—'}  ·  📞 {c.get('phone_e164') or '—'}  ·  "
                    f"Job: `{_short_id(c.get('jd_id'), 12)}…`"
                )
            with top2:
                status = c.get("status", "")
                if status == "calling":
                    st.markdown(
                        '<div style="text-align:right;margin-top:0.5rem;">'
                        '<span style="background:#fef3c7;color:#92400e;padding:4px 12px;border-radius:999px;font-weight:600;font-size:0.85rem;">'
                        '📞 Calling…</span></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div style='text-align:right;margin-top:0.5rem;'>{_fit_pill(int(c.get('interview_score') or 0))}</div>",
                        unsafe_allow_html=True,
                    )

            insights = c.get("insights") or {}
            if insights and not insights.get("extraction_failed"):
                st.markdown("**📋 Interview Insights**")
                ic1, ic2 = st.columns(2)
                with ic1:
                    if insights.get("current_role"):
                        st.write(f"💼 **Role:** {insights['current_role']}")
                    if insights.get("current_company"):
                        st.write(f"🏢 **Company:** {insights['current_company']}")
                    if insights.get("years_experience") is not None:
                        st.write(f"📅 **Experience:** {insights['years_experience']} yrs")
                    if insights.get("tech_stack"):
                        st.write(f"🛠️ **Tech:** {', '.join(insights['tech_stack'][:6])}")
                with ic2:
                    cur_sal = (insights.get("current_salary") or {}).get("raw_text")
                    exp_sal = (insights.get("expected_salary") or {}).get("raw_text")
                    if cur_sal:
                        st.write(f"💰 **Current Salary:** {cur_sal}")
                    if exp_sal:
                        st.write(f"💸 **Expected Salary:** {exp_sal}")
                    if insights.get("notice_period_weeks") is not None:
                        st.write(f"⏰ **Notice:** {insights['notice_period_weeks']} wks")
                    if insights.get("work_mode_preference"):
                        st.write(f"🏠 **Mode:** {insights['work_mode_preference']}")

            tone = c.get("interview_tone")
            red_flags = c.get("red_flags") or []
            recommendation = c.get("recommendation")
            composite = c.get("composite_score")
            if tone or red_flags or recommendation or composite is not None:
                st.markdown("**🎭 Interview Assessment**")
                ac1, ac2 = st.columns(2)
                with ac1:
                    if composite is not None:
                        st.write(f"📊 **Composite Score:** {composite:.1f}")
                    if recommendation:
                        rec_icon = RECOMMENDATION_ICON.get(recommendation, "❔")
                        st.write(f"{rec_icon} **Recommendation:** {recommendation.replace('_', ' ').title()}")
                with ac2:
                    if tone:
                        st.write(f"🎙️ **Tone (live, from voice):** {tone.title()}")
                if red_flags:
                    st.markdown("🚩 **Red Flags:** " + " · ".join(f"`{f}`" for f in red_flags))

            meeting = c.get("meeting") or {}
            if meeting:
                st.markdown("**📅 Scheduled Meeting**")
                st.write(f"🕐 **Time:** {_fmt_meeting_time(meeting.get('meeting_time'))}")
                if meeting.get("meet_link"):
                    st.markdown(f"🔗 **[Join Google Meet]({meeting['meet_link']})**")
                attendees = meeting.get("attendees") or []
                if attendees:
                    st.caption(f"👥 Attendees: {', '.join(attendees)}")
            elif status == "completed" and (c.get("interview_score") or 0) >= 60:
                st.caption("⚠️ Score qualifies but no meeting scheduled.")

            _render_candidate_detail(c)

    st.write("")
    _paginator("screened_skip", total, limit)
    _per_page_selector("screened_limit")


# -----------------------------
# PAGE: CALL LOGS
# -----------------------------

CATEGORY_BADGE = {
    "completed":  ("#dcfce7", "#166534", "✅"),
    "no_show":    ("#e5e7eb", "#374151", "🚫"),
    "incomplete": ("#fee2e2", "#991b1b", "🔄"),
}

STATUS_BADGE = {
    "pending_retry": ("#fef3c7", "#92400e", "⏰ Pending Retry"),
    "retried":       ("#dbeafe", "#1e40af", "🔁 Retried"),
    "exhausted":     ("#fee2e2", "#991b1b", "💀 Exhausted"),
    "closed":        ("#e5e7eb", "#374151", "🔒 Closed"),
}


def _badge_html(text: str, bg: str, fg: str) -> str:
    return (
        f'<span style="background:{bg};color:{fg};padding:4px 12px;'
        f'border-radius:999px;font-weight:600;font-size:0.8rem;">{text}</span>'
    )


def render_call_logs():
    _page_header("Initial Screening Logs", "Every interview attempt — categorized, retry-aware, auditable.")

    stats = _sess.get(f"{API_BASE}/call-stats", timeout=15).json()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", stats.get("total", 0))
    m2.metric("✅ Completed", stats.get("completed", 0))
    m3.metric("🚫 No Show", stats.get("no_show", 0))
    m4.metric("⏰ Pending Retry", stats.get("pending_retry", 0))
    m5.metric("💀 Exhausted", stats.get("exhausted", 0))
    st.write("")

    f1, f2 = st.columns(2)
    with f1:
        cat = st.selectbox("Category", ["All", "completed", "no_show", "incomplete"], key="cl_cat")
    with f2:
        stat = st.selectbox("Status", ["All", "pending_retry", "retried", "exhausted", "closed"], key="cl_stat")

    limit = st.session_state.get("cl_limit", 20)
    skip = st.session_state.get("cl_skip", 0)
    params = {"skip": skip, "limit": limit}
    if cat != "All":
        params["category"] = cat
    if stat != "All":
        params["status"] = stat

    try:
        resp = _sess.get(f"{API_BASE}/call-logs", params=params, timeout=15)
    except requests.RequestException as e:
        st.error(f"API error: {e}")
        return
    data = _parse_json_response(resp)
    if data is None:
        return

    items = data.get("items", [])
    total = data.get("total", 0)
    if not items:
        st.info("No call logs match these filters.")
        return

    for log in items:
        with st.container(border=True):
            top1, top2 = st.columns([4, 1])
            with top1:
                category = log.get("category", "—")
                cat_bg, cat_fg, cat_icon = CATEGORY_BADGE.get(category, ("#e5e7eb", "#374151", "📞"))
                st.markdown(f"### {cat_icon} {category.replace('_', ' ').title()}")
                st.caption(
                    f"Candidate: `{_short_id(log.get('candidate_id'), 12)}…` · "
                    f"Job: `{_short_id(log.get('jd_id'), 12)}…` · "
                    f"Attempt: **{log.get('attempt_number', 1)}/3** · "
                    f"Duration: {log.get('duration_seconds', 0)}s"
                )
                reason = log.get("category_reason") or "—"
                end_reason = log.get("end_reason") or "—"
                st.write(f"**Reason:** `{reason}`  ·  End reason: `{end_reason}`")
                if log.get("interview_score") is not None:
                    st.write(f"**Score:** {log['interview_score']}/100")
                if log.get("next_retry_at"):
                    st.write(f"⏰ **Next retry at:** {log['next_retry_at']}")
            with top2:
                status = log.get("status", "—")
                bg, fg, label = STATUS_BADGE.get(status, ("#e5e7eb", "#374151", status))
                st.markdown(
                    f"<div style='text-align:right;margin-top:0.5rem;'>{_badge_html(label, bg, fg)}</div>",
                    unsafe_allow_html=True,
                )
                st.write("")
                if status in ("pending_retry", "exhausted"):
                    if st.button("📞 Retry Now", key=f"retry_{log['_id']}"):
                        r = _sess.post(f"{API_BASE}/call-logs/{log['_id']}/retry-now", timeout=15)
                        if r.status_code == 200:
                            st.success("Queued for retry")
                            st.rerun()
                        else:
                            st.error(r.text)
                if status != "closed":
                    if st.button("✕ Close", key=f"close_{log['_id']}"):
                        r = _sess.post(f"{API_BASE}/call-logs/{log['_id']}/close", timeout=15)
                        if r.status_code == 200:
                            st.success("Closed")
                            st.rerun()
                        else:
                            st.error(r.text)

            transcript = log.get("transcript") or ""
            with st.expander(f"💬 View Transcript ({len(transcript.splitlines())} lines)" if transcript else "💬 No transcript"):
                if transcript:
                    for line in transcript.splitlines():
                        if line.startswith("Agent:"):
                            st.markdown(f"🤖 **{line}**")
                        elif line.startswith("Candidate:"):
                            st.markdown(f"🎤 {line}")
                        else:
                            st.text(line)
                else:
                    st.caption("This interview has no recorded transcript.")

    st.write("")
    _paginator("cl_skip", total, limit)
    _per_page_selector("cl_limit")


# -----------------------------
# PAGE: TEST CALL
# -----------------------------

def render_test_call():
    _page_header("Demo Interview", "Start a live browser-based AI interview to test the full voice flow.")

    st.info(
        "**How it works:** Click the button below to create a LiveKit interview room. "
        "A link will appear — open it in your browser to join the interview. "
        "The AI agent will greet you and conduct a real technical screen.",
        icon="ℹ️",
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("##### Requirements before starting")
        st.markdown(
            "- `livekit-server --dev` running in a terminal\n"
            "- `python livekit_agent.py dev` running in another terminal\n"
            "- Microphone permission enabled in your browser"
        )
    with col2:
        st.markdown("##### Uses latest job")
        st.markdown("The most recently created job description is auto-selected as the interview context.")

    st.write("")

    if st.button("🎙️ Start Demo Interview", type="primary", use_container_width=True):
        with st.spinner("Creating interview room..."):
            try:
                resp = _sess.post(f"{API_BASE}/test-interview", timeout=30)
            except requests.RequestException as e:
                st.error(f"❌ Network error: {e}")
                return

        if resp.status_code == 200:
            data = resp.json()
            interview_url = data["interview_url"]
            room_name = data["room_name"]
            job_id = data["job_id"]

            st.success("✅ Room created! Click the link below to join.")

            st.markdown(
                f"""
                <a href="{interview_url}" target="_blank"
                   style="display:block;text-align:center;padding:14px 24px;
                          background:#2563eb;color:#fff;border-radius:8px;
                          font-size:1rem;font-weight:600;text-decoration:none;
                          margin:12px 0;">
                    🔗 Open Interview Room
                </a>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("Room details"):
                st.code(
                    f"Room   : {room_name}\n"
                    f"Job ID : {job_id}\n"
                    f"URL    : {interview_url}",
                    language="text",
                )

            st.info(
                "After the interview ends, check the **🎤 Screened** page "
                "for the transcript, score, and insights.",
                icon="📋",
            )
        else:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            st.error(f"❌ Failed (HTTP {resp.status_code}): {detail}")

    st.write("")
    st.caption(
        "This bypasses the scheduler. After the interview the agent POSTs the transcript automatically: "
        "transcript → score → insights extraction → calendar meeting (if score ≥ 60)."
    )


# -----------------------------
# PAGE: CREATE NEW JOB POST
# -----------------------------

_IMPORTANCE_OPTIONS = ["must_have", "very_important", "important", "good_to_have"]
_IMPORTANCE_LABELS = {
    "must_have": "🔴 Must Have",
    "very_important": "🟡 Very Important",
    "important": "🟢 Important",
    "good_to_have": "🔵 Good to Have",
}


def _init_create_job_state():
    st.session_state.setdefault("thread_id", None)
    st.session_state.setdefault("generated_post", None)
    st.session_state.setdefault("status", None)
    st.session_state.setdefault("linkedin_posted", False)
    st.session_state.setdefault("crit_loaded", False)
    st.session_state.setdefault("crit_list", [])
    st.session_state.setdefault("crit_status", None)


def _reset_create_job_state():
    st.session_state.thread_id = None
    st.session_state.generated_post = None
    st.session_state.status = None
    st.session_state.linkedin_posted = False
    st.session_state.crit_loaded = False
    st.session_state.crit_list = []
    st.session_state.crit_status = None
    st.session_state.pop("crit_editor", None)
    st.session_state.pop("crit_linkedin_posted", None)
    st.session_state.pop("crit_linkedin_error", None)
    st.session_state.pop("crit_toast", None)


def _load_or_generate_criteria(jd_id: str) -> bool:
    resp = _sess.get(f"{API_BASE}/jobs/{jd_id}/criteria", timeout=30)
    if resp.status_code == 404:
        with st.spinner("Generating evaluation criteria from JD…"):
            r = _sess.post(f"{API_BASE}/jobs/{jd_id}/criteria/generate", timeout=120)
        if r.status_code != 200:
            st.error(f"Failed to generate criteria (HTTP {r.status_code}): {r.text}")
            return False
        doc = r.json()
    elif resp.status_code == 200:
        doc = resp.json()
    else:
        st.error(f"Failed to fetch criteria (HTTP {resp.status_code})")
        return False
    st.session_state.crit_list = doc.get("criteria", [])
    st.session_state.crit_status = doc.get("status", "draft")
    st.session_state.crit_loaded = True
    return True


def _save_criteria(jd_id: str, edited_df: pd.DataFrame) -> bool:
    criteria = []
    for _, row in edited_df.iterrows():
        name = str(row.get("criteria", "")).strip()
        if not name:
            continue
        criteria.append({
            "id": str(_uuid.uuid4()),
            "criteria": name,
            "description": str(row.get("description", "")),
            "importance": row.get("importance", "important"),
            "applies_to_cv": bool(row.get("cv", True)),
            "applies_to_interview": bool(row.get("interview", True)),
        })
    if not criteria:
        st.warning("Add at least one criterion before saving.")
        return False
    resp = _sess.put(f"{API_BASE}/jobs/{jd_id}/criteria", json={"criteria": criteria}, timeout=30)
    if resp.status_code == 200:
        st.session_state.crit_list = resp.json().get("criteria", criteria)
        return True
    st.error(f"Save failed (HTTP {resp.status_code}): {resp.text}")
    return False


def render_criteria_review(jd_id: str):
    st.write("")
    st.markdown("### Step 2 — Evaluation Criteria")
    st.caption(
        "AI-generated criteria based on your JD. Edit rows directly in the table, "
        "then **Confirm Criteria** to finish — this also publishes the job to LinkedIn."
    )

    if msg := st.session_state.pop("crit_toast", None):
        st.toast(msg)

    if not st.session_state.get("crit_loaded"):
        if not _load_or_generate_criteria(jd_id):
            return

    if st.session_state.get("crit_status") == "confirmed":
        st.success("✅ Evaluation criteria confirmed — job post is fully set up.")
        if st.session_state.get("crit_linkedin_posted"):
            st.info("📢 Job published to LinkedIn.")
        elif st.session_state.get("crit_linkedin_error"):
            st.warning(
                f"⚠️ Criteria confirmed, but LinkedIn publishing failed: "
                f"{st.session_state.crit_linkedin_error}"
            )
        return

    rows = [
        {
            "criteria": c.get("criteria", ""),
            "description": c.get("description", ""),
            "importance": c.get("importance", "important"),
            "cv": c.get("applies_to_cv", True),
            "interview": c.get("applies_to_interview", True),
        }
        for c in st.session_state.crit_list
    ]
    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["criteria", "description", "importance", "cv", "interview"]
    )

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        column_config={
            "criteria": st.column_config.TextColumn("Criterion", required=True, max_chars=200, width="medium"),
            "description": st.column_config.TextColumn("Description", max_chars=1000, width="large"),
            "importance": st.column_config.SelectboxColumn(
                "Importance",
                options=_IMPORTANCE_OPTIONS,
                required=True,
                width="small",
            ),
            "cv": st.column_config.CheckboxColumn("CV?", width="small"),
            "interview": st.column_config.CheckboxColumn("Interview?", width="small"),
        },
        hide_index=True,
        use_container_width=True,
        key="crit_editor",
    )

    st.write("")
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("🔄 Regenerate", use_container_width=True):
            with st.spinner("Regenerating…"):
                r = _sess.post(f"{API_BASE}/jobs/{jd_id}/criteria/generate", timeout=120)
            if r.status_code == 200:
                doc = r.json()
                st.session_state.crit_list = doc.get("criteria", [])
                st.session_state.crit_status = doc.get("status", "draft")
                st.session_state.pop("crit_editor", None)
                st.session_state.crit_toast = "🔄 Criteria regenerated"
                st.rerun()
            else:
                st.error(f"Regenerate failed (HTTP {r.status_code}): {r.text}")
    with c2:
        if st.button("✅ Confirm Criteria", type="primary", use_container_width=True):
            if not _save_criteria(jd_id, edited_df):
                return
            with st.spinner("Confirming criteria and publishing to LinkedIn…"):
                resp = _sess.post(f"{API_BASE}/jobs/{jd_id}/criteria/confirm", timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.crit_status = "confirmed"
                st.session_state.crit_linkedin_posted = bool(data.get("linkedin_posted"))
                st.session_state.crit_linkedin_error = data.get("linkedin_error")
                st.session_state.crit_toast = "✅ Criteria confirmed"
                st.rerun()
            else:
                st.error(f"Confirm failed (HTTP {resp.status_code}): {resp.text}")


def render_create_job_post():
    _init_create_job_state()
    _page_header("Create New Job Post", "Fill in the brief, review the generated draft, and publish to LinkedIn.")

    if st.session_state.generated_post:
        if st.button("+ Start a new job post", type="secondary"):
            _reset_create_job_state()
            st.rerun()

    with st.container(border=True):
        with st.form("job_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Job Title", placeholder="e.g. Senior Backend Engineer")
            with col2:
                experience_level = st.text_input(
                    "Experience Required",
                    placeholder="e.g. 5, Intern, 3+ years, Mid-Level",
                )
            description = st.text_area("Description", placeholder="What does the role do day to day?", height=120)
            requirements = st.text_area("Requirements", placeholder="Skills, years of experience, must-haves…", height=120)

            st.divider()
            st.markdown("**Hiring Team**")
            primary_hr_email = st.text_input(
                "Primary HR Email",
                placeholder="hr@company.com",
                help="Job owner. Meeting slot is picked based on this person's calendar availability.",
            )
            st.caption("Additional team members — invited as attendees to interview meetings")
            team_df = st.data_editor(
                pd.DataFrame(columns=["email", "role"]),
                num_rows="dynamic",
                column_config={
                    "email": st.column_config.TextColumn("Email", required=True),
                    "role": st.column_config.SelectboxColumn(
                        "Role",
                        options=["recruiter", "hiring_manager", "tech_lead", "interviewer"],
                        required=True,
                    ),
                },
                hide_index=True,
                use_container_width=True,
                key="team_editor",
            )

            submitted = st.form_submit_button("Generate Job Post", type="primary", use_container_width=True)

            if submitted:
                if not primary_hr_email.strip():
                    st.error("Primary HR Email is required.")
                    st.stop()
                team_members = [
                    {"email": r["email"].strip(), "role": r["role"]}
                    for _, r in team_df.iterrows()
                    if r.get("email") and str(r["email"]).strip() and r.get("role")
                ]
                payload = {
                    "title": title,
                    "experience_level": experience_level,
                    "description": description,
                    "requirements": requirements,
                    "primary_hr_email": primary_hr_email.strip(),
                    "team_members": team_members,
                }
                try:
                    response = _sess.post(f"{API_BASE}/job-posts", json=payload, timeout=60)
                except requests.RequestException as e:
                    st.error("Failed to call API.")
                    st.write(str(e))
                    st.stop()

                data = _parse_json_response(response)
                if data is None:
                    st.stop()

                st.session_state.thread_id = data.get("thread_id")
                st.session_state.generated_post = data.get("generated_post")
                st.session_state.status = data.get("status")
                st.session_state.linkedin_posted = bool(data.get("linkedin_posted", False))

                if not st.session_state.thread_id:
                    st.error("API response missing thread_id")
                    st.write(data)
                    st.stop()

                st.rerun()

    if st.session_state.generated_post:
        st.write("")
        st.subheader("Generated Draft")
        with st.container(border=True):
            generated_post = st.text_area(
                "Draft",
                value=st.session_state.generated_post,
                height=400,
                key="draft_view",
                label_visibility="collapsed",
            )

            if st.session_state.status == "needs_review":
                st.divider()
                action = st.radio(
                    "Choose Action",
                    ["approve", "edit", "regenerate"],
                    horizontal=True,
                )
                edited_post = None
                feedback = None

                if action == "edit":
                    edited_post = st.text_area("Edit Post", value=generated_post, height=400)
                elif action == "regenerate":
                    feedback = st.text_input("Feedback", placeholder="What should change?")

                if st.button("Submit Review", type="primary"):
                    payload = {"action": action}
                    if action == "edit":
                        payload["edited_post"] = edited_post
                    elif action == "regenerate":
                        payload["feedback"] = feedback

                    try:
                        response = _sess.post(
                            f"{API_BASE}/job-posts/{st.session_state.thread_id}/review",
                            json=payload,
                            timeout=120,
                        )
                    except requests.RequestException as e:
                        st.error("Failed to call API.")
                        st.write(str(e))
                        st.stop()

                    data = _parse_json_response(response)
                    if data is None:
                        st.stop()

                    st.session_state.generated_post = data.get("generated_post")
                    st.session_state.status = data.get("status")
                    st.session_state.linkedin_posted = bool(data.get("linkedin_posted", False))
                    st.rerun()

            elif st.session_state.status == "approved":
                st.success("✅ Job post approved!")

        if st.session_state.status == "approved":
            with st.container(border=True):
                render_criteria_review(st.session_state.thread_id)


# -----------------------------
# SIDEBAR NAV + DISPATCH
# -----------------------------

with st.sidebar:
    st.markdown("# 🎯 Recruitment")
    st.markdown("<p style='color:#64748b;font-size:0.85rem;margin-top:-0.5rem;'>Dashboard</p>", unsafe_allow_html=True)
    st.write("")

    PAGES = {
        "📊 Open Jobs": render_open_jobs,
        "👥 Candidates": render_candidates,
        "⭐ Shortlisted": render_shortlisted,
        "🎤 Screened": render_screened,
        "📋 Initial Screening Logs": render_call_logs,
        "🎙️ Demo Interview": render_test_call,
        "✏️ Create Job Post": render_create_job_post,
    }
    page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")

    st.write("")
    st.divider()
    st.caption(f"API: `{API_BASE}`")

PAGES[page]()