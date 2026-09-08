from qdrant_client import QdrantClient

from app.core.config import settings


# =========================================================
# Qdrant Client
# =========================================================

qdrant_client = QdrantClient(
    url=settings.QDRANT_URL,
)


# =========================================================
# Health Check
# =========================================================

def check_qdrant_connection() -> bool:
    """
    Check whether Qdrant is reachable.
    """

    try:

        qdrant_client.get_collections()

        return True

    except Exception as e:

        print(
            f"Qdrant connection error: {e}"
        )

        return False