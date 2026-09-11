from typing import Literal

from src.graph.state.agentstate import AgentState


def should_retry_or_format(state: AgentState) -> Literal["tool1", "tool3", "fallback"]:
    """Determines whether to retry query compilation, output, or fail out."""
    if not state.get("sql_error"):
        return "tool3"

    if state.get("retry_count", 0) > 1:
        return "fallback"

    return "tool1"


def fallback_failure_node(state: AgentState) -> AgentState:
    """Triggers if the system hits maximum retry limits without resolving syntax errors."""
    error_msg = "Issue while extracting the data from DB. Please retry later"

    updated_history = list(state.get("chat_history", []))
    updated_history.append({"role": "user", "content": state.get("user_query", "")})
    updated_history.append({"role": "assistant", "content": error_msg})
    return {
        "chat_history": updated_history,
        "final_output": error_msg,
    }