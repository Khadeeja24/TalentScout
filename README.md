# 🤝 TalentScout — AI Hiring Assistant v2

> A production-grade, modular AI chatbot that conducts structured initial candidate screenings for TalentScout, a fictional tech-recruitment agency. Built with **HuggingFace Inference API**, **LangChain**, **Streamlit**, and **MySQL** with full PII encryption at rest.

---

## 📌 Project Overview

TalentScout Hiring Assistant automates the first stage of the recruitment funnel. A candidate opens the app, is greeted by **Alex** (the AI assistant), and is guided through a structured 5–10 minute session:

| Phase | What happens |
|-------|-------------|
| **1 · Greeting** | Alex introduces itself and TalentScout |
| **2 · Profile gathering** | 7 fields collected one-at-a-time: name, email, phone, experience, desired roles, location, full tech stack |
| **3 · Technical assessment** | 3–5 tailored questions generated per technology, difficulty calibrated to years of experience |
| **4 · Wrap-up** | Graceful conclusion, profile summary, next-steps messaging |

All conversation turns and candidate profiles are **persisted to MySQL**. PII fields (name, email, phone) are **encrypted at rest** using Fernet (AES-128-CBC + HMAC-SHA256).

---

## 🗂️ Project Structure

```
talentscout_v2/
│
├── app.py                    # Streamlit entry point — wires everything together
├── setup_db.py               # One-time DB setup (creates schema, generates enc key)
├── requirements.txt
├── .env.example              # Template for environment variables
│
├── config/
│   └── settings.py           # Pydantic-settings — all config from .env
│
├── core/                     # LangChain / LLM layer
│   ├── llm.py                # HuggingFaceEndpoint → ChatHuggingFace singleton
│   ├── prompts.py            # All prompt templates (screening + extraction)
│   ├── memory.py             # Per-session ChatMessageHistory manager
│   └── chain.py              # LCEL chain builders (screening + extraction)
│
├── db/                       # Data layer
│   ├── schema.sql            # MySQL DDL — all CREATE TABLE statements
│   ├── connection.py         # Thread-safe connection pool + context manager
│   ├── models.py             # Pure Python dataclasses (Candidate, etc.)
│   └── repository.py         # SQL CRUD — CandidateRepo, ConversationRepo, AssessmentRepo
│
├── services/                 # Business logic layer
│   ├── security_service.py   # Fernet encrypt/decrypt for PII fields
│   ├── candidate_service.py  # Candidate lifecycle, stage inference, field merging
│   └── screening_service.py  # Conversation orchestration — calls chain, persists turns
│
└── ui/                       # Presentation layer
    ├── styles.py             # Custom CSS (DM Serif + JetBrains Mono theme)
    ├── components.py         # Reusable widgets (header, progress, chat bubbles)
    └── sidebar.py            # Live candidate profile sidebar
```

### Layer diagram

```
┌─────────────────────────────────┐
│         Streamlit UI (app.py)   │  ← re-renders on every user action
│  ui/components  │  ui/sidebar   │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│       Service Layer             │
│  screening_service              │  ← orchestrates one conversation turn
│  candidate_service              │  ← CRUD + stage inference
│  security_service               │  ← Fernet encrypt / decrypt
└────────────┬────────────────────┘
             │
     ┌───────┴───────┐
     │               │
┌────▼────┐   ┌──────▼──────────────────────────┐
│  DB     │   │     Core (LangChain)             │
│  layer  │   │  llm.py → HuggingFaceEndpoint    │
│ MySQL   │   │  chain.py → RunnableWithHistory  │
│ repos   │   │  memory.py → ChatMessageHistory  │
└─────────┘   └──────────────────────────────────┘
```

---

## 🚀 Installation & Setup

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | ≥ 3.10 | Uses `match`, `|` union types |
| MySQL | ≥ 5.7 or 8.x | Must be running locally |
| HuggingFace account | — | Free tier works for Mistral-7B |

### Step 1 — Clone & create virtual environment

```bash
git clone https://github.com/<your-username>/talentscout-v2.git
cd talentscout-v2

python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
HF_API_TOKEN=hf_...              # from huggingface.co/settings/tokens
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
```

Leave `ENCRYPTION_KEY` blank — `setup_db.py` will generate it for you.

