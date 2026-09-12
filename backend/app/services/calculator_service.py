
import ast
import operator
import re
from typing import Any

from groq import Groq

from app.core.config import settings


client = Groq(
    api_key=settings.GROQ_API_KEY
)


# ============================================================
# ALLOWED OPERATORS
# ============================================================

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


# ============================================================
# EXPRESSION EXTRACTION
# ============================================================

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


# ============================================================
# NUMERIC VALUE EXTRACTION
# ============================================================

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

        if hasattr(
            value,
            "as_integer_ratio",
        ):

            values.append(
                float(value)
            )

            return values

    except Exception:
        pass

    return values


# ============================================================
# PREVIOUS TOOL RESULT
# ============================================================

def extract_previous_numeric_value(
    context: str,
) -> float | None:

    if not context:
        return None

    # --------------------------------------------------------
    # Common SQL result formats
    # --------------------------------------------------------

    number_patterns = [

        r"""['"]?(?:SUM\(total_amount\)|total_sales|total_amount|revenue|total)['"]?\s*:\s*([0-9]+(?:\.[0-9]+)?)""",

        r"""['"]?SUM\(total_amount\)['"]?\s*:\s*([0-9]+(?:\.[0-9]+)?)""",

        r"""['"]?total_sales['"]?\s*:\s*([0-9]+(?:\.[0-9]+)?)""",

        r""":\s*([0-9]+(?:\.[0-9]+)?)""",
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

    # --------------------------------------------------------
    # Generic numeric extraction
    # --------------------------------------------------------

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

            large_values = [
                value
                for value in numeric_values
                if abs(value) >= 1000
            ]

            if large_values:
                return large_values[0]

            return numeric_values[0]

    return None


# ============================================================
# DIRECT PERCENTAGE CALCULATION
# ============================================================

def build_direct_percentage_expression(
    question: str,
) -> str | None:

    if not question:
        return None

    question_lower = question.lower().strip()

    # --------------------------------------------------------
    # Pattern:
    #
    # 15% of 20000
    # 10 percent of 50000
    # what is 25% of 80000
    # --------------------------------------------------------

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:%|percent)\s*(?:of)\s*"
        r"([0-9]+(?:\.[0-9]+)?)",
        question_lower,
    )

    if match:

        percentage = float(
            match.group(1)
        )

        amount = float(
            match.group(2)
        )

        expression = (
            f"{amount} * {percentage} / 100"
        )

        print(
            "[CALCULATOR] "
            f"Detected direct percentage calculation: "
            f"{expression}"
        )

        return expression

    # --------------------------------------------------------
    # Pattern:
    #
    # 80000 after 25% discount
    # 20000 after 10 percent discount
    # --------------------------------------------------------

    after_discount_match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)\s+"
        r"(?:after|minus)\s+"
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:%|percent)\s*discount",
        question_lower,
    )

    if after_discount_match:

        amount = float(
            after_discount_match.group(1)
        )

        percentage = float(
            after_discount_match.group(2)
        )

        expression = (
            f"{amount} - "
            f"({amount} * {percentage} / 100)"
        )

        print(
            "[CALCULATOR] "
            f"Detected after-discount calculation: "
            f"{expression}"
        )

        return expression

    # --------------------------------------------------------
    # Pattern:
    #
    # 25% discount on 80000
    # discount of 10% on 50000
    # --------------------------------------------------------

    discount_match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:%|percent)\s*"
        r"(?:discount)?\s*"
        r"(?:on|of)\s*"
        r"([0-9]+(?:\.[0-9]+)?)",
        question_lower,
    )

    if discount_match:

        percentage = float(
            discount_match.group(1)
        )

        amount = float(
            discount_match.group(2)
        )

        expression = (
            f"{amount} * {percentage} / 100"
        )

        print(
            "[CALCULATOR] "
            f"Detected direct discount calculation: "
            f"{expression}"
        )

        return expression

    return None


