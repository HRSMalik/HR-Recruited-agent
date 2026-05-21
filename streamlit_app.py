import streamlit as st
import requests
from requests import Response


API_BASE = "http://localhost:8000"


st.set_page_config(
    page_title="HR Job Post Generator",
    layout="wide"
)

st.title("HR Job Post Generator")


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


# -----------------------------
# SESSION STATE
# -----------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

if "generated_post" not in st.session_state:
    st.session_state.generated_post = None

if "status" not in st.session_state:
    st.session_state.status = None

if "linkedin_posted" not in st.session_state:
    st.session_state.linkedin_posted = False

if "interrupt" not in st.session_state:
    st.session_state.interrupt = False


# -----------------------------
# CREATE JOB POST FORM
# -----------------------------

with st.form("job_form"):

    title = st.text_input("Job Title")

    experience_level = st.selectbox(
        "Experience Level",
        [
            "Intern",
            "Junior",
            "Mid-level",
            "Senior",
            "Lead"
        ]
    )

    description = st.text_area(
        "Description"
    )

    requirements = st.text_area(
        "Requirements"
    )

    submitted = st.form_submit_button(
        "Generate Job Post"
    )

    if submitted:

        payload = {
            "title": title,
            "experience_level": experience_level,
            "description": description,
            "requirements": requirements
        }

        try:
            response = requests.post(
                f"{API_BASE}/job-posts",
                json=payload,
                timeout=300,
            )
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


# -----------------------------
# REVIEW SECTION
# -----------------------------

if st.session_state.generated_post:

    st.divider()

    st.subheader("Generated Job Post")

    generated_post = st.text_area(
        "Draft",
        value=st.session_state.generated_post,
        height=400
    )

    if st.session_state.status == "needs_review":

        action = st.radio(
            "Choose Action",
            [
                "approve",
                "edit",
                "regenerate"
            ]
        )

        edited_post = None
        feedback = None

        if action == "edit":

            edited_post = st.text_area(
                "Edit Post",
                value=generated_post,
                height=400
            )

        elif action == "regenerate":

            feedback = st.text_input(
                "Feedback"
            )

        if st.button("Submit Review"):

            payload = {
                "action": action
            }

            if action == "edit":
                payload["edited_post"] = edited_post

            elif action == "regenerate":
                payload["feedback"] = feedback

            try:
                response = requests.post(
                    f"{API_BASE}/job-posts/{st.session_state.thread_id}/review",
                    json=payload,
                    timeout=700,
                )
            except requests.RequestException as e:
                st.error("Failed to call API.")
                st.write(str(e))
                st.stop()

            data = _parse_json_response(response)
            if data is None:
                st.stop()

            if "generated_post" not in data or "status" not in data:
                st.error("API response missing required fields")
                st.write(data)
                st.stop()

            st.session_state.generated_post = data.get("generated_post")
            st.session_state.status = data.get("status")
            st.session_state.linkedin_posted = bool(data.get("linkedin_posted", False))

            st.rerun()


# -----------------------------
# FINAL OUTPUT
# -----------------------------

if (
    st.session_state.generated_post
    and not st.session_state.interrupt
):
    if st.session_state.status == "approved":
        if st.session_state.linkedin_posted:
            st.success("Job post approved and posted to LinkedIn!")
        else:
            st.success("Job post approved successfully!")

    st.text_area(
        "Final Job Post",
        value=st.session_state.generated_post,
        height=500
    )