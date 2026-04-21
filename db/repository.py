"""
db/repository.py
────────────────
Data-access objects for each PostgreSQL table.
All SQL lives here; business logic stays in the service layer.

Key differences from the MySQL version:
  • BYTEA columns (full_name_enc, email_enc, phone_enc) — psycopg2
    transparently converts bytes ↔ BYTEA so no extra casting needed.
  • JSONB columns — pass Python lists/dicts; psycopg2.extras.Json
    serialises them; reads come back as native Python objects.
  • RETURNING id — PostgreSQL's way to get the inserted row ID
    (replaces cursor.lastrowid from mysql-connector).
  • %s placeholders — identical to MySQL connector, no changes needed.
  • RealDictCursor set on the pool — rows arrive as dict-like objects.
"""

from __future__ import annotations

import json
import logging
from typing import Optional, TYPE_CHECKING

import psycopg2.extras

from db.connection import get_connection
from db.models import Candidate, ConversationMessage, TechnicalAssessment

if TYPE_CHECKING:
    from services.security_service import SecurityService

logger = logging.getLogger(__name__)


# ── CandidateRepository ───────────────────────────────────────────────────────

class CandidateRepository:
    """CRUD for the `candidates` table."""

    def __init__(self, security: "SecurityService") -> None:
        self._sec = security

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _encrypt_tuple(self, c: Candidate) -> tuple:
        """Return the values tuple for INSERT / UPDATE (excluding session_id)."""
        return (
            self._sec.encrypt(c.full_name),          # BYTEA
            self._sec.encrypt(c.email),               # BYTEA
            self._sec.encrypt(c.phone),               # BYTEA
            c.years_of_experience,
            psycopg2.extras.Json(c.desired_positions or []),
            c.current_location,
            psycopg2.extras.Json(c.tech_stack or []),
            c.stage,
        )

    def _row_to_candidate(self, row: dict) -> Candidate:
        """Map a DB row dict → Candidate dataclass."""
        return Candidate(
            session_id=row["session_id"],
            full_name=self._sec.decrypt(bytes(row["full_name_enc"]) if row.get("full_name_enc") else None),
            email=self._sec.decrypt(bytes(row["email_enc"]) if row.get("email_enc") else None),
            phone=self._sec.decrypt(bytes(row["phone_enc"]) if row.get("phone_enc") else None),
            years_of_experience=row.get("years_of_experience"),
            desired_positions=self._ensure_list(row.get("desired_positions")),
            current_location=row.get("current_location"),
            tech_stack=self._ensure_list(row.get("tech_stack")),
            stage=row.get("stage", "greeting"),
            is_complete=bool(row.get("is_complete", False)),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @staticmethod
    def _ensure_list(value) -> list:
        """Normalise JSONB / None → Python list."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []

    # ── Public API ────────────────────────────────────────────────────────────

    def create(self, candidate: Candidate) -> bool:
        sql = """
            INSERT INTO candidates
                (session_id, full_name_enc, email_enc, phone_enc,
                 years_of_experience, desired_positions, current_location,
                 tech_stack, stage)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (candidate.session_id, *self._encrypt_tuple(candidate)))
                conn.commit()
            logger.debug("Created candidate session=%s", candidate.session_id)
            return True
        except Exception as exc:
            logger.error("create candidate failed: %s", exc)
            return False

    def update(self, candidate: Candidate) -> bool:
        sql = """
            UPDATE candidates SET
                full_name_enc=%s, email_enc=%s, phone_enc=%s,
                years_of_experience=%s, desired_positions=%s,
                current_location=%s, tech_stack=%s, stage=%s,
                is_complete=%s
            WHERE session_id=%s
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        *self._encrypt_tuple(candidate),
                        candidate.is_complete,
                        candidate.session_id,
                    ))
                conn.commit()
            return True
        except Exception as exc:
            logger.error("update candidate failed: %s", exc)
            return False

    def get_by_session_id(self, session_id: str) -> Optional[Candidate]:
        sql = "SELECT * FROM candidates WHERE session_id = %s LIMIT 1"
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (session_id,))
                    row = cur.fetchone()
            return self._row_to_candidate(dict(row)) if row else None
        except Exception as exc:
            logger.error("get candidate failed: %s", exc)
            return None

    def list_recent(self, limit: int = 50) -> list[Candidate]:
        sql = "SELECT * FROM candidates ORDER BY created_at DESC LIMIT %s"
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (limit,))
                    rows = cur.fetchall()
            return [self._row_to_candidate(dict(r)) for r in rows]
        except Exception as exc:
            logger.error("list candidates failed: %s", exc)
            return []


# ── ConversationRepository ────────────────────────────────────────────────────

class ConversationRepository:
    """Append-only transcript log."""

    def append(self, msg: ConversationMessage) -> bool:
        sql = """
            INSERT INTO conversation_history (session_id, role, content)
            VALUES (%s, %s, %s)
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (msg.session_id, msg.role, msg.content))
                conn.commit()
            return True
        except Exception as exc:
            logger.error("append message failed: %s", exc)
            return False

    def append_batch(self, messages: list[ConversationMessage]) -> bool:
        sql = """
            INSERT INTO conversation_history (session_id, role, content)
            VALUES (%s, %s, %s)
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    psycopg2.extras.execute_batch(
                        cur,
                        sql,
                        [(m.session_id, m.role, m.content) for m in messages],
                        page_size=50,
                    )
                conn.commit()
            return True
        except Exception as exc:
            logger.error("batch append failed: %s", exc)
            return False

    def get_by_session(self, session_id: str) -> list[ConversationMessage]:
        sql = """
            SELECT id, session_id, role, content, created_at
            FROM conversation_history
            WHERE session_id = %s
            ORDER BY created_at ASC, id ASC
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (session_id,))
                    rows = cur.fetchall()
            return [
                ConversationMessage(
                    id=r["id"],
                    session_id=r["session_id"],
                    role=r["role"],
                    content=r["content"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        except Exception as exc:
            logger.error("get messages failed: %s", exc)
            return []


# ── AssessmentRepository ──────────────────────────────────────────────────────

class AssessmentRepository:
    """Tracks technical questions and candidate answers."""

    def add_question(self, assessment: TechnicalAssessment) -> Optional[int]:
        # RETURNING id is the PostgreSQL idiom for getting the auto-generated PK
        sql = """
            INSERT INTO technical_assessments (session_id, technology, question)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        assessment.session_id,
                        assessment.technology,
                        assessment.question,
                    ))
                    row = cur.fetchone()
                conn.commit()
            return row["id"] if row else None
        except Exception as exc:
            logger.error("add question failed: %s", exc)
            return None

    def update_answer(self, assessment_id: int, answer: str) -> bool:
        sql = "UPDATE technical_assessments SET answer=%s WHERE id=%s"
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (answer, assessment_id))
                conn.commit()
            return True
        except Exception as exc:
            logger.error("update answer failed: %s", exc)
            return False

    def get_by_session(self, session_id: str) -> list[TechnicalAssessment]:
        sql = """
            SELECT * FROM technical_assessments
            WHERE session_id = %s
            ORDER BY asked_at ASC
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (session_id,))
                    rows = cur.fetchall()
            return [
                TechnicalAssessment(
                    id=r["id"],
                    session_id=r["session_id"],
                    technology=r["technology"],
                    question=r["question"],
                    answer=r.get("answer"),
                    asked_at=r.get("asked_at"),
                )
                for r in rows
            ]
        except Exception as exc:
            logger.error("get assessments failed: %s", exc)
            return []