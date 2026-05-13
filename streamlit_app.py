import streamlit as st
import requests


API_BASE = "http://localhost:8000"


st.set_page_config(
    page_title="HR Job Post Generator",
    layout="wide"
)

st.title("HR Job Post Generator")


# -----------------------------
# SESSION STATE
# -----------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

if "generated_post" not in st.session_state:
    st.session_state.generated_post = None

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

        response = requests.post(
            f"{API_BASE}/job-posts",
            json=payload
        )

        data = response.json()

        st.session_state.thread_id = data["thread_id"]
        st.session_state.generated_post = data["generated_post"]
        st.session_state.status = data["status"]


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

            response = requests.post(
                f"{API_BASE}/job-posts/{st.session_state.thread_id}/review",
                json=payload
            )

            data = response.json()

            st.session_state.generated_post = (
                data["generated_post"]
            )

            st.session_state.status = (
                data["status"]
            )

            st.rerun()


# -----------------------------
# FINAL OUTPUT
# -----------------------------

if (
    st.session_state.generated_post
    and not st.session_state.interrupt
):

    st.success("Job post approved successfully!")

    st.text_area(
        "Final Job Post",
        value=st.session_state.generated_post,
        height=500
    )