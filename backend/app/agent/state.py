from typing import Literal

from typing_extensions import TypedDict


RouteType = Literal[
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

    answer: str

    tool_result: str

    sources: list[dict]

    error: str | None