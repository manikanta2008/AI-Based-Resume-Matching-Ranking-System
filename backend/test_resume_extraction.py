from pathlib import Path

from app.services.resume_text_extraction import (
    extract_resume_text
)


# ==========================================
# TEST RESUME EXTRACTION
# ==========================================

resume_folder = Path("test_resumes")

for resume_file in resume_folder.iterdir():

    if resume_file.suffix.lower() not in [".pdf", ".docx"]:
        continue

    print("\n================================")
    print("Testing:", resume_file.name)
    print("================================")

    try:

        file_bytes = resume_file.read_bytes()

        extracted_text = extract_resume_text(
            file_bytes,
            resume_file.name
        )

        print("\nExtracted Resume Content:\n")

        print(extracted_text[:2000])

        print("\nExtraction Successful!")

    except Exception as e:

        print("\nExtraction Failed:", str(e))