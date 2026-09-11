import logging

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.graph.nodes.extract_data_node import run_sqlite_query
from src.graph.nodes.format_response_node import format_response
from src.graph.nodes.input_guardrail_node import input_guardrail_node
from src.graph.nodes.intent_router_node import intent_router_node, route_based_on_intent
from src.graph.nodes.sql_retry_node import fallback_failure_node, should_retry_or_format
from src.graph.state.agentstate import AgentState
from src.graph.nodes.generate_sql_node import generate_sql_from_question

logger = logging.getLogger(__name__)


def create_and_compile_workflow() -> StateGraph:
    """Creates a workflow graph for the chatbot application."""
    try:
        workflow = StateGraph(AgentState)
        workflow.add_node("input_guardrail_node", input_guardrail_node)
        workflow.add_node("tool1_generate_sql", generate_sql_from_question)
        workflow.add_node("tool2_execute_sql", run_sqlite_query)
        workflow.add_node("tool3_format_response", format_response)
        workflow.add_node("fallback_failure", fallback_failure_node)
        workflow.add_node("intent_router_node", intent_router_node)
        workflow.add_edge(START, "input_guardrail_node")
        workflow.add_edge("input_guardrail_node", "intent_router_node")
        workflow.add_edge("tool1_generate_sql", "tool2_execute_sql")
        workflow.add_edge("tool3_format_response", END)
        workflow.add_edge("fallback_failure", "tool3_format_response")

        workflow.add_conditional_edges(
            "tool2_execute_sql",
            should_retry_or_format,
            {
                "tool1": "tool1_generate_sql",
                "tool3": "tool3_format_response",
                "fallback": "fallback_failure",
            },
        )
        workflow.add_conditional_edges(
            "intent_router_node",
            route_based_on_intent,
            {
                "generate_sql": "tool1_generate_sql",
                "respond_directly": "tool3_format_response",
            },
        )

        compiled_workflow = workflow.compile(checkpointer=MemorySaver())
        logger.info("Workflow graph compiled successfully.")
        return compiled_workflow
    except Exception as exc:
        logger.exception("Failed to create or compile workflow graph")
        raise RuntimeError("Unable to initialize the chatbot workflow.") from exc