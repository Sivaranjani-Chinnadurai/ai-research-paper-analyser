# ResearchAI — AI-Powered Research Paper Analysis

ResearchAI is a premium, polished AI research assistant designed to help you quickly understand research papers. It combines local TF-IDF document chunking and retrieval (RAG) with the powerful **Ollama** engine to provide highly accurate, grounded answers with precise page citations.

## Features
- **Professional Dashboard:** View aggregated stats, recent uploads, and drop PDFs right into your workspace.
- **AI Paper Assistant:** Split-view analysis interface. Ask questions and get answers grounded *only* in the paper's context.
- **Source Citations:** Every AI answer includes direct page references so you can verify the information.
- **My Papers Library:** Manage all your uploaded PDFs and quickly resume analysis.
- **Research Insights:** Extracted keywords and topic cross-referencing.
- **Dark & Light Mode:** Polished, responsive UI with state-of-the-art glassmorphism and modern aesthetics.

## Architecture & Tech Stack
- **Backend:** Python (Flask), SQLite
- **Frontend:** Vanilla HTML/CSS/JS with custom dark mode and responsive flex/grid layouts.
- **Document Processing:** PyMuPDF (text extraction), NLTK, Sumy (summaries), scikit-learn (TF-IDF).
- **LLM Provider:** Ollama (default model: `llama3.2:3b`).

## Installation & Setup (Windows)

1. **Install Ollama**
   Download and install Ollama for Windows from the official website.
   Verify installation:
   ```powershell
   ollama --version
   ```

2. **Pull the Model**
   Open a terminal and pull the required model:
   ```powershell
   ollama pull llama3.2:3b
   ```
   Verify it's installed:
   ```powershell
   ollama list
   ```

3. **Install Python Dependencies**
   Activate your virtual environment and install requirements:
   ```powershell
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Copy `.env.example` to `.env`. Ensure it reads:
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=llama3.2:3b
   OLLAMA_HOST=http://localhost:11434
   ```

5. **Start ResearchAI**
   From the PROJECT ROOT directory, run:
   ```powershell
   python -m backend.app
   ```
   Open `http://127.0.0.1:5000` in your browser.

## Privacy
ResearchAI runs 100% locally. Your PDFs are indexed locally using scikit-learn, and your questions are answered completely offline via Ollama. No data is sent to cloud APIs.