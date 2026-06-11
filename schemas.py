from pydantic import BaseModel, Field
from typing import Optional, Any, Literal, List, Dict


class CandidateListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    skip: int
    limit: int


class JobListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    skip: int
    limit: int


class TeamMember(BaseModel):
    email: str = Field(..., description="Email of the team member")
    role: Literal["recruiter", "hiring_manager", "tech_lead", "interviewer"] = Field(
        ..., description="Role of the team member in the hiring process"
    )


class JobPostAgentRequest(BaseModel):
    title: str = Field(..., description="The title of the job post")
    experience_level: str = Field(..., description="The experience level required for the job post")
    description: str = Field(..., description="The description of the job post")
    requirements: Optional[str] = Field(None, description="The requirements for the job post")
    primary_hr_email: str = Field(
        ..., min_length=1,
        description="Primary HR contact (owns the job, gets calendar slot picked on their freebusy)",
    )
    team_members: List[TeamMember] = Field(
        default_factory=list, description="Additional team members invited to interviews"
    )
    # location: Optional[str] = Field(None, description="The location of the job post")
    # salary_range: Optional[str] = Field(None, description="The salary range for the job post")


class HumanFeedback(BaseModel):
    action: Literal["approve", "edit", "regenerate"] = Field(
        ..., description="What to do with the generated job post"
    )
    edited_post: Optional[str] = Field(
        None, description="Full edited post (required when action=edit)"
    )
    feedback: Optional[str] = Field(
        None, description="Short feedback (required when action=regenerate)"
    )


class JobPostAgentResult(BaseModel):
    status: Literal["needs_review", "approved"]
    thread_id: str
    generated_post: str
    linkedin_posted: bool = False
    message: Optional[str] = None