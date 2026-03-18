import re
import subprocess
import os


# ─────────────────────────────────────────────────────────────────────────────
# LATEX CHARACTER ESCAPING
# ─────────────────────────────────────────────────────────────────────────────

def escape_latex(text):
    """Escape special LaTeX characters."""
    if not text:
        return ""
    text = text.replace('&',  r'\&')
    text = text.replace('%',  r'\%')
    text = text.replace('$',  r'\$')
    text = text.replace('#',  r'\#')
    text = text.replace('_',  r'\_')
    text = text.replace('{',  r'\{')
    text = text.replace('}',  r'\}')
    text = text.replace('~',  r'\textasciitilde{}')
    text = text.replace('^',  r'\textasciicircum{}')
    text = text.replace('\n', ' ')
    text = text.replace('\r', ' ')
    return text


def is_valid_url(url):
    """Return True only if value looks like a real URL."""
    if not url:
        return False
    url_lower = url.lower().strip()
    bad = {'empty', '<empty>', 'none', 'n/a', 'na', '-', 'not provided',
           'not available', 'null', 'undefined', 'blank', 'leave blank',
           '<leave blank>'}
    if url_lower in bad:
        return False
    if re.match(r'^<.*>$', url_lower):
        return False
    if 'http' not in url_lower and '.' not in url_lower:
        return False
    return True


