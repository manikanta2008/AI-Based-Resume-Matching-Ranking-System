from pathlib import Path
import json

from app.services.resume_text_extraction import (
    extract_resume_text,
    extract_resume_links
)

from app.services.resume_information_extraction import (
    extract_resume_information
)


# Find resume files
resume_folder = Path("test_resumes")

resume_files = list(resume_folder.glob("*.pdf"))

if not resume_files:
    raise FileNotFoundError("No PDF resumes found.")

resume_file = resume_files[0]

file_bytes = resume_file.read_bytes()


# Extract resume text
resume_text = extract_resume_text(
    file_bytes,
    resume_file.name
)


# Extract professional hyperlinks
professional_links = extract_resume_links(
    file_bytes,
    resume_file.name
)


# Extract candidate information using Gemini
extracted_data = extract_resume_information(
    resume_text,
    professional_links
)


# Display final result
print("\n================================")
print("COMPLETE RESUME INFORMATION")
print("================================")

print(
    json.dumps(
        extracted_data,
        indent=4,
        ensure_ascii=False
    )
)