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
# Source Authority
# =========================================================

HIGH_AUTHORITY_KEYWORDS = [
    "policy",
    "policies",
    "official",
    "approved",
    "handbook",
    "guideline",
    "guidelines",
    "rules",
    "standard",
    "contract",
    "agreement",
    "terms",
    "compliance",
    "procedure",
    "procedures",
]

LOW_AUTHORITY_KEYWORDS = [
    "fake",
    "sample",
    "test",
    "dummy",
    "example",
    "mock",
    "draft",
]


def calculate_source_authority(
    filename: str,
) -> float:
    """
    Calculate a lightweight source-authority score
    from the document filename.

    Higher score:
        official / policy / approved documents

    Lower score:
        fake / sample / test / dummy documents

    This score is only used as a tie-breaker /
    authority signal after semantic relevance.
    """

    if not filename:
        return 0.0

    normalized_filename = filename.lower()

    score = 0.0

    for keyword in HIGH_AUTHORITY_KEYWORDS:

        if keyword in normalized_filename:
            score += 1.0

    for keyword in LOW_AUTHORITY_KEYWORDS:

        if keyword in normalized_filename:
            score -= 1.0

    return score


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

    Ranking considers:

    1. Semantic relevance from Cross-Encoder
    2. Source authority from document metadata

    The authority signal is intentionally small so that
    relevance remains the primary ranking factor.
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
    # Generate Cross-Encoder Scores
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

        filename = result.get(
            "filename",
            "",
        )

        rerank_score = float(
            score
        )

        source_authority = (
            calculate_source_authority(
                filename
            )
        )

        # -------------------------------------------------
        # Authority adjustment
        #
        # Semantic relevance remains dominant.
        # Authority is used as a small tie-breaker.
        # -------------------------------------------------

        authority_adjustment = (
            source_authority * 0.25
        )

        final_rerank_score = (
            rerank_score
            + authority_adjustment
        )

        updated_result = {
            **result,

            # Original model score
            "rerank_score": rerank_score,

            # Source authority
            "source_authority": source_authority,

            # Final ranking score
            "final_rerank_score": (
                final_rerank_score
            ),

            "retrieval_method": (
                "hybrid_reranked"
            ),
        }

        reranked_results.append(
            updated_result
        )

    # =====================================================
    # Sort
    # =====================================================

    reranked_results.sort(
        key=lambda item: item[
            "final_rerank_score"
        ],
        reverse=True,
    )

    # =====================================================
    # Return Top-K
    # =====================================================

    return reranked_results[
        :top_k
    ]