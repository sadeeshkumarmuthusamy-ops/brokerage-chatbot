import logging

from src.config.settings import settings
try:
    from langchain_chroma import Chroma
except ModuleNotFoundError:  # pragma: no cover
    from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

def get_chroma_db():
    """Initialize and return a Chroma vector store instance."""
    try:
        if not settings.CHROMA_DB_PATH:
            raise ValueError("CHROMA_DB_PATH is not configured")

        embeddings = OpenAIEmbeddings(
            base_url=settings.OPENAI_API_BASE,
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        return Chroma(
            persist_directory=settings.CHROMA_DB_PATH,
            embedding_function=embeddings,
        )
    except Exception as exc:
        logger.exception("Failed to initialize schema vector store")
        raise RuntimeError("Unable to initialize schema retrieval.") from exc

def get_relevant_schemas(user_query: str, num_tables: int = 4) -> str:
    """Searches Chroma DB and formats retrieved table schemas into a single string."""
    if not isinstance(user_query, str) or not user_query.strip():
        raise ValueError("user_query must be a non-empty string")
    if not isinstance(num_tables, int) or num_tables < 1:
        raise ValueError("num_tables must be a positive integer")

    try:
        db = get_chroma_db()
        retrieved_docs = db.similarity_search(user_query, k=num_tables)
        logger.info("Retrieved %d relevant schemas", len(retrieved_docs))
        return "".join(
            f"\n--- TABLE SCHEMA ---\n{doc.page_content}\n"
            for doc in retrieved_docs
        )
    except Exception as exc:
        logger.exception("Failed to retrieve schemas")
        raise RuntimeError("Unable to retrieve relevant schemas.") from exc