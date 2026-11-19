from sqlalchemy.orm import Session, joinedload

from app.models.resume_match import ResumeMatch
from app.models.job import JobDescription


# ==========================================
# M4 - CANDIDATE RANKING
# ==========================================

def get_ranked_candidates(db: Session, job_id: int):

    # Verify job exists
    job = (
        db.query(JobDescription)
        .filter(JobDescription.id == job_id)
        .first()
    )

    if not job:
        raise ValueError(
            f"Job description with ID {job_id} not found"
        )

    # Fetch saved matching results
    matches = (
        db.query(ResumeMatch)
        .options(joinedload(ResumeMatch.resume))
        .filter(ResumeMatch.job_id == job_id)
        .order_by(ResumeMatch.overall_score.desc())
        .all()
    )

    ranked_candidates = []

    for rank, match in enumerate(matches, start=1):

        resume = match.resume

        # Combine matched required and preferred skills
        required_skills = match.matched_required_skills or []
        preferred_skills = match.matched_preferred_skills or []
        missing_required = match.missing_required_skills or []
        missing_preferred = match.missing_preferred_skills or []

        matched_skills = list(dict.fromkeys(
            required_skills + preferred_skills
        ))
        missing_skills = list(dict.fromkeys(
            missing_required + missing_preferred
        ))

        ranked_candidates.append({

            # Ranking
            "rank": rank,
            "match_id": match.id,
            "resume_id": match.resume_id,

            # Candidate information
            "candidate_name": resume.full_name or resume.original_filename or f"Candidate {match.resume_id}",
            "email": resume.email,
            "phone": resume.phone,

            # Experience
            "experience_years": resume.work_experience,

            # Matching score
            "overall_score": match.overall_score,

            # Skills
            "matched_skills": matched_skills,
            "matched_required_skills": required_skills,
            "matched_preferred_skills": preferred_skills,
            "missing_skills": missing_skills,
            "missing_required_skills": missing_required,
            "missing_preferred_skills": missing_preferred,

            # Component Scores
            "required_skills_score": match.required_skills_score,
            "preferred_skills_score": match.preferred_skills_score,
            "experience_score": match.experience_score,
            "semantic_score": match.semantic_score,
            "education_score": match.education_score,

            # Analysis
            "experience_analysis": match.experience_analysis,
            "education_analysis": match.education_analysis,
            "semantic_analysis": match.semantic_analysis,

            # Candidate profile
            "candidate_information": {
                "full_name": resume.full_name,
                "email": resume.email,
                "phone": resume.phone,
                "technical_skills": resume.technical_skills or [],
                "soft_skills": resume.soft_skills or [],
                "education": resume.education or [],
                "experience_years": resume.work_experience,
                "previous_companies": resume.previous_companies or [],
                "experience_details": resume.experience_details or [],
                "projects": resume.projects or [],
                "certifications": resume.certifications or [],
                "professional_links": resume.professional_links or {}
            },

            # Score explanation
            "score_breakdown": match.score_breakdown,
            "ai_explanation": match.ai_explanation
        })

    return {
        "job_id": job_id,
        "job_title": job.title,
        "total_candidates": len(ranked_candidates),
        "ranked_candidates": ranked_candidates
    }


# ==========================================
# M5 - INDIVIDUAL CANDIDATE ANALYSIS
# ==========================================

def get_candidate_match_details(
    db: Session,
    job_id: int,
    resume_id: int
):

    # Fetch matching result and candidate information
    match = (
        db.query(ResumeMatch)
        .options(joinedload(ResumeMatch.resume))
        .filter(
            ResumeMatch.job_id == job_id,
            ResumeMatch.resume_id == resume_id
        )
        .first()
    )

    if not match:
        raise ValueError(
            f"No matching result found for job {job_id} "
            f"and resume {resume_id}"
        )

    resume = match.resume

    return {

        # ======================================
        # MATCH INFORMATION
        # ======================================

        "match_id": match.id,
        "job_id": match.job_id,
        "resume_id": match.resume_id,

        # ======================================
        # EXTRACTED CANDIDATE INFORMATION
        # ======================================

        "candidate_information": {

            "full_name": resume.full_name,
            "email": resume.email,
            "phone": resume.phone,

            "technical_skills": resume.technical_skills,
            "soft_skills": resume.soft_skills,

            "education": resume.education,

            "experience_years": resume.work_experience,
            "previous_companies": resume.previous_companies,
            "experience_details": resume.experience_details,

            "projects": resume.projects,
            "certifications": resume.certifications,

            "professional_links": resume.professional_links
        },

        # ======================================
        # OVERALL MATCHING SCORE
        # ======================================

        "overall_score": match.overall_score,

        # ======================================
        # SKILL ANALYSIS
        # ======================================

        "skill_analysis": {

            "required_skills_score": match.required_skills_score,
            "preferred_skills_score": match.preferred_skills_score,

            "matched_required_skills": match.matched_required_skills,
            "missing_required_skills": match.missing_required_skills,

            "matched_preferred_skills": match.matched_preferred_skills,
            "missing_preferred_skills": match.missing_preferred_skills
        },

        # ======================================
        # EXPERIENCE COMPARISON
        # ======================================

        "experience_analysis": {

            "score": match.experience_score,
            "candidate_experience_years": resume.work_experience,
            "details": match.experience_analysis
        },

        # ======================================
        # EDUCATION ANALYSIS
        # ======================================

        "education_analysis": {

            "score": match.education_score,
            "candidate_education": resume.education,
            "details": match.education_analysis
        },

        # ======================================
        # SEMANTIC ANALYSIS
        # ======================================

        "semantic_analysis": {

            "score": match.semantic_score,
            "details": match.semantic_analysis
        },

        # ======================================
        # SCORE BREAKDOWN
        # ======================================

        "score_breakdown": match.score_breakdown,

        # ======================================
        # AI-GENERATED EXPLANATION
        # ======================================

        "ai_explanation": match.ai_explanation,

        # ======================================
        # TIMESTAMP
        # ======================================

        "created_at": match.created_at
    }
