from sqlalchemy.orm import Session

from app.services.bm25_service import (
    keyword_search,
)

from app.services.qdrant_service import (
    search_documents,
)


RRF_K = 60


def hybrid_search(
    query: str,
    db: Session,
    user_id: int,
    user_role: str,
    top_k: int = 5,
) -> list[dict]:

    if not query or not query.strip():

        raise ValueError(
            "Search query cannot be empty."
        )

    if top_k <= 0:

        raise ValueError(
            "top_k must be greater than 0."
        )

    if not user_role:

        raise ValueError(
            "user_role is required for "
            "document authorization."
        )

    candidate_k = max(
        top_k * 2,
        10,
    )

    # -----------------------------------------
    # SEMANTIC SEARCH
    # -----------------------------------------

    semantic_results = search_documents(
        query=query,
        top_k=candidate_k,
        user_id=user_id,
        user_role=user_role,
    )

    # -----------------------------------------
    # BM25 SEARCH
    # -----------------------------------------

    keyword_results = keyword_search(
        query=query,
        db=db,
        user_id=user_id,
        user_role=user_role,
        top_k=candidate_k,
    )

    combined_results = {}

    # -----------------------------------------
    # SEMANTIC RANK
    # -----------------------------------------

    for rank, result in enumerate(
        semantic_results,
        start=1,
    ):

        key = (
            result["document_id"],
            result["chunk_index"],
        )

        rrf_score = 1 / (
            RRF_K + rank
        )

        if key not in combined_results:

            combined_results[key] = {
                **result,
                "rrf_score": 0.0,
                "semantic_score": None,
                "keyword_score": None,
            }

        combined_results[key][
            "rrf_score"
        ] += rrf_score

        combined_results[key][
            "semantic_score"
        ] = result.get(
            "score"
        )

    # -----------------------------------------
    # BM25 RANK
    # -----------------------------------------

    for rank, result in enumerate(
        keyword_results,
        start=1,
    ):

        key = (
            result["document_id"],
            result["chunk_index"],
        )

        rrf_score = 1 / (
            RRF_K + rank
        )

        if key not in combined_results:

            combined_results[key] = {
                **result,
                "rrf_score": 0.0,
                "semantic_score": None,
                "keyword_score": None,
            }

        combined_results[key][
            "rrf_score"
        ] += rrf_score

        combined_results[key][
            "keyword_score"
        ] = result.get(
            "score"
        )

    # -----------------------------------------
    # FINAL HYBRID RANKING
    # -----------------------------------------

    ranked_results = sorted(
        combined_results.values(),
        key=lambda item: item[
            "rrf_score"
        ],
        reverse=True,
    )

    final_results = []

    for result in ranked_results[
        :top_k
    ]:

        final_results.append(
            {
                "score": result[
                    "rrf_score"
                ],
                "semantic_score": result[
                    "semantic_score"
                ],
                "keyword_score": result[
                    "keyword_score"
                ],
                "document_id": result[
                    "document_id"
                ],
                "filename": result[
                    "filename"
                ],
                "chunk_index": result[
                    "chunk_index"
                ],
                "page_number": result[
                    "page_number"
                ],
                "content": result[
                    "content"
                ],
                "access_scope": result.get(
                    "access_scope"
                ),
                "access_role": result.get(
                    "access_role"
                ),
                "retrieval_method": (
                    "hybrid"
                ),
            }
        )

    return final_results