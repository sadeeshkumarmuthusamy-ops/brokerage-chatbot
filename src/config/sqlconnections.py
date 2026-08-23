import sqlite3
import os

from src.config.settings import settings

def get_db_connection():
    """Establishes a connection to the SQLite database.

    Args:
        db_path (str): The path to the SQLite database file.
        sql_query (str): The SQL query string to execute.
    """
    db_path = settings.CHROMA_DB_PATH_LOCAL
    if not os.path.exists(db_path):
        print(f"Error: The database file at '{db_path}' was not found.")
        return

    connection = None

    try:
        connection = sqlite3.connect(db_path, timeout=5.0)
        return connection
    except sqlite3.Error as e:
        print(f"\nSQLite Error: An unexpected database error occurred.\nDetails: {e}")
        return None