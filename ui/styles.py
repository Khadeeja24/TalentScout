"""
ui/styles.py
────────────
Custom CSS for TalentScout's Streamlit interface.
Design direction: Refined corporate-editorial with a dark sidebar
and clean white main canvas. Monospace accents for tech credibility.
"""

CUSTOM_CSS = """
<style>
/* ── Google Fonts ────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Global reset ────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Sidebar ─────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(175deg, #0d1b2a 0%, #1b2a3b 50%, #0f2d40 100%);
    border-right: 1px solid rgba(100,200,255,0.12);
}
section[data-testid="stSidebar"] * {
    color: #d0e8f2 !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
    font-family: 'DM Serif Display', serif !important;
    letter-spacing: -0.02em;
}
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: #d0e8f2 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.2s ease;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.14) !important;
    border-color: rgba(100,200,255,0.4) !important;
}

/* ── Main header ─────────────────────────────────────────────────── */
.ts-header {
    text-align: center;
    padding: 2rem 0 1rem;
}
.ts-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2.8rem;
    color: #0d1b2a;
    letter-spacing: -0.04em;
    margin-bottom: 0.2rem;
}
.ts-header .subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #5a8fa8;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

/* ── Stage progress bar ──────────────────────────────────────────── */
.stage-track {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 1.2rem auto 2rem;
    max-width: 480px;
}
.stage-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    position: relative;
}
.stage-step::after {
    content: '';
    position: absolute;
    top: 16px;
    left: 50%;
    width: 100%;
    height: 2px;
    background: #e2e8f0;
    z-index: 0;
}
.stage-step:last-child::after { display: none; }
.stage-dot {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 600;
    border: 2px solid #cbd5e0;
    background: #fff;
    color: #a0aec0;
    z-index: 1;
    position: relative;
    transition: all 0.3s ease;
}
.stage-dot.active {
    background: #0d6efd;
    border-color: #0d6efd;
    color: #fff;
    box-shadow: 0 0 0 4px rgba(13,110,253,0.18);
}
.stage-dot.done {
    background: #198754;
    border-color: #198754;
    color: #fff;
}
.stage-label {
    font-size: 0.65rem;
    font-weight: 600;
    color: #718096;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.stage-label.active { color: #0d6efd; }
.stage-label.done   { color: #198754; }

/* ── Chat bubbles ────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    border-radius: 14px !important;
    padding: 6px 10px !important;
    margin-bottom: 6px !important;
}

/* ── Profile card in sidebar ─────────────────────────────────────── */
.profile-field {
    display: flex;
    flex-direction: column;
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}
.profile-field:last-child { border-bottom: none; }
.profile-label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6baed6 !important;
    margin-bottom: 2px;
}
.profile-value {
    font-size: 0.88rem;
    color: #e8f4fd !important;
    word-break: break-word;
}
.profile-tag {
    display: inline-block;
    background: rgba(107,174,214,0.18);
    border: 1px solid rgba(107,174,214,0.35);
    border-radius: 4px;
    padding: 1px 7px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #a8d8f0 !important;
    margin: 2px 3px 2px 0;
}

/* ── Completeness bar ────────────────────────────────────────────── */
.completeness-wrap {
    margin: 12px 0;
}
.completeness-label {
    font-size: 0.7rem;
    color: #6baed6 !important;
    margin-bottom: 4px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.completeness-bar-bg {
    background: rgba(255,255,255,0.1);
    border-radius: 100px;
    height: 6px;
    overflow: hidden;
}
.completeness-bar-fill {
    height: 100%;
    border-radius: 100px;
    background: linear-gradient(90deg, #11998e, #38ef7d);
    transition: width 0.4s ease;
}

/* ── Start button ────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0d1b2a, #1e4d7b) !important;
    border: none !important;
    color: #fff !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.7rem 2rem !important;
    border-radius: 8px !important;
    letter-spacing: 0.02em;
    box-shadow: 0 4px 15px rgba(13,27,42,0.3) !important;
    transition: all 0.25s ease !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(13,27,42,0.4) !important;
}

/* ── Info/success boxes ──────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Chat input ──────────────────────────────────────────────────── */
[data-testid="stChatInput"] {
    border-radius: 12px !important;
    border: 1.5px solid #cbd5e0 !important;
}

/* ── Dividers in sidebar ─────────────────────────────────────────── */
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
    margin: 12px 0 !important;
}
</style>
"""
