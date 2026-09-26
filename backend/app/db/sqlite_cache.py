import aiosqlite
import json
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.config import settings

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources_json TEXT,
    is_insufficient_info INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS query_cache (
    query_hash TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    response TEXT NOT NULL,
    citations_json TEXT,
    model_used TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT,
    size TEXT,
    pages INTEGER DEFAULT 1,
    status TEXT NOT NULL,
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    doc_name TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

async def init_sqlite_db():
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()

# --- Document Operations ---
async def save_document(doc_id: str, name: str, path: str, size: str, pages: int, status: str, progress: int = 0):
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO documents (id, name, path, size, pages, status, progress)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, name, path, size, pages, status, progress)
        )
        await db.commit()

async def update_document_status(doc_id: str, status: str, progress: int = 100):
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute(
            "UPDATE documents SET status = ?, progress = ? WHERE id = ?",
            (status, progress, doc_id)
        )
        await db.commit()

async def get_all_documents() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM documents ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def delete_document_and_chunks(doc_id: str) -> bool:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await db.execute("DELETE FROM document_chunks WHERE doc_id = ?", (doc_id,))
        await db.commit()
        return True

# --- Chunk Operations ---
async def save_chunks(chunks: List[Dict[str, Any]]):
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        for chunk in chunks:
            emb_str = json.dumps(chunk.get("embedding", []))
            await db.execute(
                """
                INSERT OR REPLACE INTO document_chunks (id, doc_id, doc_name, page_number, chunk_index, content, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk["id"],
                    chunk["doc_id"],
                    chunk["doc_name"],
                    chunk["page_number"],
                    chunk["chunk_index"],
                    chunk["content"],
                    emb_str
                )
            )
        await db.commit()

async def get_all_chunks(doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM document_chunks"
        params = ()
        if doc_id:
            query += " WHERE doc_id = ?"
            params = (doc_id,)
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                item = dict(row)
                if item["embedding_json"]:
                    item["embedding"] = json.loads(item["embedding_json"])
                else:
                    item["embedding"] = []
                result.append(item)
            return result

# --- Query Cache ---
def hash_query(query: str, doc_filter: Optional[str] = None) -> str:
    key = f"{query.strip().lower()}|{doc_filter or 'all'}"
    return hashlib.sha256(key.encode()).hexdigest()

async def get_cached_query(query_hash: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM query_cache WHERE query_hash = ?", (query_hash,)) as cursor:
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                d["citations"] = json.loads(d["citations_json"]) if d["citations_json"] else []
                return d
            return None

async def set_cached_query(query_hash: str, query_text: str, response: str, citations: list, model_used: str):
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO query_cache (query_hash, query_text, response, citations_json, model_used)
            VALUES (?, ?, ?, ?, ?)
            """,
            (query_hash, query_text, response, json.dumps(citations), model_used)
        )
        await db.commit()

# --- Sessions & History ---
async def create_chat_session(session_id: str, title: str = "New Chat Session") -> Dict[str, Any]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO chat_sessions (id, title) VALUES (?, ?)",
            (session_id, title)
        )
        await db.commit()
    return {"id": session_id, "title": title}

async def get_all_chat_sessions() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM chat_sessions ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def delete_chat_session(session_id: str) -> bool:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        await db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        await db.commit()
        return True

async def save_chat_message(msg_id: str, session_id: str, role: str, content: str, sources: list = None, is_insufficient: bool = False):
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        # Auto-create session if not present
        await db.execute(
            "INSERT OR IGNORE INTO chat_sessions (id, title) VALUES (?, ?)",
            (session_id, f"Session {session_id[:6]}")
        )
        await db.execute(
            """
            INSERT OR REPLACE INTO chat_messages (id, session_id, role, content, sources_json, is_insufficient_info)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (msg_id, session_id, role, content, json.dumps(sources or []), 1 if is_insufficient else 0)
        )
        await db.commit()

async def get_chat_history(session_id: str = "default") -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                item = dict(r)
                item["citations"] = json.loads(item["sources_json"]) if item["sources_json"] else []
                item["isInsufficientInfo"] = bool(item["is_insufficient_info"])
                res.append(item)
            return res
