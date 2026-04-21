"""
services/screening_service.py
──────────────────────────────
Orchestrates one screening session end-to-end:
  • Detects exit intent
  • Calls the LangChain screening chain
  • Persists conversation turns to MySQL
  • Periodically extracts + merges candidate profile fields
  • Manages stage transitions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.chain import build_screening_chain, extract_candidate_info
from core.memory import memory_manager
from core.prompts import FAREWELL_MESSAGE
from db.models import Candidate, ConversationMessage
from db.repository import CandidateRepository, ConversationRepository
from services.candidate_service import CandidateService

logger = logging.getLogger(__name__)

EXIT_KEYWORDS = frozenset({
    "exit", "quit", "bye", "goodbye", "stop",
    "end", "leave", "close", "done", "finish",
})


@dataclass
class TurnResult:
    """Output of a single conversation turn."""
    reply: str
    candidate: Candidate
    session_ended: bool
    error: str | None = None


class ScreeningService:
    """
    Stateless service — all state lives in MySQL and in MemoryManager.
    Each method receives the full Candidate object and returns an updated one.
    """

    def __init__(
        self,
        candidate_service: CandidateService,
        candidate_repo: CandidateRepository,
        conversation_repo: ConversationRepository,
    ) -> None:
        self._cs = candidate_service
        self._c_repo = candidate_repo
        self._cv_repo = conversation_repo
        self._chain = build_screening_chain()

    # ── Public API ────────────────────────────────────────────────────────────

    def process_turn(
        self,
        session_id: str,
        user_input: str,
        candidate: Candidate,
        turn_count: int,
        extraction_interval: int = 4,
    ) -> TurnResult:
        """
        Process one user message and return the assistant reply + updated state.

        Args:
            session_id:           UUID for this screening session.
            user_input:           Raw text from the user.
            candidate:            Current candidate state.
            turn_count:           Number of completed turns so far.
            extraction_interval:  Run NER extraction every N turns.

        Returns:
            TurnResult with the reply, updated candidate, and session_ended flag.
        """
        # ── Exit detection ────────────────────────────────────────────────────
        if self._is_exit(user_input):
            return self._handle_exit(session_id, user_input, candidate)

        # ── LLM call ──────────────────────────────────────────────────────────
        try:
            reply = self._chain.invoke(
                {
                    "input": user_input,
                    "candidate_info": self._format_candidate(candidate),
                    "current_stage": candidate.stage,
                },
                config={"configurable": {"session_id": session_id}},
            )
        except Exception as exc:
            logger.error("LLM call failed for session %s: %s", session_id, exc)
            return TurnResult(
                reply="I'm sorry, I'm having a technical difficulty. Please try again in a moment.",
                candidate=candidate,
                session_ended=False,
                error=str(exc),
            )

        # ── Persist to DB ─────────────────────────────────────────────────────
        self._persist_turn(session_id, user_input, reply)

        # ── Periodic extraction ───────────────────────────────────────────────
        if (turn_count + 1) % extraction_interval == 0:
            candidate = self._run_extraction(session_id, candidate)
        
        # ── Update stage ──────────────────────────────────────────────────────
        new_stage = CandidateService.infer_stage(candidate)
        if new_stage != candidate.stage:
            candidate.stage = new_stage
            self._c_repo.update(candidate)

        return TurnResult(reply=reply, candidate=candidate, session_ended=False)

    def start_session(self, session_id: str) -> TurnResult:
        """Kick off the conversation with a synthetic greeting turn."""
        candidate = self._cs.get_or_create(session_id)

        try:
            greeting = self._chain.invoke(
                {
                    "input": "Hello, I would like to start my screening.",
                    "candidate_info": "Nothing collected yet.",
                    "current_stage": "greeting",
                },
                config={"configurable": {"session_id": session_id}},
            )
        except Exception as exc:
            logger.error("Greeting LLM call failed: %s", exc)
            greeting = (
                "Hello! I'm Alex from TalentScout. I'll be conducting your initial "
                "screening today. This should take about 5–10 minutes. "
                "To get started, could you please tell me your full name?"
            )

        self._persist_turn(session_id, "Hello, I would like to start my screening.", greeting)
        return TurnResult(reply=greeting, candidate=candidate, session_ended=False)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _is_exit(text: str) -> bool:
        words = set(text.lower().split())
        return bool(words & EXIT_KEYWORDS)

    def _handle_exit(
        self, session_id: str, user_input: str, candidate: Candidate
    ) -> TurnResult:
        """Build farewell, persist, mark session complete."""
        tech = ", ".join(candidate.tech_stack) if candidate.tech_stack else "various technologies"
        positions = ", ".join(candidate.desired_positions) if candidate.desired_positions else "tech roles"
        exp = candidate.years_of_experience or "N/A"

        reply = FAREWELL_MESSAGE.format(
            tech_stack=tech,
            positions=positions,
            experience=exp,
        )
        self._persist_turn(session_id, user_input, reply)

        candidate.stage = "done"
        candidate.is_complete = True
        self._c_repo.update(candidate)
        memory_manager.clear(session_id)

        logger.info("Session %s ended gracefully.", session_id)
        return TurnResult(reply=reply, candidate=candidate, session_ended=True)

    def _persist_turn(self, session_id: str, user_input: str, reply: str) -> None:
        self._cv_repo.append_batch([
            ConversationMessage(session_id=session_id, role="user", content=user_input),
            ConversationMessage(session_id=session_id, role="assistant", content=reply),
        ])

    def _run_extraction(self, session_id: str, candidate: Candidate) -> Candidate:
        """Extract profile fields from recent conversation, merge into candidate."""
        db_messages = self._cv_repo.get_by_session(session_id)
        if len(db_messages) < 4:
            return candidate

        conversation_text = "\n".join(
            f"{m.role.upper()}: {m.content}"
            for m in db_messages[-20:]
        )
        extracted = extract_candidate_info(conversation_text)
        if extracted:
            candidate = CandidateService.merge_extracted(candidate, extracted)
            self._c_repo.update(candidate)
            logger.debug(
                "Extraction updated: %s fields for session %s",
                len(extracted),
                session_id,
            )
        return candidate

    @staticmethod
    def _format_candidate(candidate: Candidate) -> str:
        import json
        fields = candidate.collected_fields()
        return json.dumps(fields, indent=2) if fields else "Nothing collected yet."
