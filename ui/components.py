"""
ui/components.py
────────────────
Reusable Streamlit UI components for TalentScout.
Each function renders a distinct piece of the interface.
"""

from __future__ import annotations

import streamlit as st
from db.models import Candidate


# ── Page header ───────────────────────────────────────────────────────────────

def render_header() -> None:
    st.markdown("""
    <div class="ts-header">
        <h1>🤝 TalentScout</h1>
        <div class="subtitle">AI-Powered Hiring Assistant &nbsp;·&nbsp; Initial Screening</div>
    </div>
    """, unsafe_allow_html=True)


# ── Stage progress tracker ────────────────────────────────────────────────────

STAGES = [
    ("greeting",  "👋", "Greet"),
    ("gathering", "📝", "Profile"),
    ("questions", "🔍", "Assessment"),
    ("done",      "✅", "Complete"),
]


def render_stage_progress(current_stage: str) -> None:
    """Render a horizontal step-by-step progress indicator."""
    stage_keys = [s[0] for s in STAGES]
    current_idx = stage_keys.index(current_stage) if current_stage in stage_keys else 0

    dots_html = ""
    for i, (key, icon, label) in enumerate(STAGES):
        if i < current_idx:
            dot_cls = "done"
            label_cls = "done"
            dot_content = "✓"
        elif i == current_idx:
            dot_cls = "active"
            label_cls = "active"
            dot_content = icon
        else:
            dot_cls = ""
            label_cls = ""
            dot_content = str(i + 1)

        dots_html += f"""
        <div class="stage-step">
            <div class="stage-dot {dot_cls}">{dot_content}</div>
            <div class="stage-label {label_cls}">{label}</div>
        </div>"""

    st.markdown(
        f'<div class="stage-track">{dots_html}</div>',
        unsafe_allow_html=True,
    )


# ── Welcome / start panel ─────────────────────────────────────────────────────

def render_welcome_panel() -> bool:
    """
    Show the welcome card with a Start button.
    Returns True when the button is clicked.
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #f8fafc, #e8f4fd);
            border: 1px solid #bee3f8;
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            margin: 1rem 0 2rem;
        ">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">🚀</div>
            <h3 style="font-family: 'DM Serif Display', serif; color: #0d1b2a; margin: 0 0 0.5rem;">
                Ready to Begin?
            </h3>
            <p style="color: #4a6fa5; font-size: 0.9rem; margin: 0 0 1.2rem; line-height: 1.6;">
                Our AI assistant Alex will guide you through a 5–10 minute 
                initial screening. We'll gather your profile and ask a few 
                technical questions tailored to your tech stack.
            </p>
            <div style="
                display: flex; gap: 1rem; 
                justify-content: center; 
                font-size: 0.82rem; 
                color: #5a8fa8;
                margin-bottom: 1.2rem;
            ">
                <span>📋 Profile collection</span>
                <span>·</span>
                <span>🔍 Tech assessment</span>
                <span>·</span>
                <span>✅ Instant summary</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        clicked = st.button(
            "▶️  Start My Screening",
            type="primary",
            use_container_width=True,
        )
    return clicked


# ── Session-ended banner ──────────────────────────────────────────────────────

def render_session_ended(candidate: Candidate) -> None:
    from datetime import datetime
    st.success("✅ Your screening session has been completed and saved!")
    st.markdown(f"""
    <div style="
        background: #f0fff4;
        border: 1px solid #9ae6b4;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-top: 0.5rem;
    ">
        <p style="margin:0; color:#276749; font-size:0.88rem;">
            <strong>Session ID:</strong> 
            <code style="font-size:0.8rem;">{candidate.session_id}</code><br/>
            <strong>Completed at:</strong> {datetime.now().strftime("%d %b %Y, %H:%M")}<br/>
            <strong>Profile completeness:</strong> {int(candidate.profile_completeness * 100)}%
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── Chat message renderer ─────────────────────────────────────────────────────

def render_chat_messages(messages: list[dict]) -> None:
    """Render all visible chat messages in the conversation."""
    SKIP_CONTENT = "Hello, I would like to start my screening."
    for msg in messages:
        if msg["role"] == "user" and msg["content"] == SKIP_CONTENT:
            continue   # hide the synthetic kick-off message
        avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])


# ── DB status badge ───────────────────────────────────────────────────────────

def render_db_status(connected: bool) -> None:
    if connected:
        st.sidebar.markdown(
            '<span style="color:#68d391;font-size:0.75rem;">● MySQL connected</span>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            '<span style="color:#fc8181;font-size:0.75rem;">● MySQL offline</span>',
            unsafe_allow_html=True,
        )


# ── Error toast ───────────────────────────────────────────────────────────────

def show_llm_error(error_msg: str) -> None:
    st.warning(
        f"⚠️ The AI assistant hit a snag: `{error_msg[:120]}`. "
        "Please try sending your message again.",
        icon="⚠️",
    )
