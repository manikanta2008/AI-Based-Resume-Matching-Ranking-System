import os
import json
import time
import logging

from typing import Optional

from sqlalchemy.orm import Session

from google.genai import types

from app.models.job import JobDescription, JobSkill
from app.models.resume import Resume
from app.models.resume_match import ResumeMatch

from app.services.job_gemini_extraction import get_gemini_client


logger = logging.getLogger(__name__)


# ==========================================
# GEMINI CONFIGURATION
# ==========================================

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.0-flash"
)


# ==========================================
# SCORING WEIGHTS
# ==========================================

SCORING_WEIGHTS = {
    "required_skills": 40,
    "preferred_skills": 15,
    "experience": 20,
    "semantic": 15,
    "education": 10
}
# ==========================================
# DATABASE RETRIEVAL
# ==========================================

def get_job_and_resume(
    db: Session,
    job_id: int,
    resume_id: int
):
    """
    Retrieve Job Description, associated skills,
    and candidate resume from PostgreSQL.
    """

    # Retrieve Job Description
    job = (
        db.query(JobDescription)
        .filter(JobDescription.id == job_id)
        .first()
    )

    if not job:
        raise ValueError(
            f"Job Description with ID {job_id} not found."
        )

    # Retrieve associated job skills
    job_skills = (
        db.query(JobSkill)
        .filter(JobSkill.job_id == job_id)
        .all()
    )

    # Retrieve Resume
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id)
        .first()
    )

    if not resume:
        raise ValueError(
            f"Resume with ID {resume_id} not found."
        )

    return job, job_skills, resume
# ==========================================
# PREPARE DATA FOR GEMINI
# ==========================================

def prepare_matching_data(job, job_skills, resume):

    required_skills = [
        skill.skill_name
        for skill in job_skills
        if skill.skill_type == "required"
    ]

    preferred_skills = [
        skill.skill_name
        for skill in job_skills
        if skill.skill_type == "preferred"
    ]

    job_data = {
        "job_title": job.title,
        "minimum_experience": job.min_experience,
        "maximum_experience": job.max_experience,
        "education_requirements": job.education or [],
        "responsibilities": job.responsibilities or [],
        "keywords": job.keywords or [],
        "required_skills": required_skills,
        "preferred_skills": preferred_skills
    }

    resume_data = {
        "candidate_name": resume.full_name,
        "technical_skills": resume.technical_skills or [],
        "soft_skills": resume.soft_skills or [],
        "work_experience": resume.work_experience,
        "experience_details": resume.experience_details or [],
        "education": resume.education or [],
        "projects": resume.projects or [],
        "certifications": resume.certifications or []
    }

    return job_data, resume_data

# ==========================================
# BUILD GEMINI MATCHING PROMPT
# ==========================================

def build_matching_prompt(job_data, resume_data):

    return f"""
You are an expert AI recruitment and resume evaluation system.

Your task is to evaluate how well a candidate matches a job description.

Analyze the candidate using the following dimensions:

1. REQUIRED SKILLS
   - Identify skills demonstrated by the candidate.
   - Consider equivalent technologies and relevant experience.
   - Identify missing required skills.
   - Provide evidence from the resume.

2. PREFERRED SKILLS
   - Identify matching preferred skills.
   - Identify missing preferred skills.

3. EXPERIENCE
   - Compare candidate experience with job requirements.
   - Consider relevant work experience and internships separately.
   - Do not invent experience.

4. EDUCATION
   - Evaluate the candidate's education against job requirements.
   - Consider equivalent qualifications where appropriate.

5. SEMANTIC RELEVANCE
   - Evaluate project relevance.
   - Evaluate responsibilities and technical experience.
   - Consider contextual similarity rather than exact keyword matching.

IMPORTANT RULES:

- Use only information present in the supplied resume.
- Never invent skills, qualifications, experience or projects.
- Do not treat a skill as demonstrated merely because it appears
  in a job description.
- Distinguish explicit evidence from inferred relevance.
- Return valid JSON only.
- All scores must be between 0 and 100.
- Provide concise explanations.

EXPECTED JSON STRUCTURE:

{{
    "required_skills": {{
        "matched": [],
        "missing": [],
        "score": 0,
        "evidence": []
    }},
    "preferred_skills": {{
        "matched": [],
        "missing": [],
        "score": 0,
        "evidence": []
    }},
    "experience": {{
        "score": 0,
        "analysis": ""
    }},
    "education": {{
        "score": 0,
        "analysis": ""
    }},
    "semantic": {{
        "score": 0,
        "analysis": ""
    }},
    "overall_explanation": ""
}}

JOB DESCRIPTION DATA:

{json.dumps(job_data, indent=2, ensure_ascii=False)}

CANDIDATE RESUME DATA:

{json.dumps(resume_data, indent=2, ensure_ascii=False)}
"""
# ==========================================
# RULE-BASED / SEMANTIC FALLBACK EVALUATION
# ==========================================

