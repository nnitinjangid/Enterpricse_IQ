from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.core.dependencies import (
    require_role,
)

from app.evaluation.dataset import (
    get_evaluation_dataset,
)

from app.evaluation.evaluator import (
    evaluate_retrieval_dataset,
    evaluate_generation_dataset,
)

from app.agent.graph import (
    run_agent,
)

from app.models import User


router = APIRouter(
    prefix="/api/evaluation",
    tags=["Evaluation"],
)


class RetrievalEvaluationRequest(BaseModel):

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class GenerationEvaluationRequest(BaseModel):

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class AgentEvaluationRequest(BaseModel):

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )


# ============================================================
# RETRIEVAL EVALUATION
# ============================================================


@router.post("/retrieval")
def run_retrieval_evaluation(
    request: RetrievalEvaluationRequest,
    current_user: User = Depends(
        require_role("admin")
    ),
    db: Session = Depends(get_db),
):

    try:

        dataset = get_evaluation_dataset()

        if not dataset:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Evaluation dataset is empty."
                ),
            )

        result = evaluate_retrieval_dataset(
            dataset=dataset,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            top_k=request.top_k,
        )

        return {
            "evaluation_type": "retrieval",
            "evaluated_by": current_user.id,
            "evaluated_role": current_user.role,
            **result,
        }

    except HTTPException:

        raise

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except PermissionError as e:

        raise HTTPException(
            status_code=403,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Retrieval evaluation failed: "
                f"{str(e)}"
            ),
        )


# ============================================================
# GENERATION EVALUATION
# ============================================================


@router.post("/generation")
def run_generation_evaluation(
    request: GenerationEvaluationRequest,
    current_user: User = Depends(
        require_role("admin")
    ),
    db: Session = Depends(get_db),
):

    try:

        dataset = get_evaluation_dataset()

        if not dataset:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Evaluation dataset is empty."
                ),
            )

        result = evaluate_generation_dataset(
            dataset=dataset,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            top_k=request.top_k,
        )

        return {
            "evaluation_type": "generation",
            "evaluated_by": current_user.id,
            "evaluated_role": current_user.role,
            **result,
        }

    except HTTPException:

        raise

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except PermissionError as e:

        raise HTTPException(
            status_code=403,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Generation evaluation failed: "
                f"{str(e)}"
            ),
        )


# ============================================================
# AGENT EVALUATION HELPERS
# ============================================================


def normalize_tools(
    tools,
) -> list[str]:

    if not tools:
        return []

    if isinstance(
        tools,
        str,
    ):

        tools = [
            item.strip().lower()
            for item in tools.split(",")
            if item.strip()
        ]

    if not isinstance(
        tools,
        list,
    ):

        return []

    normalized = []

    for tool in tools:

        if not isinstance(
            tool,
            str,
        ):
            continue

        tool = tool.strip().lower()

        if tool and tool not in normalized:
            normalized.append(tool)

    return normalized


def calculate_route_accuracy(
    expected_route: str,
    actual_route: str,
) -> bool:

    if not expected_route:
        return False

    if not actual_route:
        return False

    return (
        expected_route.strip().lower()
        == actual_route.strip().lower()
    )


def calculate_tool_selection_accuracy(
    expected_tools,
    actual_tools,
) -> bool:

    expected = normalize_tools(
        expected_tools
    )

    actual = normalize_tools(
        actual_tools
    )

    return expected == actual


def calculate_tool_execution_accuracy(
    expected_tools,
    agent_result: dict,
) -> bool:

    expected = normalize_tools(
        expected_tools
    )

    if not expected:
        return False

    tool_results = agent_result.get(
        "tool_results",
        {},
    )

    if not isinstance(
        tool_results,
        dict,
    ):

        return False

    for tool in expected:

        if tool == "general":
            continue

        if tool not in tool_results:
            return False

        tool_result = tool_results.get(
            tool
        )

        if not isinstance(
            tool_result,
            dict,
        ):
            continue

        if tool_result.get(
            "error"
        ):

            return False

    return True


def calculate_final_answer_accuracy(
    expected_answer_contains,
    answer: str,
) -> bool:

    if not expected_answer_contains:
        return bool(answer)

    if not answer:
        return False

    answer_lower = answer.lower()

    for expected_value in (
        expected_answer_contains
    ):

        if str(
            expected_value
        ).lower() not in answer_lower:

            return False

    return True


