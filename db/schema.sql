-- ============================================================
-- TalentScout Database Schema — PostgreSQL / Neon
-- ============================================================
-- PII fields (name, email, phone) stored as Fernet-encrypted
-- BYTEA blobs. All other fields are plain text / JSONB.
--
-- Run via: python setup_db.py
-- Or directly: psql $DATABASE_URL -f db/schema.sql
-- ============================================================

-- ── candidates ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    id                   SERIAL PRIMARY KEY,
    session_id           VARCHAR(36)   NOT NULL UNIQUE,

    -- PII stored encrypted (Fernet / AES-128-CBC + HMAC-SHA256)
    full_name_enc        BYTEA         DEFAULT NULL,
    email_enc            BYTEA         DEFAULT NULL,
    phone_enc            BYTEA         DEFAULT NULL,

    -- Non-PII fields
    years_of_experience  VARCHAR(20)   DEFAULT NULL,
    desired_positions    JSONB         DEFAULT '[]'::JSONB,
    current_location     VARCHAR(255)  DEFAULT NULL,
    tech_stack           JSONB         DEFAULT '[]'::JSONB,

    -- Workflow metadata
    stage                VARCHAR(30)   NOT NULL DEFAULT 'greeting',
    is_complete          BOOLEAN       NOT NULL DEFAULT FALSE,

    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_candidates_updated_at ON candidates;
CREATE TRIGGER trg_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_candidates_stage       ON candidates (stage);
CREATE INDEX IF NOT EXISTS idx_candidates_created_at  ON candidates (created_at);
CREATE INDEX IF NOT EXISTS idx_candidates_is_complete ON candidates (is_complete);

-- ── conversation_history ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversation_history (
    id          SERIAL PRIMARY KEY,
    session_id  VARCHAR(36)  NOT NULL,
    role        VARCHAR(10)  NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT         NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ch_session
        FOREIGN KEY (session_id) REFERENCES candidates (session_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ch_session ON conversation_history (session_id);

-- ── technical_assessments ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS technical_assessments (
    id          SERIAL PRIMARY KEY,
    session_id  VARCHAR(36)   NOT NULL,
    technology  VARCHAR(100)  NOT NULL,
    question    TEXT          NOT NULL,
    answer      TEXT          DEFAULT NULL,
    asked_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ta_session
        FOREIGN KEY (session_id) REFERENCES candidates (session_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ta_session    ON technical_assessments (session_id);
CREATE INDEX IF NOT EXISTS idx_ta_technology ON technical_assessments (technology);