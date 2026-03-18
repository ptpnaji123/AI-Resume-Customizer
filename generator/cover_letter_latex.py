"""
generator/cover_letter_latex.py

Renders a cover letter dict (from ai_engine/cover_letter.py) into a
professional LaTeX PDF.  No changes to any other file.
"""
import os
import re
import subprocess


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
    return text


def is_valid_url(url):
    """Return True only if value looks like a real URL."""
    if not url:
        return False
    url_lower = url.lower().strip()
    bad = {'empty', '<empty>', 'none', 'n/a', 'na', '-', 'not provided',
           'not available', 'null', 'undefined', 'blank', 'leave blank', '<leave blank>'}
    if url_lower in bad:
        return False
    if re.match(r'^<.*>$', url_lower):
        return False
    if 'http' not in url_lower and '.' not in url_lower:
        return False
    return True


def generate_cover_letter_latex(cover_letter_data, output_path):
    """
    Build a .tex file from a cover_letter_data dict and compile to PDF.

    Parameters
    ----------
    cover_letter_data : dict
        Output of ai_engine.cover_letter.generate_cover_letter()
    output_path : str
        Full path for the output PDF file.

    Returns
    -------
    str — path to the compiled PDF
    """
    name       = escape_latex(cover_letter_data.get("name",      ""))
    email      = cover_letter_data.get("email",    "")
    phone      = escape_latex(cover_letter_data.get("phone",     ""))
    linkedin   = cover_letter_data.get("linkedin", "")
    job_title  = escape_latex(cover_letter_data.get("job_title", "the position"))
    company    = escape_latex(cover_letter_data.get("company",   ""))
    paragraphs = cover_letter_data.get("paragraphs", [])

    # ── Contact row ───────────────────────────────────────────────────────────
    contact_parts = []
    if is_valid_url(linkedin):
        contact_parts.append(r"\href{" + linkedin + r"}{LinkedIn}")
    if email:
        contact_parts.append(r"\href{mailto:" + email + "}{" + email + "}")
    if phone:
        contact_parts.append(phone)

    contact_line = r" \ $|$ \ ".join(contact_parts) if contact_parts else ""

    # ── Opening line ──────────────────────────────────────────────────────────
    if company:
        recipient_line = f"Dear Hiring Team at {company},"
    else:
        recipient_line = "Dear Hiring Manager,"

    # ── Body paragraphs ───────────────────────────────────────────────────────
    body_latex = ""
    for para in paragraphs:
        body_latex += "\n" + escape_latex(para) + "\n\n\\vspace{6pt}\n"

    # ── Full LaTeX document ───────────────────────────────────────────────────
    latex = r"""\documentclass[a4paper,11pt]{article}

\usepackage{url}
\usepackage{parskip}
\usepackage{xcolor}
\usepackage[top=0.8in, bottom=0.8in, left=0.85in, right=0.85in]{geometry}
\usepackage{enumitem}
\usepackage[unicode]{hyperref}

\definecolor{linkcolour}{rgb}{0,0.2,0.6}
\hypersetup{colorlinks=true, linkcolor=linkcolour, urlcolor=linkcolour}

\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{8pt}

\begin{document}

%-- HEADER --------------------------------------------------------------------
\begin{center}
{\Huge \textbf{""" + name + r"""}} \\[5pt]
""" + contact_line + r""" \\[2pt]
\end{center}

\vspace{10pt}

%-- DATE & RECIPIENT ----------------------------------------------------------
\today

\vspace{10pt}

""" + escape_latex(recipient_line) + r"""

\vspace{6pt}

%-- SUBJECT LINE --------------------------------------------------------------
\textbf{Re: Application for """ + job_title + r"""}

\vspace{8pt}

%-- BODY ----------------------------------------------------------------------
""" + body_latex + r"""

%-- CLOSING -------------------------------------------------------------------
Warm regards,

\vspace{20pt}

\textbf{""" + name + r"""}

\end{document}
"""

    # ── Write .tex file ───────────────────────────────────────────────────────
    tex_path = os.path.splitext(output_path)[0] + ".tex"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex)

    # ── Compile to PDF ────────────────────────────────────────────────────────
    pdflatex_path = r"C:\Users\ptpna\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
    output_dir    = os.path.dirname(output_path)

    cmd = [
        pdflatex_path,
        "-interaction=nonstopmode",
        "-output-directory", output_dir,
        tex_path,
    ]
    env = os.environ.copy()
    env["MIKTEX_CHECK_UPDATE"] = "0"

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    pdf_path = os.path.splitext(tex_path)[0] + ".pdf"
    if result.returncode != 0 and not os.path.exists(pdf_path):
        print("Cover letter LaTeX errors:")
        print(result.stdout)
        print(result.stderr)
        raise Exception(f"Cover letter PDF compilation failed: {result.stderr}")

    return pdf_path