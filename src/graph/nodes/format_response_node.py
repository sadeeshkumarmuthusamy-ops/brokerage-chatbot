import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.config.settings import settings
from src.languagemodels.llmprovider import get_llm_instance
from src.graph.state.agentstate import AgentState
from src.prompts.formatting_prompts import system_dbvalue_response_prompt, system_nodbvalue_response_prompt

logger = logging.getLogger(__name__)


def format_response(state: AgentState) -> AgentState:
    """Uses an LLM to transform raw SQLite results into a natural, user-friendly response."""
    user_query = state.get("user_query", "")
    dbresult = state.get("db_query_result", [])
    need_db = state.get("needs_db", False)
    is_input_safe = state.get("is_input_safe", True)
    error = state.get("error", False)

    if not is_input_safe:
        return {"final_output": "I cannot answer questions that may pose a security risk."}

    if error:
        return {"final_output": "An error occurred while processing your request. Please try again later."}

    if state.get("sql_error"):
        return {"final_output": state["sql_error"]}

    if state.get("human_in_loop") and state.get("final_output"):
        return {
            "final_output": state["final_output"],
            "human_in_loop": True,
            "decision": state.get("decision", "pending"),
            "decision_data": state.get("decision_data", {}),
        }

    try:
        llm = get_llm_instance(settings.GROQ_LLM_PROVIDER)

        if not need_db:
            user_prompt = user_query
            system_instruction = system_nodbvalue_response_prompt
        else:
            system_instruction = system_dbvalue_response_prompt
            user_prompt = f"""
            User Question: "{user_query}"

            Database Query Results:
            \"\"\"
            {dbresult}
            \"\"\"

            Please provide a clean, direct answer to the user based on the database results above. Respond only summary or Tabular data. Don't add questions or other details.
            """

        response = llm.invoke(
            [
                SystemMessage(content=system_instruction),
                HumanMessage(content=user_prompt),
            ]
        )

        response_content = str(response.content).strip()
        if not response_content:
            raise ValueError("The language model returned an empty response.")

        updated_history = list(state.get("chat_history", []))
        updated_history.append({"role": "user", "content": user_query})
        updated_history.append({"role": "assistant", "content": response_content})
        return {
            "final_output": response_content,
            "chat_history": updated_history,
        }

    except Exception:
        logger.exception("Failed to format response for query")
        return {
            "final_output": "I could not generate a response right now. Please try again later.",
        }