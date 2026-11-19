from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.models.job import JobDescription, JobSkill
from app.schemas.job_schema import (
    JobCreate,
    JobResponse,
    JobPreviewRequest
)
from app.services.job_processing import process_job_description
from app.services.resume_text_extraction import extract_resume_text


router = APIRouter(
    prefix="/jobs",
    tags=["Job Description"]
)


# -----------------------------------------
# 1. Process Job Description from Text (Preview)
# -----------------------------------------

@router.post("/preview")
def preview_job(request: JobPreviewRequest):

    try:
        result = process_job_description(
            jd_text=request.jd_text,
            source_type=request.source_type,
            use_gemini=request.use_gemini
        )

        return {
            "message": "Job description processed successfully.",
            "data": result.model_dump()
        }

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )

    except Exception as error:
        print("JOB PREVIEW ERROR:", repr(error))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job description processing failed."
        )


# -----------------------------------------
# 2. Process Job Description from File (Upload)
# -----------------------------------------

@router.post("/upload-file")
async def upload_job_file(
    file: UploadFile = File(description="Upload Job Description in PDF or DOCX format"),
    use_gemini: bool = Form(True)
):
    filename = file.filename or "job_description"
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext not in ["pdf", "docx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a PDF or DOCX file."
        )

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        extracted_text = extract_resume_text(file_bytes, filename)

        result = process_job_description(
            jd_text=extracted_text,
            source_type=ext if ext in ["pdf", "docx"] else "text",
            use_gemini=use_gemini
        )

        return {
            "message": "Job description file uploaded and processed successfully.",
            "filename": filename,
            "source_type": ext,
            "extracted_text": extracted_text,
            "data": result.model_dump()
        }

    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )
    except Exception as error:
        print("JOB FILE UPLOAD ERROR:", repr(error))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract and process Job Description file."
        )
    finally:
        await file.close()


# -----------------------------------------
# 3. Confirm and Save Job Description
#    (with duplicate detection)
# -----------------------------------------

@router.post(
    "/confirm",
    status_code=status.HTTP_201_CREATED
)
def confirm_job(
    job_data: JobCreate,
    db: Session = Depends(get_db)
):

    try:
        # Separate job details and skills
        job_details = job_data.model_dump(
            exclude={"skills"}
        )

        # -----------------------------------------
        # Duplicate Detection (normalized comparison)
        # -----------------------------------------
        cleaned_incoming = " ".join(job_data.original_jd.strip().split()).lower()
        normalized_title = (job_data.title or "").strip().lower()

        existing_jobs = db.query(JobDescription).options(
            joinedload(JobDescription.skills)
        ).all()

        duplicate_job = None
        for ej in existing_jobs:
            existing_title = (ej.title or "").strip().lower()
            cleaned_existing = " ".join((ej.original_jd or "").strip().split()).lower()

            # Check 1: Exact content match after normalization
            if cleaned_incoming == cleaned_existing:
                duplicate_job = ej
                break

            # Check 2: Same title + same experience range + similar content prefix
            if (
                normalized_title
                and normalized_title == existing_title
                and ej.min_experience == job_data.min_experience
                and ej.max_experience == job_data.max_experience
                and len(cleaned_incoming) > 20
                and cleaned_incoming[:200] == cleaned_existing[:200]
            ):
                duplicate_job = ej
                break

        if duplicate_job:
            # Update existing record instead of creating duplicate
            for key, val in job_details.items():
                setattr(duplicate_job, key, val)

            # Update skills safely
            duplicate_job.skills.clear()
            for skill in job_data.skills:
                duplicate_job.skills.append(
                    JobSkill(
                        skill_name=skill.skill_name,
                        skill_type=skill.skill_type
                    )
                )

            db.commit()
            db.refresh(duplicate_job)

            # Return with duplicate flag so frontend can show appropriate message
            response_data = JobResponse.model_validate(duplicate_job).model_dump(mode="json")
            response_data["duplicate_detected"] = True
            response_data["message"] = (
                f"This job description already exists (Job #{duplicate_job.id}). "
                f"Updated the existing record."
            )
            return JSONResponse(
                status_code=200,
                content=jsonable_encoder(response_data)
            )

        # Create new job record if no duplicate found
        new_job = JobDescription(**job_details)

        # Add associated skills
        for skill in job_data.skills:
            new_skill = JobSkill(
                skill_name=skill.skill_name,
                skill_type=skill.skill_type
            )
            new_job.skills.append(new_skill)

        # Save to PostgreSQL
        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        return new_job

    except Exception as error:
        db.rollback()
        print("\n========== JOB SAVE ERROR ==========")
        print(repr(error))
        print("====================================\n")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save job description. Check backend terminal."
        )


# -----------------------------------------
# 4. List All Saved Job Descriptions
# -----------------------------------------

@router.get("", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    jobs = (
        db.query(JobDescription)
        .options(joinedload(JobDescription.skills))
        .order_by(JobDescription.created_at.desc())
        .all()
    )
    return jobs


# -----------------------------------------
# 5. Get Single Job Description by ID
# -----------------------------------------

@router.get("/{job_id}", response_model=JobResponse)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)):
    job = (
        db.query(JobDescription)
        .options(joinedload(JobDescription.skills))
        .filter(JobDescription.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description with ID {job_id} not found."
        )

    return job


# -----------------------------------------
# 6. Delete Job Description by ID
# -----------------------------------------

@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = (
        db.query(JobDescription)
        .filter(JobDescription.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description with ID {job_id} not found."
        )

    try:
        db.delete(job)
        db.commit()
        return {"message": f"Job description {job_id} deleted successfully."}
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(error)}"
        )
