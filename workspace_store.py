"""Durable dashboard activity snapshots, stored outside Git in SQLite."""
import json
import os
import sqlite3
from contextlib import closing


DB_PATH = os.environ.get("AIRMCP_WORKSPACE_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "workspace_state.sqlite3")
SECTIONS = {"chat", "history", "runs", "drafts"}


def _connect():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS snapshots (section TEXT PRIMARY KEY, updated_at INTEGER NOT NULL, payload TEXT NOT NULL)")
    return db


def load():
    if not os.path.exists(DB_PATH):
        return {}
    with closing(_connect()) as db:
        rows = db.execute("SELECT section, updated_at, payload FROM snapshots").fetchall()
    return {section: {"updatedAt": stamp, "value": json.loads(payload)}
            for section, stamp, payload in rows if section in SECTIONS}


def save(section, updated_at, value):
    if section not in SECTIONS:
        raise ValueError("Unknown workspace section")
    if not isinstance(updated_at, int) or isinstance(updated_at, bool) or updated_at <= 0:
        raise ValueError("updatedAt must be a positive integer")
    if section in {"chat", "drafts"} and not isinstance(value, dict):
        raise ValueError(section + " must be an object")
    if section in {"history", "runs"} and not isinstance(value, list):
        raise ValueError(section + " must be a list")
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    with closing(_connect()) as db:
        with db:
            db.execute("""INSERT INTO snapshots(section, updated_at, payload) VALUES (?, ?, ?)
                ON CONFLICT(section) DO UPDATE SET updated_at=excluded.updated_at, payload=excluded.payload
                WHERE excluded.updated_at > snapshots.updated_at""", (section, updated_at, payload))
            row = db.execute("SELECT updated_at FROM snapshots WHERE section=?", (section,)).fetchone()
    return {"saved": row[0] == updated_at, "updatedAt": row[0]}
