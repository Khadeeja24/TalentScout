"""
core/memory.py
──────────────
In-process conversation memory backed by LangChain's ChatMessageHistory.
One ChatMessageHistory object per session_id, stored in a module-level dict.

On session resume, call seed_from_db() to repopulate from the database
so the LLM has full context without loading the entire transcript into RAM.
"""

from __future__ import annotations

import logging

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages per-session ChatMessageHistory objects.
    Acts as an in-process short-term memory store.
    """

    def __init__(self) -> None:
        self._store: dict[str, ChatMessageHistory] = {}

    # ── History access ────────────────────────────────────────────────────────

    def get_history(self, session_id: str) -> ChatMessageHistory:
        """Return the history object for a session (create if absent)."""
        if session_id not in self._store:
            self._store[session_id] = ChatMessageHistory()
        return self._store[session_id]

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        return self.get_history(session_id).messages

    # ── Seeding from DB ───────────────────────────────────────────────────────

    def seed_from_db(
        self,
        session_id: str,
        db_messages: list[dict],
        max_messages: int = 30,
    ) -> None:
        """
        Populate in-memory history from database records.
        Only loads the most recent `max_messages` to bound context size.
        """
        history = self.get_history(session_id)
        history.clear()
        recent = db_messages[-max_messages:]
        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                history.add_user_message(content)
            elif role == "assistant":
                history.add_ai_message(content)
        logger.debug(
            "Seeded %d messages from DB for session %s", len(recent), session_id
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def clear(self, session_id: str) -> None:
        """Remove in-memory history for a session (e.g. on logout)."""
        self._store.pop(session_id, None)

    def session_count(self) -> int:
        return len(self._store)


# Module-level singleton — shared across all Streamlit re-runs in the process
memory_manager = MemoryManager()
