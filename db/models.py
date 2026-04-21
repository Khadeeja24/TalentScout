"""
db/models.py
────────────
Pure Python dataclasses that represent database rows.
No ORM dependency — keeps the data layer explicit and fast.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Candidate:
    """Represents one candidate screening session."""

    session_id: str

    # PII (decrypted in application layer)
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # Plain-text profile fields
    years_of_experience: Optional[str] = None
    desired_positions: list[str] = field(default_factory=list)
    current_location: Optional[str] = None
    tech_stack: list[str] = field(default_factory=list)

    # Workflow state
    stage: str = "greeting"
    is_complete: bool = False

    # Timestamps (populated from DB)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ── Helpers ──────────────────────────────────────────────────────────────

    def collected_fields(self) -> dict:
        """Return only fields that have been filled."""
        return {
            k: v
            for k, v in {
                "full_name": self.full_name,
                "email": self.email,
                "phone": self.phone,
                "years_of_experience": self.years_of_experience,
                "desired_positions": self.desired_positions,
                "current_location": self.current_location,
                "tech_stack": self.tech_stack,
            }.items()
            if v not in (None, [], "")
        }

    @property
    def display_name(self) -> str:
        return self.full_name or "Candidate"

    @property
    def profile_completeness(self) -> float:
        """0.0 – 1.0 fraction of required fields filled."""
        required = 7  # seven required fields
        filled = len(self.collected_fields())
        return min(filled / required, 1.0)


@dataclass
class ConversationMessage:
    """One turn in the conversation transcript."""

    session_id: str
    role: str       # 'user' | 'assistant'
    content: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class TechnicalAssessment:
    """A single technical question + optional candidate answer."""

    session_id: str
    technology: str
    question: str
    answer: Optional[str] = None
    id: Optional[int] = None
    asked_at: Optional[datetime] = None
