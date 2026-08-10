"""
FinVoice Memory Database – Day 4
=================================
SQLite-backed persistent user memory for the FinVoice financial voice agent.

Public API
----------
init_db()                          → Create tables if they don't exist
lookup_user(user_id)               → Return user dict or None
save_user_memory(user_id, ...)     → Upsert user record (with sensitive-data validation)
update_last_interaction(user_id)   → Stamp current UTC timestamp
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("memory_db")

# ─────────────────────────────────────────────────────────────────────────────
# Database file path — persists across agent restarts.
# Written relative to this source file so it lands at backend/finvoice_memory.db
# ─────────────────────────────────────────────────────────────────────────────
_DB_PATH = Path(__file__).parent.parent / "finvoice_memory.db"

# ─────────────────────────────────────────────────────────────────────────────
# Sensitive keyword blocklist — these must NEVER be stored
# ─────────────────────────────────────────────────────────────────────────────
_SENSITIVE_KEYWORDS = [
    "otp",
    "pin",
    "password",
    "account number",
    "card number",
    "cvv",
    "aadhaar",
    "aadhar",
    "pan",
    "upi id",
    "upi pin",
    "credit card",
    "debit card",
    "ifsc",
    "bank account",
]


def _contains_sensitive(text: str) -> bool:
    """Return True if the text contains any sensitive keyword."""
    lower = text.lower()
    return any(kw in lower for kw in _SENSITIVE_KEYWORDS)


def _get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection with row_factory set."""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """
    Initialise the database and create the users table if it doesn't exist.
    Safe to call on every startup — idempotent.
    """
    try:
        with _get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id           TEXT PRIMARY KEY,
                    name              TEXT,
                    language_preference TEXT,
                    facts             TEXT DEFAULT '{}',
                    last_interaction  TEXT
                )
                """
            )
            conn.commit()
        logger.info("[MEMORY] init_db: database ready at %s", _DB_PATH)
    except sqlite3.Error as exc:
        logger.error("[MEMORY] init_db error: %s", exc)


def lookup_user(user_id: str) -> dict | None:
    """
    Look up a caller by user_id.

    Returns a dict with keys:
        user_id, name, language_preference, facts (dict), last_interaction
    or None if no profile exists.
    """
    logger.info("[MEMORY] lookup_user: querying user_id=%s", user_id)
    try:
        with _get_connection() as conn:
            row = conn.execute(
                "SELECT user_id, name, language_preference, facts, last_interaction "
                "FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if row is None:
            logger.info("[MEMORY] lookup_user: no profile found for user_id=%s", user_id)
            return None

        facts = {}
        try:
            facts = json.loads(row["facts"] or "{}")
        except json.JSONDecodeError:
            facts = {}

        profile = {
            "user_id": row["user_id"],
            "name": row["name"],
            "language_preference": row["language_preference"],
            "facts": facts,
            "last_interaction": row["last_interaction"],
        }
        logger.info("[MEMORY] user found: name=%s, last_interaction=%s",
                    profile["name"], profile["last_interaction"])
        return profile

    except sqlite3.Error as exc:
        logger.error("[MEMORY] lookup_user error: %s", exc)
        return None


def save_user_memory(
    user_id: str,
    name: str | None = None,
    language_preference: str | None = None,
    facts_to_add: dict | None = None,
) -> tuple[bool, str]:
    """
    Create or update a user profile.

    Validates all text fields for sensitive information before saving.
    Merges new facts on top of any previously stored facts.

    Returns:
        (True, "saved") on success
        (False, reason_string) on validation failure or DB error
    """
    # ── Sensitive-data validation ──────────────────────────────────────────
    if name and _contains_sensitive(name):
        logger.warning("[MEMORY] sensitive information rejected in name field")
        return False, "sensitive_data_in_name"

    if language_preference and _contains_sensitive(language_preference):
        logger.warning("[MEMORY] sensitive information rejected in language_preference")
        return False, "sensitive_data_in_language"

    if facts_to_add:
        facts_str = json.dumps(facts_to_add)
        if _contains_sensitive(facts_str):
            logger.warning("[MEMORY] sensitive information rejected in facts")
            return False, "sensitive_data_in_facts"

    # ── Upsert logic ───────────────────────────────────────────────────────
    try:
        now = datetime.now(timezone.utc).isoformat()

        with _get_connection() as conn:
            # Check if user already exists
            existing = conn.execute(
                "SELECT facts FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()

            if existing is None:
                # New user — insert
                merged_facts = facts_to_add or {}
                conn.execute(
                    """
                    INSERT INTO users
                        (user_id, name, language_preference, facts, last_interaction)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        name,
                        language_preference,
                        json.dumps(merged_facts),
                        now,
                    ),
                )
                logger.info("[MEMORY] saving approved information: new user created user_id=%s", user_id)
            else:
                # Existing user — merge facts and update only non-None fields
                existing_facts = {}
                try:
                    existing_facts = json.loads(existing["facts"] or "{}")
                except json.JSONDecodeError:
                    existing_facts = {}

                merged_facts = {**existing_facts, **(facts_to_add or {})}

                conn.execute(
                    """
                    UPDATE users SET
                        name                = COALESCE(?, name),
                        language_preference = COALESCE(?, language_preference),
                        facts               = ?,
                        last_interaction    = ?
                    WHERE user_id = ?
                    """,
                    (
                        name,
                        language_preference,
                        json.dumps(merged_facts),
                        now,
                        user_id,
                    ),
                )
                logger.info("[MEMORY] saving approved information: updated user_id=%s", user_id)

            conn.commit()

        return True, "saved"

    except sqlite3.Error as exc:
        logger.error("[MEMORY] save_user_memory error: %s", exc)
        return False, f"db_error: {exc}"


def update_last_interaction(user_id: str) -> None:
    """
    Stamp the current UTC timestamp as last_interaction for the given user.
    Creates a minimal record if the user doesn't exist yet.
    """
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, last_interaction)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET last_interaction = excluded.last_interaction
                """,
                (user_id, now),
            )
            conn.commit()
        logger.info("[MEMORY] update_last_interaction: user_id=%s stamped at %s", user_id, now)
    except sqlite3.Error as exc:
        logger.error("[MEMORY] update_last_interaction error: %s", exc)
