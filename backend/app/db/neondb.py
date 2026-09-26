import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

logger = logging.getLogger("DocuMind.NeonDB")

class NeonCloudDB:
    """
    Cloud Persistent Vector & Document Sync Layer via NeonDB Serverless PostgreSQL + pgvector.
    
    Provides:
    - Connection health check
    - Auto-provisioning of pgvector extension and document_embeddings table
    - Batch synchronization of chunks and 384-dimensional embeddings
    - Real-time sync status reporting for offline/online transitions
    """
    def __init__(self):
        self.database_url = settings.NEON_DATABASE_URL
        self.enabled = bool(self.database_url and settings.ENABLE_CLOUD_SYNC)
        self.is_connected = False
        self.last_sync_time: Optional[str] = None
        self.total_synced_chunks = 0

    def _normalize_pg_url(self, url: str) -> str:
        """Converts postgres:// to postgresql:// and removes unsupported asyncpg params like channel_binding."""
        if not url:
            return ""
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            p = urlparse(url)
            q = parse_qs(p.query)
            q.pop("channel_binding", None)
            return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q, doseq=True), p.fragment))
        except Exception:
            return url

    async def check_connection(self) -> bool:
        if not self.database_url:
            self.is_connected = False
            return False
        try:
            import asyncpg
            clean_url = self._normalize_pg_url(self.database_url)
            conn = await asyncpg.connect(clean_url, timeout=5.0)
            await conn.execute("SELECT 1")
            await conn.close()
            self.is_connected = True
            return True
        except Exception as e:
            logger.info(f"NeonDB cloud check: {e}")
            self.is_connected = False
            return False

    async def ensure_schema(self, conn) -> None:
        """Provisions pgvector extension and document_embeddings table on NeonDB."""
        try:
            # Enable pgvector if permitted
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_embeddings (
                    id TEXT PRIMARY KEY,
                    doc_name TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(384),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        except Exception as e:
            logger.warning(f"pgvector extension or table creation note: {e}")
            # Fallback table storing embedding as jsonb / text if vector extension is restricted
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_embeddings (
                    id TEXT PRIMARY KEY,
                    doc_name TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    async def sync_chunks_to_cloud(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronizes local document chunks and embeddings to NeonDB cloud storage.
        """
        if not self.database_url:
            return {"synced": False, "reason": "NEON_DATABASE_URL not configured"}

        try:
            import asyncpg
            clean_url = self._normalize_pg_url(self.database_url)
            conn = await asyncpg.connect(clean_url, timeout=8.0)
            await self.ensure_schema(conn)

            count = 0
            for chunk in chunks:
                emb = chunk.get("embedding", [])
                emb_str = f"[{','.join(str(round(x, 6)) for x in emb)}]" if emb else None
                
                try:
                    # Try inserting with vector format
                    await conn.execute(
                        """
                        INSERT INTO document_embeddings (id, doc_name, page_number, content, embedding)
                        VALUES ($1, $2, $3, $4, $5::vector)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding;
                        """,
                        chunk["id"],
                        chunk["doc_name"],
                        chunk["page_number"],
                        chunk["content"],
                        emb_str
                    )
                    count += 1
                except Exception:
                    # Fallback inserting embedding as plain text/json
                    await conn.execute(
                        """
                        INSERT INTO document_embeddings (id, doc_name, page_number, content, embedding)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding;
                        """,
                        chunk["id"],
                        chunk["doc_name"],
                        chunk["page_number"],
                        chunk["content"],
                        json.dumps(emb)
                    )
                    count += 1

            await conn.close()
            self.is_connected = True
            self.total_synced_chunks += count
            self.last_sync_time = datetime.now().isoformat()
            logger.info(f"Successfully synced {count} chunks to NeonDB cloud.")
            return {
                "synced": True,
                "synced_count": count,
                "last_sync_time": self.last_sync_time,
                "database": "NeonDB Serverless PostgreSQL"
            }
        except Exception as e:
            logger.warning(f"Error syncing chunks to NeonDB: {e}")
            self.is_connected = False
            return {"synced": False, "error": str(e)}

    def get_sync_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "configured": bool(self.database_url),
            "is_connected": self.is_connected,
            "last_sync_time": self.last_sync_time,
            "total_synced_chunks": self.total_synced_chunks
        }

neon_db = NeonCloudDB()
