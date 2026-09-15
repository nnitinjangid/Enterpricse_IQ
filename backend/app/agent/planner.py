import json
import re

from groq import Groq

from app.core.config import settings


client = Groq(
    api_key=settings.GROQ_API_KEY
)


ALLOWED_TOOLS = {
    "rag",
    "sql",
    "calculator",
    "general",
}


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json(
    text: str,
) -> dict:

    if not text:
        raise ValueError(
            "Planner returned an empty response."
        )

    text = text.strip()

    # Remove markdown code fences.
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.strip()

    # First try direct JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find JSON object inside response.
    start = text.find("{")
    end = text.rfind("}")

    if (
        start == -1
        or end == -1
        or end <= start
    ):
        raise ValueError(
            "Planner did not return valid JSON."
        )

    json_text = text[
        start:end + 1
    ]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        raise ValueError(
            "Planner returned malformed JSON."
        )


# =========================================================
# PLAN VALIDATION
# =========================================================

def validate_plan(
    plan: list,
) -> list[dict]:

    if not isinstance(
        plan,
        list,
    ):
        raise ValueError(
            "Planner plan must be a list."
        )

    if not plan:
        raise ValueError(
            "Planner returned an empty plan."
        )

    validated_plan = []
    step_numbers = set()

    for step in plan:

        if not isinstance(
            step,
            dict,
        ):
            raise ValueError(
                "Each plan step must be an object."
            )

        step_number = step.get(
            "step"
        )

        tool = step.get(
            "tool"
        )

        depends_on = step.get(
            "depends_on",
            [],
        )

        reason = step.get(
            "reason",
            "",
        )

        if not isinstance(
            step_number,
            int,
        ):
            raise ValueError(
                "Plan step number must be an integer."
            )

        if step_number in step_numbers:
            raise ValueError(
                "Duplicate plan step number."
            )

        step_numbers.add(
            step_number
        )

        if tool not in ALLOWED_TOOLS:
            raise ValueError(
                f"Invalid tool selected: {tool}"
            )

        if not isinstance(
            depends_on,
            list,
        ):
            raise ValueError(
                "depends_on must be a list."
            )

        for dependency in depends_on:

            if dependency not in ALLOWED_TOOLS:
                raise ValueError(
                    f"Invalid dependency: {dependency}"
                )

            if dependency == tool:
                raise ValueError(
                    f"Tool cannot depend on itself: {tool}"
                )

        validated_plan.append(
            {
                "step": step_number,
                "tool": tool,
                "depends_on": depends_on,
                "reason": str(reason),
            }
        )

    # -----------------------------------------------------
    # Sequential numbering
    # -----------------------------------------------------

    expected_steps = set(
        range(
            1,
            len(validated_plan) + 1,
        )
    )

    if step_numbers != expected_steps:
        raise ValueError(
            "Plan steps must be sequential starting from 1."
        )

    # -----------------------------------------------------
    # Sort
    # -----------------------------------------------------

    validated_plan.sort(
        key=lambda item: item["step"]
    )

    # -----------------------------------------------------
    # Dependency validation
    # -----------------------------------------------------

    completed_tools = set()

    for step in validated_plan:

        for dependency in step[
            "depends_on"
        ]:

            if dependency not in completed_tools:
                raise ValueError(
                    f"Dependency '{dependency}' "
                    f"must execute before "
                    f"'{step['tool']}'."
                )

        completed_tools.add(
            step["tool"]
        )

    # -----------------------------------------------------
    # General cannot be combined
    # -----------------------------------------------------

    tools = [
        step["tool"]
        for step in validated_plan
    ]

    if (
        "general" in tools
        and len(tools) > 1
    ):
        raise ValueError(
            "General tool cannot be combined with other tools."
        )

    return validated_plan


# =========================================================
# INTENT HELPERS
# =========================================================

def contains_any(
    question_lower: str,
    phrases: list[str],
) -> bool:

    return any(
        phrase in question_lower
        for phrase in phrases
    )


def has_sql_intent(
    question_lower: str,
) -> bool:

    return contains_any(
        question_lower,
        [
            "sales",
            "sale",
            "revenue",
            "orders",
            "order",
            "customer",
            "customers",
            "transaction",
            "transactions",
            "database",
            "stored in the database",
            "records",
        ],
    )


