"""SQLite helpers and schema for CareerCompass AI."""
from contextlib import closing
from pathlib import Path
import sqlite3


def connect_db(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect_db(path)) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            answers TEXT NOT NULL, results TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS roadmap_progress (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            career_slug TEXT NOT NULL, task_id TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, career_slug, task_id)
        );
        CREATE INDEX IF NOT EXISTS idx_assessments_user ON assessments(user_id, created_at DESC);
        """)
        db.commit()
