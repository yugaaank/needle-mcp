import hashlib
import json
import sqlite3
import os

CACHE_DIR = os.path.expanduser("~/.cache/needle")
DB_PATH = os.path.join(CACHE_DIR, "mcp_cache.db")

def init_db():
    os.makedirs(CACHE_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mcp_cache (
                key TEXT PRIMARY KEY,
                output TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def get_cached_response(key_data: dict) -> str | None:
    try:
        init_db()
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT output FROM mcp_cache WHERE key = ?", (key_hash,))
            row = cursor.fetchone()
            if row:
                return row[0]
    except Exception:
        pass
    return None

def set_cached_response(key_data: dict, output: str):
    try:
        init_db()
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO mcp_cache (key, output, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key_hash, output)
            )
            conn.commit()
    except Exception:
        pass
