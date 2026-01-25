from ollama import chat
from generator.generate_docx import generate_resume_docx
from generator.convert_to_pdf import convert_docx_to_pdf

MODEL_NAME = "mistral"


def generate_tailored_resume(resume_text, jd_info):
    skills_str = ", ".join(jd_info.get("skills", []))
    keywords_str = ", ".join(jd_info.get("keywords", []))

    prompt = f"""
You are an expert resume writer.

Here is the original resume:
{resume_text[:2000]}

Job Requirements:
Skills: {skills_str}
Keywords: {keywords_str}

Rewrite the resume to tailor it for this job:
- Keep all real experiences, do NOT invent anything
- Highlight skills relevant to the job
- Use clear, professional language
- Make it ATS-friendly
- Output plain text only
"""

    response = chat(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response["message"]["content"]


if __name__ == "__main__":
    import sys
    import os

    # Allow imports from project root
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from resume_parser.parse_resume import parse_resume
    from jd_parser.extract_requirements import extract_skills_and_keywords

    # -------------------------------
    # Paths
    # -------------------------------
    resume_path = "data/input_resume/sample_resume.pdf"
    jd_path = "data/jd_raw/sample_jd.txt"

    output_docx = "outputs/tailored_resume.docx"
    output_pdf_dir = "outputs/pdf"

    os.makedirs("outputs", exist_ok=True)
    os.makedirs(output_pdf_dir, exist_ok=True)

    # -------------------------------
    # Load Resume
    # -------------------------------
    print("Parsing resume...")
    resume_text = parse_resume(resume_path)

    # -------------------------------
    # Load Job Description
    # -------------------------------
    print("Parsing job description...")
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()

    jd_info = extract_skills_and_keywords(jd_text)

    # -------------------------------
    # Generate Tailored Resume
    # -------------------------------
    print("Generating tailored resume using Mistral...\n")
    tailored_resume = generate_tailored_resume(resume_text, jd_info)

    print("----- GENERATED RESUME -----\n")
    print(tailored_resume)

    # -------------------------------
    # Save DOCX
    # -------------------------------
    print("\nSaving resume as DOCX...")
    generate_resume_docx(tailored_resume, output_docx)

    # -------------------------------
    # Convert to PDF
    # -------------------------------
    print("Converting DOCX to PDF...")
    convert_docx_to_pdf(output_docx, output_pdf_dir)

    print("\n✅ Resume generation complete!")
    print(f"DOCX: {output_docx}")
    print(f"PDF saved in: {output_pdf_dir}")
