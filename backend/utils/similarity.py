from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.data.sample_docs import documents

def find_similar_docs(input_text, top_n=3):
    if not input_text or not input_text.strip():
        return []

    all_docs = documents + [input_text]

    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        vectors = vectorizer.fit_transform(all_docs)
    except ValueError:
        return []

    similarity_matrix = cosine_similarity(vectors)

    input_similarities = similarity_matrix[-1][:-1]

    similar_indices = input_similarities.argsort()[-top_n:][::-1]

    results = [documents[i] for i in similar_indices]

    return results