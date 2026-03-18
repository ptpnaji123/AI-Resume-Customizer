"""
employer/embedder.py

Wraps Ollama's nomic-embed-text model to produce vector embeddings.
Requires: ollama pull nomic-embed-text  (run once in terminal)
"""
import re
import ollama

EMBED_MODEL = "nomic-embed-text"


def embed(text: str) -> list[float]:
    """
    Return a vector embedding for the given text.
    Truncates to 4000 chars to stay within model limits.
    """
    text = text.strip()[:4000]
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def embed_sections(resume_text: str) -> dict[str, list[float]]:
    """
    Embed a resume as multiple section-level chunks for richer retrieval.

    Returns a dict:
    {
        'full'        : embedding of entire resume (capped),
        'skills'      : embedding of SKILLS section only,
        'experience'  : embedding of EXPERIENCE section only,
        'summary'     : embedding of SUMMARY section only,
    }
    Missing sections fall back to the full embedding.
    """
    def extract_section(text, marker):
        """Extract text between ---MARKER--- and the next ---...---"""
        pattern = rf'---{marker}---\s*(.*?)(?=---[A-Z]+---|$)'
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    full_text   = resume_text.strip()[:4000]
    skills_text = extract_section(resume_text, "SKILLS")    or full_text
    exp_text    = extract_section(resume_text, "EXPERIENCE") or full_text
    summary_text = extract_section(resume_text, "SUMMARY")  or full_text

    return {
        "full":       embed(full_text),
        "skills":     embed(skills_text),
        "experience": embed(exp_text),
        "summary":    embed(summary_text),
    }