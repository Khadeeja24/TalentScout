"""
db/connection.py
────────────────
Thread-safe PostgreSQL connection pool for Neon serverless DB.

Uses psycopg2's ThreadedConnectionPool so multiple Streamlit sessions
can safely share connections. Neon requires SSL — the sslmode=require
parameter in DATABASE_URL handles this automatically.

"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras          # RealDictCursor
from psycopg2 import pool as pg_pool

from config.settings import settings

logger = logging.getLogger(__name__)

_pool: pg_pool.ThreadedConnectionPool | None = None


def _create_pool() -> pg_pool.ThreadedConnectionPool:
    """Initialise the psycopg2 threaded connection pool (called once)."""
    if not settings.DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is not set. "
            "Paste your Neon connection string into .env:\n"
            "  DATABASE_URL=postgresql://user:pass@host/db?sslmode=require"
        )
    return pg_pool.ThreadedConnectionPool(
        minconn=settings.DB_POOL_MIN,
        maxconn=settings.DB_POOL_MAX,
        dsn=settings.DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,  # rows as dicts
    )


def get_pool() -> pg_pool.ThreadedConnectionPool:
    """Return the singleton pool, creating it on first call."""
    global _pool
    if _pool is None:
        try:
            _pool = _create_pool()
            logger.info(
                "Neon PostgreSQL pool initialised (min=%d, max=%d)",
                settings.DB_POOL_MIN,
                settings.DB_POOL_MAX,
            )
        except Exception as exc:
            logger.error("Failed to create PostgreSQL pool: %s", exc)
            raise
    return _pool


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager that checks out a pooled connection and guarantees
    it is returned to the pool (even on exception).

    Usage::

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ...")
                results = cur.fetchall()
            conn.commit()
    """
    conn = get_pool().getconn()
    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            get_pool().putconn(conn)
        except Exception:
            pass


def check_connectivity() -> bool:
    """Ping the database. Returns True if reachable."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as exc:
        logger.warning("DB connectivity check failed: %s", exc)
        return False