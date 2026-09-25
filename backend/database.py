import os
import sqlite3
import hashlib
import hmac
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import jwt

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from config import (
    DATABASE_URL,
    DATABASE_PATH,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRATION_DAYS,
)

logger = logging.getLogger("resumefit.database")

def is_using_postgres(db_url: Optional[str] = None) -> bool:
    url = db_url or DATABASE_URL
    return bool(url and url.strip().startswith(("postgres://", "postgresql://")) and PSYCOPG2_AVAILABLE)

def get_postgres_connection(db_url: Optional[str] = None):
    raw_url = (db_url or DATABASE_URL).strip()
    # Normalize postgres:// to postgresql:// if needed
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    
    # Supabase strictly requires SSL. Append sslmode=require if omitted in URI
    kwargs = {"cursor_factory": psycopg2.extras.RealDictCursor}
    if "sslmode=" not in raw_url:
        kwargs["sslmode"] = "require"

    conn = psycopg2.connect(raw_url, **kwargs)
    conn.autocommit = True
    return conn

def get_sqlite_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = db_path or DATABASE_PATH
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db(db_path: Optional[str] = None, db_url: Optional[str] = None) -> None:
    """Initializes tables in either Supabase PostgreSQL or local SQLite."""
    if is_using_postgres(db_url):
        logger.info("Initializing tables in Supabase PostgreSQL...")
        conn = get_postgres_connection(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        is_pro INTEGER NOT NULL DEFAULT 0,
                        pro_code_used TEXT DEFAULT NULL,
                        pro_redeemed_at TEXT DEFAULT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                    ALTER TABLE users ENABLE ROW LEVEL SECURITY;

                    CREATE TABLE IF NOT EXISTS scan_files (
                        scan_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_bytes BYTEA NOT NULL,
                        file_type TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_scan_files_id ON scan_files(scan_id);
                """)
            logger.info("Supabase PostgreSQL tables & RLS verified successfully.")
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection(db_path)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        is_pro INTEGER NOT NULL DEFAULT 0,
                        pro_code_used TEXT DEFAULT NULL,
                        pro_redeemed_at TEXT DEFAULT NULL,
                        created_at TEXT NOT NULL
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scan_files (
                        scan_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_bytes BLOB NOT NULL,
                        file_type TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_scan_files_id ON scan_files(scan_id);
                """)
        finally:
            conn.close()

# Password Security (PBKDF2-HMAC-SHA256)
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations=100_000
    )
    return f"{salt.hex()}${key.hex()}"

def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        salt_hex, key_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        computed_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations=100_000
        )
        return hmac.compare_digest(computed_key.hex(), key_hex)
    except Exception:
        return False

# JWT Helpers
def create_access_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=JWT_EXPIRATION_DAYS)
    payload = {
        "sub": str(user_id),
        "email": email.lower().strip(),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

# User Database Queries
def format_user_dict(row: Any) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "is_pro": bool(row["is_pro"]),
        "pro_code_used": row["pro_code_used"],
        "pro_redeemed_at": row["pro_redeemed_at"],
        "created_at": str(row["created_at"])
    }

def create_user(name: str, email: str, password_hash: str, db_path: Optional[str] = None, db_url: Optional[str] = None) -> Dict[str, Any]:
    clean_email = email.lower().strip()
    clean_name = name.strip()
    now_str = datetime.now(timezone.utc).isoformat()

    if is_using_postgres(db_url):
        conn = get_postgres_connection(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (name, email, password_hash, is_pro, created_at)
                    VALUES (%s, %s, %s, 0, %s)
                    RETURNING *;
                    """,
                    (clean_name, clean_email, password_hash, now_str)
                )
                row = cur.fetchone()
                return format_user_dict(row)
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection(db_path)
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO users (name, email, password_hash, is_pro, created_at)
                    VALUES (?, ?, ?, 0, ?)
                    """,
                    (clean_name, clean_email, password_hash, now_str)
                )
                user_id = cursor.lastrowid
                row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                return format_user_dict(row)
        finally:
            conn.close()

