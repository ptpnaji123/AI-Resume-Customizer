import os
import pdfplumber
from docx import Document

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text


def parse_resume(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError("Resume file not found")

    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)

    elif file_path.lower().endswith(".docx"):
        return extract_text_from_docx(file_path)

    else:
        raise ValueError("Unsupported file format. Use PDF or DOCX.")


if __name__ == "__main__":
    # TEMP test (we will remove this later)
    resume_path = "data/input_resume/sample_resume.pdf"
    text = parse_resume(resume_path)
    print(text[:1000])  # print first 1000 characters

