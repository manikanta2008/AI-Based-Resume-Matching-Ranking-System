import hashlib
import time
import logging
from typing import Literal, Dict

from pydantic import ValidationError

from app.schemas.job_schema import JobCreate
from app.services.job_nlp_extraction import extract_job_details
from app.services.job_gemini_extraction import extract_job_details_with_gemini

logger = logging.getLogger(__name__)

# ==========================================
# IN-MEMORY LRU CACHE FOR JOB EXTRACTIONS
# ==========================================
_MAX_CACHE_SIZE = 128
_jd_cache: Dict[str, dict] = {}


def _get_cache_key(jd_text: str, use_gemini: bool) -> str:
    cleaned = " ".join(jd_text.strip().split())
    return hashlib.sha256(f"{cleaned}_{use_gemini}".encode("utf-8")).hexdigest()


# ==========================================
# MERGE NLP AND GEMINI RESULTS
# ==========================================

def merge_extraction_results(
    gemini_data: dict,
    nlp_data: dict
):
    final_data = gemini_data.copy()

    # Fill missing scalar fields using NLP
    scalar_fields = ["title", "min_experience", "max_experience"]
    for field in scalar_fields:
        if final_data.get(field) is None:
            final_data[field] = nlp_data.get(field)

    # Merge list fields
    list_fields = ["education", "responsibilities", "keywords"]
    for field in list_fields:
        gemini_items = final_data.get(field) or []
        nlp_items = nlp_data.get(field) or []
        combined = []
        seen = set()

        for item in gemini_items + nlp_items:
            normalized = item.strip().lower()
            if normalized and normalized not in seen:
                combined.append(item)
                seen.add(normalized)

        final_data[field] = combined

    # Merge skills (Gemini classifications have priority)
    gemini_skills = final_data.get("skills") or []
    nlp_skills = nlp_data.get("skills") or []

    skill_map = {}
    for skill in gemini_skills:
        skill_name = skill["skill_name"].strip()
        skill_map[skill_name.lower()] = {
            "skill_name": skill_name,
            "skill_type": skill["skill_type"]
        }

    for skill in nlp_skills:
        skill_name = skill["skill_name"].strip()
        key = skill_name.lower()
        if key not in skill_map:
            skill_map[key] = skill

    final_data["skills"] = list(skill_map.values())
    return final_data


# ==========================================
# MAIN JOB PROCESSING FUNCTION (WITH CACHING & TIMING)
# ==========================================

def process_job_description(
    jd_text: str,
    source_type: Literal["text", "pdf", "docx"] = "text",
    use_gemini: bool = True
) -> JobCreate:
    """
    Process a Job Description with caching and performance monitoring.
    """
    start_time = time.perf_counter()

    if not jd_text or not jd_text.strip():
        raise ValueError("Job description cannot be empty.")

    cache_key = _get_cache_key(jd_text, use_gemini)
    if cache_key in _jd_cache:
        cached_data = _jd_cache[cache_key].copy()
        cached_data["source_type"] = source_type
        cached_data["original_jd"] = jd_text
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"JD extraction cache HIT! Completed in {duration_ms:.2f}ms")
        return JobCreate.model_validate(cached_data)

    # 1. NLP Extraction (fast rule-based)
    nlp_start = time.perf_counter()
    nlp_data = extract_job_details(jd_text)
    nlp_duration_ms = (time.perf_counter() - nlp_start) * 1000
    extracted_data = nlp_data

    # 2. Gemini AI Extraction
    if use_gemini:
        gemini_start = time.perf_counter()
        try:
            gemini_data = extract_job_details_with_gemini(jd_text)
            if gemini_data:
                extracted_data = merge_extraction_results(gemini_data, nlp_data)
                gemini_duration_ms = (time.perf_counter() - gemini_start) * 1000
                logger.info(
                    f"Gemini JD extraction succeeded in {gemini_duration_ms:.1f}ms "
                    f"(NLP took {nlp_duration_ms:.1f}ms)"
                )
        except Exception as error:
            logger.warning(f"Gemini extraction failed: {error}. Using fast NLP fallback.")
            extracted_data = nlp_data

    final_data = {
        "original_jd": jd_text,
        "source_type": source_type,
        **extracted_data
    }

    try:
        validated_data = JobCreate.model_validate(final_data)
    except ValidationError as error:
        raise ValueError(f"Job description validation failed: {error}") from error

    # Save to memory cache
    if len(_jd_cache) >= _MAX_CACHE_SIZE:
        _jd_cache.pop(next(iter(_jd_cache)))
    _jd_cache[cache_key] = extracted_data

    total_duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"Total JD processing completed in {total_duration_ms:.1f}ms")

    return validated_data