def _looks_like_name(line):
    """
    Return True if the line looks like a person's name.
    A name is 1-4 words, each starting with a capital letter,
    containing only letters, spaces, hyphens, and apostrophes.
    """
    line = line.strip()
    if not line:
        return False
    # Reject lines with special characters that names don't have
    if any(c in line for c in ['@', '/', '\\', '|', '+', '(', ')', '&']):
        return False
    # Reject if it contains digits
    if re.search(r'\d', line):
        return False
    # Reject if it looks like a skills headline (contains common skill keywords)
    skill_keywords = ['development', 'engineering', 'programming', 'machine learning',
                      'artificial intelligence', 'data science', 'android', 'python',
                      'java', 'sql', 'cloud', 'devops', 'analyst', 'specialist']
    if any(kw in line.lower() for kw in skill_keywords):
        return False
    # Must be 1-4 words of reasonable length
    words = line.split()
    if not (1 <= len(words) <= 4):
        return False
    # Each word should start with a capital letter and be mostly letters
    for word in words:
        if not word[0].isupper():
            return False
        if not re.match(r"^[A-Za-z\-'\.]+$", word):
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# LATEX DOCUMENT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_latex(resume_data, output_path):
    """Build a .tex file from structured resume_data dict."""
    name    = escape_latex(resume_data.get('name', 'Name'))
    title   = resume_data.get('title', '')
    summary = escape_latex(resume_data.get('summary', ''))

    # ── Preamble ──────────────────────────────────────────────────────────────
    latex = r"""\documentclass[a4paper,10pt]{article}

\usepackage{url}
\usepackage{parskip}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage[top=0.5in, bottom=0.5in, left=0.6in, right=0.6in]{geometry}
\usepackage{tabularx}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{multicol}
\usepackage[unicode]{hyperref}

\setlist[itemize]{noitemsep, topsep=2pt, parsep=0pt, partopsep=0pt}

\definecolor{linkcolour}{rgb}{0,0.2,0.6}
\hypersetup{colorlinks=true, linkcolor=linkcolour, urlcolor=linkcolour}

\pagestyle{empty}
\titleformat{\section}{\large\scshape\raggedright}{}{0em}{}[\titlerule]
\titlespacing{\section}{0pt}{6pt}{4pt}

\begin{document}

%-- HEADER --------------------------------------------------------------------
\begin{center}
{\Huge \textbf{""" + name + r"""}} \\[6pt]
"""

    # ── Contact row — only real URLs ──────────────────────────────────────────
    links = []
    if is_valid_url(resume_data.get('linkedin')):
        links.append(r"\href{" + resume_data['linkedin'] + r"}{LinkedIn}")
    if is_valid_url(resume_data.get('github')):
        links.append(r"\href{" + resume_data['github'] + r"}{GitHub}")
    if resume_data.get('email'):
        links.append(
            r"\href{mailto:" + resume_data['email'] + "}{" + resume_data['email'] + "}"
        )
    if resume_data.get('phone'):
        links.append(escape_latex(resume_data['phone']))

    if links:
        latex += r" \ $|$ \ ".join(links) + r" \\[4pt]" + "\n"

    # ── Headline: normalise separators, cap at 4 items ────────────────────────
    title_clean    = re.sub(r'\s*[—–]\s*', ' | ', title)
    headline_parts = [p.strip() for p in title_clean.split('|') if p.strip()]
    headline_parts = headline_parts[:4]

    if headline_parts:
        headline_latex = r" \ $|$ \ ".join(escape_latex(p) for p in headline_parts)
        latex += r"\textit{" + headline_latex + r"}" + "\n"

    latex += r"\end{center}" + "\n"

    # ── Profile Summary ───────────────────────────────────────────────────────
    if summary:
        latex += "\n\\section{PROFILE SUMMARY}\n" + summary + "\n"

    # ── Professional Experience ───────────────────────────────────────────────
    if resume_data.get('experience'):
        latex += "\n\\section{PROFESSIONAL EXPERIENCE}\n"
        for exp in resume_data['experience']:
            company  = escape_latex(exp.get('company',  ''))
            location = escape_latex(exp.get('location', ''))
            role     = escape_latex(exp.get('role',     ''))
            duration = escape_latex(exp.get('duration', ''))

            latex += "\n\\textbf{" + company + "} \\hfill " + location + " \\\\\n"
            latex += "\\textit{" + role + "} \\hfill " + duration + "\n"
            latex += "\\begin{itemize}[leftmargin=*]\n"
            for bullet in exp.get('bullets', []):
                latex += "    \\item " + escape_latex(bullet) + "\n"
            latex += "\\end{itemize}\n"

    # ── Projects ──────────────────────────────────────────────────────────────
    if resume_data.get('projects'):
        latex += "\n\\section{PROJECTS}\n"
        for proj in resume_data['projects']:
            proj_title = escape_latex(proj.get('title', 'Project'))
            bullets    = proj.get('bullets', [])
            latex += "\n\\textbf{" + proj_title + "}\n"
            if bullets:
                latex += "\\begin{itemize}[leftmargin=*]\n"
                for bullet in bullets:
                    latex += "    \\item " + escape_latex(bullet) + "\n"
                latex += "\\end{itemize}\n"

    # ── Education ─────────────────────────────────────────────────────────────
    if resume_data.get('education'):
        latex += "\n\\section{EDUCATION}\n"
        for edu in resume_data['education']:
            degree     = escape_latex(edu.get('degree',     ''))
            school     = escape_latex(edu.get('school',     ''))
            university = escape_latex(edu.get('university', ''))
            year       = escape_latex(edu.get('year',       ''))

            latex += "\n\\textbf{" + degree + "} \\hfill " + year + " \\\\\n"
            if school:
                latex += school + " \\\\\n"
            if university:
                latex += university + "\n"

    # ── Skills ────────────────────────────────────────────────────────────────
    if resume_data.get('skills'):
        latex += "\n\\section{SKILLS}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"
        for skill in resume_data['skills']:
            latex += "    \\item " + escape_latex(skill) + "\n"
        latex += "\\end{itemize}\n"

    latex += "\n\\vfill\n\\end{document}\n"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(latex)

    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# LATEX → PDF COMPILATION
# ─────────────────────────────────────────────────────────────────────────────

