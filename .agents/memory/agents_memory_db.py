import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

DEFAULT_DB_PATH = str(Path(__file__).resolve().parent / "core_state.db")

def get_connection(db_path=None):
    db_path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db(db_path=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            category TEXT,
            content TEXT,
            embedding BLOB,
            decay_factor REAL DEFAULT 1.0,
            source_ide TEXT,
            content_hash TEXT UNIQUE
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS constraints (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            constraint_type TEXT,
            description TEXT,
            severity TEXT,
            active_status INTEGER DEFAULT 1
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dedup_hashes (
            hash_val TEXT PRIMARY KEY
        );
    """)
    conn.commit()
    conn.close()

def store_memory(category, content, source_ide, db_path=None):
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    
    content_hash = hashlib.sha256(content.strip().encode('utf-8')).hexdigest()
    
    cur.execute("SELECT id FROM memories WHERE content_hash = ?", (content_hash,))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return {"status": "deduplicated", "memory_id": existing[0]}
        
    memory_id = f"mem_{content_hash[:8]}"
    timestamp = datetime.utcnow().isoformat()
    
    cur.execute(
        "INSERT INTO memories (id, timestamp, category, content, decay_factor, source_ide, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (memory_id, timestamp, category, content, 1.0, source_ide, content_hash)
    )
    conn.commit()
    conn.close()
    return {"status": "created", "memory_id": memory_id}

def assert_constraint(constraint_type, description, severity, db_path=None):
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    
    desc_hash = hashlib.sha256(description.strip().encode('utf-8')).hexdigest()
    constraint_id = f"const_{desc_hash[:8]}"
    created_at = datetime.utcnow().isoformat()
    
    cur.execute(
        "INSERT OR REPLACE INTO constraints (id, created_at, constraint_type, description, severity, active_status) VALUES (?, ?, ?, ?, ?, 1)",
        (constraint_id, created_at, constraint_type, description, severity)
    )
    conn.commit()
    conn.close()
    return {"status": "created", "constraint_id": constraint_id}

def query_memory(query="", max_results=5, db_path=None):
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    
    active_constraints = [
        f"[{row[2]}] ({row[0]}): {row[1]}"
        for row in cur.execute(
            "SELECT constraint_type, description, severity FROM constraints WHERE active_status = 1 ORDER BY id DESC"
        ).fetchall()
    ]
    
    memories = cur.execute(
        "SELECT category, content, source_ide, decay_factor FROM memories ORDER BY id DESC LIMIT ?",
        (max_results,)
    ).fetchall()
    
    conn.close()
    
    return {
        "active_constraints": active_constraints,
        "matched_memories": [
            f"[{cat}] (IDE: {ide} | Weight: {weight:.2f}): {content}"
            for cat, content, ide, weight in memories
        ]
    }
