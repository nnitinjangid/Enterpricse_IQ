import ast
import operator
import re

from groq import Groq

from app.core.config import settings


client = Groq(
    api_key=settings.GROQ_API_KEY
)


# =========================================================
# Allowed Operators
# =========================================================

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


# =========================================================
# Expression Extraction
# =========================================================

def extract_expression(
    text_response: str,
) -> str:

    if not text_response:
        raise ValueError(
            "Calculator returned an empty expression."
        )

    expression = text_response.strip()

    expression = re.sub(
        r"```python\s*",
        "",
        expression,
        flags=re.IGNORECASE,
    )

    expression = re.sub(
        r"```text\s*",
        "",
        expression,
        flags=re.IGNORECASE,
    )

    expression = re.sub(
        r"```\s*$",
        "",
        expression,
        flags=re.IGNORECASE,
    )

    expression = expression.strip()

    return expression


# =========================================================
# Generate Mathematical Expression
# =========================================================

def generate_expression(
    question: str,
) -> str:

    if not question or not question.strip():
        raise ValueError(
            "Question cannot be empty."
        )

    system_prompt = """
You are the calculation expression generator
for EnterpriseIQ.

Convert the user's mathematical question into
ONE mathematical expression that Python can calculate.

STRICT RULES:

1. Return ONLY the mathematical expression.
2. Do not return explanations.
3. Do not return markdown.
4. Do not use variables.
5. Do not use functions.
6. Use only numbers and these operators:
   + - * / % **
7. Use parentheses when required.
8. For percentage calculations, convert the
   percentage into normal arithmetic.

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

Question:
Calculate 10 + 20 * 5

Return:
10 + 20 * 5
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
                "content": question.strip(),
            },
        ],
        temperature=0,
        max_tokens=100,
    )

    expression = extract_expression(
        response.choices[0].message.content
    )

    return expression


# =========================================================
# Safe Mathematical Evaluator
# =========================================================

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

    # Only mathematical characters
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

        # Number
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

        # Binary operation
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

            # Prevent division by zero
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

            # Prevent huge powers
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

        # Unary + / -
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


# =========================================================
# Format Result
# =========================================================

def format_result(
    result: float,
) -> str:

    if result.is_integer():

        return f"{int(result):,}"

    return f"{result:,.4f}".rstrip(
        "0"
    ).rstrip(".")


# =========================================================
# Calculator Tool
# =========================================================

def calculate(
    question: str,
) -> dict:

    expression = generate_expression(
        question
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