"""
ai_engine/cover_letter.py

Generates a professional 10-12 sentence cover letter from the tailored resume text
and the job description info dict.  No changes to any other file.
"""
import re
from ollama import chat

MODEL_NAME = "mistral"


def generate_cover_letter(tailored_resume_text, jd_info, candidate_name="", linkedin_url=""):
    """
    Generate a 10-12 sentence professional cover letter.

    Parameters
    ----------
    tailored_resume_text : str
        The full ---SECTION--- formatted resume text already generated.
    jd_info : dict
        The same jd_info dict used for resume generation.
        Expected keys: job_title, skills, responsibilities, keywords.
    candidate_name : str
        Candidate's full name (used in sign-off).
    linkedin_url : str
        Optional LinkedIn URL to include at the bottom.

    Returns
    -------
    dict with keys:
        'paragraphs' : list[str]  — 3 paragraphs ready for LaTeX rendering
        'name'       : str        — candidate name
        'email'      : str        — candidate email
        'phone'      : str        — candidate phone
        'linkedin'   : str        — linkedin url (may be empty)
        'job_title'  : str        — job title applied for
        'company'    : str        — company name (if found in JD info)
    """
    job_title   = jd_info.get("job_title",   "the position")
    skills_str  = ", ".join(jd_info.get("skills", [])[:8])
    resp_str    = "\n".join(f"- {r}" for r in jd_info.get("responsibilities", [])[:5])

    # Extract contact details from resume text
    email = phone = ""
    email_m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', tailored_resume_text)
    if email_m:
        email = email_m.group()

    phone_m = re.search(r'\+?[\d][\d\s\-]{8,}', tailored_resume_text)
    if phone_m:
        phone = re.sub(r'[\s\-\(\)\[\]]+$', '', phone_m.group()).strip()

    # Derive company name from job title context or jd keywords if possible
    company = jd_info.get("company", "")

    prompt = f"""
You are a professional cover letter writer. Write a cover letter for a job application.

CANDIDATE NAME: {candidate_name or "the candidate"}
JOB TITLE APPLYING FOR: {job_title}
COMPANY (if known): {company or "the company"}

CANDIDATE'S KEY SKILLS (from their resume):
{tailored_resume_text[tailored_resume_text.find('---SKILLS---'):tailored_resume_text.find('---SKILLS---')+600] if '---SKILLS---' in tailored_resume_text else skills_str}

CANDIDATE'S EXPERIENCE SUMMARY:
{tailored_resume_text[tailored_resume_text.find('---SUMMARY---'):tailored_resume_text.find('---SUMMARY---')+600] if '---SUMMARY---' in tailored_resume_text else ''}

JOB RESPONSIBILITIES:
{resp_str}

RULES:
- Write EXACTLY 3 paragraphs
- Total letter must be 10-12 sentences (split naturally across 3 paragraphs)
- Paragraph 1 (2-3 sentences): Opening — state the role, express enthusiasm, brief self-intro
- Paragraph 2 (5-6 sentences): Body — connect candidate's specific skills and experience to the job responsibilities. Be concrete and specific. Reference real skills from the resume.
- Paragraph 3 (2-3 sentences): Closing — express desire to discuss further, thank the reader, professional sign-off line
- Tone: professional, confident, human — NOT robotic or generic
- Do NOT use phrases like "I am writing to apply" or "Please find attached"
- Do NOT mention AI, LLM, or that this was generated
- Do NOT use bullet points — flowing prose only
- Each paragraph separated by a blank line

Output ONLY the 3 paragraphs of the letter body, nothing else.
No salutation, no "Dear Hiring Manager", no "Sincerely", no name at the end.
Just the 3 paragraphs.
"""

    response = chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    raw = response["message"]["content"].strip()

    # Split into paragraphs on blank lines
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', raw) if p.strip()]

    # Ensure we have exactly 3 — pad or trim if Mistral misbehaves
    while len(paragraphs) < 3:
        paragraphs.append(paragraphs[-1] if paragraphs else "")
    paragraphs = paragraphs[:3]

    return {
        "paragraphs": paragraphs,
        "name":       candidate_name,
        "email":      email,
        "phone":      phone,
        "linkedin":   linkedin_url,
        "job_title":  job_title,
        "company":    company,
    }