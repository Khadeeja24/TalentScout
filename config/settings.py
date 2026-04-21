"""
config/settings.py
──────────────────
Centralised configuration via pydantic-settings.
All secrets are loaded from environment variables / .env file.

Database backend: Neon serverless PostgreSQL.
Set DATABASE_URL to your Neon connection string, e.g.:
    postgresql://user:password@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── HuggingFace ──────────────────────────────────────────────────────────
    HF_API_TOKEN: str = ""
    HF_MODEL_ID: str = "mistralai/Mistral-7B-Instruct-v0.2"
    # Inference provider — "hf-inference" uses HuggingFace's own servers.
    # Other valid options: auto, cerebras, fireworks-ai, together, sambanova, novita
    HF_PROVIDER: str = "hf-inference"
    MAX_NEW_TOKENS: int = 600
    TEMPERATURE: float = 0.65
    REPETITION_PENALTY: float = 1.1

    # ── Neon PostgreSQL ───────────────────────────────────────────────────────
    # Full connection string — paste your Neon connection string here.
    # Format: postgresql://user:password@host/dbname?sslmode=require
    DATABASE_URL: str = ""
    DB_POOL_MIN: int = 1   # minimum idle connections in pool
    DB_POOL_MAX: int = 5   # maximum connections in pool

    # ── Security ─────────────────────────────────────────────────────────────
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    # ── App ──────────────────────────────────────────────────────────────────
    APP_TITLE: str = "TalentScout"
    EXTRACTION_INTERVAL: int = 4   # run extraction every N messages
    CONTEXT_WINDOW: int = 20       # how many messages to include in extraction

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Convenient singleton
settings = get_settings()