def has_rag_intent(
    question_lower: str,
) -> bool:

    return contains_any(
        question_lower,
        [
            "policy",
            "policies",
            "discount policy",
            "maximum discount",
            "maximum standard discount",
            "standard discount",
            "allowed discount",
            "payment due date",
            "due date",
            "contract",
            "invoice",
            "manual",
            "document",
            "documents",
            "uploaded file",
            "knowledge base",
            "services does",
            "services do",
            "provide",
            "provides",
        ],
    )


def has_calculator_intent(
    question_lower: str,
) -> bool:

    # Explicit mathematical calculations.
    if contains_any(
        question_lower,
        [
            "calculate",
            "percentage",
            "percent",
            "discount on",
            "gst on",
            "tax on",
            "what is 10%",
            "what is 15%",
            "what is 18%",
        ],
    ):
        return True

    # Mathematical operators.
    if re.search(
        r"\d+\s*[\+\-\*/]\s*\d+",
        question_lower,
    ):
        return True

    # Number followed by %.
    if re.search(
        r"\b\d+(?:\.\d+)?\s*%",
        question_lower,
    ):
        return True

    return False


def has_explicit_numeric_calculation(
    question_lower: str,
) -> bool:

    return (
        bool(
            re.search(
                r"\b\d+(?:\.\d+)?\s*%",
                question_lower,
            )
        )
        or bool(
            re.search(
                r"\d+\s*[\+\-\*/]\s*\d+",
                question_lower,
            )
        )
    )


# =========================================================
# DETERMINISTIC PLAN HELPERS
# =========================================================

def rag_only_plan(
    reason: str,
) -> dict:

    return {
        "plan": [
            {
                "step": 1,
                "tool": "rag",
                "depends_on": [],
                "reason": reason,
            }
        ],
        "tools": [
            "rag"
        ],
        "reason": (
            "Only RAG is required because "
            "the requested information comes "
            "from enterprise documents."
        ),
    }


def sql_only_plan(
    reason: str,
) -> dict:

    return {
        "plan": [
            {
                "step": 1,
                "tool": "sql",
                "depends_on": [],
                "reason": reason,
            }
        ],
        "tools": [
            "sql"
        ],
        "reason": (
            "Only SQL is required."
        ),
    }


# =========================================================
# DETERMINISTIC PLANNER
# =========================================================

