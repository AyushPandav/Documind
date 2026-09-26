"""
DocuMind Auth — NeonDB Cloud User Store (with Connection Pooling & Offline SQLite Fallback)
=============================================================================================
Stores and manages user accounts for DocuMind.
Primary store: NeonDB Serverless PostgreSQL (with asyncpg connection pooling)
Offline fallback: Local SQLite cache (app_cache.db)
"""

import uuid
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.config import settings

logger = logging.getLogger("DocuMind.Auth.NeonUsers")

CREATE_PG_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id              VARCHAR(64) PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    full_name       VARCHAR(255) DEFAULT '',
    hashed_password TEXT NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    role            VARCHAR(50) DEFAULT 'user',
    created_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
"""

ALTER_PG_USERS_COLUMNS = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password TEXT;
"""

CREATE_SQLITE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS local_users (
    id              TEXT PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    full_name       TEXT DEFAULT '',
    hashed_password TEXT NOT NULL,
    is_active       INTEGER DEFAULT 1,
    role            TEXT DEFAULT 'user',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP
);
"""

# Global connection pool for NeonDB
_pg_pool = None


def _sanitize_pg_url(url: str) -> str:
    """Normalizes Postgres URL and removes unsupported query params like channel_binding."""
    if not url:
        return ""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    try:
        p = urlparse(url)
        q = parse_qs(p.query)
        q.pop("channel_binding", None)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q, doseq=True), p.fragment))
    except Exception:
        return url


async def get_pg_pool():
    """Returns the singleton asyncpg connection pool to NeonDB."""
    global _pg_pool
    if _pg_pool is None and settings.NEON_DATABASE_URL:
        import asyncpg
        clean_url = _sanitize_pg_url(settings.NEON_DATABASE_URL)
        try:
            _pg_pool = await asyncpg.create_pool(
                clean_url,
                min_size=1,
                max_size=10,
                command_timeout=15.0,
                timeout=10.0
            )
            logger.info("[Auth] ✓ NeonDB asyncpg connection pool created (size: 1-10)")
        except Exception as e:
            logger.warning(f"[Auth] Could not create NeonDB pool ({e})")
            _pg_pool = None
    return _pg_pool


async def close_pg_pool():
    """Gracefully closes the connection pool."""
    global _pg_pool
    if _pg_pool is not None:
        try:
            await _pg_pool.close()
            logger.info("[Auth] NeonDB pool closed.")
        except Exception:
            pass
        _pg_pool = None


async def _init_sqlite_users():
    import aiosqlite
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute(CREATE_SQLITE_USERS_TABLE)
        await db.commit()


async def ensure_users_table() -> bool:
    """
    Initializes the users schema. Tries NeonDB first; if offline, initializes SQLite.
    Returns True if NeonDB is online.
    """
    if settings.NEON_DATABASE_URL:
        try:
            logger.info("[Auth] Connecting to NeonDB Cloud PostgreSQL to verify 'users' table...")
            pool = await get_pg_pool()
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute(CREATE_PG_USERS_TABLE)
                    await conn.execute(ALTER_PG_USERS_COLUMNS)
                logger.info("[Auth] ✅ NeonDB 'users' table initialized & online (Cloud PostgreSQL)")
                return True
        except Exception as e:
            logger.warning(f"[Auth] NeonDB unavailable for users ({e}) — activating local SQLite store")

    try:
        await _init_sqlite_users()
        logger.info("[Auth] ✓ Local SQLite user store initialized (offline mode)")
    except Exception as e:
        logger.error(f"[Auth] Failed to initialize SQLite user store: {e}")
    return False


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetches user record by email from NeonDB, falling back to SQLite."""
    clean_email = email.lower().strip()

    if settings.NEON_DATABASE_URL:
        try:
            pool = await get_pg_pool()
            if pool:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT id, email, full_name, hashed_password, is_active, role, created_at, last_login 
                        FROM users WHERE email = $1
                        """,
                        clean_email
                    )
                    if row:
                        d = dict(row)
                        d["source"] = "neondb"
                        return d
        except Exception as e:
            logger.warning(f"[Auth] NeonDB fetch error ({e}), trying SQLite...")

    # Fallback SQLite
    try:
        import aiosqlite
        await _init_sqlite_users()
        async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, email, full_name, hashed_password, is_active, role, created_at, last_login 
                FROM local_users WHERE email = ?
                """,
                (clean_email,)
            )
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                d["source"] = "sqlite_local"
                return d
    except Exception as e:
        logger.error(f"[Auth] SQLite fetch error: {e}")

    return None