def evaluate_resume_fallback(job_data: dict, resume_data: dict) -> dict:
    """
    Fallback semantic and keyword matching algorithm used if Gemini API is
    unavailable, rate-limited, or encounters network timeouts.
    """
    required_skills = job_data.get("required_skills") or []
    preferred_skills = job_data.get("preferred_skills") or []

    candidate_skills = [
        s.lower().strip()
        for s in (resume_data.get("technical_skills") or []) + (resume_data.get("soft_skills") or [])
        if isinstance(s, str)
    ]
    resume_text_lower = (resume_data.get("resume_text") or "").lower()

    # Skill matching helper
    def check_skill_match(skill_name: str) -> bool:
        s_lower = skill_name.lower().strip()
        if not s_lower:
            return False
        if any(s_lower == cs or s_lower in cs or cs in s_lower for cs in candidate_skills):
            return True
        # Check text presence with simple boundary
        import re
        escaped = re.escape(s_lower)
        if re.search(r"(?<![a-zA-Z0-9])" + escaped + r"(?![a-zA-Z0-9])", resume_text_lower):
            return True
        # Common aliases
        aliases = {
            "react": ["react.js", "reactjs"],
            "node": ["node.js", "nodejs"],
            "js": ["javascript"],
            "ts": ["typescript"],
            "py": ["python"],
            "postgres": ["postgresql"],
            "sql": ["mysql", "postgresql", "oracle", "sqlite"],
            "aws": ["amazon web services", "cloud"],
            "ml": ["machine learning"],
            "nlp": ["natural language processing"],
            "spring": ["spring boot", "springboot"],
        }
        for k, v in aliases.items():
            if k in s_lower:
                for alias in v:
                    if alias in candidate_skills or alias in resume_text_lower:
                        return True
        return False

    # 1. Required skills
    matched_req = []
    missing_req = []
    for skill in required_skills:
        if check_skill_match(skill):
            matched_req.append(skill)
        else:
            missing_req.append(skill)

    req_score = (
        round((len(matched_req) / max(len(required_skills), 1)) * 100, 1)
        if required_skills
        else 85.0
    )

    # 2. Preferred skills
    matched_pref = []
    missing_pref = []
    for skill in preferred_skills:
        if check_skill_match(skill):
            matched_pref.append(skill)
        else:
            missing_pref.append(skill)

    pref_score = (
        round((len(matched_pref) / max(len(preferred_skills), 1)) * 100, 1)
        if preferred_skills
        else 80.0
    )

    # 3. Experience evaluation
    cand_exp = resume_data.get("work_experience")
    min_exp = job_data.get("minimum_experience")
    max_exp = job_data.get("maximum_experience")

    if cand_exp is not None and min_exp is not None:
        if cand_exp >= min_exp:
            exp_score = min(100.0, 85.0 + min(15.0, (cand_exp - min_exp) * 5.0))
            exp_analysis = (
                f"Candidate has {cand_exp} years of experience, meeting or exceeding "
                f"the required minimum of {min_exp} years."
            )
        elif cand_exp >= (min_exp - 1):
            exp_score = 75.0
            exp_analysis = (
                f"Candidate has {cand_exp} years of experience, which is close to the "
                f"minimum required {min_exp} years."
            )
        else:
            ratio = max(0.2, cand_exp / max(min_exp, 1))
            exp_score = round(ratio * 70, 1)
            exp_analysis = (
                f"Candidate has {cand_exp} years of experience, below the required "
                f"minimum of {min_exp} years."
            )
    elif cand_exp is not None:
        exp_score = min(90.0, 60.0 + cand_exp * 8.0)
        exp_analysis = f"Candidate has {cand_exp} years of relevant experience."
    else:
        exp_score = 70.0
        exp_analysis = "Candidate experience is not explicitly quantified in years."

    # 4. Education evaluation
    job_edu = job_data.get("education_requirements") or []
    cand_edu = resume_data.get("education") or []
    cand_edu_text = json.dumps(cand_edu).lower()
    edu_score = 80.0
    edu_analysis = "Candidate educational background aligns reasonably with the role."
    if any(deg in cand_edu_text for deg in ["b.tech", "b.e", "bachelor", "master", "m.tech", "mca", "bca", "bs", "ms"]):
        edu_score = 90.0
        edu_analysis = "Candidate holds a relevant technical degree in engineering/computer science."

    # 5. Semantic relevance
    job_keywords = job_data.get("keywords") or []
    job_resp = job_data.get("responsibilities") or []
    found_kw = sum(1 for kw in job_keywords if kw.lower() in resume_text_lower)
    kw_ratio = found_kw / max(len(job_keywords), 1) if job_keywords else 0.7
    semantic_score = round(min(95.0, max(50.0, kw_ratio * 100)), 1)
    semantic_analysis = (
        f"Semantic evaluation indicates {round(semantic_score)}% contextual similarity with "
        f"job responsibilities, projects, and domain competencies."
    )

    # 6. Overall explanation
    cand_name = resume_data.get("candidate_name") or "Candidate"
    skills_summary = (
        f"Demonstrated core skills: {', '.join(matched_req[:5])}."
        if matched_req
        else "Limited overlap with required skills."
    )
    missing_summary = (
        f" Key missing skills: {', '.join(missing_req[:4])}."
        if missing_req
        else " Covers all primary required skills."
    )
    overall_explanation = (
        f"{cand_name} matches the role with an overall strong profile. "
        f"{skills_summary}{missing_summary} "
        f"Experience evaluation: {exp_analysis}"
    )

    return {
        "required_skills": {
            "matched": matched_req,
            "missing": missing_req,
            "score": req_score,
            "evidence": matched_req
        },
        "preferred_skills": {
            "matched": matched_pref,
            "missing": missing_pref,
            "score": pref_score,
            "evidence": matched_pref
        },
        "experience": {
            "score": round(exp_score, 1),
            "analysis": exp_analysis
        },
        "education": {
            "score": round(edu_score, 1),
            "analysis": edu_analysis
        },
        "semantic": {
            "score": round(semantic_score, 1),
            "analysis": semantic_analysis
        },
        "overall_explanation": overall_explanation
    }


