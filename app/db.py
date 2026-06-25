from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from app.config import settings


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    settings.ensure_dirs()
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_jobs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                user_email TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                instructions TEXT NOT NULL,
                status TEXT NOT NULL,
                input_pages INTEGER,
                output_pages INTEGER,
                operations_json TEXT,
                error TEXT,
                input_path TEXT,
                output_path TEXT,
                input_bytes INTEGER,
                output_bytes INTEGER,
                model TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_jobs_created_at ON usage_jobs(created_at)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_jobs_user ON usage_jobs(user_email)")


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def create_job(
    *,
    job_id: str,
    user_email: str,
    original_filename: str,
    instructions: str,
    input_path: Path,
    input_bytes: int,
    model: str,
) -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO usage_jobs (
                id, created_at, user_email, original_filename, instructions, status,
                input_path, input_bytes, model
            )
            VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?)
            """,
            (
                job_id,
                now_iso(),
                user_email,
                original_filename,
                instructions,
                str(input_path),
                input_bytes,
                model,
            ),
        )


def finish_job(
    *,
    job_id: str,
    status: str,
    input_pages: int | None = None,
    output_pages: int | None = None,
    operations: list[dict[str, Any]] | None = None,
    error: str | None = None,
    output_path: Path | None = None,
    output_bytes: int | None = None,
) -> None:
    with db() as conn:
        conn.execute(
            """
            UPDATE usage_jobs
            SET status = ?,
                input_pages = ?,
                output_pages = ?,
                operations_json = ?,
                error = ?,
                output_path = ?,
                output_bytes = ?
            WHERE id = ?
            """,
            (
                status,
                input_pages,
                output_pages,
                json.dumps(operations or [], ensure_ascii=False),
                error,
                str(output_path) if output_path else None,
                output_bytes,
                job_id,
            ),
        )


def get_job(job_id: str) -> sqlite3.Row | None:
    with db() as conn:
        return conn.execute("SELECT * FROM usage_jobs WHERE id = ?", (job_id,)).fetchone()


def admin_stats() -> dict[str, Any]:
    with db() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total_jobs,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_jobs,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_jobs,
                COALESCE(SUM(input_pages), 0) AS input_pages,
                COALESCE(SUM(output_pages), 0) AS output_pages,
                COALESCE(SUM(input_bytes), 0) AS input_bytes,
                COALESCE(SUM(output_bytes), 0) AS output_bytes
            FROM usage_jobs
            """
        ).fetchone()
        by_user = conn.execute(
            """
            SELECT user_email, COUNT(*) AS jobs,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                   MAX(created_at) AS last_job_at
            FROM usage_jobs
            GROUP BY user_email
            ORDER BY jobs DESC, user_email ASC
            """
        ).fetchall()
        recent = conn.execute(
            """
            SELECT id, created_at, user_email, original_filename, status, input_pages,
                   output_pages, error
            FROM usage_jobs
            ORDER BY created_at DESC
            LIMIT 50
            """
        ).fetchall()
    return {"totals": totals, "by_user": by_user, "recent": recent}
