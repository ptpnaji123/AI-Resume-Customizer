"""
employer/shortlist.py

Two-stage shortlisting:
  Stage 1 — Vector search: fast semantic retrieval from ChromaDB
  Stage 2 — LLM scoring:  Mistral re-ranks top candidates with detailed scores
"""
from ollama import chat
from employer.embedder import embed
from employer.database import search_resumes

MODEL_NAME = "mistral"


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — VECTOR RETRIEVAL
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_candidates(jd_text: str, top_k: int = 10) -> list[dict]:
    """
    Embed the JD and retrieve the top_k semantically similar candidates
    from ChromaDB using weighted multi-section search.
    """
    jd_embedding = embed(jd_text)
    return search_resumes(jd_embedding, top_k=top_k)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — LLM SCORING
# ─────────────────────────────────────────────────────────────────────────────

def score_candidate(jd_text: str, candidate: dict) -> dict:
    """
    Ask Mistral to score a single candidate against the JD.

    Adds to candidate dict:
        llm_score        : int   (0-100 overall)
        skill_match      : int   (0-100)
        experience_match : int   (0-100)
        education_match  : int   (0-100)
        justification    : str   (2-3 sentence explanation)
        skill_gaps       : list[str]
        strengths        : list[str]
    """
    prompt = f"""
You are an expert technical recruiter. Score this candidate against the job description.

JOB DESCRIPTION:
{jd_text[:2000]}

CANDIDATE RESUME PREVIEW:
{candidate.get('preview', '')[:1500]}

Score the candidate on each dimension from 0-100.
Be honest and realistic — not every candidate will score high.

Output ONLY this exact format, no extra text:

OVERALL: <0-100>
SKILL_MATCH: <0-100>
EXPERIENCE_MATCH: <0-100>
EDUCATION_MATCH: <0-100>
STRENGTHS:
- <strength 1>
- <strength 2>
- <strength 3>
SKILL_GAPS:
- <missing skill 1>
- <missing skill 2>
JUSTIFICATION: <2-3 sentences explaining the overall score. Be specific.>
"""
    response = chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    raw      = response["message"]["content"].strip()

    # Parse output
    result = {
        "llm_score":        candidate.get("combined_score", 0),
        "skill_match":      0,
        "experience_match": 0,
        "education_match":  0,
        "strengths":        [],
        "skill_gaps":       [],
        "justification":    "",
    }

    current_list = None
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("OVERALL:"):
            try:
                result["llm_score"] = int(line.replace("OVERALL:", "").strip())
            except ValueError:
                pass
        elif line.startswith("SKILL_MATCH:"):
            try:
                result["skill_match"] = int(line.replace("SKILL_MATCH:", "").strip())
            except ValueError:
                pass
        elif line.startswith("EXPERIENCE_MATCH:"):
            try:
                result["experience_match"] = int(line.replace("EXPERIENCE_MATCH:", "").strip())
            except ValueError:
                pass
        elif line.startswith("EDUCATION_MATCH:"):
            try:
                result["education_match"] = int(line.replace("EDUCATION_MATCH:", "").strip())
            except ValueError:
                pass
        elif line.startswith("STRENGTHS:"):
            current_list = "strengths"
        elif line.startswith("SKILL_GAPS:"):
            current_list = "skill_gaps"
        elif line.startswith("JUSTIFICATION:"):
            result["justification"] = line.replace("JUSTIFICATION:", "").strip()
            current_list = None
        elif line.startswith("-") and current_list:
            value = line.lstrip("- ").strip()
            if value:
                result[current_list].append(value)

    return {**candidate, **result}


def shortlist(jd_text: str, top_k: int = 10, llm_score: bool = True) -> list[dict]:
    """
    Full two-stage pipeline.

    Parameters
    ----------
    jd_text  : str   — raw job description text
    top_k    : int   — number of candidates to retrieve and score
    llm_score: bool  — if True, run LLM scoring on retrieved candidates

    Returns list of candidate dicts sorted by llm_score descending.
    """
    # Stage 1: vector retrieval
    candidates = retrieve_candidates(jd_text, top_k=top_k)

    if not candidates:
        return []

    if not llm_score:
        return candidates

    # Stage 2: LLM scoring (one call per candidate)
    scored = []
    for candidate in candidates:
        try:
            scored.append(score_candidate(jd_text, candidate))
        except Exception as e:
            print(f"Scoring failed for {candidate.get('name')}: {e}")
            scored.append(candidate)

    # Sort by LLM score
    scored.sort(key=lambda x: x.get("llm_score", 0), reverse=True)
    return scored