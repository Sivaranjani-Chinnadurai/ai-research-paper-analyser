import os
import json
import hashlib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .pdf_extractor import extract_text_by_page
from dotenv import load_dotenv
import requests

load_dotenv()

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama').strip().lower()
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')

ollama_client = None


def load_llm_clients():
    global LLM_PROVIDER, OLLAMA_MODEL, OLLAMA_HOST, ollama_client
    load_dotenv()
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama').strip().lower()
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')

    ollama_client = None

    try:
        import ollama
        if OLLAMA_HOST:
            ollama_client = ollama.Client(host=OLLAMA_HOST)
        else:
            ollama_client = ollama.Client()
    except Exception:
        ollama_client = None

# Initialize clients once at import time.
load_llm_clients()

def check_ollama_health():
    """Verify Ollama is reachable and model is available."""
    try:
        if not ollama_client:
            return False, "Ollama Python package is not installed."
        
        # We can ping the host directly to check if server is running
        host = OLLAMA_HOST.rstrip('/')
        try:
            requests.get(f"{host}/api/version", timeout=3)
        except Exception:
            return False, "Ollama is not running. Start Ollama and try again."

        # Check model exists
        models = ollama_client.list()
        model_names = [m.get('model', '') for m in models.get('models', [])]
        if not any(OLLAMA_MODEL in m for m in model_names):
            return False, f"The configured Ollama model '{OLLAMA_MODEL}' is not installed. Run: ollama pull {OLLAMA_MODEL}"
        
        return True, "Connected"
    except Exception as e:
        return False, "Ollama is not running. Start Ollama and try again."

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
    
    health_ok, health_msg = check_ollama_health()
    if not health_ok:
        return None, health_msg

    if not context_chunks:
        return None, "I couldn't find enough information about this in the selected paper."

    system_instruction = (
        "You are ResearchAI, an academic research assistant.\n\n"
        "Answer the user's question using ONLY the provided research-paper context.\n\n"
        "Do not invent information.\n"
        "Do not use unsupported facts.\n"
        "Do not answer from general knowledge when the required information is absent from the context.\n\n"
        "If the answer cannot be determined from the provided context, clearly say:\n"
        "'I couldn't find enough information about this in the selected paper.'\n\n"
        "Give concise but useful academic answers.\n\n"
        "When possible, mention the relevant page number(s)."
    )

    context_text = "\n\n".join([f"[page {c['page']}] {c['text']}" for c in context_chunks])
    
    prompt = f"Context:\n{context_text}\n\nQuestion:\n{question}"

    try:
        response = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]
            # Deliberately avoiding unsupported parameters like 'temperature' 
            # to ensure strict API compatibility across Ollama package versions.
        )
        
        answer = response.get('message', {}).get('content')
        if answer:
            return answer.strip(), None
        else:
            return None, 'Something went wrong while processing your question. Please try again.'
    except Exception as exc:
        err_str = str(exc).lower()
        if 'connection refused' in err_str:
            return None, 'Ollama is not running. Start Ollama and try again.'
        if 'not found' in err_str:
            return None, f"The configured Ollama model '{OLLAMA_MODEL}' is not installed. Run: ollama pull {OLLAMA_MODEL}"
        return None, 'Something went wrong while processing your question. Please try again.'


def answer_question(file_path, question, top_k=5):
    if not os.path.exists(file_path):
        return {'success': False, 'error': 'The selected paper could not be found.'}

    meta = build_index(file_path)
    results = query_index(file_path, question, top_k=top_k)

    if not results and not meta.get('chunks'):
        return {'success': False, 'error': 'I could not find enough information about this question in the selected paper.', 'sources': []}

    sources = [{'page': r['chunk']['page'], 'text': r['chunk']['text'], 'score': r['score']} for r in results]
    context_chunks = [r['chunk'] for r in results]

    # Heuristic: ALWAYS include the first 2 chunks (usually page 1: title, authors, abstract)
    # TF-IDF often misses these for questions like "who is the author" if the word "author" isn't explicitly there.
    if meta.get('chunks'):
        for i in range(min(2, len(meta['chunks']))):
            c = meta['chunks'][i]
            already_in = any(existing['id'] == c['id'] for existing in context_chunks)
            if not already_in:
                context_chunks.insert(i, c)
                sources.insert(i, {'page': c['page'], 'text': c['text'], 'score': 1.0})

    if not context_chunks:
         return {'success': False, 'error': 'I could not find enough information about this question in the selected paper.', 'sources': []}

    answer, error = generate_answer_with_llm(question, context_chunks)
    if error:
        return {'success': False, 'error': error, 'sources': sources}

    return {'success': True, 'answer': answer, 'sources': sources}
