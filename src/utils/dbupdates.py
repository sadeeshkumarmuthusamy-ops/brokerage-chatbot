
import sqlite3
import re

from src.config.sqlconnections import get_db_connection


def update_database(query: str) -> int:
    """Execute an approved write query and return the affected row count."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("A non-empty SQL query is required.")
    if not re.match(r"^\s*(?:UPDATE|INSERT|DELETE)\b", query, flags=re.IGNORECASE):
        raise ValueError("Only UPDATE, INSERT, or DELETE queries are allowed.")

    connection = get_db_connection()
    if not connection:
        raise sqlite3.Error("Failed to establish database connection.")

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        affected_rows = cursor.rowcount
        connection.commit()
        return affected_rows
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    