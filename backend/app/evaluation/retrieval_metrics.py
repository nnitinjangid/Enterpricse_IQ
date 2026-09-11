# =========================================================
# EnterpriseIQ - Retrieval Evaluation Metrics
# =========================================================


def precision_at_k(
    retrieved_chunks: list,
    relevant_chunks: list,
    k: int,
) -> float:
    """
    Precision@K

    Formula:
        relevant retrieved chunks / K

    Example:
        Retrieved = [1, 2, 3]
        Relevant  = [2, 4]

        Precision@3 = 1 / 3
    """

    if k <= 0:
        raise ValueError(
            "k must be greater than 0."
        )

    if not retrieved_chunks:
        return 0.0

    relevant_set = set(
        relevant_chunks
    )

    retrieved_at_k = retrieved_chunks[:k]

    relevant_count = sum(
        1
        for chunk in retrieved_at_k
        if chunk in relevant_set
    )

    return (
        relevant_count
        / len(retrieved_at_k)
    )


def recall_at_k(
    retrieved_chunks: list,
    relevant_chunks: list,
    k: int,
) -> float:
    """
    Recall@K

    Formula:
        relevant retrieved chunks / total relevant chunks
    """

    if k <= 0:
        raise ValueError(
            "k must be greater than 0."
        )

    if not relevant_chunks:
        return 0.0

    relevant_set = set(
        relevant_chunks
    )

    retrieved_at_k = retrieved_chunks[:k]

    relevant_count = sum(
        1
        for chunk in retrieved_at_k
        if chunk in relevant_set
    )

    return (
        relevant_count
        / len(relevant_set)
    )


def hit_rate_at_k(
    retrieved_chunks: list,
    relevant_chunks: list,
    k: int,
) -> float:
    """
    Hit Rate@K

    Returns:

        1.0 -> at least one relevant chunk found
        0.0 -> no relevant chunk found
    """

    if k <= 0:
        raise ValueError(
            "k must be greater than 0."
        )

    if not retrieved_chunks:
        return 0.0

    if not relevant_chunks:
        return 0.0

    relevant_set = set(
        relevant_chunks
    )

    retrieved_at_k = retrieved_chunks[:k]

    for chunk in retrieved_at_k:

        if chunk in relevant_set:
            return 1.0

    return 0.0


def mean_reciprocal_rank(
    retrieved_chunks: list,
    relevant_chunks: list,
) -> float:
    """
    MRR

    Finds the rank of the first relevant result.

    Example:

        Retrieved:
        [10, 20, 30, 40]

        Relevant:
        [30]

        First relevant result is rank 3.

        Reciprocal Rank = 1 / 3
    """

    if not retrieved_chunks:
        return 0.0

    if not relevant_chunks:
        return 0.0

    relevant_set = set(
        relevant_chunks
    )

    for rank, chunk in enumerate(
        retrieved_chunks,
        start=1,
    ):

        if chunk in relevant_set:

            return 1.0 / rank

    return 0.0


def evaluate_retrieval(
    retrieved_chunks: list,
    relevant_chunks: list,
    k: int = 5,
) -> dict:
    """
    Calculate all retrieval metrics
    for a single question.
    """

    precision = precision_at_k(
        retrieved_chunks=retrieved_chunks,
        relevant_chunks=relevant_chunks,
        k=k,
    )

    recall = recall_at_k(
        retrieved_chunks=retrieved_chunks,
        relevant_chunks=relevant_chunks,
        k=k,
    )

    hit_rate = hit_rate_at_k(
        retrieved_chunks=retrieved_chunks,
        relevant_chunks=relevant_chunks,
        k=k,
    )

    mrr = mean_reciprocal_rank(
        retrieved_chunks=retrieved_chunks,
        relevant_chunks=relevant_chunks,
    )

    return {
        "precision_at_k": round(
            precision,
            4,
        ),
        "recall_at_k": round(
            recall,
            4,
        ),
        "hit_rate_at_k": round(
            hit_rate,
            4,
        ),
        "mrr": round(
            mrr,
            4,
        ),
    }


def evaluate_multiple_queries(
    evaluation_cases: list[dict],
    k: int = 5,
) -> dict:
    """
    Calculate average retrieval metrics
    across multiple evaluation questions.

    Expected input:

    [
        {
            "retrieved_chunks": [...],
            "relevant_chunks": [...]
        },
        ...
    ]
    """

    if not evaluation_cases:
        return {
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "hit_rate_at_k": 0.0,
            "mrr": 0.0,
        }

    all_results = []

    for case in evaluation_cases:

        result = evaluate_retrieval(
            retrieved_chunks=case[
                "retrieved_chunks"
            ],
            relevant_chunks=case[
                "relevant_chunks"
            ],
            k=k,
        )

        all_results.append(
            result
        )

    total_precision = sum(
        result["precision_at_k"]
        for result in all_results
    )

    total_recall = sum(
        result["recall_at_k"]
        for result in all_results
    )

    total_hit_rate = sum(
        result["hit_rate_at_k"]
        for result in all_results
    )

    total_mrr = sum(
        result["mrr"]
        for result in all_results
    )

    count = len(
        all_results
    )

    return {
        "precision_at_k": round(
            total_precision / count,
            4,
        ),
        "recall_at_k": round(
            total_recall / count,
            4,
        ),
        "hit_rate_at_k": round(
            total_hit_rate / count,
            4,
        ),
        "mrr": round(
            total_mrr / count,
            4,
        ),
    }