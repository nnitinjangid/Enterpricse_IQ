from app.agent.graph import run_agent

from app.evaluation.agent_metrics import (
    average_agent_metrics,
    evaluate_agent,
)


def normalize_tools(
    tools: list,
) -> list[str]:
    """
    Normalize tool names returned by the agent.

    Example:

        ["sql", "rag"]

    remains:

        ["sql", "rag"]
    """

    if not tools:
        return []

    normalized = []

    for tool in tools:

        if isinstance(
            tool,
            str,
        ):

            tool_name = tool.strip()

            if tool_name:
                normalized.append(
                    tool_name
                )

        elif isinstance(
            tool,
            dict,
        ):

            tool_name = tool.get(
                "tool"
            )

            if not tool_name:
                tool_name = tool.get(
                    "name"
                )

            if isinstance(
                tool_name,
                str,
            ):

                tool_name = tool_name.strip()

                if tool_name:
                    normalized.append(
                        tool_name
                    )

    return normalized


def evaluate_single_agent_case(
    case: dict,
    db,
    user_id: int,
    user_role: str,
) -> dict:
    """
    Run one Agent Evaluation test case.
    """

    question = case.get(
        "question"
    )

    expected_route = case.get(
        "expected_route",
        "",
    )

    expected_tools = case.get(
        "expected_tools",
        [],
    )

    expected_answer_contains = case.get(
        "expected_answer_contains",
        [],
    )

    if not question:
        raise ValueError(
            "Evaluation question cannot be empty."
        )

    if not expected_route:
        raise ValueError(
            "expected_route is required."
        )

    if not expected_tools:
        raise ValueError(
            "expected_tools is required."
        )

    agent_result = run_agent(
        question=question,
        user_id=user_id,
        user_role=user_role,
        db=db,
    )

    actual_route = agent_result.get(
        "route",
        "",
    )

    actual_tools = normalize_tools(
        agent_result.get(
            "tools",
            [],
        )
    )

    tool_results = agent_result.get(
        "tool_results",
        {},
    )

    answer = agent_result.get(
        "answer",
        "",
    )

    metrics = evaluate_agent(
        actual_route=actual_route,
        expected_route=expected_route,
        actual_tools=actual_tools,
        expected_tools=expected_tools,
        tool_results=tool_results,
        answer=answer,
        expected_answer_contains=(
            expected_answer_contains
        ),
    )

    return {
        "question": question,
        "expected_route": expected_route,
        "actual_route": actual_route,
        "expected_tools": expected_tools,
        "actual_tools": actual_tools,
        "expected_answer_contains": (
            expected_answer_contains
        ),
        "answer": answer,
        "tool_results": tool_results,
        "metrics": metrics,
    }


def evaluate_agent_dataset(
    dataset: list[dict],
    db,
    user_id: int,
    user_role: str,
) -> dict:
    """
    Evaluate the Agent against the complete
    evaluation dataset.
    """

    if not dataset:
        raise ValueError(
            "Agent evaluation dataset cannot be empty."
        )

    question_results = []

    for index, case in enumerate(
        dataset,
        start=1,
    ):

        print()
        print(
            "-" * 70
        )

        print(
            f"Agent Evaluation "
            f"{index}/{len(dataset)}"
        )

        print(
            f"Question: "
            f"{case.get('question', '')}"
        )

        result = evaluate_single_agent_case(
            case=case,
            db=db,
            user_id=user_id,
            user_role=user_role,
        )

        question_results.append(
            result
        )

    metric_results = [
        result["metrics"]
        for result in question_results
    ]

    average_metrics = average_agent_metrics(
        results=metric_results
    )

    return {
        "total_questions": len(
            question_results
        ),
        "average_metrics": average_metrics,
        "questions": question_results,
    }