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

    question: str

    user_id: int

    conversation_id: int | None

    route: RouteType

    route_confidence: float

    tools: list[ToolType]

    plan_reason: str

    plan: list[dict]

    current_tool_index: int

    tool_results: dict

    answer: str

    tool_result: str

    sources: list[dict]

    error: str | None

    security_checked: bool

    security_status: str

    security_message: str