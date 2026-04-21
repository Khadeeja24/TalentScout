"""
setup_db.py
───────────
One-time database setup for Neon PostgreSQL.

Usage:
    python setup_db.py

What it does:
  1. Reads DATABASE_URL from .env
  2. Connects to the Neon database
  3. Runs schema.sql (idempotent — uses IF NOT EXISTS everywhere)
  4. If ENCRYPTION_KEY is missing, generates one and appends it to .env
"""

from __future__ import annotations

import os
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def split_sql(sql: str) -> list[str]:
    """
    Split a SQL file into individual statements correctly.

    Naive splitting on ';' breaks dollar-quoted function bodies like:

        CREATE FUNCTION foo() RETURNS TRIGGER AS $$
        BEGIN
            NEW.x = NOW();   ← semicolon INSIDE the body
            RETURN NEW;      ← another one
        END;
        $$;

    This parser tracks whether we are inside a $$ ... $$ block and
    only treats ';' as a statement terminator when we are outside one.
    It also strips -- line comments before parsing.
    """
    # Strip single-line comments first
    clean_lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        clean_lines.append(line)
    clean = "\n".join(clean_lines)

    statements: list[str] = []
    buf: list[str] = []
    in_dollar_quote = False
    i = 0

    while i < len(clean):
        # Detect $$ delimiter (toggle dollar-quote mode)
        if clean[i : i + 2] == "$$":
            in_dollar_quote = not in_dollar_quote
            buf.append("$$")
            i += 2
            continue

        # Semicolon is a statement terminator only outside dollar-quotes
        if clean[i] == ";" and not in_dollar_quote:
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(clean[i])
        i += 1

    # Catch any trailing statement without a final semicolon
    stmt = "".join(buf).strip()
    if stmt:
        statements.append(stmt)

    return [s for s in statements if s.strip()]


def main() -> None:
    print("\n" + "═" * 60)
    print("  TalentScout — Neon PostgreSQL Setup")
    print("═" * 60 + "\n")

    # ── 1. Check / generate encryption key ───────────────────────────────────
    enc_key = os.getenv("ENCRYPTION_KEY", "").strip()
    if not enc_key:
        from cryptography.fernet import Fernet
        new_key = Fernet.generate_key().decode()
        print("⚠️  ENCRYPTION_KEY not found in .env — generating one now.\n")
        env_path = ROOT / ".env"
        if env_path.exists():
            with open(env_path, "a") as f:
                f.write(f"\nENCRYPTION_KEY={new_key}\n")
            print(f"   ✅ Key appended to {env_path}\n")
        else:
            print(f"   Add this line to your .env:\n\n   ENCRYPTION_KEY={new_key}\n")

    # ── 2. Validate DATABASE_URL ──────────────────────────────────────────────
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("❌ DATABASE_URL is not set in your .env file.")
        print("   Paste your Neon connection string, e.g.:")
        print("   DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require\n")
        sys.exit(1)

    # Mask password for display
    display_url = database_url
    if "@" in database_url:
        pre, post = database_url.split("@", 1)
        if ":" in pre.split("//")[-1]:
            user_part = pre.rsplit(":", 1)[0]
            display_url = f"{user_part}:***@{post}"
    print(f"Connecting to: {display_url}\n")

    # ── 3. Connect ────────────────────────────────────────────────────────────
    import psycopg2

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True          # each statement commits immediately
        print("✅ Connected to Neon PostgreSQL.\n")
    except Exception as exc:
        print(f"❌ Connection failed: {exc}")
        print("\nDouble-check your DATABASE_URL in .env.")
        sys.exit(1)

    # ── 4. Run schema ─────────────────────────────────────────────────────────
    schema_path = ROOT / "db" / "schema.sql"
    if not schema_path.exists():
        print(f"❌ Schema file not found at {schema_path}")
        sys.exit(1)

    print(f"Applying schema from {schema_path.name} …\n")
    schema_sql = schema_path.read_text(encoding="utf-8")
    statements = split_sql(schema_sql)

    cursor = conn.cursor()
    tables_created = 0

    for stmt in statements:
        first = stmt.strip().upper()
        try:
            cursor.execute(stmt)
            if "CREATE TABLE" in first:
                # Extract table name for friendly output
                words = stmt.split()
                # Find the word after TABLE / EXISTS
                for idx, w in enumerate(words):
                    if w.upper() in ("TABLE", "EXISTS"):
                        tbl = words[idx + 1].strip('"').strip()
                        break
                else:
                    tbl = "?"
                print(f"   ✅ Table `{tbl}` ready.")
                tables_created += 1
            elif "CREATE OR REPLACE FUNCTION" in first:
                print("   ✅ Function `set_updated_at` ready.")
            elif "CREATE TRIGGER" in first:
                print("   ✅ Trigger `trg_candidates_updated_at` ready.")
            elif "DROP TRIGGER" in first:
                pass  # silent
            elif "CREATE INDEX" in first:
                pass  # silent
        except Exception as exc:
            preview = stmt.replace("\n", " ")[:80]
            print(f"   ⚠️  Statement skipped ({exc}): {preview}…")

    cursor.close()
    conn.close()

    print(f"\n✅ Schema applied — {tables_created} table(s) verified.")
    print("\n" + "═" * 60)
    print("  Setup complete! You can now run:\n")
    print("      streamlit run app.py")
    print("\n" + "═" * 60 + "\n")


if __name__ == "__main__":
    main()