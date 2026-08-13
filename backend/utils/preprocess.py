import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Ensure required NLTK data is available; try to avoid downloading at import time when possible
try:
    nltk.data.find('tokenizers/punkt')
except Exception:
    try:
        nltk.download('punkt')
    except Exception:
        pass

try:
    nltk.data.find('corpora/stopwords')
except Exception:
    try:
        nltk.download('stopwords')
    except Exception:
        pass

stop_words = set()
try:
    stop_words = set(stopwords.words('english'))
except Exception:
    stop_words = set()

def clean_text(text):
    # Lowercase
    text = text.lower()
    
    # Remove special characters and numbers
    text = re.sub(r'[^a-z\s]', '', text)
    
    # Tokenize
    words = word_tokenize(text)
    
    # Remove stopwords
    filtered_words = [word for word in words if word not in stop_words]
    
    # Join back
    cleaned_text = " ".join(filtered_words)
    
    return cleaned_text