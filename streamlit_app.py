import streamlit as st
import requests
from requests import Response


API_BASE = "http://localhost:8000"


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
        resp = requests.get(
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


# -----------------------------
# PAGE: OPEN JOBS
# -----------------------------

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
            col1, col2 = st.columns([3, 2])
            with col1:
                st.markdown(f"### {c.get('name') or '—'}")
                st.caption(f"{c.get('email') or '—'} · {c.get('phone') or '—'}")
            with col2:
                st.markdown(
                    f"**Experience:** {c.get('experience_years') or '—'} yrs  \n"
                    f"**Degree:** {c.get('last_education_degree') or '—'}"
                )
            st.caption(
                f"Job ID: `{_short_id(c.get('jd_id'), 16)}…` · "
                f"CV ID: `{_short_id(c.get('_id'), 8)}…`"
            )

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

    st.write("")
    _paginator("shortlisted_skip", total, limit)
    _per_page_selector("shortlisted_limit")


# -----------------------------
# PAGE: CREATE NEW JOB POST
# -----------------------------

def _init_create_job_state():
    st.session_state.setdefault("thread_id", None)
    st.session_state.setdefault("generated_post", None)
    st.session_state.setdefault("status", None)
    st.session_state.setdefault("linkedin_posted", False)


def _reset_create_job_state():
    st.session_state.thread_id = None
    st.session_state.generated_post = None
    st.session_state.status = None
    st.session_state.linkedin_posted = False


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
                experience_level = st.selectbox(
                    "Experience Level",
                    ["Intern", "Junior", "Mid-level", "Senior", "Lead"],
                )
            description = st.text_area("Description", placeholder="What does the role do day to day?", height=120)
            requirements = st.text_area("Requirements", placeholder="Skills, years of experience, must-haves…", height=120)
            submitted = st.form_submit_button("Generate Job Post", type="primary", use_container_width=True)

            if submitted:
                payload = {
                    "title": title,
                    "experience_level": experience_level,
                    "description": description,
                    "requirements": requirements,
                }
                try:
                    response = requests.post(f"{API_BASE}/job-posts", json=payload, timeout=60)
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
                        response = requests.post(
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
                if st.session_state.linkedin_posted:
                    st.success("Job post approved and posted to LinkedIn!")
                else:
                    st.success("Job post approved successfully!")


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
        "✏️ Create Job Post": render_create_job_post,
    }
    page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")

    st.write("")
    st.divider()
    st.caption(f"API: `{API_BASE}`")

PAGES[page]()