# ============================================================
# DEPENDENT CALCULATIONS
# ============================================================

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

    # --------------------------------------------------------
    # Percentage detection
    # --------------------------------------------------------

    percentage_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:%|percent)",
        question_lower,
    )

    if not percentage_match:
        return None

    percentage = float(
        percentage_match.group(1)
    )

    # --------------------------------------------------------
    # Discount language
    # --------------------------------------------------------

    has_discount = (
        "discount" in question_lower
    )

    # --------------------------------------------------------
    # Previous-value references
    # --------------------------------------------------------

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

    if not references_previous_value:
        return None

    # --------------------------------------------------------
    # After-discount calculation
    # --------------------------------------------------------

    if has_discount:

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

        # ----------------------------------------------------
        # Discount amount
        # ----------------------------------------------------

        expression = (
            f"{previous_value} * "
            f"{percentage} / 100"
        )

        print(
            "[CALCULATOR] "
            "Detected dependent discount calculation."
        )

        return expression

    # --------------------------------------------------------
    # Percentage of previous value
    # --------------------------------------------------------

    expression = (
        f"{previous_value} * "
        f"{percentage} / 100"
    )

    print(
        "[CALCULATOR] "
        "Detected percentage of previous value."
    )

    return expression


# ============================================================
# NORMAL ARITHMETIC EXPRESSION
# ============================================================

def build_direct_arithmetic_expression(
    question: str,
) -> str | None:

    if not question:
        return None

    question_lower = question.lower()

    # --------------------------------------------------------
    # Find expressions such as:
    #
    # 20000 + 5000
    # 50000 - 10000
    # 100 * 20
    # 10000 / 5
    # --------------------------------------------------------

    match = re.search(
        r"(?<![A-Za-z0-9_])"
        r"(\d+(?:\.\d+)?\s*"
        r"[\+\-\*/]\s*"
        r"\d+(?:\.\d+)?)"
        r"(?![A-Za-z0-9_])",
        question_lower,
    )

    if not match:
        return None

    expression = match.group(1)

    print(
        "[CALCULATOR] "
        f"Detected direct arithmetic expression: "
        f"{expression}"
    )

    return expression


# ============================================================
# EXPRESSION GENERATION
# ============================================================

def generate_expression(
    question: str,
    context: str = "",
) -> str:

    if not question or not question.strip():

        raise ValueError(
            "Question cannot be empty."
        )

    # --------------------------------------------------------
    # STEP 1
    # Direct percentage calculation
    #
    # Example:
    # 15% of 20000
    #
    # MUST NOT require LLM.
    # --------------------------------------------------------

    direct_percentage = (
        build_direct_percentage_expression(
            question
        )
    )

    if direct_percentage:

        return direct_percentage

    # --------------------------------------------------------
    # STEP 2
    # Dependent calculation
    #
    # Example:
    # 10% of those sales
    # 25% discount on that total
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # STEP 3
    # Direct arithmetic
    # --------------------------------------------------------

    direct_arithmetic = (
        build_direct_arithmetic_expression(
            question
        )
    )

    if direct_arithmetic:

        return direct_arithmetic

    # --------------------------------------------------------
    # STEP 4
    # Use Groq for complex calculation language
    # --------------------------------------------------------

    system_prompt = """

You are the calculation expression generator
for EnterpriseIQ.

Convert the user's calculation requirement
into ONE mathematical expression.

STRICT RULES:

1. Return ONLY the mathematical expression.
2. Do not return explanations.
3. Do not return markdown.
4. Do not use variables.
5. Do not use functions.
6. Use only numbers and these operators:

   + - * / % **

7. Use parentheses when required.
8. Resolve references using the previous tool result.
9. Never return words.
10. Never return an empty response.

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

Use the numeric value from the previous
tool result whenever the question refers to:

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

    content = (
        response.choices[0].message.content
    )

    expression = extract_expression(
        content
    )

    if expression:
        return expression

    raise ValueError(
        "Calculator returned an empty expression."
    )


# ============================================================
# SAFE CALCULATOR
# ============================================================

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

    # Only allow mathematical characters.
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

        # ----------------------------------------------------
        # Numbers
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Binary operations
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Unary operations
        # ----------------------------------------------------

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


# ============================================================
# RESULT FORMATTING
# ============================================================

def format_result(
    result: float,
) -> str:

    if result.is_integer():

        return f"{int(result):,}"

    return (
        f"{result:,.4f}"
        .rstrip("0")
        .rstrip(".")
    )


# ============================================================
# MAIN CALCULATOR
# ============================================================

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

    print(
        "[CALCULATOR] "
        f"{expression} = {formatted_result}"
    )

    return {
        "question": question.strip(),
        "expression": expression,
        "result": result,
        "formatted_result": formatted_result,
    }

