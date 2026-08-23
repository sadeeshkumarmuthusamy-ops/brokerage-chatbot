from typing import Annotated, TypedDict, List, Dict, Any

from langgraph.graph import add_messages


class AgentState(TypedDict, total=False):
    user_query: str
    chat_history: Annotated[List[Dict[str, str]], add_messages]
    generated_sql: str
    db_columns: list
    db_rows: list
    db_schema: str
    db_query_result: List[Any]
    sql_error: str
    retry_count: int
    final_output: str
    messages: Annotated[list, add_messages]
    is_input_safe: bool
    needs_db : bool 
    error: bool
    human_in_loop: bool
    decision: str
    decision_data: Dict[str, Any]