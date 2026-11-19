from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime


# ==========================================
# 1. JOB SKILL SCHEMA
# ==========================================

class JobSkillSchema(BaseModel):

    skill_name: str = Field(..., min_length=1)

    skill_type: Literal["required", "preferred"]


# ==========================================
# 2. JOB CREATE SCHEMA
# ==========================================

class JobCreate(BaseModel):

    original_jd: str = Field(..., min_length=10)

    source_type: Literal["text", "pdf", "docx"]

    title: Optional[str] = None

    min_experience: Optional[int] = Field(None, ge=0)

    max_experience: Optional[int] = Field(None, ge=0)

    # Multiple educational qualifications
    education: Optional[List[str]] = None

    # Multiple responsibilities
    responsibilities: Optional[List[str]] = None

    # Important JD keywords
    keywords: Optional[List[str]] = None

    # Required and preferred skills
    skills: List[JobSkillSchema] = Field(default_factory=list)


# ==========================================
# 3. JOB RESPONSE SCHEMA
# ==========================================

class JobResponse(BaseModel):

    id: int

    original_jd: str

    source_type: str

    title: Optional[str] = None

    min_experience: Optional[int] = None

    max_experience: Optional[int] = None

    education: Optional[List[str]] = None

    responsibilities: Optional[List[str]] = None

    keywords: Optional[List[str]] = None

    skills: List[JobSkillSchema]

    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobPreviewRequest(BaseModel):
    jd_text: str = Field(..., min_length=10)
    source_type: Literal["text", "pdf", "docx"] = "text"
    use_gemini: bool = False