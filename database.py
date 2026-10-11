
import sqlite3
import uuid
from pathlib import Path

APP_DIR = Path.home() / ".ahmad_intelligence"
APP_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DIR / "chats.db"


def connect():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    return db


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

        db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                instructions TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New conversation',
                project_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
                    ON DELETE SET NULL
            )
        """)

        # Create a default project for existing and new chats.
        db.execute("""
            INSERT OR IGNORE INTO projects (id, name, instructions)
            VALUES ('default', 'General', '')
        """)

        # Register conversations that already exist in messages.
        existing_ids = db.execute("""
            SELECT DISTINCT conversation_id FROM messages
        """).fetchall()

        for (conversation_id,) in existing_ids:
            db.execute("""
                INSERT OR IGNORE INTO conversations
                    (id, title, project_id)
                VALUES (?, 'New conversation', 'default')
            """, (conversation_id,))

        # Ensure newly created tables know about the latest messages.
        db.execute("""
            UPDATE conversations
            SET updated_at = COALESCE(
                (SELECT MAX(created_at)
                 FROM messages
                 WHERE messages.conversation_id = conversations.id),
                created_at
            )
        """)


def create_project(name, instructions=""):
    project_id = str(uuid.uuid4())

    with connect() as db:
        db.execute("""
            INSERT INTO projects (id, name, instructions)
            VALUES (?, ?, ?)
        """, (project_id, name.strip(), instructions.strip()))

    return project_id


def get_projects():
    with connect() as db:
        return db.execute("""
            SELECT id, name, instructions
            FROM projects
            ORDER BY name COLLATE NOCASE
        """).fetchall()


def update_project(project_id, name, instructions):
    with connect() as db:
        db.execute("""
            UPDATE projects
            SET name = ?, instructions = ?
            WHERE id = ?
        """, (name.strip(), instructions.strip(), project_id))


def create_conversation(project_id="default", title="New conversation"):
    conversation_id = str(uuid.uuid4())

    with connect() as db:
        db.execute("""
            INSERT INTO conversations (id, title, project_id)
            VALUES (?, ?, ?)
        """, (conversation_id, title, project_id))

    return conversation_id


def update_conversation_title(conversation_id, title):
    with connect() as db:
        db.execute("""
            UPDATE conversations
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (title, conversation_id))


def move_conversation_to_project(conversation_id, project_id):
    with connect() as db:
        db.execute("""
            UPDATE conversations
            SET project_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (project_id, conversation_id))


def get_conversations(project_id=None):
    with connect() as db:
        if project_id is None:
            return db.execute("""
                SELECT id, title, project_id, updated_at
                FROM conversations
                ORDER BY updated_at DESC, created_at DESC
            """).fetchall()

        return db.execute("""
            SELECT id, title, project_id, updated_at
            FROM conversations
            WHERE project_id = ?
            ORDER BY updated_at DESC, created_at DESC
        """, (project_id,)).fetchall()


def save_message(conversation_id, role, content):
    with connect() as db:
        db.execute("""
            INSERT OR IGNORE INTO conversations (id, project_id)
            VALUES (?, 'default')
        """, (conversation_id,))

        db.execute("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES (?, ?, ?)
        """, (conversation_id, role, content))

        db.execute("""
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (conversation_id,))


def get_messages(conversation_id):
    with connect() as db:
        return db.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id
        """, (conversation_id,)).fetchall()


def get_project_instructions_for_conversation(conversation_id):
    with connect() as db:
        row = db.execute("""
            SELECT projects.instructions
            FROM conversations
            LEFT JOIN projects
                ON conversations.project_id = projects.id
            WHERE conversations.id = ?
        """, (conversation_id,)).fetchone()

        return row[0] if row and row[0] else ""
