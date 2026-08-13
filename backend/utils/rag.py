import os
import json
import hashlib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .pdf_extractor import extract_text_by_page
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'gemini').strip().lower()
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.1-pro-preview')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

gemini_client = None


def load_llm_clients():
    global LLM_PROVIDER, GEMINI_MODEL, GEMINI_API_KEY, gemini_client
    load_dotenv()
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'gemini').strip().lower()
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.1-pro-preview')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    gemini_client = None

    if GEMINI_API_KEY:
        try:
            from google import genai
            gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception:
            gemini_client = None

# Initialize clients once at import time.
load_llm_clients()

# Local index storage
INDEX_DIR = os.path.join(os.path.dirname(__file__), '..', 'indexes')
os.makedirs(INDEX_DIR, exist_ok=True)


def _doc_id_from_path(path):
    # deterministic id from file path
    h = hashlib.sha1(path.encode('utf-8')).hexdigest()
    return h


def _index_meta_path(doc_id):
    return os.path.join(INDEX_DIR, f"{doc_id}_meta.json")


def _index_vectors_path(doc_id):
    return os.path.join(INDEX_DIR, f"{doc_id}_vecs.npy")


def chunk_pages(pages, chunk_size=800, overlap=100):
    """Chunk page texts into smaller chunks (by characters) keeping page refs.

    Returns list of dicts: {id, page, text}
    """
    chunks = []
    cid = 0
    for page_num, text in pages:
        if not text:
            continue
        start = 0
        L = len(text)
        while start < L:
            end = min(start + chunk_size, L)
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({'id': f"c{cid}", 'page': page_num, 'text': chunk_text})
                cid += 1
            if end == L:
                break
            start = max(0, end - overlap)
    return chunks


def build_index(file_path, force=False):
    """Build or load an index for a PDF file. Uses TF-IDF vectors stored on disk.

    Returns metadata dict with keys: doc_id, chunks (list), vectorizer present.
    """
    doc_id = _doc_id_from_path(file_path)
    meta_path = _index_meta_path(doc_id)
    vecs_path = _index_vectors_path(doc_id)

    if os.path.exists(meta_path) and os.path.exists(vecs_path) and not force:
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        try:
            vectors = np.load(vecs_path)
        except Exception:
            vectors = None
        meta['vectors'] = vectors
        return meta

    # extract pages
    pages = extract_text_by_page(file_path)
    chunks = chunk_pages(pages)
    texts = [c['text'] for c in chunks]

    # guard
    if not texts:
        meta = {'doc_id': doc_id, 'chunks': [], 'vectorizer': None}
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f)
        np.save(vecs_path, np.array([]))
        meta['vectors'] = np.array([])
        return meta

    vectorizer = TfidfVectorizer(stop_words='english', max_features=1024)
    try:
        vectors = vectorizer.fit_transform(texts).toarray()
    except Exception:
        vectors = np.zeros((len(texts), 1))

    vocab = {k: int(v) for k, v in vectorizer.vocabulary_.items()}
    meta = {'doc_id': doc_id, 'file_path': file_path, 'chunks': chunks, 'vocab': vocab}

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f)

    np.save(vecs_path, vectors)
    meta['vectors'] = vectors
    return meta


def query_index(file_path, query, top_k=4):
    doc_id = _doc_id_from_path(file_path)
    meta_path = _index_meta_path(doc_id)
    vecs_path = _index_vectors_path(doc_id)

    if not os.path.exists(meta_path) or not os.path.exists(vecs_path):
        # build index
        meta = build_index(file_path)
    else:
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        try:
            vectors = np.load(vecs_path)
        except Exception:
            vectors = None
        meta['vectors'] = vectors

    if not meta.get('chunks'):
        return []

    # Recreate vectorizer from vocab and fit it on the same corpus to compute IDF.
    vocab = meta.get('vocab', {})
    vectorizer = TfidfVectorizer(stop_words='english', vocabulary=vocab)
    texts = [c['text'] for c in meta['chunks']]
    try:
        vectorizer.fit(texts)
        corpus_vectors = vectorizer.transform(texts).toarray()
        query_vec = vectorizer.transform([query]).toarray()
    except Exception:
        return []

    sims = cosine_similarity(query_vec, corpus_vectors)[0]
    idxs = sims.argsort()[-top_k:][::-1]

    results = []
    for i in idxs:
        results.append({'chunk': meta['chunks'][i], 'score': float(sims[i])})
    return results


def generate_answer_with_llm(question, context_chunks):
    """Generate an answer using the configured LLM provider. Returns (answer, error)."""
    load_llm_clients()
    if not context_chunks:
        return None, 'No relevant document context was found.'

    system_instruction = (
        "You are ResearchAI, an academic research assistant.\n"
        "Answer questions using ONLY the supplied context from the selected research paper.\n"
        "Do not invent facts.\n"
        "If the supplied context does not contain enough information to answer the question, clearly say that the information could not be found in the selected paper.\n"
        "Give concise but useful explanations.\n"
        "When possible, reference the page number associated with the supporting context."
    )

    context_text = "\n\n".join([f"[page {c['page']}] {c['text']}" for c in context_chunks])
    prompt = f"Context:\n{context_text}\n\nQuestion: {question}"

    provider = LLM_PROVIDER
    if provider == 'gemini':
        if not GEMINI_API_KEY:
            return None, 'Gemini API is not configured. Please check your environment configuration.'
        if gemini_client is None:
            return None, 'Gemini authentication failed. Please verify the API key.'

        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.0
                }
            )
            if response and response.text:
                return response.text.strip(), None
            else:
                return None, 'The AI service returned an empty response.'
        except Exception as exc:
            err_str = str(exc).lower()
            if 'quota' in err_str or 'rate' in err_str or '429' in err_str:
                return None, 'Gemini API quota or rate limit has been reached. Please try again later.'
            if 'not found' in err_str or 'unavailable' in err_str:
                return None, 'The configured Gemini model is currently unavailable.'
            if 'api key' in err_str or '403' in err_str or 'unauthorized' in err_str:
                return None, 'Gemini authentication failed. Please verify the API key.'
            return None, 'ResearchAI could not generate an answer. Please try again.'

    return None, f'LLM provider "{provider}" is not supported. Set LLM_PROVIDER=gemini.'


def answer_question(file_path, question, top_k=6):
    if not os.path.exists(file_path):
        return {'success': False, 'error': 'The selected paper could not be found.'}

    meta = build_index(file_path)
    results = query_index(file_path, question, top_k=top_k)

    if not results:
        return {'success': False, 'error': 'I could not find enough information about this question in the selected paper.', 'sources': []}

    sources = [{'page': r['chunk']['page'], 'text': r['chunk']['text'], 'score': r['score']} for r in results]
    context_chunks = [r['chunk'] for r in results]

    answer, error = generate_answer_with_llm(question, context_chunks)
    if error:
        return {'success': False, 'error': error, 'sources': sources}

    return {'success': True, 'answer': answer, 'sources': sources}