def create_deterministic_plan(
    question: str,
) -> dict | None:

    if not question or not question.strip():
        return None

    question_lower = (
        question.lower().strip()
    )

    # -----------------------------------------------------
    # STRONG RAG-ONLY RULES
    #
    # IMPORTANT:
    # These rules execute BEFORE generic SQL detection.
    #
    # Therefore words such as:
    #
    # customer
    # customers
    #
    # cannot incorrectly force SQL.
    # -----------------------------------------------------

    rag_only_phrases = [

        # Discount / policy
        "maximum standard discount",
        "maximum discount allowed",
        "maximum discount",
        "standard discount allowed",
        "allowed discount",
        "discount policy",
        "standard discount",
        "what discount is allowed",

        # Payment / document
        "payment due date",
        "due date",

        # Company / services
        "what services does",
        "what services do",
        "services does",
        "services do",
        "provide",
        "provides",
    ]

    if contains_any(
        question_lower,
        rag_only_phrases,
    ):

        print(
            "[PLANNER] Strong RAG-only rule matched."
        )

        print(
            f"[PLANNER] Question: {question}"
        )

        print(
            "[PLANNER] SQL explicitly disabled "
            "for this document/policy question."
        )

        return rag_only_plan(
            reason=(
                "The question asks for "
                "enterprise document, policy, "
                "payment, or company information."
            )
        )

    # -----------------------------------------------------
    # GENERAL CONVERSATION
    # -----------------------------------------------------

    general_phrases = [
        "hello",
        "hi",
        "hey",
        "how are you",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
    ]

    if (
        contains_any(
            question_lower,
            general_phrases,
        )
        and not has_sql_intent(
            question_lower
        )
        and not has_rag_intent(
            question_lower
        )
        and not has_calculator_intent(
            question_lower
        )
    ):

        return {
            "plan": [
                {
                    "step": 1,
                    "tool": "general",
                    "depends_on": [],
                    "reason": (
                        "This is general conversation."
                    ),
                }
            ],
            "tools": [
                "general"
            ],
            "reason": (
                "No enterprise tool is required."
            ),
        }

    # -----------------------------------------------------
    # INTENT DETECTION
    # -----------------------------------------------------

    sql_required = has_sql_intent(
        question_lower
    )

    rag_required = has_rag_intent(
        question_lower
    )

    calculator_required = has_calculator_intent(
        question_lower
    )

    # -----------------------------------------------------
    # DISCOUNT POLICY SAFETY
    #
    # Any policy-style discount question belongs to RAG.
    #
    # Examples:
    #
    # maximum discount
    # standard discount
    # allowed discount
    # discount policy
    #
    # Even if "customer" or "sales" appears,
    # RAG remains the correct tool for the policy part.
    # -----------------------------------------------------

    if (
        "discount" in question_lower
        and (
            "maximum" in question_lower
            or "standard" in question_lower
            or "allowed" in question_lower
            or "policy" in question_lower
        )
    ):

        rag_required = True

        sql_required = False

    # -----------------------------------------------------
    # PURE CALCULATOR
    # -----------------------------------------------------

    if (
        calculator_required
        and not sql_required
        and not rag_required
    ):

        return {
            "plan": [
                {
                    "step": 1,
                    "tool": "calculator",
                    "depends_on": [],
                    "reason": (
                        "The question requires "
                        "a mathematical calculation."
                    ),
                }
            ],
            "tools": [
                "calculator"
            ],
            "reason": (
                "Only Calculator is required."
            ),
        }

    # -----------------------------------------------------
    # RAG ONLY
    # -----------------------------------------------------

    if (
        rag_required
        and not sql_required
    ):

        if calculator_required:

            return {
                "plan": [
                    {
                        "step": 1,
                        "tool": "rag",
                        "depends_on": [],
                        "reason": (
                            "RAG retrieves the required "
                            "policy or document information."
                        ),
                    },
                    {
                        "step": 2,
                        "tool": "calculator",
                        "depends_on": [
                            "rag"
                        ],
                        "reason": (
                            "Calculator uses the value "
                            "returned by RAG."
                        ),
                    },
                ],
                "tools": [
                    "rag",
                    "calculator",
                ],
                "reason": (
                    "RAG retrieves the policy value "
                    "and Calculator performs the calculation."
                ),
            }

        return rag_only_plan(
            reason=(
                "The requested information is "
                "contained in enterprise documents "
                "or policies."
            )
        )

    # -----------------------------------------------------
    # SQL ONLY
    # -----------------------------------------------------

    if (
        sql_required
        and not rag_required
    ):

        if calculator_required:

            return {
                "plan": [
                    {
                        "step": 1,
                        "tool": "sql",
                        "depends_on": [],
                        "reason": (
                            "SQL retrieves the required "
                            "structured business value."
                        ),
                    },
                    {
                        "step": 2,
                        "tool": "calculator",
                        "depends_on": [
                            "sql"
                        ],
                        "reason": (
                            "Calculator uses the value "
                            "returned by SQL."
                        ),
                    },
                ],
                "tools": [
                    "sql",
                    "calculator",
                ],
                "reason": (
                    "SQL retrieves the business value "
                    "and Calculator performs the calculation."
                ),
            }

        return sql_only_plan(
            reason=(
                "The requested structured business "
                "data is stored in the database."
            )
        )

    # -----------------------------------------------------
    # SQL + RAG
    # -----------------------------------------------------

    if (
        sql_required
        and rag_required
    ):

        plan = [
            {
                "step": 1,
                "tool": "sql",
                "depends_on": [],
                "reason": (
                    "SQL retrieves the required "
                    "structured business data."
                ),
            },
            {
                "step": 2,
                "tool": "rag",
                "depends_on": [],
                "reason": (
                    "RAG retrieves the required "
                    "policy or document information."
                ),
            },
        ]

        tools = [
            "sql",
            "rag",
        ]

        if calculator_required:

            plan.append(
                {
                    "step": 3,
                    "tool": "calculator",
                    "depends_on": [
                        "sql"
                    ],
                    "reason": (
                        "Calculator uses the sales "
                        "value returned by SQL."
                    ),
                }
            )

            tools.append(
                "calculator"
            )

        return {
            "plan": plan,
            "tools": tools,
            "reason": (
                "SQL and RAG retrieve independent "
                "enterprise information, while "
                "Calculator uses the required numerical result."
            ),
        }

    # -----------------------------------------------------
    # NO CLEAR DETERMINISTIC INTENT
    # -----------------------------------------------------

    return None


# =========================================================
# LLM PLANNER
# =========================================================