def compile_latex_to_pdf(tex_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    pdf_name = os.path.splitext(os.path.basename(tex_path))[0] + '.pdf'
    pdf_path = os.path.join(output_dir, pdf_name)

    pdflatex_path = r"C:\Users\ptpna\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
    cmd = [
        pdflatex_path,
        '-interaction=nonstopmode',
        '-output-directory', output_dir,
        tex_path
    ]
    env = os.environ.copy()
    env['MIKTEX_CHECK_UPDATE'] = '0'

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0 and not os.path.exists(pdf_path):
        print("LaTeX compilation errors:")
        print(result.stdout)
        print(result.stderr)
        raise Exception(f"LaTeX compilation failed: {result.stderr}")

    return pdf_path


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def generate_resume_latex(resume_text, docx_path, pdf_path):
    """Full pipeline: LLM text → parsed dict → .tex → .pdf"""
    resume_data = parse_resume_text(resume_text)
    tex_path    = os.path.splitext(pdf_path)[0] + '.tex'
    generate_latex(resume_data, tex_path)
    compile_latex_to_pdf(tex_path, os.path.dirname(pdf_path))
    return pdf_path


# ─────────────────────────────────────────────────────────────────────────────
# TEXT → STRUCTURED DATA PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_resume_text(text):
    data = {
        'name': '', 'linkedin': '', 'github': '', 'email': '',
        'phone': '', 'title': '', 'summary': '',
        'experience': [], 'projects': [], 'education': [], 'skills': []
    }

    # Strip markdown artefacts
    text = re.sub(r'__(.+?)__',      r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*',  r'\1', text)
    text = re.sub(r'`(.+?)`',        r'\1', text)

    # Split on ---SECTION--- markers
    raw_parts = re.compile(r'---([A-Z]+)---').split(text)
    sections  = {}
    for i in range(1, len(raw_parts), 2):
        if i + 1 < len(raw_parts):
            sections[raw_parts[i].strip()] = raw_parts[i + 1].strip()

    # ── HEADER ────────────────────────────────────────────────────────────────
    if 'HEADER' in sections:
        header = sections['HEADER']

        # If LLM put everything on one line with — separators, split it
        if '\n' not in header.strip() and '—' in header:
            header = re.sub(r'\s*—\s*', '\n', header)

        lines = [l.strip() for l in header.split('\n') if l.strip()]

        # ── Name: find the line that looks most like a person's name ─────────
        # Priority 1: first line that passes _looks_like_name()
        # Priority 2: first line with no @, http, digits
        for line in lines:
            if _looks_like_name(line):
                data['name'] = line
                break
        if not data['name']:
            for line in lines:
                if ('@' not in line
                        and 'http' not in line.lower()
                        and not re.search(r'\d', line)):
                    data['name'] = line
                    break

        # ── Email ─────────────────────────────────────────────────────────────
        email_m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', header)
        if email_m:
            data['email'] = email_m.group()

        # ── Phone: digits only, no trailing punctuation ───────────────────────
        # Match: optional +, then digits/spaces/dashes, but NOT trailing ( ) [ ]
        phone_m = re.search(r'\+?[\d][\d\s\-]{8,}', header)
        if phone_m:
            # Strip any trailing non-digit characters
            phone = re.sub(r'[\s\-\(\)\[\]]+$', '', phone_m.group())
            data['phone'] = phone.strip()

        # ── LinkedIn ─────────────────────────────────────────────────────────
        li_m = re.search(r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+', header, re.I)
        if li_m:
            data['linkedin'] = li_m.group()
        else:
            li_m2 = re.search(r'linkedin\.com/in/[\w\-]+', header, re.I)
            if li_m2:
                data['linkedin'] = 'https://' + li_m2.group()

        # ── GitHub ───────────────────────────────────────────────────────────
        gh_m = re.search(r'https?://(?:www\.)?github\.com/[\w\-]+', header, re.I)
        if gh_m:
            data['github'] = gh_m.group()
        else:
            gh_m2 = re.search(r'github\.com/[\w\-]+', header, re.I)
            if gh_m2:
                data['github'] = 'https://' + gh_m2.group()

        # ── Headline: last non-contact, non-name line ─────────────────────────
        for line in reversed(lines):
            is_contact = (
                line == data['name']
                or '@' in line
                or re.search(r'\+?\d[\d\s\-]{7,}', line)
                or 'linkedin' in line.lower()
                or 'github'   in line.lower()
                or 'http'     in line.lower()
            )
            if not is_contact and line and line != data['name']:
                data['title'] = line
                break

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    if 'SUMMARY' in sections:
        data['summary'] = sections['SUMMARY']

    # ── EXPERIENCE ────────────────────────────────────────────────────────────
    if 'EXPERIENCE' in sections:
        data['experience'] = _parse_experience(sections['EXPERIENCE'])

    # ── PROJECTS ──────────────────────────────────────────────────────────────
    if 'PROJECTS' in sections:
        data['projects'] = _parse_projects(sections['PROJECTS'])

    # ── EDUCATION ─────────────────────────────────────────────────────────────
    if 'EDUCATION' in sections:
        data['education'] = _parse_education(sections['EDUCATION'])

    # ── SKILLS ────────────────────────────────────────────────────────────────
    if 'SKILLS' in sections:
        for line in sections['SKILLS'].split('\n'):
            line = line.strip().lstrip('-•* ')
            if line and len(line) > 2 and not _is_jd_qualification(line):
                data['skills'].append(line)

    return data


def _is_jd_qualification(line):
    """
    Return True if a skills line looks like a JD requirement that leaked in,
    e.g. "Bachelor's degree in Computer Science" or "3+ years experience".
    These should never appear in the SKILLS section.
    """
    jd_patterns = [
        r"bachelor'?s?\s+degree",
        r"master'?s?\s+degree",
        r"\d\+\s+years?\s+of",
        r"\d\+\s+years?\s+experience",
        r"years?\s+of\s+experience",
        r"required\s+education",
        r"preferred\s+education",
        r"non-internship",
        r"internship\s+experience",
    ]
    line_lower = line.lower()
    return any(re.search(pat, line_lower) for pat in jd_patterns)


# ─────────────────────────────────────────────────────────────────────────────
# PARSER HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _is_bullet(line):
    return bool(
        re.match(r'^[-•*\u2022\u25cf✓]', line)
        or re.match(r'^\d+[.)]\s', line)
    )


def _clean_bullet(line):
    """Remove bullet/number prefix."""
    line = re.sub(r'^[-•*\u2022\u25cf✓]\s*', '', line)
    line = re.sub(r'^\d+[.)]\s*',             '', line)
    return line.strip()


def _parse_experience(exp_text):
    """
    Handles:
      FORMAT A — COMPANY: / ROLE: prefixes
      FORMAT B — plain "Company  City" then "Role | Month Year"
      FORMAT C — "Role — Duration" with em-dash
    """
    experiences = []
    current_exp = None
    bullets     = []
    lines       = [l.strip() for l in exp_text.split('\n')]

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue

        if line.upper().startswith('COMPANY:'):
            if current_exp is not None:
                current_exp['bullets'] = bullets
                experiences.append(current_exp)
            val = line[len('COMPANY:'):].strip()
            if '|' in val:
                cp = val.split('|', 1)
                current_exp = {'company': cp[0].strip(), 'location': cp[1].strip()}
            else:
                current_exp = {'company': val, 'location': ''}
            bullets = []

        elif line.upper().startswith('ROLE:'):
            val = line[len('ROLE:'):].strip()
            if current_exp is not None:
                if '|' in val:
                    rp = val.split('|', 1)
                    current_exp['role']     = rp[0].strip()
                    current_exp['duration'] = rp[1].strip()
                else:
                    current_exp['role']     = val
                    current_exp['duration'] = ''

        elif re.search(
            r'.+\|\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec'
            r'|January|February|March|April|May|June|July|August|September'
            r'|October|November|December)\s+\d{4}',
            line, re.I
        ):
            rp       = line.split('|', 1)
            role     = rp[0].strip()
            duration = rp[1].strip() if len(rp) > 1 else ''

            if current_exp is not None and 'role' not in current_exp:
                current_exp['role']     = role
                current_exp['duration'] = duration
            else:
                if current_exp is not None:
                    current_exp['bullets'] = bullets
                    experiences.append(current_exp)
                company = location = ''
                for prev in reversed(lines[:i]):
                    prev = prev.strip()
                    if prev and not _is_bullet(prev) and not re.search(r'.+\|.+\d{4}', prev):
                        if ',' in prev:
                            pts      = prev.split(',', 1)
                            company  = pts[0].strip()
                            location = pts[1].strip()
                        else:
                            company = prev
                        break
                current_exp = {
                    'company': company, 'location': location,
                    'role': role,       'duration': duration,
                }
                bullets = []

        elif re.search(r'.+[—–].+\d{4}', line) and not _is_bullet(line):
            parts    = re.split(r'[—–]', line, maxsplit=1)
            role     = parts[0].strip()
            duration = parts[1].strip() if len(parts) > 1 else ''
            if current_exp is not None and 'role' not in current_exp:
                current_exp['role']     = role
                current_exp['duration'] = duration
            else:
                if current_exp is not None:
                    current_exp['bullets'] = bullets
                    experiences.append(current_exp)
                current_exp = {
                    'company': '', 'location': '',
                    'role': role,  'duration': duration,
                }
                bullets = []

        elif (
            not _is_bullet(line)
            and not re.search(r'\d{4}', line)
            and current_exp is not None
            and 'role' in current_exp
            and len(line) > 3
        ):
            current_exp['bullets'] = bullets
            experiences.append(current_exp)
            current_exp = {'company': line, 'location': ''}
            bullets     = []

        elif _is_bullet(line):
            if current_exp is not None:
                clean = _clean_bullet(line)
                if clean:
                    bullets.append(clean)

        i += 1

    if current_exp is not None:
        current_exp['bullets'] = bullets
        experiences.append(current_exp)

    return experiences


def _parse_projects(proj_text):
    projects     = []
    current_proj = None
    bullets      = []

    for line in proj_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith('PROJECT:'):
            if current_proj is not None:
                current_proj['bullets'] = bullets
                projects.append(current_proj)
            title        = line[len('PROJECT:'):].strip()
            title        = re.sub(r'\s*\|.*$', '', title).strip()
            current_proj = {'title': title}
            bullets      = []

        elif _is_bullet(line):
            if current_proj is None:
                current_proj = {'title': 'Project'}
                bullets      = []
            bullets.append(_clean_bullet(line))

        else:
            if current_proj is not None:
                current_proj['bullets'] = bullets
                projects.append(current_proj)
            title        = re.sub(r'\s*\|.*$', '', line).strip()
            current_proj = {'title': title}
            bullets      = []

    if current_proj is not None:
        current_proj['bullets'] = bullets
        projects.append(current_proj)

    return projects


def _parse_education(edu_text):
    edu_lines = [l.strip() for l in edu_text.split('\n') if l.strip()]
    if not edu_lines:
        return []

    degree_line = edu_lines[0]
    year_match  = re.search(r'\d{4}\s*[-–—]{1,2}\s*\d{4}', degree_line)
    year        = year_match.group() if year_match else ''
    degree      = re.sub(r'\s*\|.*$', '', degree_line).strip()

    school = university = ''
    if len(edu_lines) > 1:
        second      = edu_lines[1]
        paren_match = re.search(r'\((.+?)\)', second)
        if paren_match:
            university = paren_match.group(1).strip()
            school     = re.sub(r'\s*\(.+?\)', '', second).strip()
        else:
            school = second
    if len(edu_lines) > 2 and not university:
        university = edu_lines[2]

    return [{'degree': degree, 'school': school, 'university': university, 'year': year}]