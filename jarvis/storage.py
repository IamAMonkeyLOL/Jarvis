"""SQLite persistence; no cloud account or external database is required."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'complete', 'interrupted', 'error')),
                    model TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS messages_by_chat ON messages(conversation_id, id);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def conversations(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM conversations ORDER BY updated_at DESC, id DESC")]

    def create(self, title="New conversation"):
        stamp = now()
        with self.connect() as db:
            return db.execute("INSERT INTO conversations(title,created_at,updated_at) VALUES(?,?,?)", (title, stamp, stamp)).lastrowid

    def messages(self, conversation_id):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (conversation_id,)).fetchall()
        return [dict(row, metadata=json.loads(row["metadata"])) for row in rows]

    def add(self, conversation_id, role, content, status="complete", model=None):
        stamp = now()
        with self.connect() as db:
            first = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=?", (conversation_id,)).fetchone()[0] == 0
            cursor = db.execute("INSERT INTO messages(conversation_id,role,content,status,model,created_at) VALUES(?,?,?,?,?,?)", (conversation_id, role, content, status, model, stamp))
            if first and role == "user":
                title = " ".join(content.split())[:60] or "New conversation"
                db.execute("UPDATE conversations SET title=?,updated_at=? WHERE id=?", (title, stamp, conversation_id))
            else:
                db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (stamp, conversation_id))
            return cursor.lastrowid

    def update(self, message_id, content, status, metadata=None):
        with self.connect() as db:
            db.execute("UPDATE messages SET content=?,status=?,metadata=? WHERE id=?", (content, status, json.dumps(metadata or {}), message_id))
            db.execute("UPDATE conversations SET updated_at=? WHERE id=(SELECT conversation_id FROM messages WHERE id=?)", (now(), message_id))

    def delete(self, conversation_id):
        with self.connect() as db:
            db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))

    def recover_pending(self):
        """Only call when no generation is running in this single-user app."""
        with self.connect() as db:
            db.execute("UPDATE messages SET status='interrupted' WHERE status='pending'")

    def export(self, conversation_id):
        with self.connect() as db:
            conversation = db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        if conversation is None:
            raise ValueError("Conversation not found.")
        return json.dumps({"format": "jarvis-chat-v1", "conversation": dict(conversation), "messages": self.messages(conversation_id)}, indent=2, ensure_ascii=False)

    def backup(self, destination):
        """Use SQLite's backup API so WAL contents are included."""
        target = Path(destination)
        if target.resolve() == self.path.resolve():
            raise ValueError("Choose a different backup destination.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as source:
            with sqlite3.connect(target) as output:
                source.backup(output)
        return target
