import spacy
from collections import Counter

nlp = spacy.load("en_core_web_sm")

COMMON_SKILLS = {
    "python", "java", "sql", "machine learning", "deep learning",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn",
    "flask", "django", "aws", "docker", "kubernetes", "git",
    "nlp", "data analysis", "statistics"
}

def extract_skills_and_keywords(jd_text):
    doc = nlp(jd_text.lower())

    skills_found = set()
    keywords = []

    for chunk in doc.noun_chunks:
        text = chunk.text.strip()
        if text in COMMON_SKILLS:
            skills_found.add(text)

    for token in doc:
        if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop:
            keywords.append(token.lemma_)

    top_keywords = [
        word for word, _ in Counter(keywords).most_common(20)
    ]

    return {
        "skills": sorted(list(skills_found)),
        "keywords": top_keywords
    }


if __name__ == "__main__":
    # TEMP test
    with open("data/jd_raw/sample_jd.txt", "r", encoding="utf-8") as f:
        jd_text = f.read()

    result = extract_skills_and_keywords(jd_text)
    print(result)
