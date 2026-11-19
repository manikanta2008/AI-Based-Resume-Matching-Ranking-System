import re
from pathlib import Path
from io import BytesIO

from pypdf import PdfReader
from docx import Document


# ==========================================
# 1. CLEAN EXTRACTED TEXT
# ==========================================

def clean_jd_text(text: str) -> str:

    if not text or not text.strip():
        raise ValueError("Job description is empty.")

    # Remove unnecessary whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ==========================================
# 2. EXTRACT TEXT FROM PDF
# ==========================================

def extract_text_from_pdf(file_content: bytes) -> str:

    try:

        pdf_file = BytesIO(file_content)

        reader = PdfReader(pdf_file)

        extracted_text = []

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:
                extracted_text.append(page_text)

        text = "\n".join(extracted_text)

        if not text.strip():
            raise ValueError(
                "No readable text found in PDF. "
                "The PDF may require OCR."
            )

        return clean_jd_text(text)

    except Exception as e:

        raise ValueError(
            f"PDF extraction failed: {str(e)}"
        )


# ==========================================
# 3. EXTRACT TEXT FROM DOCX
# ==========================================

def extract_text_from_docx(file_content: bytes) -> str:

    try:

        docx_file = BytesIO(file_content)

        document = Document(docx_file)

        extracted_text = []

        # Extract paragraphs
        for paragraph in document.paragraphs:

            if paragraph.text.strip():
                extracted_text.append(paragraph.text)

        # Extract table content
        for table in document.tables:

            for row in table.rows:

                row_text = [
                    cell.text.strip()
                    for cell in row.cells
                ]

                extracted_text.append(
                    " | ".join(row_text)
                )

        text = "\n".join(extracted_text)

        if not text.strip():
            raise ValueError(
                "No readable text found in DOCX."
            )

        return clean_jd_text(text)

    except Exception as e:

        raise ValueError(
            f"DOCX extraction failed: {str(e)}"
        )


# ==========================================
# 4. PROCESS PASTED JD
# ==========================================

def extract_text_from_input(jd_text: str) -> str:

    if not jd_text or not jd_text.strip():

        raise ValueError(
            "Please provide a valid job description."
        )

    return clean_jd_text(jd_text)


# ==========================================
# 5. PROCESS UPLOADED JD
# ==========================================

def extract_text_from_file(
    filename: str,
    file_content: bytes
) -> str:

    if not filename or not file_content:

        raise ValueError(
            "Invalid file or empty file."
        )

    extension = Path(filename).suffix.lower()

    if extension == ".pdf":

        return extract_text_from_pdf(file_content)

    elif extension == ".docx":

        return extract_text_from_docx(file_content)

    else:

        raise ValueError(
            "Unsupported file format. "
            "Please upload PDF or DOCX."
        )
