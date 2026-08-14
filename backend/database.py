import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'users.db')

SCHEMA_UPDATES = {
    'history': {
        'paper_id': 'TEXT',
        'uploaded_at': 'TEXT',
        'pages': 'INTEGER',
        'status': 'TEXT'
    }
}


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        phone TEXT,
        dob TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        paper_id TEXT UNIQUE,
        filename TEXT,
        summary TEXT,
        keywords TEXT,
        uploaded_at TEXT,
        pages INTEGER,
        status TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id TEXT,
        username TEXT,
        role TEXT,
        content TEXT,
        sources TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("PRAGMA table_info(history)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    for column, column_type in SCHEMA_UPDATES['history'].items():
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE history ADD COLUMN {column} {column_type}")

    conn.commit()
    conn.close()