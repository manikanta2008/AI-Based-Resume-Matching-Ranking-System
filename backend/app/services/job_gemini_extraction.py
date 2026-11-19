import os
import json
import time
import threading

from dotenv import load_dotenv
from google import genai
from google.genai import types

from pydantic import BaseModel, Field
from typing import Optional, List, Literal


load_dotenv()

# ==========================================
# THREAD-SAFE GEMINI CLIENT SINGLETON
# ==========================================
_client_lock = threading.Lock()
_cached_client = None

def get_gemini_client():
    global _cached_client
    if _cached_client is not None:
        return _cached_client

    with _client_lock:
        if _cached_client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in .env")
            _cached_client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=15000  # 15s timeout for fast responsiveness
                )
            )
        return _cached_client

class ExtractedSkill(BaseModel):

    skill_name: str

    skill_type: Literal["required", "preferred"]


class GeminiJobExtraction(BaseModel):

    title: Optional[str] = None

    min_experience: Optional[int] = None

    max_experience: Optional[int] = None

    education: List[str] = Field(default_factory=list)

    responsibilities: List[str] = Field(default_factory=list)

    keywords: List[str] = Field(default_factory=list)

    skills: List[ExtractedSkill] = Field(default_factory=list)


# ==========================================
# BUILD GEMINI PROMPT
# ==========================================

def build_job_prompt(jd_text: str):

    return f"""
You are an expert HR recruitment and job description
analysis system.

Analyze the following Job Description carefully.

Extract these fields:

1. TITLE
   Identify the actual job title.

2. MIN_EXPERIENCE
   Minimum required experience in years.
   Return null if not specified.

3. MAX_EXPERIENCE
   Maximum required experience in years.
   Return null if not specified.

4. EDUCATION
   Extract all educational qualifications.

5. RESPONSIBILITIES
   Extract important job responsibilities.

6. KEYWORDS
   Extract important domain-specific keywords.

7. SKILLS
   Extract technical skills and relevant professional skills.

   Classify every skill as:

   - required
   - preferred

IMPORTANT RULES:

- Extract only information supported by the JD.
- Never invent missing information.
- Understand the context instead of relying only on keywords.
- Distinguish required skills from preferred skills.
- Include relevant tools, frameworks, programming languages,
  technologies and professional competencies.
- Do not confuse responsibilities with skills.
- Return experience in years as integers.
- If experience is not specified, return null.
- Return valid JSON only.

JOB DESCRIPTION:

{jd_text}
"""


# ==========================================
# GEMINI JOB EXTRACTION
# ==========================================

def extract_job_details_with_gemini(jd_text: str) -> dict:

    if not jd_text or not jd_text.strip():
        raise ValueError(
            "Job description text cannot be empty."
        )

    client = get_gemini_client()

    primary_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    # Candidate models for fast fallback if primary fails
    candidate_models = [primary_model, "gemini-2.0-flash", "gemini-1.5-flash"]
    candidate_models = list(dict.fromkeys(candidate_models))

    # Trim to 4000 characters to keep prompt compact and fast
    trimmed_text = jd_text[:4000] if len(jd_text) > 4000 else jd_text
    prompt = build_job_prompt(trimmed_text)

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
            validated_data = GeminiJobExtraction(**extracted_data)
            return validated_data.model_dump()

        except Exception as error:
            # If rate-limited or unavailable, try next candidate model quickly
            continue

    raise RuntimeError(
        "Job extraction could not be completed with Gemini. Falling back to NLP."
    )