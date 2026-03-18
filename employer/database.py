"""
employer/database.py

Manages the ChromaDB vector database of candidate resumes.

Collections used:
  resumes_full        — full resume embeddings
  resumes_skills      — skills section embeddings
  resumes_experience  — experience section embeddings
  resumes_summary     — summary section embeddings

Each document is stored with metadata:
  name, email, phone, filename, upload_date, raw_text (first 2000 chars)
"""
import re
import hashlib
from datetime import datetime

import chromadb
from employer.embedder import embed_sections

# ── ChromaDB persistent client ─────────────────────────────────────────────────
_CLIENT = chromadb.PersistentClient(path="./resume_db")

_COLLECTIONS = {
    "full":       _CLIENT.get_or_create_collection("resumes_full"),
    "skills":     _CLIENT.get_or_create_collection("resumes_skills"),
    "experience": _CLIENT.get_or_create_collection("resumes_experience"),
    "summary":    _CLIENT.get_or_create_collection("resumes_summary"),
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_contact(text: str) -> dict:
    """Pull name, email, phone from raw resume text."""
    name = email = phone = ""

    email_m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_m:
        email = email_m.group()

    phone_m = re.search(r'\+?[\d][\d\s\-]{8,}', text)
    if phone_m:
        phone = re.sub(r'[\s\-\(\)\[\]]+$', '', phone_m.group()).strip()

    # Name heuristic: first non-empty line that looks like a name
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '@' in line or re.search(r'\d', line) or len(line) > 40:
            continue
        words = line.split()
        if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            name = line
            break

    return {"name": name, "email": email, "phone": phone}


def _make_id(filename: str, text: str) -> str:
    """Stable unique ID based on filename + content hash."""
    content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    safe_name    = re.sub(r'[^a-zA-Z0-9_\-]', '_', filename)
    return f"{safe_name}_{content_hash}"


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def add_resume(resume_text: str, filename: str) -> dict:
    """
    Embed and store a resume in all four collections.

    Returns metadata dict for display in the UI.
    """
    contact     = _extract_contact(resume_text)
    doc_id      = _make_id(filename, resume_text)
    upload_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    metadata = {
        "name":        contact["name"]  or filename,
        "email":       contact["email"] or "",
        "phone":       contact["phone"] or "",
        "filename":    filename,
        "upload_date": upload_date,
        "preview":     resume_text[:500].replace("\n", " "),
    }

    embeddings = embed_sections(resume_text)

    for section, collection in _COLLECTIONS.items():
        # Check if already exists — avoid duplicates
        existing = collection.get(ids=[doc_id])
        if existing["ids"]:
            collection.update(
                ids        = [doc_id],
                embeddings = [embeddings[section]],
                documents  = [resume_text[:2000]],
                metadatas  = [metadata],
            )
        else:
            collection.add(
                ids        = [doc_id],
                embeddings = [embeddings[section]],
                documents  = [resume_text[:2000]],
                metadatas  = [metadata],
            )

    return {"id": doc_id, **metadata}


def list_resumes() -> list[dict]:
    """
    Return all stored resumes (from the full collection) as a list of dicts.
    Each dict: id, name, email, phone, filename, upload_date
    """
    result = _COLLECTIONS["full"].get(include=["metadatas"])
    items  = []
    for doc_id, meta in zip(result["ids"], result["metadatas"]):
        items.append({"id": doc_id, **meta})
    # Sort newest first
    items.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
    return items


def delete_resume(doc_id: str) -> bool:
    """Delete a resume from all collections. Returns True on success."""
    for collection in _COLLECTIONS.values():
        try:
            collection.delete(ids=[doc_id])
        except Exception:
            pass
    return True


def search_resumes(
    jd_embedding: list[float],
    top_k: int = 10,
    section_weights: dict = None,
) -> list[dict]:
    """
    Weighted semantic search across all four section collections.

    section_weights defaults to:
        full: 0.3, skills: 0.35, experience: 0.25, summary: 0.10

    Returns top_k candidates as list of dicts with keys:
        id, name, email, phone, filename, preview, combined_score
    """
    if section_weights is None:
        section_weights = {
            "full":       0.30,
            "skills":     0.35,
            "experience": 0.25,
            "summary":    0.10,
        }

    # Collect weighted scores per candidate
    scores: dict[str, dict] = {}

    for section, weight in section_weights.items():
        collection = _COLLECTIONS[section]
        if collection.count() == 0:
            continue

        results = collection.query(
            query_embeddings = [jd_embedding],
            n_results        = min(top_k * 2, collection.count()),
            include          = ["metadatas", "distances"],
        )

        for doc_id, meta, dist in zip(
            results["ids"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Convert distance to similarity score (0-1)
            similarity = max(0.0, 1.0 - dist)
            weighted   = similarity * weight

            if doc_id not in scores:
                scores[doc_id] = {"meta": meta, "total": 0.0, "sections": {}}
            scores[doc_id]["total"]             += weighted
            scores[doc_id]["sections"][section]  = round(similarity * 100, 1)

    # Sort by combined score
    ranked = sorted(scores.values(), key=lambda x: x["total"], reverse=True)

    results_out = []
    for item in ranked[:top_k]:
        meta = item["meta"]
        results_out.append({
            "name":           meta.get("name",     "Unknown"),
            "email":          meta.get("email",    ""),
            "phone":          meta.get("phone",    ""),
            "filename":       meta.get("filename", ""),
            "upload_date":    meta.get("upload_date", ""),
            "preview":        meta.get("preview",  ""),
            "combined_score": round(item["total"] * 100, 1),
            "section_scores": item["sections"],
        })

    return results_out


def get_resume_count() -> int:
    """Return total number of resumes in the database."""
    return _COLLECTIONS["full"].count()