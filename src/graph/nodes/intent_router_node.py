import logging
from pydantic import BaseModel, Field
from src.graph.state.agentstate import AgentState
from src.languagemodels.llmprovider import get_llm_instance
from src.config.settings import settings
from langchain_core.prompts import ChatPromptTemplate
from src.prompts.formatting_prompts import intent_router_system_prompt

logger = logging.getLogger(__name__)

class IntentClassification(BaseModel):
    requires_database: str = Field(
        description="Return exactly 'true' if the question asks for dynamic information, metrics, or records in our database tables; otherwise return exactly 'false'."
    )

def intent_router_node(state: AgentState):
    # Initialize a fast, cheap model for routing
    if(state.get("is_input_safe") is False):
        logger.warning(f"Input safety check failed for question: '{state.get('user_query', '')}'. Aborting intent routing.")
        return {
            "user_query": state.get("user_query", ""),
            "needs_db": False,
            "intent_error": "Input safety check failed.",
        }

    llm =  get_llm_instance(settings.GROQ_LLM_PROVIDER)
    structured_llm = llm.with_structured_output(IntentClassification)
    user_query = state.get("user_query", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", intent_router_system_prompt),
        ("human", user_query)
    ])

    logger.info(f"Routing user query: '{user_query}' through intent classification model.")
    try:
        chain = prompt | structured_llm
        decision = chain.invoke({"user_query": user_query})
            
        needs_db = decision.requires_database.strip().lower() == "true"
        return {
            "needs_db": needs_db,
            "retry_count": 0,
            "generated_sql": "",
            "sql_error": "",
        }
    except Exception as e:
        logger.error(f"Error during intent routing for query '{user_query}': {e}")
        return {
            "user_query": user_query,
            "messages": str(e),
            "needs_db": False,
            "error": "Intent routing failed.",
        }
        

# The conditional edge function evaluated by LangGraph
def route_based_on_intent(state: AgentState):
    if state.get("needs_db") is True:
        return "generate_sql"
    return "respond_directly"