from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==========================================
# RESUME RESPONSE SCHEMA
# ==========================================

class ResumeResponse(BaseModel):

    id: int

    # RESUME FILE INFORMATION
    original_filename: str
    file_type: str

    # CANDIDATE PERSONAL INFORMATION
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # SKILLS
    technical_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None

    # EDUCATION
    education: Optional[List[Dict[str, Any]]] = None

    # EXPERIENCE
    work_experience: Optional[float] = None
    previous_companies: Optional[List[str]] = None
    experience_details: Optional[List[Dict[str, Any]]] = None

    # PROJECTS
    projects: Optional[List[Dict[str, Any]]] = None

    # CERTIFICATIONS
    certifications: Optional[List[str]] = None

    # PROFESSIONAL LINKS
    professional_links: Optional[Dict[str, Optional[str]]] = None

    # TIMESTAMP
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# RESUME UPLOAD RESPONSE SCHEMA
# ==========================================

class ResumeUploadResponse(BaseModel):

    total_uploaded: int

    successful: int

    failed: int

    duplicates_detected: int = 0

    resumes: List[ResumeResponse]

    errors: Optional[List[Dict[str, str]]] = None

    duplicates: Optional[List[Dict[str, Any]]] = None

# ==========================================
# BATCH RESUME MATCHING SCHEMAS (M4)
# ==========================================

class BatchMatchRequest(BaseModel):

    job_id: int

    resume_ids: Optional[List[int]] = None


class BatchMatchResponse(BaseModel):

    job_id: int

    total_resumes: int

    successful: int

    failed: int

    ranked_candidates: List[Dict[str, Any]]

    errors: Optional[List[Dict[str, Any]]] = None
