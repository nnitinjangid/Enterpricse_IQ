from groq import Groq
from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from sqlalchemy.orm import Session

from app.agent.router import (
    classify_query,
)

from app.agent.state import (
    AgentState,
)

from app.core.config import settings

from app.services.calculator_service import (
    calculate,
)

from app.services.rag_service import (
    ask_rag,
)

from app.services.sql_service import (
    ask_sql,
)


# =========================================================
# Router Node
# =========================================================

def router_node(
    state: AgentState,
) -> AgentState:

    question = state["question"]

    result = classify_query(
        question
    )

    return {
        **state,
        "route": result["route"],
        "route_confidence": result[
            "confidence"
        ],
    }


# =========================================================
# RAG Node
# =========================================================

def rag_node(
    state: AgentState,
    db: Session,
) -> AgentState:

    result = ask_rag(
        question=state["question"],
        db=db,
        user_id=state["user_id"],
        top_k=5,
    )

    return {
        **state,
        "answer": result["answer"],
        "sources": result["sources"],
        "tool_result": result["answer"],
    }


# =========================================================
# SQL Answer Generator
# =========================================================

def generate_sql_answer(
    question: str,
    sql: str,
    results: list[dict],
) -> str:

    if not results:

        return (
            "No matching records were found "
            "in the business database."
        )

    result_text = "\n".join(
        str(row)
        for row in results
    )

    prompt = f"""
You are EnterpriseIQ.

Answer the user's question using ONLY
the SQL result provided below.

User question:
{question}

Executed SQL:
{sql}

SQL result:
{result_text}

Rules:

1. Do not invent data.
2. Use only the SQL result.
3. Keep the answer concise.
4. Clearly mention the important number/value.
5. If there are multiple rows, summarize them clearly.
"""

    client = Groq(
        api_key=settings.GROQ_API_KEY
    )

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an enterprise "
                    "business data assistant."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        max_tokens=500,
    )

    answer = response.choices[0].message.content

    if not answer:

        return (
            "The database returned data, "
            "but the answer could not be generated."
        )

    return answer.strip()


# =========================================================
# SQL Node
# =========================================================

def sql_node(
    state: AgentState,
    db: Session,
) -> AgentState:

    result = ask_sql(
        question=state["question"],
        db=db,
    )

    answer = generate_sql_answer(
        question=state["question"],
        sql=result["sql"],
        results=result["results"],
    )

    return {
        **state,
        "answer": answer,
        "tool_result": str(
            result["results"]
        ),
        "sources": [],
    }


# =========================================================
# Calculator Node
# =========================================================

def calculator_node(
    state: AgentState,
) -> AgentState:

    result = calculate(
        question=state["question"]
    )

    answer = (
        f"The result is "
        f"{result['formatted_result']}."
    )

    return {
        **state,
        "answer": answer,
        "tool_result": (
            f"Expression: "
            f"{result['expression']}; "
            f"Result: "
            f"{result['formatted_result']}"
        ),
        "sources": [],
    }


# =========================================================
# General Node
# =========================================================

def general_node(
    state: AgentState,
) -> AgentState:

    return {
        **state,
        "answer": (
            "General route selected."
        ),
    }


# =========================================================
# Route Decision
# =========================================================

def route_decision(
    state: AgentState,
) -> str:

    return state["route"]


# =========================================================
# Build Agent Graph
# =========================================================

def build_agent_graph(
    db: Session,
):

    graph = StateGraph(
        AgentState
    )

    graph.add_node(
        "router",
        router_node,
    )

    graph.add_node(
        "rag",
        lambda state: rag_node(
            state,
            db,
        ),
    )

    graph.add_node(
        "sql",
        lambda state: sql_node(
            state,
            db,
        ),
    )

    graph.add_node(
        "calculator",
        calculator_node,
    )

    graph.add_node(
        "general",
        general_node,
    )

    graph.add_edge(
        START,
        "router",
    )

    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "rag": "rag",
            "sql": "sql",
            "calculator": "calculator",
            "general": "general",
        },
    )

    graph.add_edge(
        "rag",
        END,
    )

    graph.add_edge(
        "sql",
        END,
    )

    graph.add_edge(
        "calculator",
        END,
    )

    graph.add_edge(
        "general",
        END,
    )

    return graph.compile()


# =========================================================
# Run Agent
# =========================================================

def run_agent(
    question: str,
    user_id: int,
    db: Session,
) -> AgentState:

    if not question or not question.strip():

        raise ValueError(
            "Question cannot be empty."
        )

    initial_state: AgentState = {
        "question": question.strip(),
        "user_id": user_id,
        "conversation_id": None,
        "route": "general",
        "route_confidence": 0.0,
        "answer": "",
        "tool_result": "",
        "sources": [],
        "error": None,
    }

    agent_graph = build_agent_graph(
        db
    )

    result = agent_graph.invoke(
        initial_state
    )

    return result