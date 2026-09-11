import re


def route_accuracy(
    actual_route: str,
    expected_route: str,
) -> float:
    """
    Check whether the agent selected
    the expected primary route.
    """

    if not actual_route:
        return 0.0

    if not expected_route:
        return 0.0

    return 1.0 if actual_route == expected_route else 0.0


def tool_selection_accuracy(
    actual_tools: list[str],
    expected_tools: list[str],
) -> float:
    """
    Measure tool selection accuracy.

    Exact match:
        1.0

    Partial match:
        fraction of expected tools selected.

    Extra unexpected tools reduce the score.
    """

    if not expected_tools:
        return 0.0

    actual_set = set(actual_tools)
    expected_set = set(expected_tools)

    if actual_set == expected_set:
        return 1.0

    if not actual_set:
        return 0.0

    correct_tools = (
        actual_set & expected_set
    )

    matched_count = len(
        correct_tools
    )

    extra_tools = (
        actual_set - expected_set
    )

    expected_count = len(
        expected_set
    )

    if extra_tools:

        total_expected_and_extra = (
            expected_count
            + len(extra_tools)
        )

        return round(
            matched_count
            / total_expected_and_extra,
            4,
        )

    return round(
        matched_count
        / expected_count,
        4,
    )


def tool_execution_accuracy(
    tool_results: dict,
    expected_tools: list[str],
) -> float:
    """
    Check whether all expected tools
    were actually executed successfully.
    """

    if not expected_tools:
        return 0.0

    if not tool_results:
        return 0.0

    executed_tools = set(
        tool_results.keys()
    )

    expected_set = set(
        expected_tools
    )

    successfully_executed = 0

    for tool in expected_set:

        if tool not in executed_tools:
            continue

        result = tool_results.get(
            tool
        )

        if result is None:
            continue

        if isinstance(
            result,
            dict,
        ):

            if result.get("error"):
                continue

        successfully_executed += 1

    return round(
        successfully_executed
        / len(expected_set),
        4,
    )


def extract_numbers(
    text: str,
) -> list[float]:
    """
    Extract numeric values from text.

    Examples:

        890000
        890,000
        890000.0
        890,000.0

    are all converted to:

        890000.0
    """

    if not text:
        return []

    normalized = (
        text
        .replace("\u202f", " ")
        .replace("\xa0", " ")
    )

    matches = re.findall(
        r"(?<![A-Za-z])"
        r"\d[\d,]*(?:\.\d+)?"
        r"(?![A-Za-z])",
        normalized,
    )

    numbers = []

    for value in matches:

        value = value.replace(
            ",",
            "",
        )

        try:

            number = float(value)

            numbers.append(
                number
            )

        except ValueError:
            continue

    return numbers


def extract_percentages(
    text: str,
) -> list[float]:
    """
    Extract percentage values.

    Examples:

        25%
        25 %
        25.0%

    are converted to:

        25.0
    """

    if not text:
        return []

    normalized = (
        text
        .replace("\u202f", " ")
        .replace("\xa0", " ")
    )

    matches = re.findall(
        r"(\d+(?:,\d{3})*(?:\.\d+)?)"
        r"\s*%",
        normalized,
    )

    percentages = []

    for value in matches:

        value = value.replace(
            ",",
            "",
        )

        try:

            percentages.append(
                float(value)
            )

        except ValueError:
            continue

    return percentages


def is_numeric_value(
    value: str,
) -> bool:
    """
    Determine whether a value is numeric.

    Supports:

        890000
        890,000
        890000.0
        ₹890000
        $890,000
    """

    if not value:
        return False

    cleaned = (
        str(value)
        .strip()
        .replace(
            ",",
            "",
        )
        .replace(
            "₹",
            "",
        )
        .replace(
            "$",
            "",
        )
        .replace(
            "€",
            "",
        )
        .replace(
            "£",
            "",
        )
        .strip()
    )

    try:

        float(cleaned)

        return True

    except ValueError:

        return False


