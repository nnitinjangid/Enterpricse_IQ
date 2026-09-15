import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

from app.evaluation.evaluator import (
    evaluate_retrieval_dataset,
    evaluate_generation_dataset,
)

from app.agent.graph import run_agent


router = APIRouter(
    prefix="/api/evaluation",
    tags=["Evaluation"],
)


# =========================================================
# Request Schemas
# =========================================================

class EvaluationRequest(BaseModel):
    top_k: int = Field(
        default=3,
        ge=1,
        le=20,
    )


# =========================================================
# Admin Check
# =========================================================

def require_admin(
    current_user: User,
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    return current_user


# =========================================================
# Evaluation Dataset Loader
# =========================================================

def load_evaluation_dataset() -> list[dict]:
    """
    Load the shared evaluation dataset from:

        app/evaluation/evaluation_dataset.json
    """

    dataset_path = (
        Path(__file__).resolve().parent.parent
        / "evaluation"
        / "evaluation_dataset.json"
    )

    if not dataset_path.exists():
        raise FileNotFoundError(
            "Evaluation dataset not found: "
            f"{dataset_path}"
        )

    with open(
        dataset_path,
        "r",
        encoding="utf-8",
    ) as file:

        dataset = json.load(file)

    if not isinstance(
        dataset,
        list,
    ):
        raise ValueError(
            "Evaluation dataset must contain a JSON list."
        )

    return dataset


# =========================================================
# Helper Functions
# =========================================================

def normalize_route(
    route,
) -> str:
    """
    Normalize route values for evaluation.
    """

    if route is None:
        return ""

    return str(route).strip().lower()


def normalize_tools(
    tools,
) -> list[str]:
    """
    Normalize tool list for evaluation.
    """

    if not tools:
        return []

    normalized = []

    for tool in tools:

        if isinstance(
            tool,
            dict,
        ):

            tool_name = tool.get(
                "tool"
            )

        else:

            tool_name = tool

        if tool_name:

            normalized.append(
                str(tool_name)
                .strip()
                .lower()
            )

    return normalized


def get_planned_tools(
    result: dict,
) -> list[str]:
    """
    Get tools selected by the agent.

    Primary source:
        result["tools"]

    Fallback:
        result["plan"]
    """

    tools = result.get(
        "tools"
    )

    if tools:

        return normalize_tools(
            tools
        )

    plan = result.get(
        "plan",
        []
    )

    if not plan:
        return []

    planned_tools = []

    for step in plan:

        if not isinstance(
            step,
            dict,
        ):
            continue

        tool = step.get(
            "tool"
        )

        if tool:

            planned_tools.append(
                tool
            )

    return normalize_tools(
        planned_tools
    )


def get_executed_tools(
    result: dict,
) -> list[str]:
    """
    Determine which tools were actually executed.

    The graph stores tool results in:

        result["tool_results"]
    """

    tool_results = result.get(
        "tool_results"
    )

    if isinstance(
        tool_results,
        dict,
    ):

        return normalize_tools(
            list(
                tool_results.keys()
            )
        )

    # -----------------------------------------------------
    # Fallback for older result formats
    # -----------------------------------------------------

    executed = result.get(
        "executed_tools"
    )

    if executed:

        return normalize_tools(
            executed
        )

    return []


def extract_actual_answer(
    result: dict,
) -> str:
    """
    Extract the final answer returned by the agent.
    """

    answer = result.get(
        "answer"
    )

    if answer is None:
        return ""

    return str(
        answer
    ).strip()


def check_answer_contains(
    actual_answer: str,
    expected_contains: list[str],
) -> float:
    """
    Check whether all expected strings occur
    in the actual answer.

    Case-insensitive.
    """

    if not expected_contains:
        return 1.0

    normalized_answer = (
        actual_answer.lower()
    )

    for expected in expected_contains:

        if not expected:
            continue

        if (
            str(expected).lower()
            not in normalized_answer
        ):

            return 0.0

    return 1.0


# =========================================================
# Evaluation Result Printers
# =========================================================

def print_retrieval_metrics(
    result: dict,
    top_k: int,
):
    """
    Print final retrieval evaluation metrics.

    The evaluator returns metrics inside:

        result["average_metrics"]

    The "metrics" key is kept as a fallback
    for compatibility with older result formats.
    """

    print()
    print(
        "=" * 70
    )

    print(
        "RETRIEVAL EVALUATION FINAL RESULTS"
    )

    print(
        "=" * 70
    )

    total_questions = result.get(
        "total_questions",
        result.get(
            "questions",
            0,
        ),
    )

    print(
        f"Total Questions : {total_questions}"
    )

    print(
        f"Top K           : {top_k}"
    )

    metrics = result.get(
        "average_metrics",
        result.get(
            "metrics",
            {},
        ),
    )

    precision = metrics.get(
        "precision_at_k",
        0.0,
    )

    recall = metrics.get(
        "recall_at_k",
        0.0,
    )

    hit_rate = metrics.get(
        "hit_rate_at_k",
        0.0,
    )

    mrr = metrics.get(
        "mrr",
        0.0,
    )

    print(
        f"Precision@{top_k}     : {precision}"
    )

    print(
        f"Recall@{top_k}        : {recall}"
    )

    print(
        f"Hit Rate@{top_k}      : {hit_rate}"
    )

    print(
        f"MRR                   : {mrr}"
    )

    print(
        "=" * 70
    )


def print_generation_metrics(
    result: dict,
    top_k: int,
):
    """
    Print final generation evaluation metrics.

    The evaluator returns metrics inside:

        result["average_metrics"]

    The "metrics" key is kept as a fallback
    for compatibility with older result formats.
    """

    print()
    print(
        "=" * 70
    )

    print(
        "GENERATION EVALUATION FINAL RESULTS"
    )

    print(
        "=" * 70
    )

    total_questions = result.get(
        "total_questions",
        result.get(
            "questions",
            0,
        ),
    )

    print(
        f"Total Questions      : {total_questions}"
    )

    print(
        f"Top K                : {top_k}"
    )

    metrics = result.get(
        "average_metrics",
        result.get(
            "metrics",
            {},
        ),
    )

    faithfulness = metrics.get(
        "faithfulness",
        0.0,
    )

    answer_relevance = metrics.get(
        "answer_relevance",
        0.0,
    )

    answer_correctness = metrics.get(
        "answer_correctness",
        0.0,
    )

    print(
        f"Faithfulness         : {faithfulness}"
    )

    print(
        f"Answer Relevance     : {answer_relevance}"
    )

    print(
        f"Answer Correctness   : {answer_correctness}"
    )

    print(
        "=" * 70
    )


# =========================================================
# RAG Debug Helpers
# =========================================================

def extract_rag_sources(
    result: dict,
) -> list[dict]:
    """
    Extract RAG source information from different
    possible agent result formats.

    Possible locations:

        result["sources"]

        result["tool_results"]["rag"]["sources"]

        result["tool_results"]["rag"]["result"]["sources"]

    Returns a normalized list of source dictionaries.
    """

    sources = []

    # -----------------------------------------------------
    # Case 1:
    # result["sources"]
    # -----------------------------------------------------

    direct_sources = result.get(
        "sources"
    )

    if isinstance(
        direct_sources,
        list,
    ):

        sources.extend(
            direct_sources
        )

    # -----------------------------------------------------
    # Case 2:
    # result["tool_results"]["rag"]
    # -----------------------------------------------------

    tool_results = result.get(
        "tool_results"
    )

    if isinstance(
        tool_results,
        dict,
    ):

        rag_result = tool_results.get(
            "rag"
        )

        if isinstance(
            rag_result,
            dict,
        ):

            nested_sources = rag_result.get(
                "sources"
            )

            if isinstance(
                nested_sources,
                list,
            ):

                sources.extend(
                    nested_sources
                )

            # ---------------------------------------------
            # Older / nested result format
            # ---------------------------------------------

            nested_result = rag_result.get(
                "result"
            )

            if isinstance(
                nested_result,
                dict,
            ):

                nested_result_sources = (
                    nested_result.get(
                        "sources"
                    )
                )

                if isinstance(
                    nested_result_sources,
                    list,
                ):

                    sources.extend(
                        nested_result_sources
                    )

    # -----------------------------------------------------
    # Remove duplicate source objects
    # -----------------------------------------------------

    unique_sources = []

    seen = set()

    for source in sources:

        if not isinstance(
            source,
            dict,
        ):
            continue

        filename = source.get(
            "filename"
        )

        page_number = source.get(
            "page_number"
        )

        chunk_id = source.get(
            "chunk_id"
        )

        content = source.get(
            "content",
            "",
        )

        identity = (
            filename,
            page_number,
            chunk_id,
            content,
        )

        if identity in seen:
            continue

        seen.add(
            identity
        )

        unique_sources.append(
            source
        )

    return unique_sources


def build_debug_source(
    source: dict,
) -> dict:
    """
    Create a clean source object for terminal output
    and API debugging response.
    """

    return {
        "filename": source.get(
            "filename"
        ),

        "page_number": source.get(
            "page_number"
        ),

        "chunk_id": source.get(
            "chunk_id"
        ),

        "document_id": source.get(
            "document_id"
        ),

        "content": source.get(
            "content",
            "",
        ),

        "score": source.get(
            "score"
        ),

        "rerank_score": source.get(
            "rerank_score"
        ),

        "source_authority": source.get(
            "source_authority"
        ),

        "final_rerank_score": source.get(
            "final_rerank_score"
        ),
    }


def print_rag_debug(
    result: dict,
):
    """
    Print complete RAG retrieval information
    for debugging evaluation failures.
    """

    print()
    print(
        "=" * 70
    )

    print(
        "[RAG DEBUG] FULL AGENT RESULT"
    )

    print(
        "=" * 70
    )

    print(
        result
    )

    sources = extract_rag_sources(
        result
    )

    print()
    print(
        "=" * 70
    )

    print(
        f"[RAG DEBUG] TOTAL SOURCES FOUND: {len(sources)}"
    )

    print(
        "=" * 70
    )

    if not sources:

        print(
            "[RAG DEBUG] No RAG sources found."
        )

        return

    for source_index, source in enumerate(
        sources,
        start=1,
    ):

        debug_source = build_debug_source(
            source
        )

        print()
        print(
            "-" * 70
        )

        print(
            f"[RAG DEBUG] SOURCE {source_index}"
        )

        print(
            "-" * 70
        )

        print(
            "[RAG DEBUG] Filename:",
            debug_source["filename"],
        )

        print(
            "[RAG DEBUG] Document ID:",
            debug_source["document_id"],
        )

        print(
            "[RAG DEBUG] Chunk ID:",
            debug_source["chunk_id"],
        )

        print(
            "[RAG DEBUG] Page:",
            debug_source["page_number"],
        )

        print(
            "[RAG DEBUG] Score:",
            debug_source["score"],
        )

        print(
            "[RAG DEBUG] Rerank Score:",
            debug_source["rerank_score"],
        )

        print(
            "[RAG DEBUG] Source Authority:",
            debug_source["source_authority"],
        )

        print(
            "[RAG DEBUG] Final Rerank Score:",
            debug_source["final_rerank_score"],
        )

        print()
        print(
            "[RAG DEBUG] CONTENT:"
        )

        print(
            debug_source["content"]
        )

        print()


# =========================================================
# Retrieval Evaluation
# =========================================================

@router.post(
    "/retrieval"
)
def run_retrieval_evaluation(
    request: EvaluationRequest,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Run retrieval evaluation.

    Admin only.
    """

    require_admin(
        current_user
    )

    try:

        evaluation_dataset = (
            load_evaluation_dataset()
        )

        result = evaluate_retrieval_dataset(
            dataset=evaluation_dataset,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            top_k=request.top_k,
        )

        print_retrieval_metrics(
            result=result,
            top_k=request.top_k,
        )

        # =================================================
        # Flatten metrics for frontend compatibility
        # =================================================

        average_metrics = result.get(
            "average_metrics",
            {},
        )

        response = {
            **result,

            "precision_at_3": average_metrics.get(
                "precision_at_k",
                0.0,
            ),

            "recall_at_3": average_metrics.get(
                "recall_at_k",
                0.0,
            ),

            "hit_rate_at_3": average_metrics.get(
                "hit_rate_at_k",
                0.0,
            ),

            "precision": average_metrics.get(
                "precision_at_k",
                0.0,
            ),

            "recall": average_metrics.get(
                "recall_at_k",
                0.0,
            ),

            "hit_rate": average_metrics.get(
                "hit_rate_at_k",
                0.0,
            ),

            "mrr": average_metrics.get(
                "mrr",
                0.0,
            ),
        }

        print(
            "[EVALUATION API] Retrieval response:"
        )

        print(
            response
        )

        return response

    except Exception as e:

        print(
            f"[RETRIEVAL EVALUATION ERROR] {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Generation Evaluation
# =========================================================

@router.post(
    "/generation"
)
def run_generation_evaluation(
    request: EvaluationRequest,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Run generation evaluation.

    Admin only.
    """

    require_admin(
        current_user
    )

    try:

        evaluation_dataset = (
            load_evaluation_dataset()
        )

        result = evaluate_generation_dataset(
            dataset=evaluation_dataset,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            top_k=request.top_k,
        )

        print_generation_metrics(
            result=result,
            top_k=request.top_k,
        )

        # =================================================
        # Flatten metrics for frontend compatibility
        # =================================================

        average_metrics = result.get(
            "average_metrics",
            {},
        )

        response = {
            **result,

            "faithfulness": average_metrics.get(
                "faithfulness",
                0.0,
            ),

            "answer_relevance": average_metrics.get(
                "answer_relevance",
                0.0,
            ),

            "answer_correctness": average_metrics.get(
                "answer_correctness",
                0.0,
            ),

            # CamelCase compatibility
            "answerRelevance": average_metrics.get(
                "answer_relevance",
                0.0,
            ),

            "answerCorrectness": average_metrics.get(
                "answer_correctness",
                0.0,
            ),
        }

        print(
            "[EVALUATION API] Generation response:"
        )

        print(
            response
        )

        return response

    except Exception as e:

        print(
            f"[GENERATION EVALUATION ERROR] {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Agent Evaluation
# =========================================================

@router.post(
    "/agent"
)
def run_agent_evaluation(
    request: EvaluationRequest,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Run complete Agent evaluation.

    Evaluates:

    1. Route accuracy
    2. Tool selection accuracy
    3. Tool execution accuracy
    4. Final answer accuracy
    """

    require_admin(
        current_user
    )

    # =====================================================
    # Load Shared Evaluation Dataset
    # =====================================================

    evaluation_dataset = (
        load_evaluation_dataset()
    )

    # =====================================================
    # Metrics
    # =====================================================

    route_scores = []

    tool_selection_scores = []

    tool_execution_scores = []

    final_answer_scores = []

    evaluation_results = []

    print()
    print(
        "=" * 70
    )

    print(
        "AGENT EVALUATION"
    )

    print(
        "=" * 70
    )

    print(
        f"[EVALUATION] Dataset Questions: "
        f"{len(evaluation_dataset)}"
    )

    # =====================================================
    # Run Each Question
    # =====================================================

    for index, item in enumerate(
        evaluation_dataset,
        start=1,
    ):

        question = item.get(
            "question",
            "",
        )

        expected_route = normalize_route(
            item.get(
                "expected_route"
            )
        )

        expected_tools = normalize_tools(
            item.get(
                "expected_tools",
                [],
            )
        )

        expected_answer = str(
            item.get(
                "expected_answer",
                "",
            )
        ).strip()

        expected_contains = item.get(
            "expected_answer_contains",
            [],
        )

        print()
        print(
            "-" * 70
        )

        print(
            f"[EVALUATION] Question "
            f"{index}/{len(evaluation_dataset)}"
        )

        print(
            f"[EVALUATION] {question}"
        )

        try:

            # =================================================
            # Run Agent
            # =================================================

            result = run_agent(
                question=question,
                db=db,
                user_id=current_user.id,
                user_role=current_user.role,
            )

            # =================================================
            # Actual Route
            # =================================================

            actual_route = normalize_route(
                result.get(
                    "route"
                )
            )

            # =================================================
            # Actual Planned Tools
            # =================================================

            actual_tools = get_planned_tools(
                result
            )

            # =================================================
            # Actual Executed Tools
            # =================================================

            executed_tools = get_executed_tools(
                result
            )

            # =================================================
            # Actual Final Answer
            # =================================================

            actual_answer = extract_actual_answer(
                result
            )

            # =================================================
            # Extract RAG Sources
            # =================================================

            rag_sources = extract_rag_sources(
                result
            )

            debug_sources = []

            for source in rag_sources:

                debug_sources.append(
                    build_debug_source(
                        source
                    )
                )

            # =================================================
            # Route Accuracy
            # =================================================

            route_accuracy = (
                1.0
                if actual_route
                == expected_route
                else 0.0
            )

            # =================================================
            # Tool Selection Accuracy
            # =================================================

            tool_selection_accuracy = (
                1.0
                if actual_tools
                == expected_tools
                else 0.0
            )

            # =================================================
            # Tool Execution Accuracy
            # =================================================

            tool_execution_accuracy = (
                1.0
                if executed_tools
                == expected_tools
                else 0.0
            )

            # =================================================
            # Final Answer Accuracy
            # =================================================

            final_answer_accuracy = (
                check_answer_contains(
                    actual_answer,
                    expected_contains,
                )
            )

            # =================================================
            # Store Scores
            # =================================================

            route_scores.append(
                route_accuracy
            )

            tool_selection_scores.append(
                tool_selection_accuracy
            )

            tool_execution_scores.append(
                tool_execution_accuracy
            )

            final_answer_scores.append(
                final_answer_accuracy
            )

            # =================================================
            # Terminal Output
            # =================================================

            print(
                f"[EVALUATION] Expected Route: "
                f"{expected_route}"
            )

            print(
                f"[EVALUATION] Actual Route: "
                f"{actual_route}"
            )

            print(
                f"[EVALUATION] Expected Tools: "
                f"{expected_tools}"
            )

            print(
                f"[EVALUATION] Actual Tools: "
                f"{actual_tools}"
            )

            print(
                f"[EVALUATION] Executed Tools: "
                f"{executed_tools}"
            )

            print(
                "[EVALUATION] Expected Answer: "
                f"{expected_answer}"
            )

            print(
                "[EVALUATION] Actual Answer: "
                f"{actual_answer}"
            )

            print(
                "[EVALUATION] Expected Contains: "
                f"{expected_contains}"
            )

            print(
                "[EVALUATION] Route: "
                f"{route_accuracy}"
            )

            print(
                "[EVALUATION] Tool Selection: "
                f"{tool_selection_accuracy}"
            )

            print(
                "[EVALUATION] Tool Execution: "
                f"{tool_execution_accuracy}"
            )

            print(
                "[EVALUATION] Final Answer: "
                f"{final_answer_accuracy}"
            )

            # =================================================
            # RAG Debug
            # =================================================

            if "rag" in actual_tools:

                print_rag_debug(
                    result
                )

            # =================================================
            # Detailed Result
            # =================================================

            evaluation_results.append(
                {
                    "question": question,

                    "expected_route": (
                        expected_route
                    ),

                    "actual_route": (
                        actual_route
                    ),

                    "expected_tools": (
                        expected_tools
                    ),

                    "actual_tools": (
                        actual_tools
                    ),

                    "executed_tools": (
                        executed_tools
                    ),

                    "expected_answer": (
                        expected_answer
                    ),

                    "actual_answer": (
                        actual_answer
                    ),

                    "expected_answer_contains": (
                        expected_contains
                    ),

                    "route_accuracy": (
                        route_accuracy
                    ),

                    "tool_selection_accuracy": (
                        tool_selection_accuracy
                    ),

                    "tool_execution_accuracy": (
                        tool_execution_accuracy
                    ),

                    "final_answer_accuracy": (
                        final_answer_accuracy
                    ),

                    "rag_sources": (
                        debug_sources
                    ),
                }
            )

        except Exception as e:

            print(
                f"[EVALUATION] ERROR: {e}"
            )

            route_scores.append(
                0.0
            )

            tool_selection_scores.append(
                0.0
            )

            tool_execution_scores.append(
                0.0
            )

            final_answer_scores.append(
                0.0
            )

            evaluation_results.append(
                {
                    "question": question,

                    "error": str(e),

                    "route_accuracy": 0.0,

                    "tool_selection_accuracy": 0.0,

                    "tool_execution_accuracy": 0.0,

                    "final_answer_accuracy": 0.0,

                    "rag_sources": [],
                }
            )

    # =====================================================
    # Calculate Final Metrics
    # =====================================================

    total_questions = len(
        evaluation_dataset
    )

    if total_questions == 0:

        raise HTTPException(
            status_code=500,
            detail="Evaluation dataset is empty.",
        )

    route_accuracy = (
        sum(route_scores)
        / total_questions
    )

    tool_selection_accuracy = (
        sum(tool_selection_scores)
        / total_questions
    )

    tool_execution_accuracy = (
        sum(tool_execution_scores)
        / total_questions
    )

    final_answer_accuracy = (
        sum(final_answer_scores)
        / total_questions
    )

    # =====================================================
    # Final Metrics
    # =====================================================

    metrics = {
        "route_accuracy": round(
            route_accuracy,
            4,
        ),

        "tool_selection_accuracy": round(
            tool_selection_accuracy,
            4,
        ),

        "tool_execution_accuracy": round(
            tool_execution_accuracy,
            4,
        ),

        "final_answer_accuracy": round(
            final_answer_accuracy,
            4,
        ),
    }

    # =====================================================
    # Final Terminal Output
    # =====================================================

    print()
    print(
        "=" * 70
    )

    print(
        "[EVALUATION] FINAL METRICS"
    )

    print(
        "=" * 70
    )

    print(
        metrics
    )

    print(
        "=" * 70
    )

    # =====================================================
    # Return API Response
    # =====================================================

    response = {
        "evaluation": "agent",

        "total_questions": (
            total_questions
        ),

        "route_accuracy": (
            metrics[
                "route_accuracy"
            ]
        ),

        "tool_selection_accuracy": (
            metrics[
                "tool_selection_accuracy"
            ]
        ),

        "tool_execution_accuracy": (
            metrics[
                "tool_execution_accuracy"
            ]
        ),

        "final_answer_accuracy": (
            metrics[
                "final_answer_accuracy"
            ]
        ),

        "metrics": metrics,

        "results": evaluation_results,
    }

    print(
        "[EVALUATION API] Agent response:"
    )

    print(
        response
    )

    return response