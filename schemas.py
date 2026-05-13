from pydantic import BaseModel, Field
from typing import Optional, Any


class JobPost(BaseModel):
    title: str = Field(..., description="The title of the job post")
    experience_level: str = Field(..., description="The experience level required for the job post")
    description: str = Field(..., description="The description of the job post")
    requirements: Optional[str] = Field(None, description="The requirements for the job post")
    # location: Optional[str] = Field(None, description="The location of the job post")
    # salary_range: Optional[str] = Field(None, description="The salary range for the job post")