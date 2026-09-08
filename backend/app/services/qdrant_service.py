from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.core.qdrant import qdrant_client
from app.services.embedding_service import (
    generate_embedding,
    generate_embeddings,
)


# =========================================================
# Collection
# =========================================================

def create_collection_if_not_exists(
    vector_size: int,
) -> None:
    """
    Create Qdrant collection if it does not exist.
    """

    collections = qdrant_client.get_collections()

    collection_names = [
        collection.name
        for collection in collections.collections
    ]

    if settings.QDRANT_COLLECTION not in collection_names:

        qdrant_client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

        print(
            f"Created Qdrant collection: "
            f"{settings.QDRANT_COLLECTION}"
        )


# =========================================================
# Delete Document Vectors
# =========================================================

def delete_document_vectors(
    document_id: int,
) -> None:
    """
    Delete all vectors belonging to a document.
    """

    try:

        qdrant_client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(
                            value=document_id
                        ),
                    )
                ]
            ),
        )

    except Exception as e:

        error_message = str(e).lower()

        if "doesn't exist" in error_message:
            return

        raise


# =========================================================
# Store Document Chunks
# =========================================================

def store_document_chunks(
    chunks: list[dict],
    document_id: int,
    filename: str,
) -> int:
    """
    Generate embeddings for document chunks
    and store them in Qdrant.
    """

    if not chunks:
        return 0

    # -----------------------------------------------------
    # Extract chunk texts
    # -----------------------------------------------------

    texts = [
        chunk["content"]
        for chunk in chunks
    ]

    # -----------------------------------------------------
    # Generate embeddings
    # -----------------------------------------------------

    embeddings = generate_embeddings(
        texts
    )

    if not embeddings:
        return 0

    # -----------------------------------------------------
    # Create collection
    # -----------------------------------------------------

    vector_size = len(
        embeddings[0]
    )

    create_collection_if_not_exists(
        vector_size=vector_size
    )

    # -----------------------------------------------------
    # Remove previous vectors
    # -----------------------------------------------------

    delete_document_vectors(
        document_id=document_id
    )

    # -----------------------------------------------------
    # Create Qdrant points
    # -----------------------------------------------------

    points = []

    for index, chunk in enumerate(chunks):

        point_id = (
            document_id * 1_000_000
            + chunk["chunk_index"]
        )

        payload = {
            "document_id": document_id,
            "filename": filename,
            "chunk_index": chunk["chunk_index"],
            "page_number": chunk["page_number"],
            "content": chunk["content"],
        }

        points.append(
            PointStruct(
                id=point_id,
                vector=embeddings[index],
                payload=payload,
            )
        )

    # -----------------------------------------------------
    # Upload points
    # -----------------------------------------------------

    qdrant_client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=points,
    )

    print(
        f"Stored {len(points)} vectors in Qdrant "
        f"for document {document_id}."
    )

    return len(points)


# =========================================================
# Semantic Search
# =========================================================

def search_documents(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Search relevant document chunks using
    semantic vector similarity.
    """

    if not query or not query.strip():
        raise ValueError(
            "Search query cannot be empty."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    # -----------------------------------------------------
    # Generate query embedding
    # -----------------------------------------------------

    query_embedding = generate_embedding(
        query.strip()
    )

    # -----------------------------------------------------
    # Search Qdrant
    # -----------------------------------------------------

    search_results = qdrant_client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_embedding,
        limit=top_k,
        with_payload=True,
    ).points

    # -----------------------------------------------------
    # Format results
    # -----------------------------------------------------

    results = []

    for result in search_results:

        payload = result.payload or {}

        results.append(
            {
                "score": float(result.score),
                "document_id": payload.get(
                    "document_id"
                ),
                "filename": payload.get(
                    "filename"
                ),
                "chunk_index": payload.get(
                    "chunk_index"
                ),
                "page_number": payload.get(
                    "page_number"
                ),
                "content": payload.get(
                    "content",
                    "",
                ),
            }
        )

    return results