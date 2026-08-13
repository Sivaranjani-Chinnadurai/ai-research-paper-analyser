import fitz  # PyMuPDF
import re

def extract_text_from_pdf(file_path):
    """Backward-compatible single-string extractor (existing usage)."""
    text = ""

    doc = fitz.open(file_path)

    for page in doc:
        text += page.get_text()

    # Remove extra spaces between letters
    text = re.sub(r'\b(?:[a-zA-Z]\s){2,}[a-zA-Z]\b', 
                  lambda x: x.group(0).replace(" ", ""), text)

    # Normalize spaces
    text = re.sub(r'\s+', ' ', text)

    return text


def extract_text_by_page(file_path):
    """Return list of (page_number, text) preserving page boundaries.

    Page numbers are 1-based.
    """
    pages = []
    doc = fitz.open(file_path)
    for i, page in enumerate(doc):
        txt = page.get_text()
        # Normalize
        txt = re.sub(r'\b(?:[a-zA-Z]\s){2,}[a-zA-Z]\b', lambda x: x.group(0).replace(" ", ""), txt)
        txt = re.sub(r'\s+', ' ', txt).strip()
        pages.append((i+1, txt))

    return pages