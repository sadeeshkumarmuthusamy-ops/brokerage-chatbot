import sqlite3
import os
import logging

from src.config.settings import settings

logger = logging.getLogger(__name__)

def get_db_connection():
    """Establishes a connection to the SQLite database.

    Args:
        db_path (str): The path to the SQLite database file.
        sql_query (str): The SQL query string to execute.
    """
    db_path = settings.CHROMA_DB_PATH_LOCAL
    if not os.path.exists(db_path):
        logger.error("Database file was not found at %s", db_path)
        return

    connection = None

    try:
        connection = sqlite3.connect(db_path, timeout=5.0)
        return connection
    except sqlite3.Error as e:
        logger.exception("Failed to establish SQLite database connection")
        return None