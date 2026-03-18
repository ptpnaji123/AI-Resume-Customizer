import re


# Lines that look like preservation rules — must never be treated as project/company names
_RULE_PHRASES = [
    'must appear', 'must be copied', 'do not drop', 'original bullets',
    'every company', 'every project', 'do not merge', 'do not shorten',
]


def _is_rule_text(value):
    """Return True if the value looks like a preservation rule, not a real name."""
    v = value.lower()
    return any(phrase in v for phrase in _RULE_PHRASES)


def _safe_key(value, words=2):
    """Return first N words of value as a lowercase key for fuzzy matching."""
    if not value:
        return ''
    return ' '.join(value.split()[:words]).lower()


def validate_resume_content(resume_text, jd_info, min_words=180):
    """
    Validate the LLM-generated resume text.
    Intentionally lenient — the goal is to catch truly broken output,
    not penalise candidates whose background doesn't perfectly match the JD.
    """
    errors = []

    # ── 1. Word count ─────────────────────────────────────────────────────────
    words = re.findall(r"\b\w+\b", resume_text)
    if len(words) < min_words:
        errors.append(f"Only {len(words)} words (minimum {min_words})")

    # ── 2. Mandatory section markers present ──────────────────────────────────
    required_sections = [
        "---HEADER---",
        "---SUMMARY---",
        "---EXPERIENCE---",
        "---PROJECTS---",
        "---EDUCATION---",
        "---SKILLS---",
    ]
    for section in required_sections:
        if section not in resume_text:
            errors.append(f"Missing section: {section}")

    # Stop early if sections missing — other checks will false-fire
    if errors:
        return {"valid": False, "errors": errors, "word_count": len(words)}

    # ── 3. Extract sections ───────────────────────────────────────────────────
    exp_section    = resume_text.split("---EXPERIENCE---")[-1].split("---PROJECTS---")[0]
    proj_section   = resume_text.split("---PROJECTS---")[-1].split("---EDUCATION---")[0]
    skills_section = resume_text.split("---SKILLS---")[-1]

    # ── 4. Known companies preserved ─────────────────────────────────────────
    # Only check if we have valid company names (not rule text)
    known_companies = [
        c for c in jd_info.get("known_companies", [])
        if c and not _is_rule_text(c) and len(c.split()) >= 1
    ]
    for company in known_companies:
        key = _safe_key(company, words=2)
        if key and key not in exp_section.lower():
            errors.append(f"Company missing from experience: '{company}'")

    # ── 5. Known projects preserved ───────────────────────────────────────────
    known_projects = [
        p for p in jd_info.get("known_projects", [])
        if p and not _is_rule_text(p) and len(p.split()) >= 1
    ]
    for proj in known_projects:
        key = _safe_key(proj, words=3)
        if key and key not in resume_text.lower():
            errors.append(f"Project missing: '{proj}'")

    # ── 6. Minimum bullets in experience ──────────────────────────────────────
    exp_bullets = [
        l for l in exp_section.split('\n')
        if re.match(r'^\s*[-•*\u2022]', l)
    ]
    if len(exp_bullets) < 3:
        errors.append(f"Only {len(exp_bullets)} experience bullets (minimum 3)")

    # ── 7. Minimum 2 distinct projects ────────────────────────────────────────
    proj_title_count = len(re.findall(r'(?i)^PROJECT:', proj_section, re.MULTILINE))
    if proj_title_count == 0:
        # Fallback: count non-bullet lines as project titles
        proj_lines = [l.strip() for l in proj_section.split('\n') if l.strip()]
        proj_title_count = sum(
            1 for l in proj_lines
            if not re.match(r'^[-•*\u2022\d]', l)
            and len(l) > 5
            and not l.startswith('---')
        )
    if proj_title_count < 2:
        errors.append(f"Only {proj_title_count} projects detected (minimum 2)")

    # NOTE: Deliberately NOT checking JD skills coverage in SKILLS section.
    # Candidates often apply for roles where they don't yet have all listed skills.
    # Failing generation because skills don't match JD defeats the purpose.

    # NOTE: Deliberately NOT checking project-JD-skill alignment.
    # Same reason — the new project handles this, existing ones don't need to match.

    return {
        "valid":      len(errors) == 0,
        "errors":     errors,
        "word_count": len(words),
    }