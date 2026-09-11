from typing import Literal

from typing_extensions import TypedDict


RouteType = Literal[
    "rag",
    "sql",
    "calculator",
    "general",
]


ToolType = Literal[
    "rag",
    "sql",
    "calculator",
    "general",
]


class AgentState(TypedDict, total=False):

    # -----------------------------------------
    # USER REQUEST
    # -----------------------------------------

    question: str

    # -----------------------------------------
    # USER CONTEXT
    # -----------------------------------------

    user_id: int

    user_role: str

    conversation_id: int | None

    # -----------------------------------------
    # ROUTING
    # -----------------------------------------

    route: RouteType

    route_confidence: float

    tools: list[ToolType]

    # -----------------------------------------
    # PLANNING
    # -----------------------------------------

    plan_reason: str

    plan: list[dict]

    current_tool_index: int

    # -----------------------------------------
    # TOOL RESULTS
    # -----------------------------------------

    tool_results: dict

    tool_result: str

    # -----------------------------------------
    # FINAL RESPONSE
    # -----------------------------------------

    answer: str

    sources: list[dict]

    # -----------------------------------------
    # ERROR
    # -----------------------------------------

    error: str | None

    # -----------------------------------------
    # SECURITY
    # -----------------------------------------

    security_checked: bool

    security_status: str

    security_message: str