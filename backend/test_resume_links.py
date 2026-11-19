from pathlib import Path

from app.services.resume_text_extraction import (
    extract_resume_links
)


resume_folder = Path("test_resumes")

resume_files = list(resume_folder.glob("*.pdf"))

if not resume_files:
    raise FileNotFoundError("No PDF resumes found.")

resume_file = resume_files[0]

file_bytes = resume_file.read_bytes()

professional_links = extract_resume_links(
    file_bytes,
    resume_file.name
)

print("\n================================")
print("PROFESSIONAL LINK EXTRACTION")
print("================================")

for link_type, url in professional_links.items():

    print(f"{link_type}: {url}")

print("\nLink extraction completed!")