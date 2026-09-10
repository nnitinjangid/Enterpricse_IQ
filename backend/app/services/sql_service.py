import re
import time

from groq import Groq
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings


client = Groq(
    api_key=settings.GROQ_API_KEY
)


DATABASE_SCHEMA = """
Table: sales_records

Columns:

id              INTEGER
sale_date       DATE
region          VARCHAR
customer_name   VARCHAR
product_name    VARCHAR
quantity        INTEGER
unit_price      FLOAT
total_amount    FLOAT
created_at      DATETIME
"""


def extract_sql(
    text_response: str,
) -> str:

    if not text_response:
        return ""

    sql = text_response.strip()

    sql = re.sub(
        r"```sql\s*",
        "",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"```\s*$",
        "",
        sql,
        flags=re.IGNORECASE,
    )

    sql = sql.strip()

    # Remove accidental explanation before SELECT.
    select_match = re.search(
        r"\bSELECT\b",
        sql,
        flags=re.IGNORECASE,
    )

    if select_match:
        sql = sql[
            select_match.start():
        ]

    # Remove accidental text after a trailing code fence.
    sql = sql.split(
        "```",
        1
    )[0].strip()

    return sql


def validate_sql(
    sql: str,
) -> None:

    if not sql:
        raise ValueError(
            "Generated SQL is empty."
        )

    normalized = sql.strip().lower()

    if not normalized.startswith(
        "select"
    ):
        raise ValueError(
            "Only SELECT queries are allowed."
        )

    sql_without_trailing_semicolon = (
        normalized.rstrip(";").strip()
    )

    if ";" in sql_without_trailing_semicolon:
        raise ValueError(
            "Multiple SQL statements are not allowed."
        )

    blocked_keywords = [
        "insert ",
        "update ",
        "delete ",
        "drop ",
        "alter ",
        "truncate ",
        "create ",
        "replace ",
        "grant ",
        "revoke ",
        "execute ",
        "call ",
        "load ",
        "outfile",
        "infile",
    ]

    for keyword in blocked_keywords:

        if keyword in normalized:

            raise ValueError(
                "Unsafe SQL query detected."
            )

    if "sales_records" not in normalized:

        raise ValueError(
            "Query attempted to access an unauthorized table."
        )

    # -----------------------------------------------------
    # Basic completeness checks
    # -----------------------------------------------------

    if normalized.count("(") != normalized.count(")"):

        raise ValueError(
            "Generated SQL contains unbalanced parentheses."
        )

    if normalized.count("'") % 2 != 0:

        raise ValueError(
            "Generated SQL contains an unclosed string."
        )

    if normalized.count('"') % 2 != 0:

        raise ValueError(
            "Generated SQL contains an unclosed string."
        )

    # SQL should not end with an obviously incomplete clause.
    incomplete_endings = [
        "select",
        "from",
        "where",
        "and",
        "or",
        "in",
        "on",
        "join",
        "group by",
        "order by",
        "having",
        "limit",
        ",",
        "(",
    ]

    stripped = normalized.rstrip(";").strip()

    for ending in incomplete_endings:

        if stripped.endswith(
            ending
        ):

            raise ValueError(
                "Generated SQL appears to be incomplete."
            )


def build_fallback_sql(
    question: str,
) -> str | None:

    if not question or not question.strip():

        return None

    question_lower = question.lower()

    region = None

    region_matches = [
        "west",
        "north",
        "south",
        "east",
    ]

    for candidate in region_matches:

        if candidate in question_lower:

            region = candidate.title()

            break

    # -----------------------------------------------------
    # Q2
    # -----------------------------------------------------

    if (
        "q2" in question_lower
        or "second quarter" in question_lower
    ):

        if region:

            return (
                "SELECT "
                "SUM(total_amount) AS total_sales "
                "FROM sales_records "
                f"WHERE region = '{region}' "
                "AND sale_date >= '2026-04-01' "
                "AND sale_date < '2026-07-01'"
            )

        return (
            "SELECT "
            "SUM(total_amount) AS total_sales "
            "FROM sales_records "
            "WHERE sale_date >= '2026-04-01' "
            "AND sale_date < '2026-07-01'"
        )

    # -----------------------------------------------------
    # Q1
    # -----------------------------------------------------

    if (
        "q1" in question_lower
        or "first quarter" in question_lower
    ):

        if region:

            return (
                "SELECT "
                "SUM(total_amount) AS total_sales "
                "FROM sales_records "
                f"WHERE region = '{region}' "
                "AND sale_date >= '2026-01-01' "
                "AND sale_date < '2026-04-01'"
            )

        return (
            "SELECT "
            "SUM(total_amount) AS total_sales "
            "FROM sales_records "
            "WHERE sale_date >= '2026-01-01' "
            "AND sale_date < '2026-04-01'"
        )

    # -----------------------------------------------------
    # Q3
    # -----------------------------------------------------

    if (
        "q3" in question_lower
        or "third quarter" in question_lower
    ):

        if region:

            return (
                "SELECT "
                "SUM(total_amount) AS total_sales "
                "FROM sales_records "
                f"WHERE region = '{region}' "
                "AND sale_date >= '2026-07-01' "
                "AND sale_date < '2026-10-01'"
            )

        return (
            "SELECT "
            "SUM(total_amount) AS total_sales "
            "FROM sales_records "
            "WHERE sale_date >= '2026-07-01' "
            "AND sale_date < '2026-10-01'"
        )

    # -----------------------------------------------------
    # Q4
    # -----------------------------------------------------

    if (
        "q4" in question_lower
        or "fourth quarter" in question_lower
    ):

        if region:

            return (
                "SELECT "
                "SUM(total_amount) AS total_sales "
                "FROM sales_records "
                f"WHERE region = '{region}' "
                "AND sale_date >= '2026-10-01' "
                "AND sale_date < '2027-01-01'"
            )

        return (
            "SELECT "
            "SUM(total_amount) AS total_sales "
            "FROM sales_records "
            "WHERE sale_date >= '2026-10-01' "
            "AND sale_date < '2027-01-01'"
        )

    # -----------------------------------------------------
    # Generic sales total
    # -----------------------------------------------------

    sales_keywords = [
        "sales",
        "revenue",
        "total sales",
        "total revenue",
    ]

    if any(
        keyword in question_lower
        for keyword in sales_keywords
    ):

        if region:

            return (
                "SELECT "
                "SUM(total_amount) AS total_sales "
                "FROM sales_records "
                f"WHERE region = '{region}'"
            )

        return (
            "SELECT "
            "SUM(total_amount) AS total_sales "
            "FROM sales_records"
        )

    return None


