"""
DB Service – PostgreSQL query helpers for Neon serverless.
Uses psycopg v3 with a fresh connection per operation (avoids SSL drop issues
with Neon's serverless compute that suspends idle connections).
"""
from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

import psycopg
from psycopg.rows import dict_row


def _get_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    # Remove channel_binding — not supported by Neon pooler
    parsed = urlparse(dsn)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop("channel_binding", None)
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))


def _connect() -> psycopg.Connection:
    return psycopg.connect(_get_dsn(), row_factory=dict_row, connect_timeout=10)


class DBService:
    """Thin wrapper around psycopg v3. Opens a fresh connection per call."""

    def execute(self, sql: str, params: tuple = ()) -> list[dict]:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def execute_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()

    def execute_write(self, sql: str, params: tuple = ()) -> None:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()

    def execute_returning(self, sql: str, params: tuple = ()) -> Optional[dict]:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                result = cur.fetchone()
            conn.commit()
            return result
