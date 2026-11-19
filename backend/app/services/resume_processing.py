import time
import hashlib
import logging
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.services.resume_text_extraction import extract_resume_content
from app.services.resume_information_extraction import extract_resume_information

logger = logging.getLogger(__name__)


# ==========================================
# PROCESS AND SAVE RESUME (WITH DUPLICATE DETECTION)
# ==========================================

def process_and_save_resume(
    file_bytes: bytes,
    filename: str,
    db: Session
):
    """
    Parses a single resume file and stores candidate profile in PostgreSQL.
    Includes SHA-256 hash-based and email-based duplicate detection.
    """
    start_time = time.perf_counter()

    # 1. Validate file format
    filename_lower = filename.lower()
    if not filename_lower.endswith((".pdf", ".docx")):
        raise ValueError("Only PDF and DOCX files are supported.")

    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    # 2. Compute SHA-256 hash of the file for exact duplicate detection
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # 3. Check for exact duplicate by file hash (fastest - no extraction needed)
    existing_resume = db.query(Resume).filter(
        Resume.file_hash == file_hash
    ).first()

    if existing_resume:
        existing_resume._is_duplicate = True
        existing_resume._duplicate_reason = "exact_file"
        total_duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Exact duplicate file detected for [{filename}] (hash match). "
            f"Returning existing Resume #{existing_resume.id} in {total_duration_ms:.1f}ms."
        )
        return existing_resume

    # 4. Extract resume text & professional hyperlinks in a SINGLE PASS
    io_start = time.perf_counter()
    resume_text, professional_links = extract_resume_content(file_bytes, filename)
    io_duration_ms = (time.perf_counter() - io_start) * 1000

    # 5. Extract structured candidate information
    ai_start = time.perf_counter()
    extracted_data = extract_resume_information(resume_text, professional_links)
    ai_duration_ms = (time.perf_counter() - ai_start) * 1000

    # 6. Check for duplicate by email (same candidate, possibly updated resume)
    file_extension = filename_lower.rsplit(".", 1)[-1]
    candidate_email = extracted_data.get("email")
    candidate_name = extracted_data.get("full_name")

    existing_resume = None
    if candidate_email and candidate_email.strip():
        existing_resume = db.query(Resume).filter(
            Resume.email == candidate_email.strip()
        ).first()

    # 7. Check for duplicate by filename + candidate name
    if not existing_resume and filename and candidate_name:
        existing_resume = db.query(Resume).filter(
            Resume.original_filename == filename,
            Resume.full_name == candidate_name
        ).first()

    if existing_resume:
        # Update existing candidate record with latest extracted data
        try:
            existing_resume.original_filename = filename
            existing_resume.file_type = file_extension
            existing_resume.file_hash = file_hash
            if candidate_name:
                existing_resume.full_name = candidate_name
            if candidate_email:
                existing_resume.email = candidate_email
            if extracted_data.get("phone"):
                existing_resume.phone = extracted_data.get("phone")
            if extracted_data.get("technical_skills"):
                existing_resume.technical_skills = extracted_data.get("technical_skills")
            if extracted_data.get("soft_skills"):
                existing_resume.soft_skills = extracted_data.get("soft_skills")
            if extracted_data.get("education"):
                existing_resume.education = extracted_data.get("education")
            if extracted_data.get("work_experience") is not None:
                existing_resume.work_experience = extracted_data.get("work_experience")
            if extracted_data.get("previous_companies"):
                existing_resume.previous_companies = extracted_data.get("previous_companies")
            if extracted_data.get("experience_details"):
                existing_resume.experience_details = extracted_data.get("experience_details")
            if extracted_data.get("projects"):
                existing_resume.projects = extracted_data.get("projects")
            if extracted_data.get("certifications"):
                existing_resume.certifications = extracted_data.get("certifications")
            if extracted_data.get("professional_links"):
                existing_resume.professional_links = extracted_data.get("professional_links")
            existing_resume.raw_text = resume_text

            db.commit()
            db.refresh(existing_resume)

            existing_resume._is_duplicate = True
            existing_resume._duplicate_reason = "email_match" if candidate_email else "name_match"

            total_duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Duplicate resume detected for [{filename} / {candidate_email}]. "
                f"Updated existing Resume #{existing_resume.id} in {total_duration_ms:.1f}ms."
            )
            return existing_resume
        except Exception as error:
            db.rollback()
            raise RuntimeError(f"Failed to update duplicate resume: {str(error)}") from error

    # 8. Create new Resume record if not duplicate
    new_resume = Resume(
        original_filename=filename,
        file_type=file_extension,
        file_path=None,
        file_hash=file_hash,
        full_name=extracted_data.get("full_name"),
        email=extracted_data.get("email"),
        phone=extracted_data.get("phone"),
        technical_skills=extracted_data.get("technical_skills"),
        soft_skills=extracted_data.get("soft_skills"),
        education=extracted_data.get("education"),
        work_experience=extracted_data.get("work_experience"),
        previous_companies=extracted_data.get("previous_companies"),
        experience_details=extracted_data.get("experience_details"),
        projects=extracted_data.get("projects"),
        certifications=extracted_data.get("certifications"),
        professional_links=extracted_data.get("professional_links"),
        raw_text=resume_text
    )

    try:
        db.add(new_resume)
        db.commit()
        db.refresh(new_resume)

        new_resume._is_duplicate = False
        new_resume._duplicate_reason = None

        total_duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Resume [{filename}] processed in {total_duration_ms:.1f}ms "
            f"(Document parse: {io_duration_ms:.1f}ms, Extraction: {ai_duration_ms:.1f}ms)"
        )

        return new_resume

    except Exception as error:
        db.rollback()
        raise RuntimeError(f"Failed to save resume: {str(error)}") from error
