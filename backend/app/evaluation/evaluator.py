from sqlalchemy.orm import Session

from app.evaluation.retrieval_metrics import (
    evaluate_retrieval,
)

from app.services.hybrid_search_service import (
    hybrid_search,
)

from app.services.rag_service import (
    ask_rag,
    build_context,
)

from app.services.reranker_service import (
    rerank_results,
)

from app.evaluation.generation_metrics import (
    evaluate_generation,
)


def normalize_chunk_ids(
    chunks: list,
) -> list[tuple[int, int]]:
    """
    Convert JSON chunk IDs such as:

        [[2, 1], [2, 2]]

    into Python tuples:

        [(2, 1), (2, 2)]
    """

    normalized = []

    for chunk in chunks:

        if not isinstance(
            chunk,
            (list, tuple),
        ):

            raise ValueError(
                "Each relevant chunk must be "
                "[document_id, chunk_index]."
            )

        if len(chunk) != 2:

            raise ValueError(
                "Each relevant chunk must contain "
                "document_id and chunk_index."
            )

        try:

            document_id = int(
                chunk[0]
            )

            chunk_index = int(
                chunk[1]
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "document_id and chunk_index "
                "must be integers."
            )

        normalized.append(
            (
                document_id,
                chunk_index,
            )
        )

    return normalized


def evaluate_single_question(
    question: str,
    relevant_chunks: list,
    db: Session,
    user_id: int,
    user_role: str,
    top_k: int = 5,
) -> dict:

    if not question or not question.strip():

        raise ValueError(
            "Evaluation question cannot be empty."
        )

    if not relevant_chunks:

        raise ValueError(
            "Relevant chunks cannot be empty."
        )

    if top_k <= 0:

        raise ValueError(
            "top_k must be greater than 0."
        )

    normalized_relevant_chunks = (
        normalize_chunk_ids(
            relevant_chunks
        )
    )

    # ------------------------------------------------
    # RETRIEVAL
    # ------------------------------------------------

    candidates = hybrid_search(
        query=question.strip(),
        db=db,
        user_id=user_id,
        user_role=user_role,
        top_k=max(
            top_k * 2,
            10,
        ),
    )

    reranked_results = rerank_results(
        query=question.strip(),
        results=candidates,
        top_k=top_k,
    )

    # ------------------------------------------------
    # RETRIEVAL METRICS
    # ------------------------------------------------

    retrieved_chunks = []

    for result in reranked_results:

        document_id = result.get(
            "document_id"
        )

        chunk_index = result.get(
            "chunk_index"
        )

        if (
            document_id is not None
            and chunk_index is not None
        ):

            chunk_id = (
                int(document_id),
                int(chunk_index),
            )

            retrieved_chunks.append(
                chunk_id
            )

    retrieval_metrics = evaluate_retrieval(
        retrieved_chunks=retrieved_chunks,
        relevant_chunks=normalized_relevant_chunks,
        k=top_k,
    )

    return {
        "question": question.strip(),
        "top_k": top_k,
        "retrieved_chunks": [
            list(chunk)
            for chunk in retrieved_chunks
        ],
        "relevant_chunks": [
            list(chunk)
            for chunk in normalized_relevant_chunks
        ],
        "metrics": retrieval_metrics,
        "results": reranked_results,
    }


