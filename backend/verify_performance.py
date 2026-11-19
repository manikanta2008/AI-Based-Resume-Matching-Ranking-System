import os
import sys
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.job_processing import process_job_description
from app.services.job_nlp_extraction import extract_job_details
from app.services.resume_text_extraction import (
    extract_resume_content,
    extract_resume_text,
    extract_resume_links
)
from app.services.resume_information_extraction import (
    extract_resume_information,
    extract_resume_information_fallback
)
from app.services.resume_matching import (
    evaluate_resume_fallback,
    calculate_matching_score
)

SAMPLE_JD = """Job Title: Senior Java & React Full Stack Developer
Location: Remote / Hybrid
Experience Required: 4 - 7 years
Education: Bachelor's degree in Computer Science, Engineering or related technical field.

About the Role:
We are seeking an experienced Senior Full Stack Developer to build high-performance cloud applications.

Responsibilities:
- Build and maintain microservices using Java and Spring Boot.
- Create dynamic, responsive frontends with React, TypeScript, and HTML/CSS.
- Design database schemas and optimize queries in PostgreSQL and SQL.
- Implement containerization with Docker and Kubernetes on AWS.

Required Skills:
- Java, Spring Boot, Microservices
- React, JavaScript, TypeScript, HTML, CSS
- PostgreSQL, SQL, Docker, Git

Preferred Skills:
- AWS, Kubernetes, Python, Redis, CI/CD
"""

def test_jd_extraction():
    print("\n--- 1. Testing Job Description Extraction ---")
    
    # 1.1 Pure NLP Extraction Speed
    t0 = time.perf_counter()
    nlp_res = extract_job_details(SAMPLE_JD)
    t_nlp = (time.perf_counter() - t0) * 1000
    print(f"NLP Extraction Time: {t_nlp:.2f} ms")
    print(f"  Title: {nlp_res['title']}")
    print(f"  Experience: {nlp_res['min_experience']} - {nlp_res['max_experience']} yrs")
    print(f"  Skills Found ({len(nlp_res['skills'])}): {[s['skill_name'] for s in nlp_res['skills']]}")

    # 1.2 Full Pipeline with use_gemini=False (Instant NLP mode)
    t0 = time.perf_counter()
    jd_obj = process_job_description(SAMPLE_JD, source_type="text", use_gemini=False)
    t_pipeline_nlp = (time.perf_counter() - t0) * 1000
    print(f"process_job_description (use_gemini=False): {t_pipeline_nlp:.2f} ms")

    # 1.3 Cached Lookup Speed
    t0 = time.perf_counter()
    cached_obj = process_job_description(SAMPLE_JD, source_type="text", use_gemini=False)
    t_cached = (time.perf_counter() - t0) * 1000
    print(f"process_job_description (Cache Hit): {t_cached:.4f} ms (Instant!)")

def test_resume_document_parsing():
    print("\n--- 2. Testing Resume Document Parsing (PDF I/O) ---")
    resume_dir = Path("test_resumes")
    pdf_files = list(resume_dir.glob("*.pdf"))
    if not pdf_files:
        print("No test PDFs found in test_resumes folder.")
        return []

    print(f"Found {len(pdf_files)} test resumes.")

    # 2.1 Measure Single-Pass Extraction (Unified text + links)
    timings = []
    parsed_resumes = []
    for pdf in pdf_files:
        raw_bytes = pdf.read_bytes()
        t0 = time.perf_counter()
        text, links = extract_resume_content(raw_bytes, pdf.name)
        dt = (time.perf_counter() - t0) * 1000
        timings.append(dt)
        parsed_resumes.append((pdf.name, raw_bytes, text, links))

    avg_parse_time = sum(timings) / len(timings)
    print(f"Single-Pass Parse Time (Average across {len(pdf_files)} PDFs): {avg_parse_time:.2f} ms")
    for name, dt in zip(pdf_files, timings):
        print(f"  {name.name}: {dt:.2f} ms")

    return parsed_resumes