def answer_contains_expected_value(
    answer: str,
    expected_value: str,
) -> bool:
    """
    Check whether an expected value exists
    in the actual answer.

    Numeric formatting differences are ignored.

    Examples:

        expected: 890000
        answer:   890,000.0

        -> True


        expected: 3000
        answer:   3,000

        -> True


        expected: 25%
        answer:   25 %

        -> True
    """

    if not answer:
        return False

    if not expected_value:
        return False

    expected_value = str(
        expected_value
    ).strip()

    # -------------------------------------------------
    # Percentage comparison
    # -------------------------------------------------

    if "%" in expected_value:

        expected_percentages = (
            extract_percentages(
                expected_value
            )
        )

        answer_percentages = (
            extract_percentages(
                answer
            )
        )

        for expected_number in (
            expected_percentages
        ):

            for answer_number in (
                answer_percentages
            ):

                if (
                    expected_number
                    == answer_number
                ):
                    return True

        return False

    # -------------------------------------------------
    # Numeric comparison
    # -------------------------------------------------

    if is_numeric_value(
        expected_value
    ):

        expected_cleaned = (
            expected_value
            .replace(
                ",",
                "",
            )
            .replace(
                "₹",
                "",
            )
            .replace(
                "$",
                "",
            )
            .replace(
                "€",
                "",
            )
            .replace(
                "£",
                "",
            )
            .strip()
        )

        try:

            expected_number = float(
                expected_cleaned
            )

        except ValueError:

            return False

        answer_numbers = extract_numbers(
            answer
        )

        for answer_number in (
            answer_numbers
        ):

            if (
                expected_number
                == answer_number
            ):
                return True

        return False

    # -------------------------------------------------
    # Text comparison
    # -------------------------------------------------

    normalized_answer = (
        answer
        .lower()
        .replace("\u202f", " ")
        .replace("\xa0", " ")
    )

    normalized_expected = (
        expected_value
        .lower()
        .replace("\u202f", " ")
        .replace("\xa0", " ")
    )

    return (
        normalized_expected
        in normalized_answer
    )


def final_answer_accuracy(
    answer: str,
    expected_answer_contains: list[str],
) -> float:
    """
    Measure final answer accuracy.

    Every expected value must be present.
    """

    if not answer:
        return 0.0

    if not expected_answer_contains:
        return 0.0

    valid_expected_values = [
        str(value).strip()
        for value in expected_answer_contains
        if value is not None
        and str(value).strip()
    ]

    if not valid_expected_values:
        return 0.0

    matched = 0

    for expected_value in (
        valid_expected_values
    ):

        if answer_contains_expected_value(
            answer=answer,
            expected_value=expected_value,
        ):

            matched += 1

    return round(
        matched
        / len(valid_expected_values),
        4,
    )


def evaluate_agent(
    actual_route: str,
    expected_route: str,
    actual_tools: list[str],
    expected_tools: list[str],
    tool_results: dict,
    answer: str,
    expected_answer_contains: list[str],
) -> dict:
    """
    Evaluate one complete agent execution.
    """

    route_score = route_accuracy(
        actual_route=actual_route,
        expected_route=expected_route,
    )

    tool_selection_score = (
        tool_selection_accuracy(
            actual_tools=actual_tools,
            expected_tools=expected_tools,
        )
    )

    tool_execution_score = (
        tool_execution_accuracy(
            tool_results=tool_results,
            expected_tools=expected_tools,
        )
    )

    final_answer_score = (
        final_answer_accuracy(
            answer=answer,
            expected_answer_contains=(
                expected_answer_contains
            ),
        )
    )

    return {
        "route_accuracy": route_score,
        "tool_selection_accuracy": (
            tool_selection_score
        ),
        "tool_execution_accuracy": (
            tool_execution_score
        ),
        "final_answer_accuracy": (
            final_answer_score
        ),
    }


def average_agent_metrics(
    results: list[dict],
) -> dict:
    """
    Calculate average Agent Evaluation
    metrics across all evaluation questions.
    """

    if not results:

        return {
            "route_accuracy": 0.0,
            "tool_selection_accuracy": 0.0,
            "tool_execution_accuracy": 0.0,
            "final_answer_accuracy": 0.0,
        }

    count = len(results)

    total_route = 0.0
    total_tool_selection = 0.0
    total_tool_execution = 0.0
    total_final_answer = 0.0

    for result in results:

        total_route += result[
            "route_accuracy"
        ]

        total_tool_selection += result[
            "tool_selection_accuracy"
        ]

        total_tool_execution += result[
            "tool_execution_accuracy"
        ]

        total_final_answer += result[
            "final_answer_accuracy"
        ]

    return {
        "route_accuracy": round(
            total_route / count,
            4,
        ),
        "tool_selection_accuracy": round(
            total_tool_selection / count,
            4,
        ),
        "tool_execution_accuracy": round(
            total_tool_execution / count,
            4,
        ),
        "final_answer_accuracy": round(
            total_final_answer / count,
            4,
        ),
    }