"""
app.py
──────
TalentScout Hiring Assistant — Streamlit entry point.

Run with:
    streamlit run app.py

Architecture (top → bottom):
    UI layer      (ui/)            → Streamlit components
    Service layer (services/)      → Business logic & LangChain orchestration
    DB layer      (db/)            → MySQL repositories
    Core layer    (core/)          → LLM + LangChain chains + memory
    Config        (config/)        → Pydantic settings from .env
"""

from __future__ import annotations

import logging
import sys

import streamlit as st

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("talentscout.app")

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="TalentScout – Hiring Assistant",
    page_icon="🤝",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Deferred imports (after set_page_config) ──────────────────────────────────
from config.settings import settings
from db.connection import check_connectivity
from db.repository import CandidateRepository, ConversationRepository
from services.security_service import SecurityService
from services.candidate_service import CandidateService
from services.screening_service import ScreeningService
from ui.styles import CUSTOM_CSS
from ui.components import (
    render_header,
    render_stage_progress,
    render_welcome_panel,
    render_chat_messages,
    render_session_ended,
    show_llm_error,
)
from ui.sidebar import render_sidebar


# ── Dependency injection (cached across re-runs) ──────────────────────────────

@st.cache_resource(show_spinner="Connecting to services…")
def _build_services() -> tuple[CandidateService, ScreeningService, bool]:
    """
    Build and cache all service singletons.
    Returns (candidate_service, screening_service, db_ok).
    """
    try:
        security = SecurityService()
        candidate_repo = CandidateRepository(security)
        conversation_repo = ConversationRepository()
        candidate_service = CandidateService(candidate_repo)
        screening_service = ScreeningService(
            candidate_service, candidate_repo, conversation_repo
        )
        db_ok = check_connectivity()
        logger.info("Services initialised. DB reachable: %s", db_ok)
        return candidate_service, screening_service, db_ok
    except Exception as exc:
        logger.error("Service initialisation failed: %s", exc)
        st.error(
            f"⚠️ **Initialisation error:** {exc}\n\n"
            "Check your `.env` file and ensure MySQL is running."
        )
        st.stop()


# ── Session state initialisation ──────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "messages":          [],       # list of {role, content} dicts
        "candidate":         None,     # Candidate dataclass instance
        "session_ended":     False,
        "started":           False,
        "turn_count":        0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── Main app ──────────────────────────────────────────────────────────────────

def main() -> None:
    # Inject CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    _init_state()

    # Build (or retrieve cached) services
    candidate_svc, screening_svc, db_ok = _build_services()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    render_sidebar(st.session_state.candidate, db_ok)

    # ── Main panel ────────────────────────────────────────────────────────────
    render_header()
    render_stage_progress(
        st.session_state.candidate.stage
        if st.session_state.candidate
        else "greeting"
    )

    # ── Session-ended state ───────────────────────────────────────────────────
    if st.session_state.session_ended:
        render_chat_messages(st.session_state.messages)
        render_session_ended(st.session_state.candidate)
        return

    # ── Not yet started: show welcome panel ───────────────────────────────────
    if not st.session_state.started:
        if render_welcome_panel():
            _handle_start(candidate_svc, screening_svc)
        return

    # ── Active conversation ───────────────────────────────────────────────────
    render_chat_messages(st.session_state.messages)

    user_input: str | None = st.chat_input(
        "Type your response here…",
        key="chat_input",
    )
    if user_input and user_input.strip():
        _handle_turn(user_input.strip(), screening_svc)


# ── Event handlers ────────────────────────────────────────────────────────────

def _handle_start(
    candidate_svc: CandidateService,
    screening_svc: ScreeningService,
) -> None:
    """Create a new session and fetch the opening greeting from the LLM."""
    with st.spinner("Connecting you to Alex…"):
        candidate = candidate_svc.create_session()
        result = screening_svc.start_session(candidate.session_id)

    st.session_state.candidate = result.candidate
    st.session_state.started = True
    st.session_state.messages = [
        {"role": "user",      "content": "Hello, I would like to start my screening."},
        {"role": "assistant", "content": result.reply},
    ]
    st.session_state.turn_count = 1
    st.rerun()


def _handle_turn(user_input: str, screening_svc: ScreeningService) -> None:
    """Process one user message turn."""
    candidate = st.session_state.candidate
    turn_count = st.session_state.turn_count

    # Optimistically display the user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Alex is typing…"):
        result = screening_svc.process_turn(
            session_id=candidate.session_id,
            user_input=user_input,
            candidate=candidate,
            turn_count=turn_count,
            extraction_interval=settings.EXTRACTION_INTERVAL,
        )

    # Append assistant reply
    st.session_state.messages.append({"role": "assistant", "content": result.reply})
    st.session_state.candidate  = result.candidate
    st.session_state.turn_count = turn_count + 1

    if result.error:
        show_llm_error(result.error)

    if result.session_ended:
        st.session_state.session_ended = True

    st.rerun()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
