from pathlib import Path
from pypdf import PdfReader


# ==========================================
# SELECT RESUME
# ==========================================

resume_folder = Path("test_resumes")

pdf_files = list(resume_folder.glob("*.pdf"))

if not pdf_files:
    raise FileNotFoundError("No PDF resumes found.")

resume_file = pdf_files[0]

print("\nTesting:", resume_file.name)


# ==========================================
# READ PDF
# ==========================================

reader = PdfReader(str(resume_file))

extracted_links = []


# ==========================================
# EXTRACT CLICKABLE HYPERLINKS
# ==========================================

for page_number, page in enumerate(reader.pages, start=1):

    annotations = page.get("/Annots")

    if not annotations:
        continue

    for annotation_ref in annotations:

        annotation = annotation_ref.get_object()

        if annotation.get("/Subtype") == "/Link":

            action = annotation.get("/A")

            if action:

                url = action.get("/URI")

                if url:
                    extracted_links.append(str(url))


# ==========================================
# DISPLAY RESULTS
# ==========================================

print("\n================================")
print("PDF HYPERLINK EXTRACTION")
print("================================")

if extracted_links:

    for index, url in enumerate(extracted_links, start=1):
        print(f"{index}. {url}")

else:

    print("No clickable hyperlinks found in this PDF.")

print("\nTotal hyperlinks:", len(extracted_links))