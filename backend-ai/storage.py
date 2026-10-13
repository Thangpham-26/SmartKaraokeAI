"""Store analysis summaries and feedback locally; never store raw audio."""
import json
import os
import sqlite3
from pathlib import Path
from uuid import uuid4


def connect():
    path = Path(os.environ.get("SMARTKARAOKE_DB", Path(__file__).parent / "data" / "smartkaraoke.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    return db


def save_analysis(payload):
    db = connect()
    try:
        with db:
            db.execute("INSERT INTO analyses VALUES (?, ?)", (payload["analysis_id"], json.dumps(payload, allow_nan=False)))
    finally:
        db.close()


def get_analysis(analysis_id):
    db = connect()
    try:
        row = db.execute("SELECT payload FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        db.close()


def save_feedback(payload):
    feedback_id = str(uuid4())
    db = connect()
    try:
        with db:
            db.execute("INSERT INTO feedback VALUES (?, ?)", (feedback_id, json.dumps(payload, allow_nan=False)))
    finally:
        db.close()
    return feedback_id