async def get_user_by_id(user_id: Union[str, int]) -> Optional[Dict[str, Any]]:
    """Fetches user record by ID from NeonDB, falling back to SQLite."""
    uid_str = str(user_id)
    if settings.NEON_DATABASE_URL:
        try:
            pool = await get_pg_pool()
            if pool:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT id, email, full_name, hashed_password, is_active, role, created_at, last_login 
                        FROM users WHERE id = $1
                        """,
                        uid_str
                    )
                    if row:
                        d = dict(row)
                        d["source"] = "neondb"
                        return d
        except Exception as e:
            logger.warning(f"[Auth] NeonDB fetch by ID error ({e}), trying SQLite...")

    try:
        import aiosqlite
        await _init_sqlite_users()
        async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, email, full_name, hashed_password, is_active, role, created_at, last_login 
                FROM local_users WHERE id = ?
                """,
                (uid_str,)
            )
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                d["source"] = "sqlite_local"
                return d
    except Exception as e:
        logger.error(f"[Auth] SQLite fetch by ID error: {e}")

    return None


async def create_user(
    email: str,
    full_name: str,
    hashed_pw: str,
    role: str = "user"
) -> Optional[Dict[str, Any]]:
    """
    Creates a new user record.
    Inserts into NeonDB if connected, and mirrors into local SQLite for offline resilience.
    """
    clean_email = email.lower().strip()
    clean_name = full_name.strip()
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    result = None

    if settings.NEON_DATABASE_URL:
        try:
            pool = await get_pg_pool()
            if pool:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        INSERT INTO users (id, email, full_name, hashed_password, role, is_active)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (email) DO NOTHING
                        RETURNING id, email, full_name, is_active, role, created_at
                        """,
                        user_id, clean_email, clean_name, hashed_pw, role, True
                    )
                    if row:
                        result = dict(row)
                        result["source"] = "neondb"
                        logger.info(f"[Auth] ✅ User created on NeonDB: '{clean_email}' (ID: {result['id']})")
        except Exception as e:
            logger.warning(f"[Auth] NeonDB create_user failed ({e}) — falling back to SQLite")

    # Local SQLite mirror / fallback
    try:
        import aiosqlite
        await _init_sqlite_users()
        async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO local_users (id, email, full_name, hashed_password, role, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (user_id, clean_email, clean_name, hashed_pw, role)
            )
            await db.commit()
            if not result:
                result = {
                    "id": user_id,
                    "email": clean_email,
                    "full_name": clean_name,
                    "is_active": True,
                    "role": role,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source": "sqlite_local"
                }
                logger.info(f"[Auth] ✓ User created in local SQLite: '{clean_email}'")
    except Exception as e:
        logger.error(f"[Auth] SQLite create_user error: {e}")

    return result


async def update_last_login(user_id: Union[str, int]) -> None:
    """Updates the last_login timestamp for a user."""
    uid_str = str(user_id)
    now = datetime.now(timezone.utc)
    if settings.NEON_DATABASE_URL:
        try:
            pool = await get_pg_pool()
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute("UPDATE users SET last_login = $1 WHERE id = $2", now.replace(tzinfo=None), uid_str)
        except Exception:
            pass

    try:
        import aiosqlite
        async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
            await db.execute("UPDATE local_users SET last_login = ? WHERE id = ?", (now.isoformat(), uid_str))
            await db.commit()
    except Exception:
        pass
