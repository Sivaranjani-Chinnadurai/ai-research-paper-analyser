import os

def generate_summary(text, sentence_count=3):
    """Generate a summary using Ollama, falling back to basic extraction if unavailable."""
    # Take the first 6000 characters which reliably covers Title, Abstract and Intro
    intro_text = text[:6000]
    
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    
    prompt = f"Please provide a concise, 3-sentence summary of the following research paper's main objective and findings based on its introduction/abstract. Do not include any conversational filler, just the summary.\n\nPaper text:\n{intro_text}"
    
    try:
        import ollama
        client = ollama.Client(host=OLLAMA_HOST)
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.get('message', {}).get('content')
        if answer:
            return answer.strip()
    except Exception:
        pass
        
    # Fallback to sumy text rank if Ollama is unreachable
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.text_rank import TextRankSummarizer

    try:
        parser = PlaintextParser.from_string(intro_text, Tokenizer("english"))
        summarizer = TextRankSummarizer()
        summary_sentences = summarizer(parser.document, sentence_count)
        
        final_summary = []
        for sentence in summary_sentences:
            if len(str(sentence).split()) > 8:
                final_summary.append(str(sentence))
        return " ".join(final_summary)
    except Exception:
        return "Summary could not be generated."