# ============================================================
# AGENT EVALUATION
# ============================================================


@router.post("/agent")
def run_agent_evaluation(
    request: AgentEvaluationRequest,
    current_user: User = Depends(
        require_role("admin")
    ),
    db: Session = Depends(get_db),
):

    try:

        dataset = get_evaluation_dataset()

        if not dataset:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Evaluation dataset is empty."
                ),
            )

        total_questions = len(
            dataset
        )

        route_correct = 0
        tool_selection_correct = 0
        tool_execution_correct = 0
        final_answer_correct = 0

        evaluation_results = []

        for item in dataset:

            question = item.get(
                "question",
                "",
            )

            expected_route = item.get(
                "expected_route",
                "",
            )

            expected_tools = normalize_tools(
                item.get(
                    "expected_tools",
                    [],
                )
            )

            expected_answer_contains = item.get(
                "expected_answer_contains",
                [],
            )

            # ------------------------------------------------
            # Run actual EnterpriseIQ agent
            # ------------------------------------------------

            agent_result = run_agent(
                question=question,
                user_id=current_user.id,
                user_role=current_user.role,
                db=db,
            )

            actual_route = agent_result.get(
                "route"
            )

            actual_tools = normalize_tools(
                agent_result.get(
                    "tools",
                    [],
                )
            )

            actual_answer = agent_result.get(
                "answer",
                "",
            )

            # ------------------------------------------------
            # Metric 1: Route Accuracy
            # ------------------------------------------------

            route_is_correct = (
                calculate_route_accuracy(
                    expected_route=expected_route,
                    actual_route=actual_route,
                )
            )

            if route_is_correct:
                route_correct += 1

            # ------------------------------------------------
            # Metric 2: Tool Selection Accuracy
            # ------------------------------------------------

            tools_are_correct = (
                calculate_tool_selection_accuracy(
                    expected_tools=expected_tools,
                    actual_tools=actual_tools,
                )
            )

            if tools_are_correct:
                tool_selection_correct += 1

            # ------------------------------------------------
            # Metric 3: Tool Execution Accuracy
            # ------------------------------------------------

            execution_is_correct = (
                calculate_tool_execution_accuracy(
                    expected_tools=expected_tools,
                    agent_result=agent_result,
                )
            )

            if execution_is_correct:
                tool_execution_correct += 1

            # ------------------------------------------------
            # Metric 4: Final Answer Accuracy
            # ------------------------------------------------

            answer_is_correct = (
                calculate_final_answer_accuracy(
                    expected_answer_contains=(
                        expected_answer_contains
                    ),
                    answer=actual_answer,
                )
            )

            if answer_is_correct:
                final_answer_correct += 1

            # ------------------------------------------------
            # Store per-question result
            # ------------------------------------------------

            evaluation_results.append(
                {
                    "question": question,
                    "expected_route": expected_route,
                    "actual_route": actual_route,
                    "route_correct": route_is_correct,
                    "expected_tools": expected_tools,
                    "actual_tools": actual_tools,
                    "tool_selection_correct": (
                        tools_are_correct
                    ),
                    "tool_execution_correct": (
                        execution_is_correct
                    ),
                    "expected_answer_contains": (
                        expected_answer_contains
                    ),
                    "actual_answer": actual_answer,
                    "final_answer_correct": (
                        answer_is_correct
                    ),
                }
            )

        # ----------------------------------------------------
        # Calculate percentages
        # ----------------------------------------------------

        if total_questions == 0:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No evaluation questions found."
                ),
            )

        route_accuracy = (
            route_correct
            / total_questions
        )

        tool_selection_accuracy = (
            tool_selection_correct
            / total_questions
        )

        tool_execution_accuracy = (
            tool_execution_correct
            / total_questions
        )

        final_answer_accuracy = (
            final_answer_correct
            / total_questions
        )

        return {
            "evaluation_type": "agent",
            "evaluated_by": current_user.id,
            "evaluated_role": current_user.role,

            "total_questions": total_questions,

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

            "metrics": {
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
            },

            "details": evaluation_results,
        }

    except HTTPException:

        raise

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except PermissionError as e:

        raise HTTPException(
            status_code=403,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Agent evaluation failed: "
                f"{str(e)}"
            ),
        )