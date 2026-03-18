from ollama import chat

MODEL_NAME = "mistral"


def extract_skills_and_keywords(jd_text):
    """
    Use LLM to extract structured information from raw job description text.
    Returns a dict with keys: job_title, skills, responsibilities, keywords,
    known_companies, known_projects.
    """
    prompt = f"""
You are a job description analyst. Extract information from the job description below.

JOB DESCRIPTION:
{jd_text[:4000]}

Output ONLY this exact format — no extra text, no explanations, no preamble:

JOB_TITLE: <exact job title from the posting>

SKILLS:
- <skill 1>
- <skill 2>
- <skill 3>
(list every technical skill, tool, technology, framework, or certification mentioned)

RESPONSIBILITIES:
- <responsibility 1>
- <responsibility 2>
- <responsibility 3>
(list the 8-10 most important responsibilities from the job posting)

KEY_KEYWORDS:
- <keyword 1>
- <keyword 2>
(list 10 important domain-specific keywords that appear in the JD)
"""

    response = chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    raw = response["message"]["content"].strip()

    # ── Parse LLM output ──────────────────────────────────────────────────────
    data = {
        "job_title":       "the position",
        "skills":          [],
        "responsibilities": [],
        "keywords":        [],
        "known_companies": [],   # populated later in app.py from parsed resume
        "known_projects":  [],   # populated later in app.py from parsed resume
    }

    current_section = None

    for line in raw.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Section headers
        if line.startswith("JOB_TITLE:"):
            title = line.replace("JOB_TITLE:", "").strip()
            if title:
                data["job_title"] = title
            current_section = None

        elif line.startswith("SKILLS:"):
            current_section = "skills"

        elif line.startswith("RESPONSIBILITIES:"):
            current_section = "responsibilities"

        elif line.startswith("KEY_KEYWORDS:"):
            current_section = "keywords"

        # Bullet items under current section
        elif line.startswith("-") and current_section:
            value = line.lstrip("-").strip()
            # Skip meta-lines like "(list every technical skill...)"
            if value and not value.startswith("("):
                data[current_section].append(value)

    return data


if __name__ == "__main__":
    import os

    sample_path = os.path.join("data", "jd_raw", "sample_jd.txt")

    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as f:
            jd_text = f.read()
    else:
        # Inline test if no file available
        jd_text = """
        Job Title: Data Science Analyst
        We are looking for a Data Science Analyst with experience in Python, SQL,
        machine learning, and data visualisation. The candidate should be proficient
        in Pandas, NumPy, Scikit-learn, and Power BI. Experience with cloud platforms
        such as AWS or Azure is a plus. Responsibilities include building predictive
        models, performing EDA, creating dashboards, and presenting insights to stakeholders.
        """

    result = extract_skills_and_keywords(jd_text)

    print("Job Title     :", result["job_title"])
    print("Skills        :", result["skills"])
    print("Responsibilities:", result["responsibilities"])
    print("Keywords      :", result["keywords"])