def test_resume_information_extraction(parsed_resumes):
    print("\n--- 3. Testing Candidate Information Extraction ---")
    if not parsed_resumes:
        return

    name, raw_bytes, text, links = parsed_resumes[0]
    
    # 3.1 Fast Rule-Based Fallback
    t0 = time.perf_counter()
    extracted = extract_resume_information_fallback(text, links)
    dt_fb = (time.perf_counter() - t0) * 1000
    print(f"Candidate Extraction Fallback Time: {dt_fb:.2f} ms")
    print(f"  Candidate Name: {extracted['full_name']}")
    print(f"  Email: {extracted['email']}")
    print(f"  Phone: {extracted['phone']}")
    print(f"  Experience: {extracted['work_experience']} yrs")
    print(f"  Technical Skills ({len(extracted['technical_skills'])}): {extracted['technical_skills'][:6]}")

    # 3.2 Cached extraction test
    t0 = time.perf_counter()
    extract_resume_information(text, links)  # first run or fallback
    t0 = time.perf_counter()
    cached_cand = extract_resume_information(text, links)
    dt_cached = (time.perf_counter() - t0) * 1000
    print(f"Resume Information Extraction (Cache Hit): {dt_cached:.4f} ms")

def test_parallel_batch_processing(parsed_resumes):
    print("\n--- 4. Testing Parallel Batch Resume Processing ---")
    if not parsed_resumes:
        return

    def _worker(item):
        fname, bts, txt, lnks = item
        t0 = time.perf_counter()
        cand = extract_resume_information_fallback(txt, lnks)
        return fname, cand, (time.perf_counter() - t0) * 1000

    # Test sequential vs parallel
    # Sequential:
    t0 = time.perf_counter()
    seq_results = [_worker(item) for item in parsed_resumes]
    dt_seq = (time.perf_counter() - t0) * 1000

    # Parallel (ThreadPoolExecutor with 6 workers):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(6, len(parsed_resumes))) as ex:
        par_results = list(ex.map(_worker, parsed_resumes))
    dt_par = (time.perf_counter() - t0) * 1000

    print(f"Processed {len(parsed_resumes)} resumes:")
    print(f"  Sequential processing: {dt_seq:.2f} ms")
    print(f"  Parallel processing:   {dt_par:.2f} ms")
    print(f"  Speedup: {dt_seq / max(dt_par, 0.001):.1f}x")

def test_candidate_matching():
    print("\n--- 5. Testing Candidate Matching Algorithm ---")
    job_data = {
        "job_title": "Senior Java Developer",
        "minimum_experience": 4,
        "maximum_experience": 7,
        "education_requirements": ["Bachelor"],
        "required_skills": ["Java", "Spring Boot", "SQL", "PostgreSQL", "Docker"],
        "preferred_skills": ["AWS", "Kubernetes", "React", "Kafka"],
        "keywords": ["java", "spring", "microservices", "sql"]
    }

    resume_data = {
        "candidate_name": "Manikanta Repaka",
        "work_experience": 5.0,
        "technical_skills": ["Java", "Spring Boot", "SQL", "PostgreSQL", "React", "Docker", "Python", "Git"],
        "soft_skills": ["Communication", "Problem Solving"],
        "education": [{"degree": "Bachelor of Technology", "field_of_study": "Computer Science"}],
        "resume_text": "Experienced software engineer with 5 years in Java, Spring Boot, SQL, PostgreSQL, Docker."
    }

    t0 = time.perf_counter()
    eval_result = evaluate_resume_fallback(job_data, resume_data)
    scores = calculate_matching_score(eval_result)
    dt = (time.perf_counter() - t0) * 1000

    print(f"Match Evaluation Time: {dt:.2f} ms")
    print(f"  Overall Match Score: {scores['overall_score']}%")
    print(f"  Matched Skills: {eval_result['required_skills']['matched'] + eval_result['preferred_skills']['matched']}")
    print(f"  Missing Skills: {eval_result['required_skills']['missing'] + eval_result['preferred_skills']['missing']}")
    print(f"  Experience Score: {scores['experience_score']}%")

if __name__ == "__main__":
    print("=" * 60)
    print("AI RESUME PARSER - PERFORMANCE VERIFICATION BENCHMARK")
    print("=" * 60)
    test_jd_extraction()
    parsed = test_resume_document_parsing()
    test_resume_information_extraction(parsed)
    test_parallel_batch_processing(parsed)
    test_candidate_matching()
    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETED SUCCESSFULLY!")
    print("=" * 60)