def generate_sql(
    question: str,
) -> str:

    if not question or not question.strip():

        raise ValueError(
            "Question cannot be empty."
        )

    system_prompt = f"""
You are the SQL generation tool for EnterpriseIQ.

Your ONLY job is to generate the SQL query required
to retrieve structured business data from MySQL.

Database schema:

{DATABASE_SCHEMA}

STRICT RULES:

1. Return ONLY SQL.
2. Generate ONLY ONE SELECT query.
3. Never generate INSERT.
4. Never generate UPDATE.
5. Never generate DELETE.
6. Never generate DROP.
7. Never generate ALTER.
8. Never generate CREATE.
9. Never access tables other than sales_records.
10. Use MySQL syntax.
11. Use SUM(total_amount) for sales/revenue totals.
12. Use COUNT(*) for record counts.
13. Use AVG(total_amount) for average sales.
14. Use sale_date for date filtering.
15. Use region for regional filtering.
16. Use exact column names from the schema.
17. Do not use markdown.
18. Do not include explanations.
19. Do not perform mathematical calculations that belong
    to the Calculator tool.
20. If the question asks for a percentage/discount calculation,
    return ONLY the underlying database value needed for
    that calculation.
21. NEVER return an incomplete query.
22. Always finish the SQL query.
23. Prefer simple SQL.
24. For quarters, use explicit date ranges instead of
    MONTH(... ) IN (...).
"""

    user_prompt = f"""
Generate ONLY the SQL required to retrieve the
structured database information for this question:

{question.strip()}

IMPORTANT:

The question may contain multiple requirements.

For example:

"What were Q2 West sales, what is the discount policy,
and what would a 10% discount on those sales be?"

You must generate ONLY the SQL needed to retrieve:

Q2 West sales.

Do NOT calculate the 10% discount.

Do NOT include Calculator logic.

Do NOT include document-policy logic.

Return exactly ONE complete SELECT query.
"""

    for attempt in range(2):

        try:

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

            content = (
                response.choices[0]
                .message
                .content
            )

            sql = extract_sql(
                content
            )

            if not sql:

                print(
                    "[SQL] "
                    f"Empty response on attempt "
                    f"{attempt + 1}."
                )

            else:

                try:

                    validate_sql(
                        sql
                    )

                    print(
                        "[SQL] "
                        f"Generated successfully on attempt "
                        f"{attempt + 1}."
                    )

                    print(
                        f"[SQL] Query: {sql}"
                    )

                    return sql

                except ValueError as validation_error:

                    print(
                        "[SQL] "
                        f"Invalid generated SQL on attempt "
                        f"{attempt + 1}: "
                        f"{validation_error}"
                    )

                    print(
                        f"[SQL] Invalid query: {sql}"
                    )

        except Exception as e:

            print(
                "[SQL] "
                f"Generation attempt {attempt + 1} "
                f"failed: {e}"
            )

        if attempt == 0:

            time.sleep(0.5)

    # -----------------------------------------------------
    # Deterministic fallback
    # -----------------------------------------------------

    fallback_sql = build_fallback_sql(
        question
    )

    if fallback_sql:

        validate_sql(
            fallback_sql
        )

        print(
            "[SQL] "
            "LLM returned invalid/incomplete SQL. "
            "Using deterministic fallback SQL."
        )

        print(
            f"[SQL] Fallback query: {fallback_sql}"
        )

        return fallback_sql

    raise ValueError(
        "SQL generator returned an invalid or empty "
        "response and no fallback SQL could be generated."
    )


def execute_sql(
    sql: str,
    db: Session,
) -> list[dict]:

    validate_sql(
        sql
    )

    try:

        result = db.execute(
            text(sql)
        )

        rows = result.mappings().all()

        return [
            dict(row)
            for row in rows
        ]

    except Exception as e:

        raise RuntimeError(
            f"SQL execution failed: {str(e)}"
        )


def ask_sql(
    question: str,
    db: Session,
) -> dict:

    sql = generate_sql(
        question
    )

    results = execute_sql(
        sql=sql,
        db=db,
    )

    return {
        "question": question.strip(),
        "sql": sql,
        "results": results,
    }