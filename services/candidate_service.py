"""
services/candidate_service.py
──────────────────────────────
Business logic for candidate lifecycle management.
Sits between the Streamlit UI and the repository layer.
"""

from __future__ import annotations

import uuid
import logging
from typing import Optional

from db.models import Candidate
from db.repository import CandidateRepository

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = frozenset({
    "full_name", "email", "phone",
    "years_of_experience", "desired_positions",
    "current_location", "tech_stack",
})


class CandidateService:
    """Manages candidate sessions and profile state."""

    def __init__(self, candidate_repo: CandidateRepository) -> None:
        self._repo = candidate_repo

    # ── Session management ────────────────────────────────────────────────────

    def create_session(self) -> Candidate:
        """Create a brand-new screening session with a fresh UUID."""
        candidate = Candidate(session_id=str(uuid.uuid4()))
        success = self._repo.create(candidate)
        if not success:
            raise RuntimeError("Failed to persist new candidate session to DB.")
        logger.info("New session created: %s", candidate.session_id)
        return candidate

    def get_or_create(self, session_id: str) -> Candidate:
        """Return existing session or create if absent (idempotent)."""
        existing = self._repo.get_by_session_id(session_id)
        if existing:
            return existing
        candidate = Candidate(session_id=session_id)
        self._repo.create(candidate)
        return candidate

    def load(self, session_id: str) -> Optional[Candidate]:
        return self._repo.get_by_session_id(session_id)

    def save(self, candidate: Candidate) -> bool:
        return self._repo.update(candidate)

    # ── Stage inference ───────────────────────────────────────────────────────

    @staticmethod
    def infer_stage(candidate: Candidate) -> str:
        """
        Determine the correct conversation stage from collected fields.
        Avoids fragile keyword matching – uses data completeness instead.
        """
        fields = candidate.collected_fields()
        if not fields:
            return "greeting"
        if REQUIRED_FIELDS.issubset(set(fields.keys())):
            return "questions"
        return "gathering"

    # ── Profile merging ───────────────────────────────────────────────────────

    @staticmethod
    def merge_extracted(candidate: Candidate, extracted: dict) -> Candidate:
        """
        Merge an extraction dict (from LLM) into a Candidate, only
        overwriting fields that are currently empty.
        """
        mapping = {
            "full_name": "full_name",
            "email": "email",
            "phone": "phone",
            "years_of_experience": "years_of_experience",
            "desired_positions": "desired_positions",
            "current_location": "current_location",
            "tech_stack": "tech_stack",
        }
        for ext_key, attr in mapping.items():
            value = extracted.get(ext_key)
            if not value:
                continue
            current = getattr(candidate, attr)
            # Only overwrite if current field is empty
            if not current or current == []:
                setattr(candidate, attr, value)
            # Lists: merge unique items
            elif isinstance(current, list) and isinstance(value, list):
                merged = list(dict.fromkeys(current + value))  # preserve order, dedupe
                setattr(candidate, attr, merged)
        return candidate
