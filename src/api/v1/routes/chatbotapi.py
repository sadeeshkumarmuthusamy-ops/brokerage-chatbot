from typing import Any, Literal
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from src.graph.chatbot_graph import create_and_compile_workflow
from src.graph.state.agentstate import AgentState
from src.utils.sanitize_data import sanitize_all_input
from src.utils.dbupdates import update_database

from mockup_sql_ragsetup.ragsetup.dataingestionandload import convertschemattodocument, load_table_schema

logger = logging.getLogger(__name__)
app = create_and_compile_workflow()

router = APIRouter(prefix="/brokeragent", tags=["Chat & Agents"])


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    human_in_loop: bool = False


class DecisionRequest(BaseModel):
    session_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    sql: str = Field(min_length=1)
    decision: Literal["approved", "rejected"]
    decision_data: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str
    human_in_loop: bool
    decision_data: dict[str, Any] = Field(default_factory=dict)

def normalize_json_url(file_url: str) -> str:
    """Convert GitHub browser URLs to raw JSON URLs so they return file content."""
    parsed = urlparse(file_url)
    if parsed.netloc.lower() == "github.com" and "/blob/" in parsed.path:
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 4:
            owner, repo, _, branch, *rest = path_parts
            if branch and rest:
                raw_path = "/".join([owner, repo, branch, *rest])
                return f"https://raw.githubusercontent.com/{raw_path}"
    return file_url


@router.post("/ragload", summary="Load table schema documents for RAG processing")
async def stream_chat_response(url: str):
    """Validate the JSON file URL and return a success or error message."""
    try:
        if not url or not str(url).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": ["URL is required."]},
            )

        file_url = normalize_json_url(str(url).strip())
        parsed = urlparse(file_url)

        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": [f"Invalid URL: {file_url}"]},
            )

        try:
            with urlopen(file_url, timeout=10) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail={"errors": [f"JSON file not found: {file_url}"]},
                    )

                content = response.read()
                if not content:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"errors": [f"JSON file is empty: {file_url}"]},
                    )

                data = json.loads(content.decode("utf-8"))
        except (HTTPError, URLError, ValueError, UnicodeDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"errors": [f"JSON file not found or invalid: {file_url}"]},
            ) from exc
        logger.info("Loaded schema JSON from %s", file_url)
        table_documents = convertschemattodocument(data)
        len_doc = load_table_schema(table_documents)

        return {"message": "Table schema documents loaded successfully.", "loaded_documents": len_doc}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("RAG document loading failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"errors": [f"Document loading failed: {str(exc)}"]},
        ) from exc

@router.post("/broker-chat", response_model=ChatResponse, summary="Chat with the broker agent")
async def broker_chat_response(payload: ChatRequest):
    """broker agent chat endpoint."""
    sanitize_data = sanitize_all_input(payload.text)
    config = {"configurable": {"thread_id": payload.session_id}}

    prior_state = app.get_state(config)
    prior_history = []
    if prior_state and hasattr(prior_state, "values"):
        prior_history = list(prior_state.values.get("chat_history", []))

    state: AgentState = {
        "user_query": sanitize_data,
        "chat_history": prior_history,
        "human_in_loop": payload.human_in_loop,
    }
    output_state = app.invoke(state, config=config)
    response_text = str(output_state.get("final_output", "Unable to generate a response.")).strip()
    human_in_loop = output_state.get("human_in_loop") is True
    decision_data = dict(output_state.get("decision_data", {}))
    if not decision_data:
        decision_data = {
            "summary": response_text,
            "generated_sql": output_state.get("generated_sql", ""),
            "status": "pending" if human_in_loop else "auto",
            "query": payload.text,
        }
    else:
        decision_data.setdefault("query", payload.text)
    return ChatResponse(
        response=response_text,
        human_in_loop=human_in_loop,
        decision_data=decision_data,
    )


@router.post("/broker-chat/decision", summary="Approve or reject a chatbot decision")
async def broker_chat_decision(payload: DecisionRequest):
    """Persist the user's approval decision for the current chat session."""
    logger.info("Received %s decision for session %s", payload.decision, payload.session_id)
    config = {"configurable": {"thread_id": payload.session_id}}
    try:
        app.update_state(
            config,
            {
                "decision": payload.decision,
                "user_query": payload.query,
                "generated_sql": payload.sql,
                "decision_data": payload.decision_data,
            },
        )
        rows_updated = None
        if payload.decision == "approved":
            rows_updated = update_database(payload.sql)

        logger.info(f"Decision for session {payload.session_id} updated to: {payload.decision}")
        if(payload.decision == "rejected"):
            logger.info(f"User rejected the decision for session {payload.session_id}.")
        if(payload.decision == "approved"):
            logger.info(f"User approved the decision for session {payload.session_id}.")
            logger.info(f"Query: {payload.query}")
        return {
            "status": payload.decision,
            "query": payload.query,
            "sql": payload.sql,
            "rows_updated": rows_updated,
            "decision_data": payload.decision_data,
        }
    except Exception as exc:
        logger.exception("Failed to save chatbot decision")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save the chatbot decision.",
        ) from exc