"""
ui/sidebar.py
─────────────
Renders the TalentScout sidebar:
  • Branding header
  • Live candidate profile card (populated as the conversation progresses)
  • Profile completeness bar
  • Session controls (Start Over, copy session ID)
  • DB connectivity badge
"""

from __future__ import annotations

import streamlit as st

from db.models import Candidate
from ui.components import render_db_status


def render_sidebar(candidate: Candidate | None, db_ok: bool) -> None:
    """
    Main sidebar renderer.
    Called on every Streamlit re-run so the profile stays live.
    """
    with st.sidebar:
        _render_brand()
        st.divider()

        if candidate:
            _render_profile(candidate)
            st.divider()
            _render_completeness(candidate)
            st.divider()
            _render_controls(candidate)
        else:
            st.info("Start a screening to see the candidate profile here.")

        st.divider()
        render_db_status(db_ok)
        _render_footer()


# ── Brand header ──────────────────────────────────────────────────────────────

def _render_brand() -> None:
    st.markdown("""
    <div style="text-align:center; padding: 0.5rem 0 0.2rem;">
        <div style="font-size:2.2rem;">🤝</div>
        <h2 style="
            font-family: 'DM Serif Display', serif;
            margin: 0.2rem 0 0;
            font-size: 1.5rem;
            letter-spacing: -0.02em;
        ">TalentScout</h2>
        <div style="
            font-size: 0.65rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #6baed6 !important;
            margin-top: 2px;
        ">Hiring Assistant · AI Screening</div>
    </div>
    """, unsafe_allow_html=True)


# ── Candidate profile card ────────────────────────────────────────────────────

_FIELD_META = [
    ("full_name",           "👤",  "Full Name",       "text"),
    ("email",               "📧",  "Email",           "text"),
    ("phone",               "📞",  "Phone",           "text"),
    ("years_of_experience", "🗓️",  "Experience",      "text"),
    ("current_location",    "📍",  "Location",        "text"),
    ("desired_positions",   "💼",  "Desired Role(s)", "tags"),
    ("tech_stack",          "🛠️",  "Tech Stack",      "tags"),
]


def _render_profile(candidate: Candidate) -> None:
    st.markdown(
        "<div style='font-size:0.7rem;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.1em;"
        "color:#6baed6;margin-bottom:8px;'>📋 Candidate Profile</div>",
        unsafe_allow_html=True,
    )

    filled_any = False
    for attr, icon, label, kind in _FIELD_META:
        value = getattr(candidate, attr, None)
        if not value or value == []:
            continue
        filled_any = True
        _render_field(icon, label, value, kind)

    if not filled_any:
        st.markdown(
            "<p style='font-size:0.8rem;color:#6baed6;font-style:italic;'>"
            "Profile filling in as you chat…</p>",
            unsafe_allow_html=True,
        )


def _render_field(icon: str, label: str, value, kind: str) -> None:
    if kind == "tags" and isinstance(value, list):
        tags_html = "".join(
            f'<span class="profile-tag">{v}</span>' for v in value
        )
        content = f'<div style="margin-top:4px;">{tags_html}</div>'
    else:
        val_str = str(value)
        # Mask email partially for display (privacy-by-design)
        if label == "Email" and "@" in val_str:
            parts = val_str.split("@")
            masked = parts[0][:2] + "***@" + parts[1]
            val_str = masked
        # Mask phone
        if label == "Phone" and len(val_str) >= 6:
            val_str = val_str[:3] + "***" + val_str[-2:]
        content = f'<div class="profile-value">{val_str}</div>'

    st.markdown(
        f"""
        <div class="profile-field">
            <div class="profile-label">{icon} {label}</div>
            {content}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Completeness bar ──────────────────────────────────────────────────────────

def _render_completeness(candidate: Candidate) -> None:
    pct = int(candidate.profile_completeness * 100)
    color = (
        "#38ef7d" if pct == 100
        else "#f6c90e" if pct >= 50
        else "#fc8181"
    )
    st.markdown(
        f"""
        <div class="completeness-wrap">
            <div class="completeness-label">Profile completeness — {pct}%</div>
            <div class="completeness-bar-bg">
                <div class="completeness-bar-fill"
                     style="width:{pct}%; background:{color};"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    stage_labels = {
        "greeting":  "👋 Greeting",
        "gathering": "📝 Gathering info",
        "questions": "🔍 Technical assessment",
        "done":      "✅ Complete",
    }
    stage_text = stage_labels.get(candidate.stage, candidate.stage)
    st.markdown(
        f"<div style='font-size:0.75rem;color:#a8d8f0;margin-top:6px;'>"
        f"Stage: <strong>{stage_text}</strong></div>",
        unsafe_allow_html=True,
    )


# ── Session controls ──────────────────────────────────────────────────────────

def _render_controls(candidate: Candidate) -> None:
    st.markdown(
        "<div style='font-size:0.65rem;color:#6baed6;"
        "text-transform:uppercase;letter-spacing:0.1em;"
        "font-weight:700;margin-bottom:8px;'>⚙️ Session</div>",
        unsafe_allow_html=True,
    )

    # Session ID display
    st.markdown(
        f"<div style='font-family:monospace;font-size:0.65rem;"
        f"color:#6baed6;word-break:break-all;margin-bottom:8px;'>"
        f"{candidate.session_id[:8]}…{candidate.session_id[-4:]}</div>",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Start Over", use_container_width=True, key="btn_restart"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.markdown(
        "<p style='font-size:0.7rem;color:#5a8fa8;margin-top:10px;line-height:1.5;'>"
        "Type <code>exit</code>, <code>quit</code>, or <code>bye</code> "
        "to end the session.</p>",
        unsafe_allow_html=True,
    )


# ── Footer ────────────────────────────────────────────────────────────────────

def _render_footer() -> None:
    st.markdown(
        """
        <div style='font-size:0.65rem;color:#3d5a6e;
                    text-align:center;margin-top:12px;line-height:1.6;'>
            🔒 PII encrypted at rest (Fernet/AES)<br/>
            Powered by HuggingFace · LangChain · MySQL
        </div>
        """,
        unsafe_allow_html=True,
    )
