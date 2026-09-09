import re

from groq import Groq
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings


client = Groq(
    api_key=settings.GROQ_API_KEY
)


# =========================================================
# Database Schema
# =========================================================

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
# SQL Extraction
# =========================================================

def extract_sql(
    text_response: str,
) -> str:

    if not text_response:
        raise ValueError(
            "SQL generator returned an empty response."
        )

    sql = text_response.strip()

    # Remove markdown code fences
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

    return sql


# =========================================================
# SQL Safety Validation
# =========================================================

def validate_sql(
    sql: str,
) -> None:

    if not sql:
        raise ValueError(
            "Generated SQL is empty."
        )

    normalized = sql.strip().lower()

    # Only SELECT statements are allowed
    if not normalized.startswith("select"):
        raise ValueError(
            "Only SELECT queries are allowed."
        )

    # Prevent multiple statements
    if ";" in normalized.rstrip(";"):
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

    # Only allow our known table
    if "sales_records" not in normalized:

        raise ValueError(
            "Query attempted to access an unauthorized table."
        )


# =========================================================
# Generate SQL
# =========================================================

def generate_sql(
    question: str,
) -> str:

    if not question or not question.strip():

        raise ValueError(
            "Question cannot be empty."
        )

    system_prompt = f"""
You are the SQL generation tool for EnterpriseIQ.

Your job is to convert the user's natural language
question into a MySQL SELECT query.

Database schema:

{DATABASE_SCHEMA}

STRICT RULES:

1. Return ONLY SQL.
2. Generate ONLY SELECT queries.
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
17. Do not use markdown code fences.
"""

    user_prompt = f"""
Generate SQL for this question:

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
        max_tokens=500,
    )

    sql = extract_sql(
        response.choices[0].message.content
    )

    validate_sql(
        sql
    )

    return sql


# =========================================================
# Execute SQL
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
# SQL Tool
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