def get_user_by_email(email: str, db_path: Optional[str] = None, db_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    clean_email = email.lower().strip()

    if is_using_postgres(db_url):
        conn = get_postgres_connection(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email = %s;", (clean_email,))
                row = cur.fetchone()
                if not row:
                    return None
                res = format_user_dict(row)
                res["password_hash"] = row["password_hash"]
                return res
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection(db_path)
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (clean_email,)).fetchone()
            if not row:
                return None
            res = format_user_dict(row)
            res["password_hash"] = row["password_hash"]
            return res
        finally:
            conn.close()

def get_user_by_id(user_id: int, db_path: Optional[str] = None, db_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if is_using_postgres(db_url):
        conn = get_postgres_connection(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return format_user_dict(row)
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection(db_path)
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                return None
            return format_user_dict(row)
        finally:
            conn.close()

def upgrade_user_to_pro(user_id: int, promo_code: str, db_path: Optional[str] = None, db_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    now_str = datetime.now(timezone.utc).isoformat()
    clean_code = promo_code.upper().strip()

    if is_using_postgres(db_url):
        conn = get_postgres_connection(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET is_pro = 1, pro_code_used = %s, pro_redeemed_at = %s
                    WHERE id = %s
                    RETURNING *;
                    """,
                    (clean_code, now_str, user_id)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return format_user_dict(row)
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection(db_path)
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE users
                    SET is_pro = 1, pro_code_used = ?, pro_redeemed_at = ?
                    WHERE id = ?
                    """,
                    (clean_code, now_str, user_id)
                )
                row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                if not row:
                    return None
                return format_user_dict(row)
        finally:
            conn.close()

# In-memory fast cache for recent uploaded scan files
_IN_MEMORY_SCAN_CACHE: Dict[str, Dict[str, Any]] = {}

def save_scan_file(
    scan_id: str,
    filename: str,
    file_bytes: bytes,
    file_type: str,
    db_path: Optional[str] = None,
    db_url: Optional[str] = None
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    # Cache in memory
    _IN_MEMORY_SCAN_CACHE[scan_id] = {
        "scan_id": scan_id,
        "filename": filename,
        "file_bytes": file_bytes,
        "file_type": file_type,
        "created_at": now
    }
    # Keep cache bounded to 100 items
    if len(_IN_MEMORY_SCAN_CACHE) > 100:
        oldest_key = next(iter(_IN_MEMORY_SCAN_CACHE))
        _IN_MEMORY_SCAN_CACHE.pop(oldest_key, None)

    try:
        if is_using_postgres(db_url):
            conn = get_postgres_connection(db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO scan_files (scan_id, filename, file_bytes, file_type, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (scan_id) DO UPDATE SET
                            filename = EXCLUDED.filename,
                            file_bytes = EXCLUDED.file_bytes,
                            file_type = EXCLUDED.file_type,
                            created_at = EXCLUDED.created_at;
                        """,
                        (scan_id, filename, psycopg2.Binary(file_bytes), file_type, now)
                    )
            finally:
                conn.close()
        else:
            conn = get_sqlite_connection(db_path)
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO scan_files (scan_id, filename, file_bytes, file_type, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (scan_id, filename, file_bytes, file_type, now)
                    )
            finally:
                conn.close()
    except Exception as e:
        logger.warning(f"Could not persist scan_file to database: {e}. In-memory cache is active.")


def get_scan_file(
    scan_id: str,
    db_path: Optional[str] = None,
    db_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    # Check in-memory cache first
    if scan_id in _IN_MEMORY_SCAN_CACHE:
        return _IN_MEMORY_SCAN_CACHE[scan_id]

    try:
        if is_using_postgres(db_url):
            conn = get_postgres_connection(db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT scan_id, filename, file_bytes, file_type, created_at FROM scan_files WHERE scan_id = %s;",
                        (scan_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        raw_bytes = row["file_bytes"]
                        if isinstance(raw_bytes, memoryview):
                            raw_bytes = bytes(raw_bytes)
                        record = {
                            "scan_id": row["scan_id"],
                            "filename": row["filename"],
                            "file_bytes": raw_bytes,
                            "file_type": row["file_type"],
                            "created_at": row["created_at"]
                        }
                        _IN_MEMORY_SCAN_CACHE[scan_id] = record
                        return record
                    return None
            finally:
                conn.close()
        else:
            conn = get_sqlite_connection(db_path)
            try:
                with conn:
                    cursor = conn.execute(
                        "SELECT scan_id, filename, file_bytes, file_type, created_at FROM scan_files WHERE scan_id = ?",
                        (scan_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        raw_bytes = row["file_bytes"]
                        if isinstance(raw_bytes, memoryview):
                            raw_bytes = bytes(raw_bytes)
                        record = {
                            "scan_id": row["scan_id"],
                            "filename": row["filename"],
                            "file_bytes": raw_bytes,
                            "file_type": row["file_type"],
                            "created_at": row["created_at"]
                        }
                        _IN_MEMORY_SCAN_CACHE[scan_id] = record
                        return record
                    return None
            finally:
                conn.close()
    except Exception as e:
        logger.warning(f"Error querying scan_file from database: {e}")
        return None


def get_latest_scan_file(
    db_path: Optional[str] = None,
    db_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    # Check in-memory cache first
    if _IN_MEMORY_SCAN_CACHE:
        latest_key = next(reversed(_IN_MEMORY_SCAN_CACHE))
        return _IN_MEMORY_SCAN_CACHE[latest_key]

    try:
        if is_using_postgres(db_url):
            conn = get_postgres_connection(db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT scan_id, filename, file_bytes, file_type, created_at FROM scan_files ORDER BY created_at DESC LIMIT 1;"
                    )
                    row = cur.fetchone()
                    if row:
                        raw_bytes = row["file_bytes"]
                        if isinstance(raw_bytes, memoryview):
                            raw_bytes = bytes(raw_bytes)
                        record = {
                            "scan_id": row["scan_id"],
                            "filename": row["filename"],
                            "file_bytes": raw_bytes,
                            "file_type": row["file_type"],
                            "created_at": row["created_at"]
                        }
                        _IN_MEMORY_SCAN_CACHE[row["scan_id"]] = record
                        return record
                    return None
            finally:
                conn.close()
        else:
            conn = get_sqlite_connection(db_path)
            try:
                with conn:
                    cursor = conn.execute(
                        "SELECT scan_id, filename, file_bytes, file_type, created_at FROM scan_files ORDER BY created_at DESC LIMIT 1"
                    )
                    row = cursor.fetchone()
                    if row:
                        raw_bytes = row["file_bytes"]
                        if isinstance(raw_bytes, memoryview):
                            raw_bytes = bytes(raw_bytes)
                        record = {
                            "scan_id": row["scan_id"],
                            "filename": row["filename"],
                            "file_bytes": raw_bytes,
                            "file_type": row["file_type"],
                            "created_at": row["created_at"]
                        }
                        _IN_MEMORY_SCAN_CACHE[row["scan_id"]] = record
                        return record
                    return None
            finally:
                conn.close()
    except Exception as e:
        logger.warning(f"Error querying latest scan_file: {e}")
        return None

