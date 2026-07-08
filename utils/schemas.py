from enum import Enum
from pydantic import BaseModel, Field, model_validator
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


class RankedListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    skip: int
    limit: int


class RerankRequest(BaseModel):
    cv_weight: Optional[float] = Field(None, ge=0, description="Override CV weight for this run")
    interview_weight: Optional[float] = Field(None, ge=0, description="Override interview weight for this run")

    @model_validator(mode="after")
    def _weights_must_sum_positive(self):
        # When both overrides are given they must sum > 0, else the ranking
        # normalisation divides by zero (was an uncaught 500). Reject at the
        # validation layer -> 422 instead.
        if self.cv_weight is not None and self.interview_weight is not None:
            if self.cv_weight + self.interview_weight <= 0:
                raise ValueError("cv_weight + interview_weight must sum to > 0")
        return self


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


class CriterionImportance(str, Enum):
    must_have      = "must_have"
    very_important = "very_important"
    important      = "important"
    good_to_have   = "good_to_have"


class Criterion(BaseModel):
    id: str
    criteria: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=1000)
    importance: CriterionImportance
    applies_to_cv: bool = True
    applies_to_interview: bool = True


class CriteriaUpdateRequest(BaseModel):
    criteria: List[Criterion]


class CriterionScore(BaseModel):
    criterion_name: str
    score: int = Field(ge=1, le=10, description="1=no evidence, 5=partial/related, 10=strong direct proof")
    evidence: str = Field(description="Specific CV evidence; state what is missing if score < 8")


class CriteriaScoringResult(BaseModel):
    scores: List[CriterionScore] = Field(description="One entry per criterion, same order as provided")


class DocumentProfessionalism(BaseModel):
    attention_to_detail: int = Field(ge=1, le=10, description="Formatting, no typos, date consistency, clean layout")
    attention_evidence: str
    clarity_completion: int = Field(ge=1, le=10, description="All sections present, complete dates, no ambiguous info")
    clarity_evidence: str


class ProfessionalProfile(BaseModel):
    strategic_focus: int = Field(ge=1, le=10, description="Coherent career direction; roles align toward a clear goal")
    strategic_evidence: str
    intellectual_ability: int = Field(ge=1, le=10, description="Complexity handled, publications, advanced problem-solving signals")
    intellectual_evidence: str
    managerial_experience: int = Field(ge=1, le=10, description="Led teams or people; score 1 if no evidence")
    managerial_evidence: str
    recognized_accomplishments: int = Field(ge=1, le=10, description="Awards, certifications, notable mentions, publications")
    accomplishments_evidence: str
    critical_thinking: int = Field(ge=1, le=10, description="Quantified results, problem/solution framing, impact-oriented language")
    critical_thinking_evidence: str


class CVRedFlags(BaseModel):
    timeline_tenure: bool = Field(description="True if gaps > 3 months or avg tenure < 1 yr")
    timeline_evidence: str
    experience_misrepresentation: bool = Field(description="True if claims appear inflated, vague, or inconsistent")
    representation_evidence: str
    unprofessional_email: bool = Field(description="True if email looks unprofessional (random numbers, informal handles)")


class ProfessionalScoringResult(BaseModel):
    document_professionalism: DocumentProfessionalism
    professional_profile: ProfessionalProfile
    red_flags: CVRedFlags


class CandidateEvaluation(BaseModel):
    technical_skill_match: float = Field(
        ge=0.0, le=2.0, multiple_of=0.5,
        description="Steps of 0.5: 0=no match, 0.5=partial, 1.0=core skills only, 1.5=most required, 2.0=all required skills (direct or equivalent)"
    )
    technical_evidence: str = Field(description="List matched skills, then explicitly state which required skills are missing or weak and why the score was not 2.0")

    education_alignment: float = Field(
        ge=0.0, le=1.0, multiple_of=0.5,
        description="Steps of 0.5: 0=unrelated field, 0.5=related field or lower level, 1.0=aligned degree and level (or higher)"
    )
    education_evidence: str = Field(description="Degree and field vs JD requirement")

    project_specificity: float = Field(
        ge=0.0, le=1.0, multiple_of=0.5,
        description="Steps of 0.5: 0=no concrete examples, 0.5=some project examples, 1.0=quantifiable impact demonstrated"
    )
    project_evidence: str = Field(description="Specific project examples cited from CV")

    domain_match: float = Field(
        ge=0.0, le=1.0, multiple_of=0.5,
        description="Steps of 0.5: 0=no domain match, 0.5=adjacent domain, 1.0=direct domain match with JD"
    )
    domain_evidence: str = Field(description="Domain match or mismatch details")

    required_experience_years: float = Field(
        ge=0.0,
        description="Minimum years of experience the JD requires; 0.0 if not stated"
    )


class InterviewEvaluation(BaseModel):
    skill_match: float = Field(
        ge=0.0, le=2.0, multiple_of=0.5,
        description="Steps of 0.5: 0=no JD skills mentioned, 0.5=1-2 skills vaguely, 1.0=core skills named, 1.5=most required with examples, 2.0=all required skills with concrete examples"
    )
    skill_evidence: str = Field(description="Skills mentioned, which required skills were missing or lacked depth, and why score is not 2.0")

    experience_fit: float = Field(
        ge=0.0, le=1.0, multiple_of=0.5,
        description="Steps of 0.5: 0=experience doesn't match JD, 0.5=partial match, 1.0=stated experience clearly aligns with JD requirements"
    )
    experience_evidence: str = Field(description="Stated experience vs JD requirements")

    communication_clarity: float = Field(
        ge=0.0, le=1.0, multiple_of=0.5,
        description="Steps of 0.5: 0=unclear or incoherent, 0.5=acceptable, 1.0=specific, structured, confident answers"
    )

    engagement_motivation: float = Field(
        ge=0.0, le=1.0, multiple_of=0.5,
        description="Steps of 0.5: 0=disengaged or no interest shown, 0.5=neutral, 1.0=clear genuine interest in this specific role"
    )

    red_flags: List[str] = Field(
        default_factory=list,
        description="Genuine warning signs grounded in transcript (e.g. 'evasive about employment gap'). Empty list if none."
    )