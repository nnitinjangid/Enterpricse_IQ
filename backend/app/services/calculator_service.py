import ast
import operator
import re
from typing import Any

from groq import Groq

from app.core.config import settings


client = Groq(
    api_key=settings.GROQ_API_KEY
)


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def extract_expression(
    text_response: str,
) -> str:

    if not text_response:
        return ""

    expression = text_response.strip()

    expression = re.sub(
        r"```(?:python|text|math)?\s*",
        "",
        expression,
        flags=re.IGNORECASE,
    )

    expression = re.sub(
        r"```\s*$",
        "",
        expression,
    )

    expression = expression.strip()

    return expression


def extract_numeric_values(
    value: Any,
) -> list[float]:

    values = []

    if value is None:
        return values

    if isinstance(value, bool):
        return values

    if isinstance(value, (int, float)):
        values.append(float(value))
        return values

    if isinstance(value, dict):

        for item in value.values():

            values.extend(
                extract_numeric_values(item)
            )

        return values

    if isinstance(value, (list, tuple)):

        for item in value:

            values.extend(
                extract_numeric_values(item)
            )

        return values

    try:

        if hasattr(value, "as_integer_ratio"):

            values.append(
                float(value)
            )

            return values

    except Exception:
        pass

    return values


def extract_previous_numeric_value(
    context: str,
) -> float | None:

    if not context:
        return None

    # -------------------------------------------------
    # Try common SQL result formats first.
    # -------------------------------------------------

    number_patterns = [
        r"['\"](?:SUM\(total_amount\)|total_sales|total_amount|revenue|total)['\"]?\s*:\s*([0-9]+(?:\.[0-9]+)?)",

        r"['\"]SUM\(total_amount\)['\"]?\s*:\s*([0-9]+(?:\.[0-9]+)?)",

        r"['\"]total_sales['\"]?\s*:\s*([0-9]+(?:\.[0-9]+)?)",

        r":\s*([0-9]+(?:\.[0-9]+)?)",
    ]

    for pattern in number_patterns:

        matches = re.findall(
            pattern,
            context,
            flags=re.IGNORECASE,
        )

        if matches:

            try:

                return float(
                    matches[0]
                )

            except ValueError:

                continue

    # -------------------------------------------------
    # Generic numeric extraction.
    # -------------------------------------------------

    generic_numbers = re.findall(
        r"(?<![A-Za-z0-9_])\d+(?:\.\d+)?(?![A-Za-z0-9_])",
        context,
    )

    if generic_numbers:

        numeric_values = []

        for value in generic_numbers:

            try:

                numeric_values.append(
                    float(value)
                )

            except ValueError:

                pass

        if numeric_values:

            # Prefer business-sized values.
            large_values = [
                value
                for value in numeric_values
                if abs(value) >= 1000
            ]

            if large_values:

                return large_values[0]

            return numeric_values[0]

    return None


def build_fallback_expression(
    question: str,
    context: str,
) -> str | None:

    if not question or not context:
        return None

    question_lower = question.lower()

    previous_value = (
        extract_previous_numeric_value(
            context
        )
    )

    if previous_value is None:
        return None

    # -------------------------------------------------
    # Detect percentage.
    #
    # Examples:
    #
    # 10% discount
    # 15% of that amount
    # 5.5% on those sales
    # -------------------------------------------------

    percentage_match = re.search(
        r"(\d+(?:\.\d+)?)\s*%",
        question_lower,
    )

    if not percentage_match:
        return None

    percentage = float(
        percentage_match.group(1)
    )

    # -------------------------------------------------
    # Detect discount language.
    # -------------------------------------------------

    has_discount = (
        "discount" in question_lower
    )

    # -------------------------------------------------
    # Detect references to a previous tool result.
    # -------------------------------------------------

    references_previous_value = any(
        phrase in question_lower
        for phrase in [
            "that amount",
            "that value",
            "that total",
            "that sales",
            "that sale",
            "those sales",
            "those amounts",
            "those values",
            "the amount",
            "the total",
            "the sales",
            "the sale",
            "the result",
        ]
    )

    # -------------------------------------------------
    # Case 1:
    #
    # "What would a 10% discount on those sales be?"
    #
    # We need the DISCOUNT VALUE.
    #
    # 540000 * 10 / 100
    # -------------------------------------------------

    if (
        has_discount
        and references_previous_value
    ):

        # If user explicitly asks for the amount
        # AFTER discount, calculate remaining amount.
        after_discount = any(
            phrase in question_lower
            for phrase in [
                "after discount",
                "after a discount",
                "after the discount",
                "remaining amount",
                "final amount",
                "amount after",
                "sales after",
            ]
        )

        if after_discount:

            expression = (
                f"{previous_value} - "
                f"({previous_value} * "
                f"{percentage} / 100)"
            )

            print(
                "[CALCULATOR] "
                "Detected dependent after-discount calculation."
            )

            return expression

        # Otherwise return discount amount.
        expression = (
            f"{previous_value} * "
            f"{percentage} / 100"
        )

        print(
            "[CALCULATOR] "
            "Detected dependent discount calculation."
        )

        return expression

    # -------------------------------------------------
    # Case 2:
    #
    # "What is 10% of that amount?"
    #
    # 540000 * 10 / 100
    # -------------------------------------------------

    if references_previous_value:

        expression = (
            f"{previous_value} * "
            f"{percentage} / 100"
        )

        print(
            "[CALCULATOR] "
            "Detected percentage of previous value."
        )

        return expression

    return None


