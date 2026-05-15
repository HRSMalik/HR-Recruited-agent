import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Header, File, UploadFile, status, Form, Query, Depends
from fastapi.responses import Response, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from schemas import JobPostAgentRequest, HumanFeedback, JobPostAgentResult
import uuid

from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from job_post import create_workflow_agent




app = FastAPI(title="Recruitment Module API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compile once per process so InMemorySaver can keep thread state.
job_post_agent = create_workflow_agent()



@app.post(
    "/job-posts",
    tags=["Job Posts"],
    status_code=status.HTTP_201_CREATED,
    response_model=JobPostAgentResult,
)
async def create_job_post(job_post: JobPostAgentRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "form_data": job_post.model_dump(),
        "generated_post": None,
        "human_feedback": None,
        "approved": False,
        "linkedin_posted": False,
    }

    try:
        response = job_post_agent.invoke(initial_state, config=config)
    except GraphInterrupt as e:
        interrupts = e.args[0] if e.args else []
        interrupt_value = interrupts[0].value if interrupts else {}
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "needs_review",
                "thread_id": thread_id,
                "generated_post": interrupt_value.get("generated_post", ""),
                "linkedin_posted": False,
                "message": interrupt_value.get("message"),
            },
        )

    # Fallback for LangGraph versions that surface interrupts in the response.
    if isinstance(response, dict) and "__interrupt__" in response:
        interrupts = response["__interrupt__"]
        interrupt_value = interrupts[0].value if interrupts else {}
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "needs_review",
                "thread_id": thread_id,
                "generated_post": interrupt_value.get("generated_post", ""),
                "linkedin_posted": False,
                "message": interrupt_value.get("message"),
            },
        )

    return {
        "status": "approved",
        "thread_id": thread_id,
        "generated_post": response.get("generated_post", "") if isinstance(response, dict) else "",
        "linkedin_posted": response.get("linkedin_posted", False) if isinstance(response, dict) else False,
        "message": None,
    }


@app.post(
    "/job-posts/{thread_id}/review",
    tags=["Job Posts"],
    response_model=JobPostAgentResult,
)
async def review_job_post(thread_id: str, human_feedback: HumanFeedback):
    config = {"configurable": {"thread_id": thread_id}}

    feedback_payload = human_feedback.model_dump(exclude_none=True)
    if feedback_payload.get("action") == "edit" and not feedback_payload.get("edited_post"):
        raise HTTPException(status_code=400, detail="edited_post is required when action=edit")
    if feedback_payload.get("action") == "regenerate" and not feedback_payload.get("feedback"):
        raise HTTPException(status_code=400, detail="feedback is required when action=regenerate")

    try:
        response = job_post_agent.invoke(Command(resume=feedback_payload), config=config)
    except GraphInterrupt as e:
        interrupts = e.args[0] if e.args else []
        interrupt_value = interrupts[0].value if interrupts else {}
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "needs_review",
                "thread_id": thread_id,
                "generated_post": interrupt_value.get("generated_post", ""),
                "linkedin_posted": False,
                "message": interrupt_value.get("message"),
            },
        )
    except ValueError as e:
        # Typically means the thread does not exist in the checkpointer yet.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown or expired thread_id (missing state key: {e}). Create a new thread via POST /job-posts.",
        )

    if isinstance(response, dict) and "__interrupt__" in response:
        interrupts = response["__interrupt__"]
        interrupt_value = interrupts[0].value if interrupts else {}
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "needs_review",
                "thread_id": thread_id,
                "generated_post": interrupt_value.get("generated_post", ""),
                "linkedin_posted": False,
                "message": interrupt_value.get("message"),
            },
        )

    return {
        "status": "approved",
        "thread_id": thread_id,
        "generated_post": response.get("generated_post", "") if isinstance(response, dict) else "",
        "linkedin_posted": response.get("linkedin_posted", False) if isinstance(response, dict) else False,
        "message": None,
    }





@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}