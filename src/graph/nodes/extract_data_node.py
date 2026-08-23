import sqlite3
import re
import logging

from src.config.sqlconnections import get_db_connection
from src.graph.state.agentstate import AgentState

logger = logging.getLogger(__name__)


def run_sqlite_query(state: AgentState) -> AgentState:
    """Executes an SQL query against a local SQLite database with robust error handling."""
    connection = None
    try:
        sql_query = state.get("generated_sql", "")
        if not sql_query or not str(sql_query).strip():
            logger.warning("SQL query is required")
            return {
                "sql_error": "SQL query is required.",
                "retry_count": state.get("retry_count", 0) + 1,
            }

        if re.search(r"\b(?:UPDATE|INSERT|DELETE)\b", sql_query, flags=re.IGNORECASE):
            logger.info("Write operation detected; waiting for human approval")
            return {
                "user_query": state.get("user_query", ""),
                "final_output": f"Approval required before executing this SQL:\n\n{sql_query}",
                "human_in_loop": True,
                "decision": "pending",
                "decision_data": {
                    "sql": sql_query,
                    "status": "pending",
                },
                "sql_error": "",
            }

        connection = get_db_connection()
        if not connection:
            logger.error("Failed to establish database connection")
            return {
                "sql_error": "Failed to establish database connection.",
                "retry_count": state.get("retry_count", 0) + 1,
            }

        cursor = connection.cursor()
        logger.info("Executing SQL query")
        cursor.execute(sql_query)

        columns = [column[0] for column in cursor.description] if cursor.description else []
        results = cursor.fetchall()

        if columns:
            results.insert(0, tuple(columns))

        if not results:
            logger.info("Query executed successfully with 0 rows")
            return {"user_query": state.get("user_query", "")}

        logger.info("Query succeeded; retrieved %d rows", len(results) - 1)

        return {
            "user_query": state.get("user_query", ""),
            "db_query_result": results,
            "sql_error": "",
        }

    except sqlite3.OperationalError as e:
        logger.exception("SQL operational error")
        return {
            "sql_error": f"Operational Error: Issue with database or query syntax.\nDetails: {e}",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    except sqlite3.IntegrityError as e:
        logger.exception("SQL integrity error")
        return {
            "sql_error": f"Integrity Error: Data constraints violated.\nDetails: {e}",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    except sqlite3.Error as e:
        logger.exception("SQLite error while executing query")
        return {
            "sql_error": f"SQLite Error: An unexpected database error occurred.\nDetails: {e}",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    except Exception as e:
        logger.exception("Unexpected error while executing query")
        return {
            "sql_error": f"Unexpected Error: {e}",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    finally:
        if connection:
            connection.close()
            logger.debug("Database connection closed")