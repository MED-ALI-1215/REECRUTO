import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    """
    Return a singleton ChromaDB client.
    - CHROMA_USE_SERVER=false  →  local PersistentClient (dev/current behaviour)
    - CHROMA_USE_SERVER=true   →  HttpClient pointing at Docker container (prod)
    """
    global _client
    if _client is not None:
        return _client

    settings = get_settings()

    if settings.CHROMA_USE_SERVER:
        logger.info("ChromaDB: connecting to server at %s:%s", settings.CHROMA_HOST, settings.CHROMA_PORT)
        _client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
    else:
        logger.info("ChromaDB: using local PersistentClient at %s", settings.CHROMA_DB_PATH)
        _client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

    return _client


def get_candidates_collection() -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="candidates",
        metadata={"description": "CV candidates for job matching"},
    )
