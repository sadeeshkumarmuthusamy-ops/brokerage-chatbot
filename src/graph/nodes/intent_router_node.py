import logging
from pydantic import BaseModel, Field
from src.graph.state.agentstate import AgentState
from src.languagemodels.llmprovider import get_llm_instance
from src.config.settings import settings
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class IntentClassification(BaseModel):
    requires_database: bool = Field(
        description="True if the question asks for dynamic information, metrics, or records that reside in our database tables. False for casual greetings, small talk, meta-questions about the bot, or requests that don't need a DB lookup."
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

    # Clearly outline what requires a DB vs what does not
    system_prompt = (
        "You are an AI router. Analyze the user's input message.\n"
        "Determine if answering it requires querying a sales/agreement/order database schema.\n\n"
        "Set 'requires_database' to True if they ask for things like:\n"
        "- Sales data, revenue figures, agreement/purchase order statuses, order numbers, specific dates/metrics.\n\n"
        "Set 'requires_database' to False if the input is:\n"
        "- Greetings ('Hi', 'Hello').\n"
        "- Explanations/Static knowledge ('What is Python?', 'Explain SQL').\n"
        "- Out-of-bounds text or completely unrelated questions."
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_query)
    ])

    logger.info(f"Routing user query: '{user_query}' through intent classification model.")
    try:
        chain = prompt | structured_llm
        decision = chain.invoke({"user_query": user_query})
            
        return {"needs_db": decision.requires_database}
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