def create_plan(
    question: str,
) -> dict:

    if not question or not question.strip():
        raise ValueError(
            "Question cannot be empty."
        )

    # -----------------------------------------------------
    # First use deterministic planner.
    # -----------------------------------------------------

    deterministic_plan = (
        create_deterministic_plan(
            question
        )
    )

    if deterministic_plan:

        print(
            "[PLANNER] Deterministic plan selected."
        )

        print(
            f"[PLANNER] Tools: "
            f"{deterministic_plan['tools']}"
        )

        print(
            f"[PLANNER] Plan: "
            f"{deterministic_plan['plan']}"
        )

        return deterministic_plan

    # -----------------------------------------------------
    # LLM planner fallback
    # -----------------------------------------------------

    system_prompt = """
You are the planning component of EnterpriseIQ.

Your job is to analyze the user's question and
create a dependency-aware execution plan.

Available tools:

1. rag

Use for:

- enterprise documents
- policies
- discount policies
- contracts
- invoices
- manuals
- reports
- uploaded files
- payment due dates
- company/service descriptions
- knowledge-base information

IMPORTANT:

Discount policy ALWAYS belongs to RAG.

Examples:

"maximum standard discount"
"maximum discount allowed"
"discount policy"
"what discount is allowed"

These MUST use RAG.

Company/service information contained in
enterprise documents MUST use RAG.

2. sql

Use for structured business data such as:

- sales
- revenue
- orders
- customers
- transactions
- counts
- database records

3. calculator

Use for:

- mathematical calculations
- percentages
- arithmetic
- GST
- tax
- numerical computation

4. general

Use for normal conversation that does not
require enterprise data.

IMPORTANT RULES:

- Select ONLY tools actually required.
- Each tool should appear at most once.
- SQL and RAG can run independently.
- Calculator depends on SQL when it needs a SQL result.
- Calculator depends on RAG when it needs a document value.
- Do not create unnecessary dependencies.
- General cannot be combined with other tools.

CRITICAL ROUTING RULE:

If the question asks about a discount policy,
maximum discount, standard discount, or allowed
discount, use RAG and NEVER SQL.

The presence of words such as:

"customer"
"customers"

must NOT change a discount-policy question
into SQL.

CRITICAL ROUTING RULE:

Company/service descriptions from enterprise
documents must use RAG.

Sales/revenue/order database information
must use SQL.

Return ONLY valid JSON.

Required format:

{
    "plan": [
        {
            "step": 1,
            "tool": "rag",
            "depends_on": [],
            "reason": "The information is contained in enterprise documents."
        }
    ],
    "reason": "Only RAG is required."
}

Example:

Question:
What is the maximum standard discount allowed
for any customer?

Return:

{
    "plan": [
        {
            "step": 1,
            "tool": "rag",
            "depends_on": [],
            "reason": "The discount policy is contained in enterprise documents."
        }
    ],
    "reason": "Only RAG is required."
}

Question:
What was the Q2 sales?

Return:

{
    "plan": [
        {
            "step": 1,
            "tool": "sql",
            "depends_on": [],
            "reason": "Q2 sales are stored in the database."
        }
    ],
    "reason": "Only SQL is required."
}

Question:
What were Q2 West sales and what is the
maximum discount policy?

Return:

{
    "plan": [
        {
            "step": 1,
            "tool": "sql",
            "depends_on": [],
            "reason": "SQL retrieves Q2 West sales."
        },
        {
            "step": 2,
            "tool": "rag",
            "depends_on": [],
            "reason": "RAG retrieves the discount policy."
        }
    ],
    "reason": "SQL and RAG are independent."
}

Question:
What is 18% GST on 220000?

Return:

{
    "plan": [
        {
            "step": 1,
            "tool": "calculator",
            "depends_on": [],
            "reason": "The question requires a mathematical calculation."
        }
    ],
    "reason": "Only Calculator is required."
}

Question:
Hello, how are you?

Return:

{
    "plan": [
        {
            "step": 1,
            "tool": "general",
            "depends_on": [],
            "reason": "This is general conversation."
        }
    ],
    "reason": "No enterprise tool is required."
}
"""

    user_prompt = f"""
Create a dependency-aware execution plan
for this question:

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
        max_tokens=700,
    )

    data = extract_json(
        response.choices[0].message.content
    )

    plan = validate_plan(
        data.get(
            "plan"
        )
    )

    reason = data.get(
        "reason",
        "",
    )

    tools = [
        step["tool"]
        for step in plan
    ]

    return {
        "plan": plan,
        "tools": tools,
        "reason": str(reason),
    }