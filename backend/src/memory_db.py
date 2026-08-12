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
    Initialise the database and create the users and escalations tables if they don't exist.
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS escalations (
                    reference_id                TEXT PRIMARY KEY,
                    user_name                   TEXT,
                    issue_summary               TEXT,
                    what_agent_checked          TEXT,
                    urgency                     TEXT,
                    language                    TEXT,
                    preferred_follow_up_method  TEXT,
                    status                      TEXT DEFAULT 'open',
                    created_at                  TEXT
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


def sanitize_text(text: str) -> str:
    """Sanitize the input text to redact sensitive information."""
    if not text:
        return text
    import re
    # Redact digits of length 3 or more (covers CVV, OTP, PIN, Card number, Account number)
    text = re.sub(r"\b\d{3,18}\b", "[REDACTED]", text)
    # Redact card patterns
    text = re.sub(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[REDACTED]", text)
    # Redact sensitive words
    for kw in _SENSITIVE_KEYWORDS:
        pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        text = pattern.sub("[REDACTED]", text)
    return text


def create_escalation_record(
    user_name: str | None,
    issue_summary: str,
    what_agent_checked: str,
    urgency: str,
    language: str,
    preferred_follow_up_method: str,
) -> tuple[bool, str | None, str | None]:
    """
    Save an escalation ticket in the database.
    Performs safety checks and sanitization.
    Returns (success, reference_id, error_message).
    """
    # Check for direct sensitive matches using _contains_sensitive on summary and details
    if _contains_sensitive(issue_summary) or _contains_sensitive(what_agent_checked):
        logger.warning("[MEMORY] sensitive information detected in escalation submission")
        # We will sanitize it instead of completely failing, but let's be safe and do both sanitization and safety log.

    # Sanitize inputs
    sanitized_summary = sanitize_text(issue_summary)
    sanitized_agent_checked = sanitize_text(what_agent_checked)
    sanitized_user_name = sanitize_text(user_name or "Anonymous User")

    try:
        now = datetime.now(timezone.utc).isoformat()
        year = datetime.now(timezone.utc).year

        with _get_connection() as conn:
            # Query number of escalations in the current year to generate reference_id
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM escalations WHERE reference_id LIKE ?",
                (f"FIN-{year}-%",)
            )
            count = cursor.fetchone()["count"]
            next_num = count + 1
            reference_id = f"FIN-{year}-{next_num:04d}"

            conn.execute(
                """
                INSERT INTO escalations (
                    reference_id,
                    user_name,
                    issue_summary,
                    what_agent_checked,
                    urgency,
                    language,
                    preferred_follow_up_method,
                    status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)
                """,
                (
                    reference_id,
                    sanitized_user_name,
                    sanitized_summary,
                    sanitized_agent_checked,
                    urgency or "normal",
                    language or "English",
                    preferred_follow_up_method or "email",
                    now
                )
            )
            conn.commit()

        logger.info("[MEMORY] Escalation record created: %s", reference_id)
        return True, reference_id, None
    except sqlite3.Error as exc:
        logger.error("[MEMORY] create_escalation_record error: %s", exc)
        return False, None, str(exc)

