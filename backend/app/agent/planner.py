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


def extract_json(
    text: str,
) -> dict:

    if not text:
        raise ValueError(
            "Planner returned an empty response."
        )

    text = text.strip()

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

        match = re.search(
            r"\{.*\}",
            text,
            flags=re.DOTALL,
        )

        if not match:

            raise ValueError(
                "Planner did not return valid JSON."
            )

        try:

            return json.loads(
                match.group(0)
            )

        except json.JSONDecodeError:

            raise ValueError(
                "Planner returned malformed JSON."
            )


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

    # -------------------------------------------------
    # Ensure step numbering is sequential.
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Sort by step number.
    # -------------------------------------------------

    validated_plan.sort(
        key=lambda item: item["step"]
    )

    # -------------------------------------------------
    # Validate dependency ordering.
    # A dependency must appear in an earlier step.
    # -------------------------------------------------

    completed_tools = set()

    for step in validated_plan:

        for dependency in step["depends_on"]:

            if dependency not in completed_tools:

                raise ValueError(
                    f"Dependency '{dependency}' "
                    f"must execute before '{step['tool']}'."
                )

        completed_tools.add(
            step["tool"]
        )

    # -------------------------------------------------
    # General cannot be combined with other tools.
    # -------------------------------------------------

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


def create_plan(
    question: str,
) -> dict:

    if not question or not question.strip():

        raise ValueError(
            "Question cannot be empty."
        )

    system_prompt = """
You are the planning component of EnterpriseIQ.

Your job is to analyze the user's question and
create a dependency-aware execution plan.

Available tools:

1. rag
   Use for enterprise documents, policies,
   contracts, invoices, manuals, reports,
   uploaded files, and knowledge-base information.

2. sql
   Use for structured business data such as
   sales, revenue, orders, customers,
   transactions, counts, and database records.

3. calculator
   Use for mathematical calculations,
   percentages, arithmetic, totals,
   conversions, and numerical computation.

4. general
   Use for normal conversation that does not
   require enterprise data.

IMPORTANT:

- You can select MORE THAN ONE tool.
- Select ONLY tools actually required.
- Each tool should appear at most once.
- Create an execution order.
- Use depends_on when one tool requires the result
  of another tool.
- SQL should run before Calculator when Calculator
  needs a value returned by SQL.
- RAG should run before Calculator when Calculator
  needs a value returned by RAG.
- SQL and RAG can run independently when neither
  depends on the other.
- Calculator should depend on SQL when the user says
  "that amount", "that total", "those sales", etc.
- Do not create unnecessary dependencies.
- General cannot be combined with other tools.

Return ONLY valid JSON.

Required format:

{
    "plan": [
        {
            "step": 1,
            "tool": "sql",
            "depends_on": [],
            "reason": "Sales data is required from the database."
        },
        {
            "step": 2,
            "tool": "calculator",
            "depends_on": ["sql"],
            "reason": "The calculation depends on the sales amount returned by SQL."
        }
    ],
    "reason": "SQL retrieves the sales amount and Calculator uses that amount."
}

Example 1:

Question:
What was the Q2 sales for the West region?

Return:
{
    "plan": [
        {
            "step": 1,
            "tool": "sql",
            "depends_on": [],
            "reason": "Q2 West sales are stored in the database."
        }
    ],
    "reason": "Only SQL is required."
}

Example 2:

Question:
What is the maximum standard discount allowed?

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

Example 3:

Question:
What were Q2 West sales and what is the maximum discount policy?

Return:
{
    "plan": [
        {
            "step": 1,
            "tool": "sql",
            "depends_on": [],
            "reason": "SQL is required to retrieve Q2 West sales."
        },
        {
            "step": 2,
            "tool": "rag",
            "depends_on": [],
            "reason": "RAG is required to retrieve the discount policy."
        }
    ],
    "reason": "SQL and RAG are independent and can execute without depending on each other."
}

Example 4:

Question:
What were Q2 West sales and what would a 10% discount on that amount be?

Return:
{
    "plan": [
        {
            "step": 1,
            "tool": "sql",
            "depends_on": [],
            "reason": "SQL retrieves the Q2 West sales amount."
        },
        {
            "step": 2,
            "tool": "calculator",
            "depends_on": ["sql"],
            "reason": "Calculator needs the sales amount returned by SQL."
        }
    ],
    "reason": "The calculator depends on the SQL result."
}

Example 5:

Question:
What were Q2 West sales, what is the discount policy,
and what would a 10% discount on those sales be?

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
        },
        {
            "step": 3,
            "tool": "calculator",
            "depends_on": ["sql"],
            "reason": "Calculator uses the sales amount returned by SQL."
        }
    ],
    "reason": "SQL and RAG provide the required information and Calculator uses the SQL amount."
}

Example 6:

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

Example 7:

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