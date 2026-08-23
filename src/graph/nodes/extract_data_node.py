import sqlite3

from src.config.sqlconnections import get_db_connection
from src.graph.state.agentstate import AgentState


def run_sqlite_query(state: AgentState) -> AgentState:
    """Executes an SQL query against a local SQLite database with robust error handling."""
    connection = None
    try:
        sql_query = state.get("generated_sql", "")
        if not sql_query or not str(sql_query).strip():
            print("SQL query is required.")
            return {
                "sql_error": "SQL query is required.",
                "retry_count": state.get("retry_count", 0) + 1,
            }

        connection = get_db_connection()
        if not connection:
            print("Failed to establish database connection.")
            return {
                "sql_error": "Failed to establish database connection.",
                "retry_count": state.get("retry_count", 0) + 1,
            }

        cursor = connection.cursor()
        print("Executing query...")
        cursor.execute(sql_query)

        columns = [column[0] for column in cursor.description] if cursor.description else []
        results = cursor.fetchall()

        if columns:
            results.insert(0, tuple(columns))

        if not results:
            print("Query executed successfully, but returned 0 rows.")
            return {"user_query": state.get("user_query", "")}

        print(f"\n--- Success! Retrieved {len(results) - 1} rows ---")

        return {
            "user_query": state.get("user_query", ""),
            "db_query_result": results,
            "sql_error": "",
        }

    except sqlite3.OperationalError as e:
        print(f"\nOperational Error: Issue with database or query syntax.\nDetails: {e}")
        return {
            "sql_error": f"Operational Error: Issue with database or query syntax.\nDetails: {e}",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    except sqlite3.IntegrityError as e:
        print(f"\nIntegrity Error: Data constraints violated.\nDetails: {e}")
        return {
            "sql_error": f"Integrity Error: Data constraints violated.\nDetails: {e}",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    except sqlite3.Error as e:
        print(f"\nSQLite Error: An unexpected database error occurred.\nDetails: {e}")
        return {
            "sql_error": f"SQLite Error: An unexpected database error occurred.\nDetails: {e}",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    except Exception as e:
        print(f"\nUnexpected Error: {e}")
        return {
            "sql_error": f"Unexpected Error: {e}",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    finally:
        if connection:
            connection.close()
            print("\nDatabase connection closed cleanly.")