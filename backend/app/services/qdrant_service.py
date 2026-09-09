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
    uploaded_by: int,
) -> int:

    if not chunks:
        return 0

    texts = [
        chunk["content"]
        for chunk in chunks
    ]

    embeddings = generate_embeddings(
        texts
    )

    if not embeddings:
        return 0

    vector_size = len(
        embeddings[0]
    )

    create_collection_if_not_exists(
        vector_size=vector_size
    )

    delete_document_vectors(
        document_id=document_id
    )

    points = []

    for index, chunk in enumerate(chunks):

        point_id = (
            document_id * 1_000_000
            + chunk["chunk_index"]
        )

        payload = {
            "document_id": document_id,
            "filename": filename,
            "uploaded_by": uploaded_by,
            "chunk_index": chunk[
                "chunk_index"
            ],
            "page_number": chunk[
                "page_number"
            ],
            "content": chunk["content"],
        }

        points.append(
            PointStruct(
                id=point_id,
                vector=embeddings[index],
                payload=payload,
            )
        )

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
    user_id: int | None = None,
) -> list[dict]:

    if not query or not query.strip():
        raise ValueError(
            "Search query cannot be empty."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    query_embedding = generate_embedding(
        query.strip()
    )

    # =====================================================
    # User Access Filter
    # =====================================================

    query_filter = None

    if user_id is not None:

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="uploaded_by",
                    match=MatchValue(
                        value=user_id
                    ),
                )
            ]
        )

    # =====================================================
    # Qdrant Search
    # =====================================================

    search_results = qdrant_client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_embedding,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    ).points

    results = []

    for result in search_results:

        payload = result.payload or {}

        results.append(
            {
                "score": float(
                    result.score
                ),
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
                "retrieval_method": "semantic",
            }
        )

    return results