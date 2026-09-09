from sentence_transformers import CrossEncoder

from app.core.config import settings


# =========================================================
# Reranker Model
# =========================================================

RERANKER_MODEL = (
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

_reranker = None


# =========================================================
# Load Reranker
# =========================================================

def get_reranker() -> CrossEncoder:
    global _reranker

    if _reranker is None:

        print(
            f"Loading reranker model: "
            f"{RERANKER_MODEL}"
        )

        _reranker = CrossEncoder(
            RERANKER_MODEL
        )

        print(
            "Reranker model loaded."
        )

    return _reranker


# =========================================================
# Rerank Results
# =========================================================

def rerank_results(
    query: str,
    results: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """
    Rerank retrieved chunks using a Cross-Encoder.

    The Cross-Encoder directly evaluates:
    
        Query + Document Chunk

    and produces a relevance score.
    """

    if not query or not query.strip():
        raise ValueError(
            "Query cannot be empty."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    if not results:
        return []

    # =====================================================
    # Prepare Query-Document Pairs
    # =====================================================

    pairs = []

    for result in results:

        content = result.get(
            "content",
            "",
        )

        if not content:
            content = ""

        pairs.append(
            [
                query.strip(),
                content,
            ]
        )

    # =====================================================
    # Generate Reranker Scores
    # =====================================================

    model = get_reranker()

    scores = model.predict(
        pairs
    )

    # =====================================================
    # Attach Scores
    # =====================================================

    reranked_results = []

    for result, score in zip(
        results,
        scores,
    ):

        updated_result = {
            **result,
            "rerank_score": float(score),
            "retrieval_method": "hybrid_reranked",
        }

        reranked_results.append(
            updated_result
        )

    # =====================================================
    # Sort by Reranker Score
    # =====================================================

    reranked_results.sort(
        key=lambda item: item[
            "rerank_score"
        ],
        reverse=True,
    )

    # =====================================================
    # Return Top-K
    # =====================================================

    return reranked_results[
        :top_k
    ]