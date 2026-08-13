from sklearn.feature_extraction.text import TfidfVectorizer

def extract_keywords(text, num_keywords=10):
    vectorizer = TfidfVectorizer(
        max_features=200,
        stop_words='english',
        ngram_range=(1, 2)
    )
    # guard: empty or stopword-only input
    if not text or not text.strip():
        return []

    try:
        X = vectorizer.fit_transform([text])
    except ValueError:
        return []

    keywords = vectorizer.get_feature_names_out()

    # ✅ Keep only meaningful words (length filter)
    filtered = [k for k in keywords if len(k) > 5]

    return filtered[:num_keywords]