### Step 4 — Set up the database

```bash
python setup_db.py
```

This will:
- Connect to MySQL using your `.env` credentials
- Create the `talentscout` database
- Create all 3 tables (`candidates`, `conversation_history`, `technical_assessments`)
- Generate and append a Fernet encryption key to your `.env`

### Step 5 — Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 📖 Usage Guide

1. Click **▶️ Start My Screening** on the welcome panel.
2. Alex will greet you — respond naturally in the chat box.
3. Answer each profile question as prompted.
4. When asked for your tech stack, list everything:
   > *"Python, FastAPI, PostgreSQL, Docker, Redis, React, TypeScript"*
5. Alex will then ask 3–5 questions per technology.
6. Type **`exit`**, **`quit`**, **`bye`**, or **`done`** at any time to end gracefully.
7. Your live candidate profile fills in the sidebar as you chat.

---

## 🗄️ Database Schema

```sql
candidates               -- one row per screening session
  session_id             -- UUID (public identifier)
  full_name_enc          -- BLOB (Fernet-encrypted)
  email_enc              -- BLOB (Fernet-encrypted)
  phone_enc              -- BLOB (Fernet-encrypted)
  years_of_experience    -- VARCHAR (plain text)
  desired_positions      -- JSON array
  current_location       -- VARCHAR (plain text)
  tech_stack             -- JSON array
  stage                  -- greeting | gathering | questions | done
  is_complete            -- TINYINT(1)
  created_at / updated_at

conversation_history     -- full transcript per session
  session_id → candidates(session_id)
  role                   -- 'user' | 'assistant'
  content                -- TEXT

technical_assessments    -- Q&A pairs per technology
  session_id → candidates(session_id)
  technology             -- e.g. 'Python'
  question               -- TEXT
  answer                 -- TEXT (nullable until answered)
```

All three tables use InnoDB with foreign key constraints and appropriate indexes on `session_id`, `stage`, and `created_at`.

---

## 🧠 Prompt Engineering

### Screening prompt design

The system prompt (`SCREENING_SYSTEM` in `core/prompts.py`) uses three proven techniques:

**1. Stage-aware context injection**
Before every API call, the current `candidate_info` dict and `stage` string are interpolated into the prompt. This keeps the LLM oriented without relying on it to track state purely from conversation history.

```python
# core/chain.py — invocation
result = chain.invoke({
    "input":          user_input,
    "candidate_info": json.dumps(candidate.collected_fields()),
    "current_stage":  candidate.stage,
})
```

**2. Ordered instruction set with named stages**
The prompt uses `[STAGE: greeting]`, `[STAGE: gathering]`, `[STAGE: questions]` blocks that mirror the application's state machine. This produces far more consistent flow than free-form instructions.

**3. Difficulty calibration**
The assessment block explicitly states the difficulty mapping:
```
< 2 yrs  → core syntax, basic concepts
2–5 yrs  → architecture, best practices
> 5 yrs  → system design, performance, trade-offs
```
Combined with the collected `years_of_experience`, this gives the LLM enough signal to calibrate without needing post-processing.

### Extraction prompt design

A separate lightweight chain runs every `EXTRACTION_INTERVAL` turns. It parses the last 20 message turns into a strict JSON object:

```python
# core/chain.py — extraction
extracted = extract_candidate_info(conversation_text)
candidate = CandidateService.merge_extracted(candidate, extracted)
```

Key decisions:
- **Separate chain, separate call** — keeps extraction JSON-only without polluting the conversational chain's output.
- **Regex-guarded JSON parsing** — strips markdown fences and finds the first `{...}` block in case the model adds preamble.
- **Merge, don't overwrite** — `merge_extracted()` only sets fields that are currently empty, so a candidate can't accidentally overwrite a confirmed field with a later ambiguous mention.

---

## 🔒 Security & Data Privacy

| Concern | Implementation |
|---------|---------------|
| PII at rest | `full_name`, `email`, `phone` stored as Fernet-encrypted BLOBs in MySQL |
| Key management | Encryption key stored in `.env` (excluded from version control via `.gitignore`) |
| Sidebar masking | Email shown as `jo***@domain.com`, phone as `+44***78` |
| Session isolation | Each session uses a UUID v4 — no sequential IDs that could be enumerated |
| SQL injection | All queries use parameterised `%s` placeholders via mysql-connector |
| No plain-text PII in logs | Logger uses `DEBUG` level only for non-PII fields |
| GDPR note | For production: add a consent screen, right-to-erasure endpoint, and audit log |

