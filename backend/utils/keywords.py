import re
from sklearn.feature_extraction.text import TfidfVectorizer

def extract_keywords(text, num_keywords=10):
    vectorizer = TfidfVectorizer(
        max_features=200,
        stop_words='english',
        ngram_range=(1, 3) # Include bigrams and trigrams for better context
    )
    if not text or not text.strip():
        return []

    try:
        X = vectorizer.fit_transform([text])
    except ValueError:
        return []

    # Get feature names and their corresponding tf-idf scores
    feature_names = vectorizer.get_feature_names_out()
    scores = X.toarray()[0]

    # Combine into a list of tuples and sort by score descending (most important first)
    scored_keywords = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)

    filtered = []
    for k, score in scored_keywords:
        # Filter out purely numeric or very short junk keywords
        if len(k) > 4 and not bool(re.search(r'\d', k)):
            filtered.append(k.title()) # Capitalize nicely
        if len(filtered) == num_keywords:
            break

    return filtered