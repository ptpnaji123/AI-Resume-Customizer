import re
from ollama import chat
from ai_engine.validate_resume import validate_resume_content

MODEL_NAME = "mistral"
MAX_ATTEMPTS = 3


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT CLEANER
# ─────────────────────────────────────────────────────────────────────────────

def clean_llm_output(text):
    """
    Strip meta-commentary, placeholder text, category annotations,
    structural errors, and JD requirement text from LLM output.
    """
    # Remove inline category annotations like (AI/ML & Visualization)
    text = re.sub(r'\s*\([A-Za-z/&\s,\-]+\)\s*$', '', text, flags=re.MULTILINE)

    # Remove (New bullet N...) style comments
    text = re.sub(r'\s*\(New bullet\s*\d+[^)]*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\(Bullet\s*\d+\)',            '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\(bullet\s*\d+\)',            '', text, flags=re.IGNORECASE)

    # Remove leaked prompt example lines
    text = re.sub(r"^.*Specific new project title.*$",  '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^.*e\.g\.\s*[\"'].*[\"'].*$",      '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^.*\(e\.g\..*\).*$",               '', text, flags=re.IGNORECASE | re.MULTILINE)

    # Remove square-bracket placeholders
    text = re.sub(r'\[New JD[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[[^\]]{3,80}\]',  '', text)

    # Merge ---PROJECTS (NEW)--- into ---PROJECTS---
    text = re.sub(r'---PROJECTS\s*\(NEW\)---', '', text, flags=re.IGNORECASE)
    text = re.sub(r'---PROJECTS\s+NEW---',     '', text, flags=re.IGNORECASE)

    # Fix COMPANY line with role/duration all on same line (3 pipe-separated parts)
    def fix_company_three_part(m):
        parts = [p.strip() for p in m.group(1).split('|')]
        if len(parts) >= 3:
            return f"COMPANY: {parts[0]}\nROLE: {parts[1]} | {parts[2]}"
        return m.group(0)

    text = re.sub(
        r'^COMPANY:\s*(.+\|.+\|.+)$',
        fix_company_three_part,
        text,
        flags=re.MULTILINE
    )

    # Fix COMPANY line with no | separator — inject ROLE: on next line if missing
    lines_in = text.split('\n')
    for idx, line in enumerate(lines_in):
        if line.strip().upper().startswith('COMPANY:') and '|' not in line:
            for j in range(idx + 1, min(idx + 3, len(lines_in))):
                nxt = lines_in[j].strip()
                if not nxt:
                    continue
                already_has_role = nxt.upper().startswith('ROLE:')
                looks_like_role  = bool(re.search(
                    r'.+\|\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec'
                    r'|January|February|March|April|May|June|July|August|September'
                    r'|October|November|December|Present)\s*',
                    nxt, re.I
                ))
                if looks_like_role and not already_has_role:
                    lines_in[j] = 'ROLE: ' + nxt
                break
    text = '\n'.join(lines_in)

    # Clean JD requirement lines from SKILLS section
    text = _clean_skills_section(text)

    # Remove lines that are just dashes or whitespace
    lines = [l.rstrip() for l in text.split('\n')]
    lines = [l for l in lines if l.strip() not in ('', '-', '--')]

    return '\n'.join(lines)


_JD_SKILL_PATTERNS = [
    r"bachelor'?s?\s+degree",
    r"master'?s?\s+degree",
    r"\d\+\s+years?\s+(of\s+)?(experience|design|architecture|development)",
    r"years?\s+of\s+experience",
    r"non-internship",
    r"design\s+or\s+architecture\s+\(design\s+patterns",
    r"design\s+patterns,?\s+reliability\s+and\s+scaling",
    r"full\s+software\s+development\s+life\s+cycle",
    r"source\s+control\s+management",
    r"build\s+processes",
    r"video\s+games\s+industry\s+experience",
    r"supporting\s+title\s+development",
    r"design\s+or\s+architecture\s+experience",
    r"software\s+development\s+life\s+cycle\s+experience",
]


def _clean_skills_section(text):
    """Remove JD requirement lines from the SKILLS section only."""
    if '---SKILLS---' not in text:
        return text

    before_skills    = text.split('---SKILLS---')[0] + '---SKILLS---\n'
    skills_and_after = text.split('---SKILLS---', 1)[1]

    next_section = re.search(r'\n---[A-Z]+---', skills_and_after)
    if next_section:
        skills_text = skills_and_after[:next_section.start()]
        after_text  = skills_and_after[next_section.start():]
    else:
        skills_text = skills_and_after
        after_text  = ''

    cleaned_lines = []
    for line in skills_text.split('\n'):
        line_lower = line.lower().strip()
        is_jd_req  = any(re.search(pat, line_lower) for pat in _JD_SKILL_PATTERNS)
        if not is_jd_req:
            cleaned_lines.append(line)

    return before_skills + '\n'.join(cleaned_lines) + after_text


def fix_section_markers(text):
    """Normalise section markers so the parser can find them reliably."""
    text = re.sub(r'---\s*HEADER\s*---',      '---HEADER---',      text, flags=re.IGNORECASE)
    text = re.sub(r'---\s*SUMMARY\s*---',     '---SUMMARY---',     text, flags=re.IGNORECASE)
    text = re.sub(r'---\s*EXPERIENCE\s*---',  '---EXPERIENCE---',  text, flags=re.IGNORECASE)
    text = re.sub(r'---\s*PROJECTS?\s*---',   '---PROJECTS---',    text, flags=re.IGNORECASE)
    text = re.sub(r'---\s*EDUCATION\s*---',   '---EDUCATION---',   text, flags=re.IGNORECASE)
    text = re.sub(r'---\s*SKILLS\s*---',      '---SKILLS---',      text, flags=re.IGNORECASE)
    return text


def has_placeholder_title(text):
    """Return True if a project title still contains leaked example text."""
    bad_patterns = [
        r'specific new project', r'e\.g\.', r'\[.*\]',
        r'ml-based fraud', r'threat detection pipeline',
    ]
    for pat in bad_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# HEADLINE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_headline(resume_text, job_title, jd_skills):
    """
    Pick 4 headline items:
    - 2 strongest skills from the candidate's existing resume
    - 2 most relevant skills from the job description

    Returns a list of exactly 4 strings.
    """
    jd_skills_str = ", ".join(jd_skills[:15])

    prompt = f"""
You are a resume consultant. Select exactly 4 skill labels for the headline of a resume.

RULES:
- Pick the 2 STRONGEST skills from the candidate's resume (the ones they are most expert in)
- Pick the 2 MOST RELEVANT skills for the job title: "{job_title}"
- Each item must be SHORT: 1-4 words only (e.g. "Machine Learning", "Python", "Android Development")
- Items must be specific skills or technologies, NOT job titles or soft skills
- Do NOT repeat the same skill twice

CANDIDATE RESUME TEXT:
{resume_text[:2000]}

JOB DESCRIPTION SKILLS:
{jd_skills_str}

Output EXACTLY 4 lines, one skill per line, nothing else:
Line 1: [strongest resume skill 1]
Line 2: [strongest resume skill 2]
Line 3: [most relevant JD skill 1]
Line 4: [most relevant JD skill 2]
"""
    response = chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    raw = response["message"]["content"].strip()

    # Parse — accept "Line N: skill" format or plain lines
    skills = []
    for line in raw.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Strip "Line N:" prefix if present
        line = re.sub(r'^Line\s*\d+\s*:\s*', '', line, flags=re.IGNORECASE)
        # Strip leading bullets or numbers
        line = re.sub(r'^[-•*\d.)\s]+', '', line).strip()
        # Strip surrounding brackets
        line = line.strip('[]')
        if line and len(line) > 1:
            skills.append(line)

    # Ensure exactly 4 items
    skills = skills[:4]
    while len(skills) < 4:
        skills.append(jd_skills[len(skills)] if len(jd_skills) > len(skills) else "Software Development")

    return skills


# ─────────────────────────────────────────────────────────────────────────────
# JD DOMAIN SKILLS GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_jd_domain_skills(job_title, jd_skills, jd_responsibilities, existing_skills_text):
    """
    Ask LLM to generate a list of specific technical skills relevant to the JD domain
    that are NOT already in the candidate's resume.

    Returns a formatted skill category string like:
    "Android Development: Kotlin, Jetpack Compose, Retrofit, Dagger/Hilt, Room DB"
    """
    jd_skills_str   = ", ".join(jd_skills[:15])
    resp_str        = "\n".join(f"- {r}" for r in jd_responsibilities[:6])

    prompt = f"""
You are a senior technical recruiter. Generate a list of specific technical skills for a resume.

The candidate is applying for: "{job_title}"

EXISTING SKILLS (do NOT repeat these):
{existing_skills_text}

JD REQUIRED SKILLS: {jd_skills_str}

JD RESPONSIBILITIES:
{resp_str}

Task:
1. Identify the primary technical domain of this job (e.g. "Android Development", "Data Engineering", etc.)
2. List 6-10 specific technical skills/tools from that domain that are commonly needed for this role
3. Only include skills that do NOT already appear in the existing skills above
4. Skills must be real, specific tool/technology names — not soft skills or degree requirements

Output ONLY this exact format, nothing else:
CATEGORY: <domain name only — e.g. "Android Development" or "Cloud Infrastructure", NO trailing word "Skills">
SKILLS: <skill1>, <skill2>, <skill3>, <skill4>, <skill5>, <skill6>
"""
    response = chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    raw = response["message"]["content"].strip()

    category = "Additional Technical Skills"
    skills   = []

    for line in raw.split('\n'):
        line = line.strip()
        if line.upper().startswith('CATEGORY:'):
            category = line.replace('CATEGORY:', '').strip()
            # Strip trailing "Skills" word if LLM added it despite instructions
            category = re.sub(r'\s+Skills\s*$', '', category, flags=re.IGNORECASE).strip()
        elif line.upper().startswith('SKILLS:'):
            skills_str = line.replace('SKILLS:', '').strip()
            skills = [s.strip() for s in skills_str.split(',') if s.strip()]

    if not skills:
        return None

    return f"{category}: {', '.join(skills)}"


# ─────────────────────────────────────────────────────────────────────────────
# RESUME CONTENT INVENTORY
# ─────────────────────────────────────────────────────────────────────────────

def extract_inventory_from_raw_text(resume_text):
    """Use LLM to extract structured inventory from raw PDF resume text."""
    prompt = f"""
Extract the following from this resume text. Copy values exactly as they appear.

RESUME TEXT:
{resume_text}

Output ONLY this exact format — no explanations, no extra text:

NAME: <full name>
EMAIL: <email>
PHONE: <phone>
LINKEDIN: <full linkedin url, or leave blank>
GITHUB: <full github url, or leave blank>

TOP_SKILLS:
- <most prominent skill 1>
- <most prominent skill 2>

COMPANIES:
- <Company 1 name> | <location> | <role> | <duration>
- <Company 2 name> | <location> | <role> | <duration>

PROJECTS:
- <Project 1 exact title>
- <Project 2 exact title>
- <Project 3 exact title>
- <Project 4 exact title>

EDUCATION:
- <degree> | <year range> | <school> | <university>

SKILLS:
- <skill category line 1>
- <skill category line 2>
"""
    response = chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"].strip()


def parse_inventory_output(inventory_text):
    """
    Parse structured inventory string.
    Returns {'companies': [...], 'projects': [...]} with no rule text.
    """
    companies       = []
    projects        = []
    current_section = None

    for line in inventory_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith('COMPANIES:'):
            current_section = 'companies'
            continue
        elif line.upper().startswith('PROJECTS:'):
            current_section = 'projects'
            continue
        elif re.match(r'^(NAME|EMAIL|PHONE|LINKEDIN|GITHUB|TOP_SKILLS|EDUCATION|SKILLS):', line, re.I):
            current_section = None
            continue

        if current_section and line.startswith('-'):
            value = line.lstrip('-').strip()
            if not value or value.lower() in ('leave blank', '<leave blank>', 'none', 'n/a'):
                continue
            if any(kw in value.lower() for kw in [
                'must appear', 'must be copied', 'do not drop',
                'original bullets', 'every company', 'every project'
            ]):
                continue

            if current_section == 'companies':
                company_name = value.split('|')[0].strip()
                if company_name:
                    companies.append(company_name)
            elif current_section == 'projects':
                if value:
                    projects.append(value)

    return {'companies': companies, 'projects': projects}


def build_content_inventory(resume_text):
    """Build hard-constraint inventory string for the main resume prompt."""
    extracted = extract_inventory_from_raw_text(resume_text)
    return f"""
=== MANDATORY CONTENT — EVERY ITEM BELOW MUST APPEAR IN THE OUTPUT ===

{extracted}

PRESERVATION RULES:
- Every company listed under COMPANIES must appear in ---EXPERIENCE--- with ALL original bullets
- Every project listed under PROJECTS must appear in ---PROJECTS--- with original bullets
- Name, email, phone, LinkedIn, GitHub must be copied exactly
- Do NOT drop, merge, shorten, or skip any item

=== END MANDATORY CONTENT ===
"""


def get_known_companies_and_projects(resume_text):
    """Public helper for app.py. Returns clean dict with no rule text."""
    raw = extract_inventory_from_raw_text(resume_text)
    return parse_inventory_output(raw)


# ─────────────────────────────────────────────────────────────────────────────
# FORMAT VERIFIER
# ─────────────────────────────────────────────────────────────────────────────

def verify_resume_format(resume_text, candidate_name):
    """
    Ask LLM to verify the resume text for formatting issues.
    Returns {'passed': bool, 'issues': [str], 'summary': str}
    """
    prompt = f"""
You are a resume quality checker. Review the resume text below for these issues:

1. Does the resume start with the candidate's full name "{candidate_name}"?
2. Are contact details (email, phone) present and clean (no stray brackets)?
3. Is there a headline with 3-4 skill items separated by |?
4. Is there a PROFILE SUMMARY section with real content?
5. Does PROFESSIONAL EXPERIENCE show company names, roles, and bullet points?
6. Does PROJECTS show project titles with bullet points for each?
7. Does EDUCATION show degree and year?
8. Does SKILLS show technical skill categories only (no job requirements like "3+ years experience")?
9. Are there any placeholder texts like [bullet] or [Company Name] still present?
10. Are there any stray characters like lone ( or ) appearing mid-sentence?

RESUME TEXT:
{resume_text[:3000]}

Output ONLY this format:

PASSED: yes or no
ISSUES:
- <issue 1 if any, or write "none" if no issues>
SUMMARY: <one sentence overall assessment>
"""
    response = chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    raw = response["message"]["content"].strip()

    result = {'passed': False, 'issues': [], 'summary': ''}

    for line in raw.split('\n'):
        line = line.strip()
        if line.upper().startswith('PASSED:'):
            result['passed'] = 'yes' in line.lower()
        elif line.startswith('- ') and not line.upper().startswith('- NONE'):
            issue = line.lstrip('- ').strip()
            if issue:
                result['issues'].append(issue)
        elif line.upper().startswith('SUMMARY:'):
            result['summary'] = line.replace('SUMMARY:', '').strip()

    return result


# ─────────────────────────────────────────────────────────────────────────────
# NEW PROJECT TITLE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_new_project_title(job_title, jd_skills, jd_responsibilities):
    """Generate one specific realistic project title aligned with the JD domain."""
    skills_str = ", ".join(jd_skills[:10])
    resp_str   = "\n".join(f"- {r}" for r in jd_responsibilities[:5])

    prompt = f"""
You are a resume consultant. Suggest ONE specific realistic project title for a candidate
applying for the role: "{job_title}".

Rules:
- Must be directly relevant to: {job_title}
- Must be a real-sounding project a professional would build
- Must be concise: 4-8 words maximum
- Must NOT be generic like "ML Pipeline" or "Data System"
- Must reflect the actual domain of this job

JOB SKILLS: {skills_str}

JOB RESPONSIBILITIES:
{resp_str}

Output ONLY the project title on a single line. No quotes. No explanation.
"""
    response = chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    title    = response["message"]["content"].strip().strip('"\'')
    title    = re.sub(r'^(Project:|Title:)\s*', '', title, flags=re.IGNORECASE)
    return title.strip()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN GENERATION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def generate_tailored_resume(resume_text, jd_info):
    """Main function called by app.py."""
    skills_str           = "\n".join(f"- {s}" for s in jd_info.get("skills", []))
    job_title            = jd_info.get("job_title", "the position")
    keywords_str         = "\n".join(f"- {k}" for k in jd_info.get("keywords", []))
    responsibilities_str = "\n".join(
        f"- {r}" for r in jd_info.get("responsibilities", [])
    ) or "- Not specified"

    # ── Step 1: Content inventory ─────────────────────────────────────────────
    print("Extracting content inventory from resume...")
    content_inventory = build_content_inventory(resume_text)
    print(content_inventory)

    # ── Step 2: Generate headline (2 resume + 2 JD) ───────────────────────────
    print("Generating headline skills...")
    headline_skills = generate_headline(
        resume_text,
        job_title,
        jd_info.get("skills", [])
    )
    headline_str = " | ".join(headline_skills)
    print(f"Headline: {headline_str}")

    # ── Step 3: Generate domain-specific JD skills ────────────────────────────
    print("Generating JD domain skills...")
    # Pass existing skills from inventory as context to avoid duplication
    existing_skills = "\n".join(
        line for line in content_inventory.split('\n')
        if 'Programming' in line or 'AI/ML' in line or 'Tools' in line or 'Skills' in line
    )
    new_skill_category = generate_jd_domain_skills(
        job_title,
        jd_info.get("skills", []),
        jd_info.get("responsibilities", []),
        existing_skills or resume_text[:1000]
    )
    print(f"New skill category: {new_skill_category}")

    # ── Step 4: New project title ─────────────────────────────────────────────
    print("Generating new project title...")
    new_project_title = generate_new_project_title(
        job_title, jd_info.get("skills", []), jd_info.get("responsibilities", [])
    )
    print(f"New project title: {new_project_title}")

    if has_placeholder_title(new_project_title) or len(new_project_title) < 5:
        new_project_title = f"{job_title} Workflow Tool"

    # Build skills instruction for prompt
    skills_instruction = ""
    if new_skill_category:
        skills_instruction = f"""
ADD THIS NEW SKILL CATEGORY to the SKILLS section (copy exactly):
{new_skill_category}
"""

    # ── Step 5: Main generation prompt ───────────────────────────────────────
    base_prompt = f"""
You are an expert resume writer. Produce a tailored full-page resume for:
JOB TITLE: {job_title}

════════════════════════════════════════════════
TASK 1 — PRESERVE EVERYTHING (non-negotiable)
════════════════════════════════════════════════
- Include EVERY company from MANDATORY CONTENT with ALL original bullet points
- Include EVERY project from MANDATORY CONTENT with their original bullets
- Copy name, email, phone, LinkedIn, GitHub exactly as given
- Do NOT shorten, merge, or remove any existing bullet

════════════════════════════════════════════════
TASK 2 — ENHANCE (add only, never remove)
════════════════════════════════════════════════
- Reword existing bullets to naturally include JD keywords
- Add exactly 2 new bullets per job referencing JD responsibilities
- Add new project: {new_project_title}
  Write 4 specific realistic bullets using JD skills
- Write 4-5 sentence SUMMARY targeting {job_title}

{content_inventory}

JD SKILLS:
{skills_str}

JD RESPONSIBILITIES:
{responsibilities_str}

JD KEYWORDS:
{keywords_str}

════════════════════════════════════════════════
STRICT OUTPUT FORMAT
════════════════════════════════════════════════

---HEADER---
[Full Name]
[email] | [phone]
[linkedin url] | [github url]
{headline_str}

---SUMMARY---
[4-5 sentences]

---EXPERIENCE---
COMPANY: [Company Name] | [Location]
ROLE: [Job Title] | [Duration]
- [bullet]
- [bullet]
- [new JD-aligned bullet 1]
- [new JD-aligned bullet 2]

COMPANY: [Company Name] | [Location]
ROLE: [Job Title] | [Duration]
- [bullet]
- [new JD-aligned bullet 1]
- [new JD-aligned bullet 2]

---PROJECTS---
PROJECT: [Exact title from MANDATORY CONTENT]
- [bullet]
- [bullet]

PROJECT: [Exact title from MANDATORY CONTENT]
- [bullet]

PROJECT: [Exact title from MANDATORY CONTENT]
- [bullet]

PROJECT: [Exact title from MANDATORY CONTENT]
- [bullet]

PROJECT: {new_project_title}
- [bullet using JD skill]
- [bullet using JD skill]
- [bullet using JD skill]
- [bullet using JD skill]

---EDUCATION---
[Degree] | [Year]
[School]
[University]

---SKILLS---
[Existing skill category 1 from resume]
[Existing skill category 2 from resume]
{new_skill_category if new_skill_category else "[Add relevant technical skills from JD domain]"}

════════════════════════════════════════════════
HEADLINE INSTRUCTION — CRITICAL
════════════════════════════════════════════════
The headline line in ---HEADER--- must be EXACTLY this — copy it word for word:
{headline_str}

Do NOT change it. Do NOT add more items. Do NOT use dashes.

════════════════════════════════════════════════
SKILLS INSTRUCTION — CRITICAL
════════════════════════════════════════════════
{skills_instruction}
SKILLS section must contain ONLY technical skill names and tools.
Do NOT include: degree requirements, years of experience, "Design or Architecture Experience",
"Software Development Life Cycle Experience", "Video Games Industry experience",
or any phrase describing job requirements rather than actual tool/technology names.

════════════════════════════════════════════════
RULES YOU MUST FOLLOW
════════════════════════════════════════════════
1. Output starts with ---HEADER--- — nothing before it
2. Use ONLY 6 markers: ---HEADER--- ---SUMMARY--- ---EXPERIENCE--- ---PROJECTS--- ---EDUCATION--- ---SKILLS---
3. ALL projects go in ONE ---PROJECTS--- section using PROJECT: prefix
4. COMPANY: Name | Location only  /  ROLE: Title | Duration only
5. Headline is already provided above — use it exactly, do not modify
6. SKILLS: tool/technology names only, no requirement phrases
7. No parenthetical labels at end of bullets
8. If LinkedIn or GitHub URL is not available, omit that line
9. Minimum 450 words
"""

    last_output = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": base_prompt}]
        )

        resume_output = response["message"]["content"]

        if "---HEADER---" in resume_output:
            resume_output = resume_output[resume_output.index("---HEADER---"):]

        resume_output = fix_section_markers(resume_output)
        resume_output = clean_llm_output(resume_output)
        last_output   = resume_output

        validation = validate_resume_content(resume_output, jd_info)

        if validation["valid"]:
            print(f"Resume validated on attempt {attempt}")
            return resume_output

        print(f"Attempt {attempt} failed:")
        for err in validation["errors"]:
            print(f"  - {err}")

        base_prompt += f"""

ATTEMPT {attempt} FAILED. Fix ALL errors:
{chr(10).join(f"- {e}" for e in validation["errors"])}

REMINDERS:
- Headline must be exactly: {headline_str}
- COMPANY: Name | Location only (no role/date on this line)
- ROLE: Title | Duration (always use ROLE: prefix)
- SKILLS: tool names only, no requirement descriptions
- All projects in ONE ---PROJECTS--- section
Output complete resume from ---HEADER---.
"""

    raise ValueError(
        f"Resume generation failed after {MAX_ATTEMPTS} attempts.\n\nLast output:\n{last_output}"
    )