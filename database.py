
import sqlite3
from pathlib import Path

APP_DIR = Path.home() / ".ahmad_intelligence"
APP_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DIR / "chats.db"


def connect():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_message(conversation_id, role, content):
    with connect() as db:
        db.execute(
            """INSERT INTO messages
               (conversation_id, role, content)
               VALUES (?, ?, ?)""",
            (conversation_id, role, content)
        )


def get_conversations():
    with connect() as db:
        return db.execute("""
            SELECT conversation_id, MAX(created_at) AS last_message
            FROM messages
            GROUP BY conversation_id
            ORDER BY last_message DESC
        """).fetchall()


def get_messages(conversation_id):
    with connect() as db:
        return db.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id
        """, (conversation_id,)).fetchall()