def generate_expression(
    question: str,
    context: str = "",
) -> str:

    if not question or not question.strip():

        raise ValueError(
            "Question cannot be empty."
        )

    # -------------------------------------------------
    # FIRST:
    #
    # Resolve dependent calculations deterministically.
    #
    # This is important for:
    #
    # "that amount"
    # "those sales"
    # "the total"
    # etc.
    # -------------------------------------------------

    fallback_expression = (
        build_fallback_expression(
            question=question,
            context=context,
        )
    )

    if fallback_expression:

        print(
            "[CALCULATOR] "
            f"Using resolved expression: "
            f"{fallback_expression}"
        )

        return fallback_expression

    # -------------------------------------------------
    # Otherwise use Groq for normal calculations.
    # -------------------------------------------------

    system_prompt = """
You are the calculation expression generator
for EnterpriseIQ.

Your job is to convert the user's calculation
requirement into ONE mathematical expression
that Python can safely calculate.

STRICT RULES:

1. Return ONLY the mathematical expression.
2. Do not return explanations.
3. Do not return markdown.
4. Do not use variables.
5. Do not use functions.
6. Use only numbers and these operators:
   + - * / % **
7. Use parentheses when required.
8. If the question refers to a value from previous
   tool results, use that value directly.
9. Never leave references such as:
   "that amount"
   "that value"
   "that total"
   "those sales"
   unresolved.
10. NEVER return an empty response.

Examples:

Question:
What is 18% of 220000?

Return:
220000 * 18 / 100

Question:
Calculate 25% discount on 80000

Return:
80000 * 25 / 100

Question:
What is 80000 after 25% discount?

Return:
80000 - (80000 * 25 / 100)

Previous SQL result:
540000

Question:
What would a 10% discount on those sales be?

Return:
540000 * 10 / 100
"""

    user_prompt = f"""
Calculation requirement:

{question.strip()}
"""

    if context:

        user_prompt += f"""

Previous tool result:

{context}

Use the numeric value from the previous tool
result whenever the question refers to:
- that amount
- that value
- that total
- those sales
- the sales
- the amount
- the total
- the result

Return ONLY one mathematical expression.
"""

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0,
        max_tokens=300,
    )

    content = response.choices[0].message.content

    expression = extract_expression(
        content
    )

    if expression:

        return expression

    raise ValueError(
        "Calculator returned an empty expression."
    )


def safe_calculate(
    expression: str,
) -> float:

    if not expression:

        raise ValueError(
            "Expression cannot be empty."
        )

    expression = expression.strip()

    if len(expression) > 200:

        raise ValueError(
            "Expression is too long."
        )

    if not re.fullmatch(
        r"[0-9+\-*/%().\s]+",
        expression,
    ):

        raise ValueError(
            "Unsafe characters detected in expression."
        )

    try:

        tree = ast.parse(
            expression,
            mode="eval",
        )

    except SyntaxError:

        raise ValueError(
            "Invalid mathematical expression."
        )

    def evaluate(node):

        if isinstance(
            node,
            ast.Constant,
        ):

            if isinstance(
                node.value,
                bool,
            ):

                raise ValueError(
                    "Boolean values are not allowed."
                )

            if isinstance(
                node.value,
                (int, float),
            ):

                return node.value

            raise ValueError(
                "Only numeric values are allowed."
            )

        if isinstance(
            node,
            ast.BinOp,
        ):

            operator_type = type(
                node.op
            )

            if operator_type not in ALLOWED_OPERATORS:

                raise ValueError(
                    "Operator is not allowed."
                )

            left = evaluate(
                node.left
            )

            right = evaluate(
                node.right
            )

            if (
                operator_type
                in {
                    ast.Div,
                    ast.Mod,
                }
                and right == 0
            ):

                raise ValueError(
                    "Division by zero is not allowed."
                )

            if (
                operator_type == ast.Pow
                and abs(right) > 10
            ):

                raise ValueError(
                    "Exponent is too large."
                )

            return ALLOWED_OPERATORS[
                operator_type
            ](
                left,
                right,
            )

        if isinstance(
            node,
            ast.UnaryOp,
        ):

            if isinstance(
                node.op,
                ast.USub,
            ):

                return -evaluate(
                    node.operand
                )

            if isinstance(
                node.op,
                ast.UAdd,
            ):

                return evaluate(
                    node.operand
                )

            raise ValueError(
                "Unary operator is not allowed."
            )

        raise ValueError(
            "Invalid expression."
        )

    result = evaluate(
        tree.body
    )

    if isinstance(
        result,
        complex,
    ):

        raise ValueError(
            "Complex results are not supported."
        )

    return float(result)


def format_result(
    result: float,
) -> str:

    if result.is_integer():

        return f"{int(result):,}"

    return f"{result:,.4f}".rstrip(
        "0"
    ).rstrip(".")


def calculate(
    question: str,
    context: str = "",
) -> dict:

    expression = generate_expression(
        question=question,
        context=context,
    )

    result = safe_calculate(
        expression
    )

    formatted_result = format_result(
        result
    )

    return {
        "question": question.strip(),
        "expression": expression,
        "result": result,
        "formatted_result": formatted_result,
    }