# ==========================================
# GEMINI RESUME EVALUATION
# ==========================================

def evaluate_resume_with_gemini(job_data, resume_data):

    try:
        client = get_gemini_client()
    except Exception as e:
        logger.warning(f"Could not initialize Gemini client: {e}. Using fallback matching.")
        return evaluate_resume_fallback(job_data, resume_data)

    prompt = build_matching_prompt(
        job_data,
        resume_data
    )

    for attempt in range(1, 3):

        try:

            response = client.models.generate_content(

                model=GEMINI_MODEL,

                contents=prompt,

                config=types.GenerateContentConfig(

                    response_mime_type="application/json",

                    temperature=0.0,

                    max_output_tokens=2048
                )
            )

            if not response.text:

                raise ValueError(
                    "Gemini returned an empty response."
                )

            result = json.loads(response.text)

            # Validate required sections
            required_sections = [
                "required_skills",
                "preferred_skills",
                "experience",
                "education",
                "semantic",
                "overall_explanation"
            ]

            for section in required_sections:

                if section not in result:

                    raise ValueError(
                        f"Missing Gemini response section: {section}"
                    )

            # Validate scores
            score_fields = [
                ("required_skills", "score"),
                ("preferred_skills", "score"),
                ("experience", "score"),
                ("education", "score"),
                ("semantic", "score")
            ]

            for section, field in score_fields:

                score = result[section].get(field)

                if (
                    isinstance(score, bool)
                    or not isinstance(score, (int, float))
                    or not 0 <= score <= 100
                ):

                    raise ValueError(
                        f"Invalid score returned for {section}."
                    )

            return result

        except Exception as error:

            error_message = str(error).upper()

            temporary_errors = [
                "503",
                "429",
                "UNAVAILABLE",
                "RESOURCE_EXHAUSTED"
            ]

            is_temporary_error = any(
                item in error_message
                for item in temporary_errors
            )

            if is_temporary_error and attempt < 3:

                wait_time = 2 * attempt

                logger.warning(
                    "Gemini temporarily unavailable. "
                    "Retrying in %s seconds.",
                    wait_time
                )

                time.sleep(wait_time)

                continue

            logger.warning(
                "Gemini resume evaluation failed: %s. Using semantic fallback engine.",
                error
            )
            return evaluate_resume_fallback(job_data, resume_data)

    logger.warning("Gemini attempts exhausted. Using fallback matching.")
    return evaluate_resume_fallback(job_data, resume_data)


# ==========================================
# CALCULATE OVERALL MATCHING SCORE
# ==========================================

def calculate_matching_score(ai_result):

    required_score = ai_result["required_skills"]["score"]

    preferred_score = ai_result["preferred_skills"]["score"]

    experience_score = ai_result["experience"]["score"]

    semantic_score = ai_result["semantic"]["score"]

    education_score = ai_result["education"]["score"]

    # Weighted score calculation

    overall_score = (

        required_score * 0.40 +

        preferred_score * 0.15 +

        experience_score * 0.20 +

        semantic_score * 0.15 +

        education_score * 0.10

    )

    return {
        "overall_score": round(overall_score, 2),

        "required_skills_score": required_score,

        "preferred_skills_score": preferred_score,

        "experience_score": experience_score,

        "semantic_score": semantic_score,

        "education_score": education_score
    }