def evaluate_retrieval_dataset(
    dataset: list[dict],
    db: Session,
    user_id: int,
    user_role: str,
    top_k: int = 5,
) -> dict:

    if not dataset:

        raise ValueError(
            "Evaluation dataset cannot be empty."
        )

    question_results = []

    for index, item in enumerate(
        dataset,
        start=1,
    ):

        question = item.get(
            "question"
        )

        relevant_chunks = item.get(
            "relevant_chunks",
            [],
        )

        if not question:

            raise ValueError(
                f"Question missing in "
                f"evaluation item {index}."
            )

        result = evaluate_single_question(
            question=question,
            relevant_chunks=relevant_chunks,
            db=db,
            user_id=user_id,
            user_role=user_role,
            top_k=top_k,
        )

        question_results.append(
            result
        )

    total_precision = 0.0
    total_recall = 0.0
    total_hit_rate = 0.0
    total_mrr = 0.0

    for result in question_results:

        metrics = result["metrics"]

        total_precision += metrics[
            "precision_at_k"
        ]

        total_recall += metrics[
            "recall_at_k"
        ]

        total_hit_rate += metrics[
            "hit_rate_at_k"
        ]

        total_mrr += metrics[
            "mrr"
        ]

    count = len(
        question_results
    )

    average_metrics = {
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

    return {
        "total_questions": count,
        "top_k": top_k,
        "average_metrics": average_metrics,
        "questions": question_results,
    }


# ============================================================
# GENERATION EVALUATION
# ============================================================


def evaluate_single_generation(
    question: str,
    expected_answer: str,
    db: Session,
    user_id: int,
    user_role: str,
    top_k: int = 5,
) -> dict:
    """
    Run the real EnterpriseIQ RAG pipeline and
    evaluate the generated answer.
    """

    if not question or not question.strip():

        raise ValueError(
            "Evaluation question cannot be empty."
        )

    if not expected_answer or not expected_answer.strip():

        raise ValueError(
            "Expected answer cannot be empty."
        )

    if top_k <= 0:

        raise ValueError(
            "top_k must be greater than 0."
        )

    # ------------------------------------------------
    # RUN ACTUAL RAG
    # ------------------------------------------------

    rag_result = ask_rag(
        question=question.strip(),
        db=db,
        user_id=user_id,
        user_role=user_role,
        top_k=top_k,
    )

    generated_answer = rag_result.get(
        "answer",
        "",
    )

    sources = rag_result.get(
        "sources",
        [],
    )

    # ------------------------------------------------
    # BUILD RETRIEVED CONTEXT
    # ------------------------------------------------

    context = build_context(
        search_results=sources
    )

    # ------------------------------------------------
    # GENERATION METRICS
    # ------------------------------------------------

    metrics = evaluate_generation(
        question=question.strip(),
        answer=generated_answer,
        expected_answer=expected_answer.strip(),
        context=context,
    )

    return {
        "question": question.strip(),
        "expected_answer": expected_answer.strip(),
        "generated_answer": generated_answer,
        "context": context,
        "sources": sources,
        "metrics": metrics,
    }


def evaluate_generation_dataset(
    dataset: list[dict],
    db: Session,
    user_id: int,
    user_role: str,
    top_k: int = 5,
) -> dict:
    """
    Run generation evaluation for the complete
    evaluation dataset.
    """

    if not dataset:

        raise ValueError(
            "Evaluation dataset cannot be empty."
        )

    question_results = []

    for index, item in enumerate(
        dataset,
        start=1,
    ):

        question = item.get(
            "question"
        )

        expected_answer = item.get(
            "expected_answer"
        )

        if not question:

            raise ValueError(
                f"Question missing in "
                f"evaluation item {index}."
            )

        if not expected_answer:

            raise ValueError(
                f"Expected answer missing in "
                f"evaluation item {index}."
            )

        print()
        print(
            "-" * 70
        )

        print(
            f"Generation Evaluation "
            f"{index}/{len(dataset)}"
        )

        print(
            f"Question: {question}"
        )

        result = evaluate_single_generation(
            question=question,
            expected_answer=expected_answer,
            db=db,
            user_id=user_id,
            user_role=user_role,
            top_k=top_k,
        )

        question_results.append(
            result
        )

    # ------------------------------------------------
    # CALCULATE AVERAGES
    # ------------------------------------------------

    total_faithfulness = 0.0
    total_relevance = 0.0
    total_correctness = 0.0

    for result in question_results:

        metrics = result["metrics"]

        total_faithfulness += metrics[
            "faithfulness"
        ]

        total_relevance += metrics[
            "answer_relevance"
        ]

        total_correctness += metrics[
            "answer_correctness"
        ]

    count = len(
        question_results
    )

    average_metrics = {
        "faithfulness": round(
            total_faithfulness / count,
            4,
        ),
        "answer_relevance": round(
            total_relevance / count,
            4,
        ),
        "answer_correctness": round(
            total_correctness / count,
            4,
        ),
    }

    return {
        "total_questions": count,
        "top_k": top_k,
        "average_metrics": average_metrics,
        "questions": question_results,
    }