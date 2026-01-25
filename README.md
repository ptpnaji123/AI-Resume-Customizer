# AI Resume Tailor

**Automatically customizes your resume for any job description using AI.**

---

## Project Overview

AI Resume Tailor is a Python-based tool that automates the creation of **tailored, ATS-friendly resumes**. Given a base resume and a job description, the system:

1. Parses your original resume (PDF/DOCX).  
2. Scrapes and extracts job descriptions from websites.  
3. Extracts relevant skills and keywords using NLP.  
4. Uses the **Mistral AI model** to rewrite your resume, emphasizing relevant skills and experiences.  
5. Generates the final resume in **DOCX and PDF formats**.

This project is useful for job seekers who want to quickly customize their resumes for multiple job applications while keeping them professional and ATS-compliant.

---

## Folder Structure

resume_ai/
│
├── data/
│ ├── input_resume/ # Place your original resume(s) here (PDF/DOCX)
│ ├── jd_raw/ # Store scraped or sample job descriptions here (TXT)
│ └── output_resume/ # Optional: temporary output storage
│
├── resume_parser/
│ └── parse_resume.py # Module to extract text from PDF/DOCX resumes
│
├── jd_scraper/
│ └── scrape_jd.py # Module to scrape job descriptions from websites
│
├── jd_parser/
│ └── extract_requirements.py # Module to extract skills and keywords from JD
│
├── ai_engine/
│ └── rewrite_resume.py # Core module to generate tailored resumes using Mistral AI
│
├── generator/
│ ├── generate_docx.py # Module to save generated resume as DOCX
│ └── convert_to_pdf.py # Module to convert DOCX resume to PDF
│
├── outputs/ # Stores generated resumes (DOCX/PDF)
│
├── main.py # Optional main pipeline runner
├── requirements.txt # Python dependencies
└── README.md # Project documentation

markdown
Copy code

---

## Input & Output

### Inputs
- **Resume file:** PDF or DOCX in `data/input_resume/`  
  - Example: `data/input_resume/sample_resume.pdf`
- **Job Description (JD):** Plain text file in `data/jd_raw/`  
  - Example: `data/jd_raw/sample_jd.txt`
- (Optional) You can also scrape JD directly from a URL using `jd_scraper/scrape_jd.py`

### Outputs
- **Tailored Resume DOCX:** Saved in `outputs/`  
  - Example: `outputs/tailored_resume_20260126_123000.docx`
- **Tailored Resume PDF:** Saved in `outputs/pdf/`  
  - Example: `outputs/pdf/tailored_resume_20260126_123000.pdf`

---

## Features

- Parses PDF and DOCX resumes to extract text
- Scrapes job descriptions from online job portals
- Extracts skills and keywords using **spaCy NLP**
- Generates ATS-friendly, tailored resumes using **Mistral AI** (via Ollama)
- Saves final resume in both **DOCX** and **PDF** formats
- Automatically prevents overwriting existing output files

---

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/resume_ai.git
cd resume_ai
Create a virtual environment and activate it:

bash
Copy code
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
Install dependencies:

bash
Copy code
pip install -r requirements.txt
Install spaCy model (if not installed):

bash
Copy code
python -m spacy download en_core_web_sm
Make sure Ollama is installed and running locally:

bash
Copy code
ollama --version
ollama list  # check if Mistral model is available
Usage
Place your original resume in data/input_resume/

Place a job description text file in data/jd_raw/ or scrape from URL using scrape_jd.py

Run the pipeline:

bash
Copy code
python -m ai_engine.rewrite_resume
Generated resume will appear in outputs/ as DOCX and PDF

Tech Stack
Python 3.13+

spaCy – NLP for extracting skills and keywords

pdfplumber & python-docx – Resume parsing and DOCX generation

Ollama + Mistral 7B Instruct – AI for tailoring resumes

BeautifulSoup & Requests – Scraping job descriptions

reportlab & docx2pdf – PDF generation

Notes
Do NOT include personal resumes in GitHub.
They should stay in data/input_resume/ (ignored by .gitignore).

Output folder is ignored in Git by default to avoid large files.

Ensure Ollama is running locally before running rewrite_resume.py.

