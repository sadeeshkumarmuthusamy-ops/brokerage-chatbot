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

from mockup_sql_ragsetup.ragsetup.dataingestionandload import convertschemattodocument, load_table_schema

logger = logging.getLogger(__name__)
app = create_and_compile_workflow()

router = APIRouter(prefix="/brokeragent", tags=["Chat & Agents"])


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    text: str = Field(min_length=1)

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
        print(f"Loaded JSON data from {file_url}: {data}")
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

@router.post("/broker-chat", summary="Chat with the broker agent")
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
    }
    output_state = app.invoke(state, config=config)
    print(f"Updated chat history: {output_state.get('chat_history', [])}")
    return {"response": output_state.get("final_output", output_state)}