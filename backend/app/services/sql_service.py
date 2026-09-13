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


# =========================================================
# SQL EXTRACTION
# =========================================================

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

    # Remove anything after code fence.
    sql = sql.split(
        "```",
        1
    )[0].strip()

    return sql


# =========================================================
# SQL VALIDATION
# =========================================================

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

    # Basic completeness checks.

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


# =========================================================
# RECORD COUNT DETECTION
# =========================================================

def is_record_count_question(
    question: str,
) -> bool:
    """
    Return True only when the user explicitly asks
    for a record count.
    """

    if not question:
        return False

    question_lower = question.lower()

    count_phrases = [
        "how many records",
        "how many sales records",
        "number of records",
        "number of sales records",
        "count of records",
        "count of sales records",
        "record count",
        "sales record count",
        "how many sales are there",
        "how many sales were there",
    ]

    return any(
        phrase in question_lower
        for phrase in count_phrases
    )


# =========================================================
# YEAR EXTRACTION
# =========================================================

def extract_year(
    question: str,
) -> int:
    """
    Extract an explicit 4-digit year from the question.

    If no year is provided, EnterpriseIQ currently uses
    2026 as the default business-data year.
    """

    if not question:
        return 2026

    year_match = re.search(
        r"\b(20\d{2})\b",
        question,
    )

    if year_match:

        return int(
            year_match.group(1)
        )

    return 2026


# =========================================================
# QUARTER DATE RANGE
# =========================================================

def get_quarter_dates(
    question: str,
) -> tuple[str, str] | None:

    if not question:
        return None

    question_lower = question.lower()

    year = extract_year(
        question
    )

    if (
        "q1" in question_lower
        or "first quarter" in question_lower
    ):

        return (
            f"{year}-01-01",
            f"{year}-04-01",
        )

    if (
        "q2" in question_lower
        or "second quarter" in question_lower
    ):

        return (
            f"{year}-04-01",
            f"{year}-07-01",
        )

    if (
        "q3" in question_lower
        or "third quarter" in question_lower
    ):

        return (
            f"{year}-07-01",
            f"{year}-10-01",
        )

    if (
        "q4" in question_lower
        or "fourth quarter" in question_lower
    ):

        return (
            f"{year}-10-01",
            f"{year + 1}-01-01",
        )

    return None


# =========================================================
# REGION EXTRACTION
# =========================================================

def extract_region(
    question: str,
) -> str | None:

    if not question:
        return None

    question_lower = question.lower()

    regions = [
        "west",
        "north",
        "south",
        "east",
    ]

    for region in regions:

        if re.search(
            rf"\b{region}\b",
            question_lower,
        ):

            return region.title()

    return None


# =========================================================
# FALLBACK SQL BUILDER
# =========================================================

def build_fallback_sql(
    question: str,
) -> str | None:

    if not question or not question.strip():

        return None

    question_lower = question.lower()

    region = extract_region(
        question
    )

    quarter_dates = get_quarter_dates(
        question
    )

    # -----------------------------------------------------
    # Explicit record-count questions
    # -----------------------------------------------------

    if is_record_count_question(
        question
    ):

        if quarter_dates:

            start_date, end_date = (
                quarter_dates
            )

            if region:

                return (
                    "SELECT COUNT(*) AS total_records "
                    "FROM sales_records "
                    f"WHERE region = '{region}' "
                    f"AND sale_date >= '{start_date}' "
                    f"AND sale_date < '{end_date}'"
                )

            return (
                "SELECT COUNT(*) AS total_records "
                "FROM sales_records "
                f"WHERE sale_date >= '{start_date}' "
                f"AND sale_date < '{end_date}'"
            )

        if region:

            return (
                "SELECT COUNT(*) AS total_records "
                "FROM sales_records "
                f"WHERE region = '{region}'"
            )

        return (
            "SELECT COUNT(*) AS total_records "
            "FROM sales_records"
        )

    # -----------------------------------------------------
    # Quarterly sales
    # -----------------------------------------------------

    if quarter_dates:

        start_date, end_date = (
            quarter_dates
        )

        if region:

            return (
                "SELECT "
                "SUM(total_amount) AS total_sales "
                "FROM sales_records "
                f"WHERE region = '{region}' "
                f"AND sale_date >= '{start_date}' "
                f"AND sale_date < '{end_date}'"
            )

        return (
            "SELECT "
            "SUM(total_amount) AS total_sales "
            "FROM sales_records "
            f"WHERE sale_date >= '{start_date}' "
            f"AND sale_date < '{end_date}'"
        )

    # -----------------------------------------------------
    # Generic sales/revenue total
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


# =========================================================
# DETERMINISTIC SALES INTENT
# =========================================================

def has_deterministic_sales_intent(
    question: str,
) -> bool:

    if not question:
        return False

    question_lower = question.lower()

    has_sales_intent = any(
        keyword in question_lower
        for keyword in [
            "sales",
            "revenue",
        ]
    )

    has_amount_intent = any(
        phrase in question_lower
        for phrase in [
            "total sales",
            "total revenue",
            "sales amount",
            "sales value",
            "revenue amount",
            "total sales records",
            "sales for",
            "revenue for",
        ]
    )

    explicit_count = (
        is_record_count_question(
            question
        )
    )

    return (
        has_sales_intent
        and has_amount_intent
        and not explicit_count
    )


# =========================================================
# SQL GENERATION
# =========================================================

def generate_sql(
    question: str,
) -> str:

    if not question or not question.strip():

        raise ValueError(
            "Question cannot be empty."
        )

    question_lower = question.lower()

    # -----------------------------------------------------
    # IMPORTANT:
    # If question clearly asks for sales/revenue amount,
    # never allow the LLM to invent dates.
    #
    # This guarantees:
    # Q2 2026 -> 2026-04-01 to 2026-07-01
    # -----------------------------------------------------

    if has_deterministic_sales_intent(
        question
    ):

        fallback_sql = build_fallback_sql(
            question
        )

        if fallback_sql:

            validate_sql(
                fallback_sql
            )

            print(
                "[SQL] Deterministic sales-amount "
                "routing applied."
            )

            print(
                f"[SQL] Query: {fallback_sql}"
            )

            return fallback_sql

    # -----------------------------------------------------
    # LLM SQL generation
    # -----------------------------------------------------

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
12. Use COUNT(*) ONLY when the user explicitly asks
    for a count or number of records.
13. "Total sales records" means total sales amount
    unless the question explicitly asks for count.
14. Use AVG(total_amount) for average sales.
15. Use sale_date for date filtering.
16. Use region for regional filtering.
17. Use exact column names from the schema.
18. Do not use markdown.
19. Do not include explanations.
20. Do not perform calculations that belong to Calculator.
21. If the question asks for a percentage calculation,
    return only the underlying database value.
22. Never generate SQL for document policies.
23. Never generate SQL for discount policies.
24. Never generate SQL for enterprise documents.
25. For quarters, use the exact year mentioned by the user.
26. If no year is mentioned, use 2026.
27. Q2 means April 1 through July 1.
28. Q1 means January 1 through April 1.
29. Q3 means July 1 through October 1.
30. Q4 means October 1 through January 1 of next year.
31. Always finish the SQL query.
32. Prefer simple SQL.
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

If the question contains an explicit year,
use that exact year.

If the question says Q2 2026, the date range MUST be:

sale_date >= '2026-04-01'
AND sale_date < '2026-07-01'
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

            time.sleep(
                0.5
            )

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


# =========================================================
# SQL EXECUTION
# =========================================================

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


# =========================================================
# ASK SQL
# =========================================================

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