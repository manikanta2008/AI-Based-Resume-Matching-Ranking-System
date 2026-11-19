import time
from typing import Optional, List, Dict, Any
import logging
import concurrent.futures

from sqlalchemy.orm import Session

from app.models.job import JobDescription, JobSkill
from app.models.resume import Resume

from app.services.resume_matching import match_resume_to_job, prepare_matching_data
from app.services.candidate_results import get_ranked_candidates
from app.database.connection import SessionLocal


logger = logging.getLogger(__name__)


def _match_single_resume(
    job_id: int,
    resume_id: int,
    job_data: Optional[dict] = None,
    job_title: Optional[str] = None
) -> dict:
    """Worker function that matches a single resume using its own DB session and precomputed job data."""
    thread_db = SessionLocal()
    try:
        match_resume_to_job(
            db=thread_db,
            job_id=job_id,
            resume_id=resume_id,
            precomputed_job_data=job_data,
            precomputed_job_title=job_title
        )
        return {"resume_id": resume_id, "success": True, "error": None}
    except Exception as error:
        logger.exception("Matching failed for resume ID %s", resume_id)
        return {"resume_id": resume_id, "success": False, "error": str(error)}
    finally:
        thread_db.close()


def match_all_resumes(
    db: Session,
    job_id: int,
    resume_ids: Optional[List[int]] = None
):
    start_time = time.perf_counter()

    # 1. Validate Job Description and fetch associated skills ONCE
    job = db.query(JobDescription).filter(
        JobDescription.id == job_id
    ).first()

    if not job:
        raise ValueError(f"Job description with ID {job_id} not found")

    job_skills = db.query(JobSkill).filter(
        JobSkill.job_id == job_id
    ).all()

    # Precompute job_data once so threads don't re-query the job table 10-20 times
    required_skills = [s.skill_name for s in job_skills if s.skill_type == "required"]
    preferred_skills = [s.skill_name for s in job_skills if s.skill_type == "preferred"]

    precomputed_job_data = {
        "job_title": job.title,
        "minimum_experience": job.min_experience,
        "maximum_experience": job.max_experience,
        "education_requirements": job.education or [],
        "responsibilities": job.responsibilities or [],
        "keywords": job.keywords or [],
        "required_skills": required_skills,
        "preferred_skills": preferred_skills
    }
    job_title = job.title

    # 2. Validate or Resolve Resume IDs
    if not resume_ids:
        all_resumes = db.query(Resume.id).order_by(Resume.id.asc()).all()
        resume_ids = [row[0] for row in all_resumes]

    if not resume_ids:
        raise ValueError("No candidate resumes found in database to match.")

    if len(resume_ids) != len(set(resume_ids)):
        raise ValueError("Duplicate resume IDs are not allowed")

    existing_resumes = db.query(Resume.id).filter(
        Resume.id.in_(resume_ids)
    ).all()

    existing_resume_ids = {row[0] for row in existing_resumes}

    missing_ids = [
        resume_id
        for resume_id in resume_ids
        if resume_id not in existing_resume_ids
    ]

    if missing_ids:
        raise ValueError(f"Resume IDs not found: {missing_ids}")

    # 3. Match Resumes Concurrently (up to 6 workers)
    successful_count = 0
    errors = []
    max_workers = min(6, max(1, len(resume_ids)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_resume = {
            executor.submit(_match_single_resume, job_id, resume_id, precomputed_job_data, job_title): resume_id
            for resume_id in resume_ids
        }

        for future in concurrent.futures.as_completed(future_to_resume):
            result = future.result()
            if result["success"]:
                successful_count += 1
            else:
                errors.append({
                    "resume_id": result["resume_id"],
                    "error": result["error"]
                })

    # 4. Fetch the enriched rankings from candidate_results
    ranking_data = get_ranked_candidates(db=db, job_id=job_id)

    # Filter to only the requested resume_ids if specified
    ranked_candidates = [
        c for c in ranking_data["ranked_candidates"]
        if c["resume_id"] in resume_ids
    ]

    # Re-rank strictly
    for rank, candidate in enumerate(ranked_candidates, start=1):
        candidate["rank"] = rank

    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"Batch matching completed for Job #{job_id} ({len(resume_ids)} resumes) in {duration_ms:.1f}ms. "
        f"Successful: {successful_count}, Failed: {len(errors)}"
    )

    # 5. Return Results
    return {
        "job_id": job_id,
        "job_title": job.title,
        "total_resumes": len(resume_ids),
        "successful": successful_count,
        "failed": len(errors),
        "ranked_candidates": ranked_candidates,
        "errors": errors if errors else None
    }