### Key rotation

`SecurityService.rotate_key(new_key, ciphertext)` re-encrypts a single value under a new key. A production rotation script would:
1. Load all encrypted BLOBs.
2. Decrypt with the old key.
3. Re-encrypt with the new key.
4. Update rows in a transaction.

---

## ⚙️ Architecture Decisions

### Why HuggingFace + LangChain?

- **HuggingFace Inference API** — Zero infrastructure; runs `mistralai/Mistral-7B-Instruct-v0.2` serverlessly with a free-tier token.
- **LangChain LCEL** — The `RunnableWithMessageHistory` pattern cleanly separates conversation memory from chain logic. Swapping the LLM backend is a one-line change in `core/llm.py`.
- **Two-chain architecture** — Screening chain (conversational) + Extraction chain (JSON-only). Keeps prompts focused and avoids forcing the conversational model to output structured data mid-turn.

### Why MySQL over SQLite?

- Connection pooling supports multiple concurrent Streamlit sessions.
- JSON column type and BLOB columns for encrypted data.
- Production-ready with replication, backups, and existing DBA tooling.
- `schema.sql` makes the schema fully reviewable and version-controllable.

### Stage machine (no keyword matching)

```python
def infer_stage(candidate: Candidate) -> str:
    filled = {k for k, v in candidate.collected_fields().items() if v}
    if not filled:          return "greeting"
    if REQUIRED_FIELDS <= filled: return "questions"
    return "gathering"
```

Stage is inferred purely from data completeness — no fragile string matching on LLM output.

---

## 🔧 Configuration Reference

All settings are in `config/settings.py` and loaded from `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_API_TOKEN` | — | HuggingFace API token (**required**) |
| `HF_MODEL_ID` | `mistralai/Mistral-7B-Instruct-v0.2` | Model ID on HuggingFace Hub |
| `MAX_NEW_TOKENS` | `600` | Max tokens per generation |
| `TEMPERATURE` | `0.65` | Sampling temperature |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_NAME` | `talentscout` | Database name |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | — | MySQL password (**required**) |
| `DB_POOL_SIZE` | `5` | Connection pool size |
| `ENCRYPTION_KEY` | — | Fernet key for PII (**required**, auto-generated by `setup_db.py`) |
| `EXTRACTION_INTERVAL` | `4` | Run NER extraction every N turns |
| `CONTEXT_WINDOW` | `20` | Messages included in extraction prompt |

---

## ⚠️ Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| LLM ignoring conversation order | Stage-aware system prompt with explicit `[STAGE: x]` blocks + current state injection |
| Structured data extraction mid-conversation | Dedicated extraction chain (separate LLM call) with a JSON-only prompt |
| PII privacy in sidebar | Partial masking of email/phone in `ui/sidebar.py`; encrypted in DB |
| Stale profile after fast typing | `merge_extracted()` runs every 4 turns; never overwrites confirmed fields |
| MySQL connection pool exhaustion | Context-manager `get_connection()` guarantees pool return on exception |
| HuggingFace model cold starts | `get_llm()` cached as module-level singleton; Streamlit `@cache_resource` for services |
| JSON parse failures from LLM | Regex-clean markdown fences + find-first-`{...}` fallback in `chain.py` |

---

## 🌟 Optional Enhancements Implemented

- ✅ **Live profile sidebar** — updates every 4 turns via NER extraction
- ✅ **Profile completeness bar** — visual progress with colour coding
- ✅ **Stage progress indicator** — 4-step tracker in the main panel
- ✅ **PII masking in UI** — email/phone partially redacted in sidebar
- ✅ **Graceful error handling** — LLM errors show a toast; DB errors reported clearly
- ✅ **Session resume** — `MemoryManager.seed_from_db()` restores conversation context from MySQL on reconnect
- ✅ **Key auto-generation** — `setup_db.py` generates Fernet key and appends it to `.env`
- ✅ **DB connectivity badge** — sidebar shows live MySQL status

---

## 📄 License

Created as an AI/ML intern assignment submission for TalentScout. All rights reserved.
