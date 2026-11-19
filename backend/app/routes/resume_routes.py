import time
import logging
import concurrent.futures
from typing import List, Annotated, Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException,
    status
)
from sqlalchemy.orm import Session

from app.database.connection import get_db, SessionLocal
from app.models.resume import Resume
from app.schemas.resume_schema import (
    ResumeResponse,
    ResumeUploadResponse,
    BatchMatchRequest,
    BatchMatchResponse
)
from app.services.resume_processing import (
    process_and_save_resume
)
from app.services.resume_matching import match_resume_to_job
from app.services.candidate_results import (
    get_ranked_candidates,
    get_candidate_match_details
)
from app.services.batch_matching import match_all_resumes

logger = logging.getLogger(__name__)


# ==========================================
# RESUME ROUTER
# ==========================================

router = APIRouter(
    prefix="/resumes",
    tags=["Resume Management"]
)


# ==========================================
# LIST ALL RESUMES
# ==========================================

@router.get("", response_model=List[ResumeResponse])
def list_resumes(db: Session = Depends(get_db)):
    resumes = db.query(Resume).order_by(Resume.created_at.desc()).all()
    return resumes


# ==========================================
# GET SINGLE RESUME BY ID
# ==========================================

@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID {resume_id} not found."
        )
    return resume


# ==========================================
# DELETE RESUME BY ID
# ==========================================

@router.delete("/{resume_id}", status_code=status.HTTP_200_OK)
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID {resume_id} not found."
        )
    try:
        db.delete(resume)
        db.commit()
        return {"message": f"Resume {resume_id} deleted successfully."}
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resume: {str(error)}"
        )


# ==========================================
# MULTIPLE RESUME UPLOAD (BATCH >= 10)
# ==========================================

@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_resumes(
    files: Annotated[
        List[UploadFile],
        File(description="Upload multiple PDF or DOCX resumes (supports 10+ files)")
    ],
    db: Session = Depends(get_db)
):
    start_time = time.perf_counter()
    total_files = len(files)
    if total_files == 0:
        return ResumeUploadResponse(
            total_uploaded=0,
            successful=0,
            failed=0,
            duplicates_detected=0,
            resumes=[],
            errors=None,
            duplicates=None
        )

    # 1. Read all file bytes in memory (async, very fast)
    file_items = []
    for file in files:
        try:
            content = await file.read()
            file_items.append((content, file.filename or "unknown"))
        finally:
            await file.close()

    # 2. Worker for concurrent extraction and DB save
    def _process_single(item):
        content, fname = item
        thread_db = SessionLocal()
        try:
            saved_resume = process_and_save_resume(
                file_bytes=content,
                filename=fname,
                db=thread_db
            )
            res_data = ResumeResponse.model_validate(saved_resume)
            is_dup = getattr(saved_resume, '_is_duplicate', False)
            dup_reason = getattr(saved_resume, '_duplicate_reason', None)
            return {
                "success": True,
                "resume": res_data,
                "filename": fname,
                "error": None,
                "is_duplicate": is_dup,
                "duplicate_reason": dup_reason
            }
        except Exception as err:
            return {
                "success": False,
                "resume": None,
                "filename": fname,
                "error": str(err),
                "is_duplicate": False,
                "duplicate_reason": None
            }
        finally:
            thread_db.close()

    # 3. Process concurrently with ThreadPoolExecutor (up to 8 parallel workers)
    workers = min(8, max(1, len(file_items)))
    successful_resumes = []
    errors = []
    duplicates = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_process_single, file_items))

    for r in results:
        if r["success"]:
            successful_resumes.append(r["resume"])
            if r["is_duplicate"]:
                duplicates.append({
                    "filename": r["filename"],
                    "reason": r["duplicate_reason"],
                    "resume_id": r["resume"].id if r["resume"] else None
                })
        else:
            errors.append({
                "filename": r["filename"],
                "error": r["error"]
            })

    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"Batch resume upload completed: {len(successful_resumes)}/{total_files} succeeded "
        f"({len(duplicates)} duplicates) in {duration_ms:.1f}ms"
    )

    return ResumeUploadResponse(
        total_uploaded=total_files,
        successful=len(successful_resumes),
        failed=len(errors),
        duplicates_detected=len(duplicates),
        resumes=successful_resumes,
        errors=errors if errors else None,
        duplicates=duplicates if duplicates else None
    )

# ==========================================
# RESUME MATCHING
# ==========================================

@router.post("/match")
def match_resume(
    job_id: int,
    resume_id: int,
    db: Session = Depends(get_db)
):

    try:

        result = match_resume_to_job(
            db=db,
            job_id=job_id,
            resume_id=resume_id
        )

        return result

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except RuntimeError as error:

        raise HTTPException(
            status_code=502,
            detail=str(error)
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Resume matching failed. Check backend terminal."
        )

@router.post(
    "/match-batch",
    response_model=BatchMatchResponse
)
def match_batch_resumes(
    request: BatchMatchRequest,
    db: Session = Depends(get_db)
):
    try:
        result = match_all_resumes(
            db=db,
            job_id=request.job_id,
            resume_ids=request.resume_ids
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Batch resume matching failed. Check backend terminal."
        )

# ==========================================
# M5 - RETRIEVE RANKED CANDIDATES
# ==========================================

@router.get("/rankings/{job_id}")
def get_candidate_rankings(
    job_id: int,
    db: Session = Depends(get_db)
):

    try:
        return get_ranked_candidates(
            db=db,
            job_id=job_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve candidate rankings."
        )

# ==========================================
# M5 - INDIVIDUAL CANDIDATE ANALYSIS
# ==========================================

@router.get("/match-details/{job_id}/{resume_id}")
def get_candidate_details(
    job_id: int,
    resume_id: int,
    db: Session = Depends(get_db)
):

    try:
        return get_candidate_match_details(
            db=db,
            job_id=job_id,
            resume_id=resume_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve candidate analysis."
        )
