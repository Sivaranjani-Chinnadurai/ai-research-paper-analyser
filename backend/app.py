from flask import Flask, request, render_template, redirect, session, send_from_directory, url_for, abort, jsonify
import os
import sqlite3
import uuid
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from backend.utils.pdf_extractor import extract_text_from_pdf, extract_text_by_page
from backend.utils.preprocess import clean_text
from backend.utils.summarizer import generate_summary
from backend.utils.keywords import extract_keywords
from backend.utils.similarity import find_similar_docs
from backend.database import init_db
from backend.utils.rag import answer_question
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "secret123")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()


@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT paper_id, filename, summary, keywords, uploaded_at, pages, status FROM history WHERE username=? ORDER BY uploaded_at DESC", (session['user'],))
    papers = cursor.fetchall()
    conn.close()

    stats = {
        'papers': len(papers),
        'questions': 0,
        'sessions': len(papers),
        'recent_activity': len([p for p in papers if p[4] and datetime.fromisoformat(p[4]) >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)])
    }

    return render_template("index.html", papers=papers, stats=stats)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/")
        else:
            return "Invalid credentials ❌"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        username = request.form["username"]
        password = request.form["password"]
        phone = request.form["phone"]
        dob = request.form["dob"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (first_name, last_name, username, password, phone, dob)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, username, password, phone, dob))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")




@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")

    username = session["user"]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT first_name, last_name, username, phone, dob 
        FROM users WHERE username=?
    """, (username,))
    
    user = cursor.fetchone()
    conn.close()

    if user:
        return render_template(
            "profile.html",
            first_name=user[0],
            last_name=user[1],
            username=user[2],
            phone=user[3],
            dob=user[4]
        )
    else:
        return "User not found"




@app.route("/upload", methods=["POST"])
def upload_file():
    if "user" not in session:
        return redirect("/login")

    if "file" not in request.files:
        return "No file uploaded"

    file = request.files["file"]

    if file.filename == "":
        return "Empty filename"

    paper_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    pages = None
    extracted_text = ''
    try:
        extracted_text = extract_text_from_pdf(file_path)
        pages = len(extract_text_by_page(file_path))
    except Exception:
        pages = None

    cleaned_text = clean_text(extracted_text)
    summary = generate_summary(extracted_text)
    keywords = extract_keywords(cleaned_text)
    similar_docs = find_similar_docs(cleaned_text)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO history (username, paper_id, filename, summary, keywords, uploaded_at, pages, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session["user"],
        paper_id,
        file.filename,
        summary,
        ", ".join(keywords),
        datetime.utcnow().isoformat(),
        pages,
        'ready'
    ))

    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        summary=summary,
        keywords=", ".join(keywords),
        similar_docs=similar_docs,
        cleaned_text=cleaned_text[:500],
        user=session["user"]
    )


@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    paper_id = data.get('paper_id') or data.get('paper')
    question = data.get('question')
    if not paper_id:
        return jsonify({'success': False, 'error': 'paper_id is required'}), 400
    if not question or not question.strip():
        return jsonify({'success': False, 'error': 'question is required'}), 400

    if 'user' not in session:
        return jsonify({'success': False, 'error': 'unauthenticated'}), 401

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT filename FROM history WHERE username=? AND paper_id=?', (session['user'], paper_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'success': False, 'error': 'The selected paper could not be found.'}), 404

    file_path = os.path.join(UPLOAD_FOLDER, row[0])
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'error': 'The selected paper file could not be found on disk.'}), 404

    res = answer_question(file_path, question)
    if not isinstance(res, dict) or not res.get('success'):
        return jsonify({'success': False, 'error': res.get('error', 'The AI service could not generate a response.'), 'sources': res.get('sources', [])}), 200

    return jsonify(res), 200




@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT paper_id, filename, summary, keywords, uploaded_at, pages, status
        FROM history
        WHERE username=?
        ORDER BY uploaded_at DESC
    """, (session["user"],))

    papers = cursor.fetchall()
    conn.close()

    stats = {
        'papers': len(papers),
        'questions': 0,
        'sessions': len(papers),
        'recent_activity': len([p for p in papers if p[4] and datetime.fromisoformat(p[4]) >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)])
    }

    return render_template("index.html", papers=papers, stats=stats)


# -------------------------
# My Papers (library)
# -------------------------
@app.route('/papers')
def papers():
    if "user" not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT paper_id, filename, summary, keywords, uploaded_at, pages FROM history WHERE username=? ORDER BY uploaded_at DESC", (session['user'],))
    rows = cursor.fetchall()
    conn.close()
    return render_template('papers.html', papers=rows)


# -------------------------
# Paper Analysis Workspace
# -------------------------
@app.route('/paper/<paper_id>')
def paper_view(paper_id):
    if "user" not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT paper_id, filename, summary, keywords FROM history WHERE username=? AND paper_id=?", (session['user'], paper_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return render_template('error.html', message='Paper not found or not analyzed yet')

    file_url = url_for('uploaded_file', filename=row[1])
    return render_template('paper.html', paper_id=row[0], filename=row[1], summary=row[2], keywords=row[3], file_url=file_url)


# -------------------------
# Serve uploaded files
# -------------------------
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception:
        abort(404)


# -------------------------
# AI Chat (UI only)
# -------------------------
@app.route('/chat')
def chat():
    if "user" not in session:
        return redirect('/login')
    # show UI; backend chat API not implemented — UI placeholder
    return render_template('chat.html')


@app.route('/api/papers')
def api_papers():
    if 'user' not in session:
        return jsonify({'error': 'unauthenticated'}), 401
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT paper_id, filename FROM history WHERE username=? ORDER BY uploaded_at DESC', (session['user'],))
    rows = cursor.fetchall()
    conn.close()
    papers = [{'paper_id': r[0], 'filename': r[1]} for r in rows]
    return jsonify({'papers': papers}), 200


# -------------------------
# Research Insights (basic)
# -------------------------
@app.route('/insights')
def insights():
    if "user" not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT keywords FROM history WHERE username=?", (session['user'],))
    rows = cursor.fetchall()
    conn.close()

    # simple aggregation of keywords
    kw_counts = {}
    for r in rows:
        if not r or not r[0]:
            continue
        for kw in r[0].split(','):
            k = kw.strip().lower()
            if not k: continue
            kw_counts[k] = kw_counts.get(k, 0) + 1

    # sort by frequency
    items = sorted(kw_counts.items(), key=lambda x: x[1], reverse=True)
    return render_template('insights.html', keywords=items)


if __name__ == "__main__":
    app.run(debug=True)