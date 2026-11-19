# AI-Based Resume Matching & Ranking System

An AI-powered recruitment platform that parses resumes and job descriptions into structured data, scores every candidate against a job with a transparent weighted model, and ranks candidates with a per-skill and per-dimension explanation.

**Live deployment:** React frontend on Vercel, FastAPI backend on Render, PostgreSQL database.

---

## Table of Contents

1. [Features](#features)
2. [System Architecture](#system-architecture)
3. [How It Works](#how-it-works)
4. [Matching Algorithm and Scoring Methodology](#matching-algorithm-and-scoring-methodology)
5. [Fallback Engine](#fallback-engine-when-gemini-is-unavailable)
6. [Ranking](#ranking)
7. [Duplicate Handling](#duplicate-handling)
8. [Database Schema](#database-schema)
9. [API Reference](#api-reference)
10. [Tech Stack](#tech-stack)
11. [Project Structure](#project-structure)
12. [Local Setup](#local-setup)
13. [Environment Variables](#environment-variables)
14. [Deployment](#deployment)
15. [Design Decisions](#design-decisions)
16. [Limitations and Future Work](#limitations-and-future-work)
17. [Author](#author)

---

## Features

- **Job description analysis:** paste text or upload a PDF/DOCX. The system extracts the title, experience range, education, responsibilities, keywords, and skills classified as required or preferred.
- **Resume parsing:** upload many PDF/DOCX resumes at once. The system extracts name, email, phone, technical and soft skills, education, total experience, companies, experience details, projects, certifications, and professional links (LinkedIn, GitHub, LeetCode, HackerRank, Kaggle, portfolio).
- **Weighted candidate scoring:** five scoring dimensions combine into one 0-100 match score.
- **Explainable results:** every match stores matched and missing skills, per-dimension scores, written analysis, and an overall explanation.
- **Batch matching and ranking:** match all resumes (or a chosen subset) against a job in parallel and get a ranked list.
- **Resilient by design:** if the Gemini API is slow, rate-limited, or unavailable, both extraction and matching fall back to rule-based engines so the pipeline still returns results.
- **Duplicate detection:** exact-file, same-email, and same-name duplicates are detected for resumes, and repeated job descriptions update the existing record.

---

## System Architecture

```mermaid
flowchart LR
    subgraph Frontend["React + Vite (Vercel)"]
        A[Dashboard]
        B[Job Descriptions]
        C[Upload Resumes]
        D[Candidate Matching]
    end

    subgraph Backend["FastAPI (Render)"]
        R1["/jobs routes"]
        R2["/resumes routes"]
        S1[Job extraction<br/>NLP + Gemini]
        S2[Resume extraction<br/>Gemini + regex fallback]
        S3[Matching engine<br/>Gemini + rule-based fallback]
        S4[Ranking service]
    end

    DB[(PostgreSQL)]
    G[Google Gemini API]

    Frontend -->|Axios / REST| Backend
    R1 --> S1
    R2 --> S2
    R2 --> S3
    S3 --> S4
    S1 --> G
    S2 --> G
    S3 --> G
    S1 --> DB
    S2 --> DB
    S3 --> DB
    S4 --> DB
```

---

## How It Works

```text
Job Description ──► Extraction ──► Structured job (title, skills required/preferred,
   (text/PDF/DOCX)                  experience range, education, keywords)  ──► saved

Resume files ─────► Text + link ──► Structured candidate (skills, education, experience,
   (PDF/DOCX)        extraction      projects, certifications, links)         ──► saved

Job + Resumes ────► Matching ─────► 5 dimension scores ──► weighted overall score ──► saved
                                                                                        │
                                                                          Ranking ◄─────┘
                                                                  (highest overall score first)
```

### 1. Job description processing

Located in `backend/app/services/job_processing.py`, `job_nlp_extraction.py`, and `job_gemini_extraction.py`.

1. **Rule-based NLP pass (always runs, milliseconds):**
   - A skill dictionary of 29 technologies (Python, Java, FastAPI, React, PostgreSQL, Docker, AWS, TensorFlow, and others) with aliases, matched using precompiled word-boundary regular expressions.
   - A skill is marked **preferred** when the sentence that mentions it contains words such as "preferred", "nice to have", "good to have", "plus", "optional", or "bonus". Otherwise it is **required**.
   - Experience is read from patterns such as `3-5 years`, `3+ years`, `minimum of 3 years`, and `at least 3 years`.
   - Title, education (B.Tech, M.Tech, MCA, MBA, PhD, Bachelor's, Master's, and others), responsibilities (sentences containing action verbs), and up to 30 keywords are also extracted.
2. **Gemini pass (optional, `use_gemini`):** the first 4,000 characters of the JD go to Gemini with a strict JSON schema. Gemini understands context, so it classifies skills as required or preferred more accurately and finds skills outside the dictionary. If the primary model fails, `gemini-2.0-flash` and then `gemini-1.5-flash` are tried.
3. **Merge:** Gemini output has priority. Missing scalar fields (title, experience) are filled from the NLP pass, list fields are de-duplicated and combined, and NLP-only skills are added.
4. **Review and save:** the recruiter reviews the extracted data in the UI, then confirms to save. Results are cached in memory (up to 128 entries) so identical JDs return instantly.

### 2. Resume processing

Located in `resume_text_extraction.py`, `resume_information_extraction.py`, and `resume_processing.py`.

1. **Single-pass text and link extraction:** PDF text is read with `pypdf` and hyperlinks are collected from link annotations in the same pass. DOCX text comes from paragraphs and tables, and hyperlinks from document relationships. Links are classified as LinkedIn, GitHub, LeetCode, HackerRank, Kaggle, portfolio, or other.
2. **Structured extraction with Gemini:** the first 4,000 characters go to Gemini with a Pydantic-validated JSON schema. The prompt forbids inventing information, tells the model not to count internships as professional experience, and not to double-count overlapping jobs. Real links found in the file override anything Gemini returns.
3. **Rule-based fallback:** if Gemini is unavailable, regular expressions extract email, phone, name (from the first lines), dictionary skills, years of experience, and degree. Results are cached in memory (up to 256 entries).
4. **Concurrent upload:** multiple files are processed in parallel (up to 8 worker threads), each with its own database session.

---

## Matching Algorithm and Scoring Methodology

Located in `backend/app/services/resume_matching.py`.

### Scoring dimensions and weights

Each candidate is scored from 0 to 100 on five dimensions. The overall score is their weighted sum.

| Dimension | Weight | What is evaluated |
|---|---|---|
| Required skills | **40%** | Share of the job's required skills the candidate demonstrates, with evidence from the resume |
| Experience | **20%** | Candidate's years of experience compared with the job's minimum and maximum |
| Preferred skills | **15%** | Share of the job's preferred (nice-to-have) skills the candidate demonstrates |
| Semantic relevance | **15%** | How relevant the candidate's projects, responsibilities, and technical background are to the role, judged by context rather than exact keywords |
| Education | **10%** | Candidate's qualifications compared with the job's education requirements |

```text
overall_score = 0.40 × required_skills
              + 0.20 × experience
              + 0.15 × preferred_skills
              + 0.15 × semantic
              + 0.10 × education
```

The weights express the hiring priorities: **hard requirements dominate** (required skills and experience make up 60% of the score), while preferred skills, contextual fit, and education refine the ranking.

### Worked example

| Dimension | Score | Weight | Contribution |
|---|---|---|---|
| Required skills | 80 | 0.40 | 32.0 |
| Experience | 90 | 0.20 | 18.0 |
| Preferred skills | 50 | 0.15 | 7.5 |
| Semantic relevance | 70 | 0.15 | 10.5 |
| Education | 90 | 0.10 | 9.0 |
| **Overall** | | | **77.0** |

### Step by step

1. **Load** the job (with its required and preferred skills) and the resume's structured profile from PostgreSQL.
2. **Build** a compact JSON for each: the job (title, experience range, education, responsibilities, keywords, required and preferred skills) and the candidate (skills, experience, education, projects, certifications).
3. **Evaluate with Gemini** using a rubric prompt and these rules:
   - use only information present in the resume
   - never invent skills, qualifications, experience, or projects
   - do not treat a skill as demonstrated merely because the job description mentions it
   - distinguish explicit evidence from inferred relevance
   - consider equivalent technologies
   - return JSON only, with all scores between 0 and 100
4. **Validate** the response: all five sections must exist and every score must be a number from 0 to 100. Otherwise the response is rejected.
5. **Score:** compute the weighted overall score, rounded to two decimals.
6. **Save** one row per job and resume pair. Re-matching the same pair updates the existing row.

### Determinism and reliability

- Gemini is called with `temperature = 0` and a JSON response type, so the same input gives consistent output.
- Temporary errors (HTTP 503, 429, `UNAVAILABLE`, `RESOURCE_EXHAUSTED`) trigger a retry after a short wait.
- Any other failure, invalid output, or missing API key switches to the fallback engine below, so a match is always produced.

### What is stored for explainability

For every match the database keeps: the overall score, all five dimension scores, matched and missing required skills, matched and missing preferred skills, a written analysis for experience, education, and semantic fit, the weights used, and an overall explanation. The UI shows this so recruiters can see why a candidate ranked where they did.

---

## Fallback Engine (when Gemini is unavailable)

`evaluate_resume_fallback` produces the same output structure with deterministic rules, so ranking keeps working offline or under rate limits.

| Dimension | Rule |
|---|---|
| Required skills | `matched / total × 100`. Skills match by exact name, substring in the candidate's skill list, or alias (for example `react` and `react.js`, `postgres` and `postgresql`, `nlp` and `natural language processing`). Score is 85 if the job lists no required skills. |
| Preferred skills | Same method. Score is 80 if the job lists no preferred skills. |
| Experience | At or above the minimum: `85 + 5 per extra year`, capped at 100. Within one year below the minimum: 75. Further below: `candidate / minimum × 70`, with a floor ratio of 0.2. If only the candidate has a value: `60 + 8 × years`, capped at 90. If unknown: 70. |
| Education | 90 if a recognized degree (B.Tech, B.E., Bachelor, Master, M.Tech, MCA, BCA) appears in the candidate's education, otherwise 80. |
| Semantic | Share of job keywords found in the resume text, clamped between 50 and 95 (70 if the job has no keywords). |

The fallback always runs through the same weighted formula and the same storage path.

---

## Ranking

Located in `backend/app/services/candidate_results.py` and `batch_matching.py`.

- Candidates are sorted by `overall_score` in descending order. Rank 1 is the best match.
- **Batch matching** (`POST /resumes/match-batch`) matches many resumes in parallel (up to 6 worker threads, each with its own database session). The job and its skills are loaded once and shared across workers, so the database is not queried repeatedly for the same job.
- One failing resume does not stop the batch. Failures are reported in an `errors` list with the resume ID and reason.
- The result lists the successful and failed counts and the ranked candidates, each with a full score breakdown and a candidate profile.

---

## Duplicate Handling

**Resumes** (`resume_processing.py`), checked in this order:

1. **Exact file:** SHA-256 hash of the file bytes. The existing record is returned and no parsing is done.
2. **Same email:** the existing candidate record is updated with the newer extracted data.
3. **Same filename and name:** the existing record is updated.

The upload response reports the duplicates and the reason (`exact_file`, `email_match`, or `name_match`).

**Job descriptions** (`job_routes.py`): a job whose normalized text matches an existing one, or that has the same title, experience range, and first 200 characters, updates the existing record instead of creating a new one.

---

## Database Schema

PostgreSQL, created automatically on startup through SQLAlchemy.

| Table | Purpose |
|---|---|
| `job_descriptions` | Original JD text, source type, title, min and max experience, education, responsibilities, keywords |
| `job_skills` | Skills for each job with `skill_type` of `required` or `preferred` (unique per job and skill) |
| `resumes` | File info and hash, candidate details, skills, education, experience, projects, certifications, links, raw text |
| `resume_matches` | Scores, matched and missing skills, analyses, score breakdown, AI explanation (unique per job and resume pair, indexed by job and score) |

Structured fields use PostgreSQL `JSONB`.

---

## API Reference

Interactive documentation is available at `/docs` (Swagger UI) when the backend is running.

### Job descriptions

| Method | Endpoint | Description |
|---|---|---|
| POST | `/jobs/preview` | Extract structured data from pasted JD text (nothing is saved) |
| POST | `/jobs/upload-file` | Extract structured data from a PDF or DOCX JD (multipart, optional `use_gemini`) |
| POST | `/jobs/confirm` | Save a reviewed job description. Updates the existing record if it is a duplicate |
| GET | `/jobs` | List all jobs |
| GET | `/jobs/{job_id}` | Get one job with its skills |
| DELETE | `/jobs/{job_id}` | Delete a job |

### Resumes and matching

| Method | Endpoint | Description |
|---|---|---|
| POST | `/resumes/upload` | Upload multiple PDF or DOCX resumes (multipart `files`) |
| GET | `/resumes` | List all resumes |
| GET | `/resumes/{resume_id}` | Get one resume |
| DELETE | `/resumes/{resume_id}` | Delete a resume |
| POST | `/resumes/match?job_id=&resume_id=` | Match one resume to one job |
| POST | `/resumes/match-batch` | Match many resumes to a job. Body: `{"job_id": 1, "resume_ids": [1, 2, 3]}` (omit `resume_ids` to match all) |
| GET | `/resumes/rankings/{job_id}` | Ranked candidates for a job |
| GET | `/resumes/match-details/{job_id}/{resume_id}` | Full analysis for one candidate |

### Example: batch match response (abridged, illustrative values)

```json
{
  "job_id": 1,
  "job_title": "Python Backend Developer",
  "total_resumes": 20,
  "successful": 20,
  "failed": 0,
  "ranked_candidates": [
    {
      "rank": 1,
      "candidate_name": "Aarav Sharma",
      "overall_score": 87.5,
      "required_skills_score": 95,
      "preferred_skills_score": 70,
      "experience_score": 90,
      "semantic_score": 85,
      "education_score": 90,
      "matched_required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
      "missing_required_skills": [],
      "ai_explanation": "..."
    }
  ],
  "errors": null
}
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Axios, Lucide icons, CSS |
| Backend | Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy |
| AI | Google Gemini (`google-genai`), default model `gemini-2.0-flash` |
| Document parsing | `pypdf` (PDF), `python-docx` (DOCX) |
| Database | PostgreSQL with `psycopg` |
| Hosting | Vercel (frontend), Render (backend) |

---

## Project Structure

```text
AI-Based-Resume-Matching-Ranking-System/
├── backend/
│   ├── app/
│   │   ├── core/            # settings (DATABASE_URL)
│   │   ├── database/        # engine, session, Base
│   │   ├── models/          # JobDescription, JobSkill, Resume, ResumeMatch
│   │   ├── routes/          # job_routes.py, resume_routes.py
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── job_processing.py              # NLP + Gemini merge, caching
│   │   │   ├── job_nlp_extraction.py          # rule-based JD extraction
│   │   │   ├── job_gemini_extraction.py       # Gemini client and JD extraction
│   │   │   ├── resume_text_extraction.py      # PDF/DOCX text and links
│   │   │   ├── resume_information_extraction.py  # Gemini + fallback parsing
│   │   │   ├── resume_processing.py           # save, duplicate detection
│   │   │   ├── resume_matching.py             # scoring and matching engine
│   │   │   ├── batch_matching.py              # parallel batch matching
│   │   │   └── candidate_results.py           # ranking and match details
│   │   └── main.py          # app, CORS, router registration
│   ├── requirements.txt
│   ├── .env.example
│   └── test_*.py, verify_performance.py
└── frontend/
    └── src/
        ├── pages/           # AddJob, UploadResumes, CandidateMatching
        ├── services/api.js  # Axios client
        └── App.jsx          # dashboard and navigation
```

---

## Local Setup

**Prerequisites:** Python 3.10+, Node.js 20+, a PostgreSQL database, and a Gemini API key from [Google AI Studio](https://aistudio.google.com/).

### Backend

```bash
git clone https://github.com/manikanta2008/AI-Based-Resume-Matching-Ranking-System.git
cd AI-Based-Resume-Matching-Ranking-System/backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then fill in the values
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000` and the docs at `http://127.0.0.1:8000/docs`. Tables are created automatically on first start.

### Frontend

```bash
cd ../frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`. By default it calls `http://127.0.0.1:8000`. To use another backend, set `VITE_API_URL`.

### Typical workflow

1. **Job Descriptions:** paste or upload a JD, review the extracted skills, and confirm.
2. **Upload Resumes:** upload PDF or DOCX files.
3. **Candidate Matching:** choose a job, run matching, and review the ranked candidates and their score breakdowns.

---

## Environment Variables

**Backend** (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string, for example `postgresql+psycopg://user:password@host:5432/dbname` |
| `GEMINI_API_KEY` | Recommended | Enables AI extraction and matching. Without it the fallback engines are used |
| `GEMINI_MODEL` | No | Gemini model name. Default `gemini-2.0-flash` |
| `CORS_ORIGINS` | No | Extra allowed frontend origins, comma-separated. Local dev origins and `*.vercel.app` are allowed by default |
| `SQL_ECHO` | No | Set to `true` to log SQL statements |

**Frontend**

| Variable | Description |
|---|---|
| `VITE_API_URL` | Base URL of the backend API |

Never commit `.env` files, API keys, or database passwords. `.env` is already listed in `.gitignore`.

---

## Deployment

### Backend on Render

- **Root directory:** `backend`
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment variables:** `DATABASE_URL`, `GEMINI_API_KEY`, and optionally `CORS_ORIGINS`
- `python-multipart` must be listed in `requirements.txt`. FastAPI needs it for file uploads, and the app will not start without it.
- On the free plan the service sleeps when idle, so the first request after inactivity can take around 30 seconds.

### Frontend on Vercel

- **Root directory:** `frontend`
- **Framework preset:** Vite
- **Environment variable:** `VITE_API_URL` set to the Render backend URL

---

## Design Decisions

- **Hybrid extraction (rules plus LLM).** Rules are fast and free but limited to a fixed dictionary. The LLM understands context but can fail or be rate-limited. Combining them gives accuracy when the API is up and a working result when it is not.
- **Fixed weights, LLM-assigned sub-scores.** The model judges each dimension, but the final formula is plain code. The weighting is therefore transparent, auditable, and consistent across candidates.
- **Evidence-based prompting.** The model is told to use only what is in the resume and to separate explicit evidence from inference. This reduces inflated scores from keywords that only appear in the job description.
- **Store everything needed to explain a score.** The full breakdown is saved with each match, so rankings are explainable and can be re-displayed without calling the model again.
- **Parallelism with isolated sessions.** Resume uploads and matching use thread pools, and each worker has its own database session to avoid sharing state across threads.
- **Idempotent writes.** Unique constraints and duplicate checks mean repeating an upload or a match updates records instead of piling up copies.

---

## Limitations and Future Work

- **Skill dictionary is small.** The rule-based job and resume extractors recognize 29 technologies. Skills outside the list are only caught when Gemini is available.
- **Semantic score is LLM-judged.** The system does not use vector embeddings. Adding embedding similarity (for example sentence transformers with pgvector) would make the semantic score reproducible and cheaper.
- **Fallback is approximate.** The rule-based engine measures skill overlap and keyword presence. Its education check does not compare against the job's stated requirement, and its overall explanation text is generic.
- **Scanned PDFs are not supported.** Text extraction needs a text layer. OCR would be required for image-only resumes.
- **No authentication.** The API is open. Recruiter accounts and per-user data would be needed before production use.
- **Possible bias.** LLM-based scoring can reflect biases in its training data. Scores should support, not replace, human review. The candidate's name is currently included in the model input, and removing it (blind screening) would be a straightforward improvement.
- **Ideas:** configurable weights per job, background job queue for large batches, OCR, embedding-based matching, exportable shortlist reports, and automated tests with sample resumes.

---

## Author

**Manikanta Repaka**

- GitHub: https://github.com/manikanta2008
- LinkedIn: https://www.linkedin.com/in/mani-kanta-repaka/
- Portfolio: https://manikanta-portfolio-ten.vercel.app/
