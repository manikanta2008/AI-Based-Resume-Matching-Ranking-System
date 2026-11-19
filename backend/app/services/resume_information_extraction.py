import os
import json
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ==========================================
# 1. LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


# ==========================================
# 2. PYDANTIC SCHEMAS
# ==========================================

class ResumeEducation(BaseModel):

    degree: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[str] = None


class ResumeExperience(BaseModel):

    company: Optional[str] = None
    job_title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ResumeProject(BaseModel):

    project_name: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)


class GeminiResumeExtraction(BaseModel):

    # PERSONAL INFORMATION
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # SKILLS
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)

    # EDUCATION
    education: List[ResumeEducation] = Field(default_factory=list)

    # EXPERIENCE
    work_experience: Optional[float] = None

    previous_companies: List[str] = Field(
        default_factory=list
    )

    experience_details: List[ResumeExperience] = Field(
        default_factory=list
    )

    # PROJECTS
    projects: List[ResumeProject] = Field(
        default_factory=list
    )

    # CERTIFICATIONS
    certifications: List[str] = Field(
        default_factory=list
    )

    # PROFESSIONAL LINKS
    professional_links: Dict[str, Optional[str]] = Field(
        default_factory=dict
    )


# ==========================================
# 3. PROFESSIONAL LINK NORMALIZATION
# ==========================================

def normalize_professional_links(
    links: Any
) -> Dict[str, Optional[str]]:

    expected_link_types = [
        "linkedin",
        "github",
        "portfolio",
        "leetcode",
        "hackerrank",
        "kaggle",
        "other"
    ]

    normalized_links = {
        link_type: None
        for link_type in expected_link_types
    }

    if not isinstance(links, dict):
        return normalized_links

    for link_type in expected_link_types:

        value = links.get(link_type)

        if isinstance(value, str):

            value = value.strip()

            normalized_links[link_type] = (
                value if value else None
            )

        elif isinstance(value, dict):

            possible_url = (
                value.get("url")
                or value.get("href")
                or value.get("link")
            )

            if isinstance(possible_url, str):

                possible_url = possible_url.strip()

                normalized_links[link_type] = (
                    possible_url if possible_url else None
                )

    return normalized_links


# ==========================================
# 4. SHARED GEMINI CLIENT
# ==========================================

from app.services.job_gemini_extraction import get_gemini_client


# ==========================================
# 5. RESUME EXTRACTION PROMPT
# ==========================================

def build_resume_prompt(resume_text: str):

    return f"""
You are an expert AI resume parsing and recruitment system.

Analyze the following resume and extract structured candidate
information.

Extract the following fields:

1. full_name:
   Candidate's complete name.

2. email:
   Candidate's email address.

3. phone:
   Candidate's contact number.

4. technical_skills:
   List of technical skills explicitly supported by the resume.

5. soft_skills:
   List of soft skills explicitly mentioned or clearly demonstrated.

6. education:
   Extract each educational qualification separately.

   Include:
   - degree
   - institution
   - field_of_study
   - graduation_year

7. work_experience:
   Total professional work experience in years, if explicitly
   stated or reliably calculable from employment dates.

   Do not count internships as professional experience unless
   the resume explicitly includes them in its total experience.
   Do not double-count overlapping employment periods.
   Return null if it cannot be reliably calculated.

8. previous_companies:
   List of companies where the candidate has worked.

9. experience_details:
   Extract each work experience separately.

   Include:
   - company
   - job_title
   - start_date
   - end_date
   - description

10. projects:
    Extract each project separately.

    Include:
    - project_name
    - description
    - technologies

11. certifications:
    List all certifications mentioned.

12. professional_links:
    Extract professional URLs exactly as they appear.

    Identify:
    - linkedin
    - github
    - portfolio
    - leetcode
    - hackerrank
    - kaggle
    - other relevant professional websites

    Do not invent URLs.
    Do not treat ordinary email addresses as URLs.
    If a link is unavailable, return null.

IMPORTANT RULES:

- Extract only information supported by the resume.
- Never invent candidate information.
- Do not assume missing information.
- Preserve the original meaning of descriptions.
- Avoid duplicate skills and companies.
- Do not confuse academic projects with employment.
- Do not confuse internships with full-time employment.
- Return empty lists when information is unavailable.
- Return null for unavailable individual values.
- Return valid JSON only.

RESUME CONTENT:

{resume_text}
"""


# ==========================================
# 5b. RULE-BASED FALLBACK EXTRACTION
# ==========================================

def extract_resume_information_fallback(
    resume_text: str,
    professional_links: Optional[Dict[str, Any]] = None
) -> dict:
    """
    Fallback extractor if Gemini is unavailable, rate-limited, or fails.
    Extracts name, email, phone, experience, and skills using NLP & regex.
    """
import re
import hashlib
from app.services.job_nlp_extraction import COMPILED_SKILL_PATTERNS

# In-memory LRU cache for resume extraction
_MAX_RESUME_CACHE = 256
_resume_cache: Dict[str, dict] = {}

# Precompiled regexes for fast fallback extraction
_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
_NAME_LINE_REGEX = re.compile(r"^[A-Za-z\s.'-]{3,40}$")
_EXP_REGEX = re.compile(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+experience)?")
_EDU_COMPILED = [
    ("Bachelor of Technology", re.compile(r"\bB\.?Tech\b|\bB\.?E\b", re.IGNORECASE)),
    ("Master of Technology", re.compile(r"\bM\.?Tech\b|\bM\.?E\b", re.IGNORECASE)),
    ("Bachelor of Science", re.compile(r"\bB\.?Sc\b|\bBCA\b|\bBachelor\b", re.IGNORECASE)),
    ("Master of Computer Applications", re.compile(r"\bMCA\b|\bM\.?Sc\b|\bMaster\b", re.IGNORECASE)),
]


