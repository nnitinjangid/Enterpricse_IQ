import json
import re

from groq import Groq

from app.core.config import settings


# =========================================================
# Groq Client
# =========================================================

client = Groq(
    api_key=settings.GROQ_API_KEY
)


# =========================================================
# Allowed Routes
# =========================================================

ALLOWED_ROUTES = {
    "rag",
    "sql",
    "calculator",
    "general",
}


# =========================================================
# Extract JSON
# =========================================================

def extract_json(
    text: str,
) -> dict:

    if not text:
        raise ValueError(
            "Router returned an empty response."
        )

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(
        r"```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"```\s*$",
        "",
        text,
    )

    text = text.strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:

        # Try finding JSON object inside response
        match = re.search(
            r"\{.*\}",
            text,
            flags=re.DOTALL,
        )

        if not match:
            raise ValueError(
                "Router did not return valid JSON."
            )

        try:
            return json.loads(
                match.group(0)
            )

        except json.JSONDecodeError:
            raise ValueError(
                "Router returned malformed JSON."
            )


# =========================================================
# Classify Query
# =========================================================

def classify_query(
    question: str,
) -> dict:
    """
    Classify a user query into:

    - rag
    - sql
    - calculator
    - general
    """

    if not question or not question.strip():
        raise ValueError(
            "Question cannot be empty."
        )

    system_prompt = """
You are the query router for EnterpriseIQ.

Your job is ONLY to classify the user's query.

Choose exactly one route:

1. rag
   Use when the user is asking about information
   contained in enterprise documents, policies,
   invoices, contracts, reports, manuals,
   uploaded files, or knowledge-base content.

2. sql
   Use when the user is asking about structured
   business data such as sales, orders, customers,
   transactions, revenue, counts, totals, dates,
   records, or database information.

3. calculator
   Use when the main task is mathematical
   calculation, arithmetic, percentages,
   totals, conversions, or numerical computation.

4. general
   Use for general conversation or questions
   that do not require enterprise documents,
   database data, or calculation.

IMPORTANT:

- Return ONLY valid JSON.
- Do not use markdown.
- Do not explain your decision.

Required JSON format:

{
    "route": "rag",
    "confidence": 0.95
}

Confidence must be a number between 0 and 1.
"""

    user_prompt = f"""
Classify this user query:

{question.strip()}
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
        max_tokens=200,
    )

    content = response.choices[0].message.content

    data = extract_json(
        content
    )

    route = data.get(
        "route"
    )

    confidence = data.get(
        "confidence"
    )

    if route not in ALLOWED_ROUTES:
        raise ValueError(
            f"Invalid route returned by router: {route}"
        )

    try:
        confidence = float(
            confidence
        )
    except (
        TypeError,
        ValueError,
    ):
        raise ValueError(
            "Router confidence must be a number."
        )

    confidence = max(
        0.0,
        min(
            confidence,
            1.0,
        ),
    )

    return {
        "route": route,
        "confidence": confidence,
    }