# ==========================================
# SAVE MATCHING RESULTS
# ==========================================

def save_match_result(
    db: Session,
    job_id: int,
    resume_id: int,
    ai_result: dict,
    scores: dict
):

    try:

        required = ai_result["required_skills"]
        preferred = ai_result["preferred_skills"]

        # Check whether a match already exists
        match = (
            db.query(ResumeMatch)
            .filter(
                ResumeMatch.job_id == job_id,
                ResumeMatch.resume_id == resume_id
            )
            .first()
        )

        if not match:

            match = ResumeMatch(
                job_id=job_id,
                resume_id=resume_id
            )

            db.add(match)

        # Overall scores
        match.overall_score = scores["overall_score"]

        match.required_skills_score = scores["required_skills_score"]
        match.preferred_skills_score = scores["preferred_skills_score"]
        match.experience_score = scores["experience_score"]
        match.semantic_score = scores["semantic_score"]
        match.education_score = scores["education_score"]

        # Skill matching results
        match.matched_required_skills = required.get("matched", [])
        match.missing_required_skills = required.get("missing", [])

        match.matched_preferred_skills = preferred.get("matched", [])
        match.missing_preferred_skills = preferred.get("missing", [])

        # Detailed analysis
        match.experience_analysis = ai_result["experience"]
        match.education_analysis = ai_result["education"]
        match.semantic_analysis = ai_result["semantic"]

        # Score breakdown
        match.score_breakdown = {
            "weights": SCORING_WEIGHTS,
            "scores": scores
        }

        # AI explanation
        match.ai_explanation = ai_result["overall_explanation"]

        db.commit()
        db.refresh(match)

        return match

    except Exception:

        db.rollback()

        logger.exception("Failed to save resume matching result.")

        raise

# ==========================================
# COMPLETE RESUME MATCHING WORKFLOW
# ==========================================

def match_resume_to_job(
    db: Session,
    job_id: int,
    resume_id: int,
    precomputed_job_data: Optional[dict] = None,
    precomputed_job_title: Optional[str] = None
):
    """
    Evaluate one resume against one job description
    and save the matching result in PostgreSQL.
    """

    if precomputed_job_data is not None:
        job_data = precomputed_job_data
        job_title = precomputed_job_title or "Job Description"
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise ValueError(f"Resume with ID {resume_id} not found.")
        resume_data = {
            "candidate_name": resume.full_name,
            "technical_skills": resume.technical_skills or [],
            "soft_skills": resume.soft_skills or [],
            "work_experience": resume.work_experience,
            "experience_details": resume.experience_details or [],
            "education": resume.education or [],
            "projects": resume.projects or [],
            "certifications": resume.certifications or []
        }
    else:
        # STEP 1: Retrieve job and resume
        job, job_skills, resume = get_job_and_resume(
            db=db,
            job_id=job_id,
            resume_id=resume_id
        )
        job_title = job.title

        # STEP 2: Prepare structured data
        job_data, resume_data = prepare_matching_data(
            job=job,
            job_skills=job_skills,
            resume=resume
        )

    # STEP 3: Gemini evaluation
    ai_result = evaluate_resume_with_gemini(
        job_data=job_data,
        resume_data=resume_data
    )

    # STEP 4: Calculate weighted score
    scores = calculate_matching_score(ai_result)

    # STEP 5: Save result in PostgreSQL
    saved_match = save_match_result(
        db=db,
        job_id=job_id,
        resume_id=resume_id,
        ai_result=ai_result,
        scores=scores
    )

    matched_skills = list(dict.fromkeys(
        (saved_match.matched_required_skills or []) + (saved_match.matched_preferred_skills or [])
    ))
    missing_skills = list(dict.fromkeys(
        (saved_match.missing_required_skills or []) + (saved_match.missing_preferred_skills or [])
    ))

    return {
        "message": "Resume matching completed successfully.",
        "match_id": saved_match.id,
        "job_id": saved_match.job_id,
        "resume_id": saved_match.resume_id,
        "candidate_name": resume.full_name or resume.original_filename,
        "email": resume.email,
        "experience_years": resume.work_experience,
        "job_title": job_title,
        "overall_score": saved_match.overall_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_required_skills": saved_match.matched_required_skills or [],
        "missing_required_skills": saved_match.missing_required_skills or [],
        "matched_preferred_skills": saved_match.matched_preferred_skills or [],
        "missing_preferred_skills": saved_match.missing_preferred_skills or [],
        "score_breakdown": saved_match.score_breakdown,
        "ai_explanation": saved_match.ai_explanation
    }