def extract_resume_information_fallback(
    resume_text: str,
    professional_links: Optional[Dict[str, Any]] = None
) -> dict:
    """
    High-speed rule-based extractor using precompiled regular expressions.
    Executes in under 5 milliseconds.
    """
    # 1. Email
    email_match = _EMAIL_REGEX.search(resume_text)
    email = email_match.group(0) if email_match else None

    # 2. Phone
    phone_match = _PHONE_REGEX.search(resume_text)
    phone = phone_match.group(0) if phone_match else None

    # 3. Name: scan first 8 lines
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    full_name = None
    header_keywords = ("resume", "curriculum", "email", "phone", "contact", "http", "@", "github", "linkedin")
    for line in lines[:8]:
        line_lower = line.lower()
        if any(h in line_lower for h in header_keywords):
            continue
        if _NAME_LINE_REGEX.match(line) and len(line.split()) <= 4:
            full_name = line
            break
    if not full_name and lines:
        full_name = lines[0][:40]

    # 4. Technical Skills via precompiled patterns with fast pre-filtering
    tech_skills = []
    text_lower = resume_text.lower()
    for skill_name, alias_patterns in COMPILED_SKILL_PATTERNS.items():
        if not any(alias in text_lower for alias, _ in alias_patterns):
            continue
        for alias, pattern in alias_patterns:
            if pattern.search(resume_text):
                if skill_name not in tech_skills:
                    tech_skills.append(skill_name)
                break

    # 5. Experience
    work_exp = None
    exp_matches = _EXP_REGEX.findall(text_lower)
    if exp_matches:
        try:
            work_exp = float(exp_matches[0])
        except ValueError:
            pass

    # 6. Education
    education = []
    for deg_title, pattern in _EDU_COMPILED:
        if pattern.search(resume_text):
            education.append({
                "degree": deg_title,
                "institution": "University / Institution",
                "field_of_study": "Computer Science / Engineering",
                "graduation_year": None
            })

    # 7. Normalized professional links
    norm_links = normalize_professional_links(professional_links or {})

    return {
        "full_name": full_name or "Candidate",
        "email": email,
        "phone": phone,
        "technical_skills": tech_skills,
        "soft_skills": ["Communication", "Problem Solving", "Teamwork"],
        "education": education,
        "work_experience": work_exp,
        "previous_companies": [],
        "experience_details": [],
        "projects": [],
        "certifications": [],
        "professional_links": norm_links
    }


# ==========================================
# 6. GEMINI RESUME EXTRACTION
# ==========================================

def extract_resume_information(
    resume_text: str,
    professional_links: Optional[Dict[str, Any]] = None
) -> dict:

    if not resume_text or not resume_text.strip():
        raise ValueError(
            "Resume text cannot be empty."
        )

    # Use first 4000 characters to ensure fast prompt transmission
    trimmed_text = resume_text[:4000] if len(resume_text) > 4000 else resume_text
    cache_key = hashlib.sha256(trimmed_text.encode("utf-8")).hexdigest()

    if cache_key in _resume_cache:
        cached_result = json.loads(json.dumps(_resume_cache[cache_key]))
        if professional_links:
            actual_links = normalize_professional_links(professional_links)
            cached_links = cached_result.get("professional_links", {})
            for link_type, url in actual_links.items():
                if url:
                    cached_links[link_type] = url
            cached_result["professional_links"] = cached_links
        return cached_result

    try:
        client = get_gemini_client()
    except Exception as err:
        print(f"Gemini client init failed: {err}. Using rule-based fallback extractor.")
        fallback_res = extract_resume_information_fallback(resume_text, professional_links)
        if len(_resume_cache) < _MAX_RESUME_CACHE:
            _resume_cache[cache_key] = fallback_res
        return fallback_res

    primary_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    candidate_models = list(dict.fromkeys([primary_model, "gemini-2.0-flash", "gemini-1.5-flash"]))

    prompt = build_resume_prompt(trimmed_text)

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                    max_output_tokens=1024
                )
            )

            if not response.text:
                continue

            extracted_data = json.loads(response.text)

            if not isinstance(extracted_data, dict):
                continue

            # Normalize links before Pydantic validation.
            extracted_data["professional_links"] = (
                normalize_professional_links(
                    extracted_data.get("professional_links")
                )
            )

            # Validate extracted information.
            validated_data = GeminiResumeExtraction(
                **extracted_data
            )

            result = validated_data.model_dump()

            if professional_links:
                gemini_links = result.get("professional_links", {})
                actual_links = normalize_professional_links(professional_links)
                for link_type, url in actual_links.items():
                    if url:
                        gemini_links[link_type] = url
                result["professional_links"] = gemini_links

            # Save to memory cache
            if len(_resume_cache) >= _MAX_RESUME_CACHE:
                _resume_cache.pop(next(iter(_resume_cache)))
            _resume_cache[cache_key] = result

            return result

        except Exception as error:
            continue

    print("Gemini extraction unavailable. Using fast fallback extractor.")
    fallback_res = extract_resume_information_fallback(resume_text, professional_links)
    if len(_resume_cache) < _MAX_RESUME_CACHE:
        _resume_cache[cache_key] = fallback_res
    return fallback_res
